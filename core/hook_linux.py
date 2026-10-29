"""Linux X11 全局热键后端：XGrabKey（组合键）+ XRecord（三次空格）。

对应 Windows 的 WH_KEYBOARD_LL 与 macOS 的 CGEventTap，判定逻辑
复用 core/hotkey_engine（平台无关），这里只做 X11 的事件翻译。

X11 的关键结构（与 Windows/macOS 都不同，必须分开两条线）：
- 组合键用 XGrabKey：XRecord 只能旁观、不能吞键；只有把组合键
  抓到根窗口（owner_events=False），按键才只发给本进程、不落到
  目标程序——“吞键”就是抓过来自己处理、不再转发，不需要像
  macOS 那样返回 NULL。抓键时把 NumLock/CapsLock 的四种组合都
  抓一遍，否则 NumLock 开着时热键会失灵。
- 三次空格用 XRecord：空格必须落到目标程序（不能抓），所以只
  旁观全量按键事件，喂给引擎计数；Record 线程看到组合键时直接
  跳过（matches_combo），只留给 Grab 线程触发，否则同一按键会被
  两个线程各喂一次，触发权会被先喂的抢走。
- 键码：X11 键码随键盘/布局而变（不像 macOS 的 ANSI 固定码），
  必须经服务器键表换算：keycode → keysym（index 0，非移位）→
  名字（'q'→'Q'、'space'→'Space'）；修饰键掩码也必须查
  get_modifier_mapping（Alt 不一定是 Mod1），不能写死 Mod1。
- Wayland：明确不支持。Wayland 会话下即使 DISPLAY 存在（XWayland）
  也只能看到 X11 程序，看不到原生 Wayland 程序，半吊子支持不如
  直接拒绝并明说（登录时选 X11 会话）。
- 剪贴板：走 pyperclip（需 xclip 或 xsel；缺失时流程优雅失败并
  提示安装命令，不崩溃）。X11 原生 selection 协议是异步的，
  首版不手写（见 replacer_linux）。

本模块 import 在任何平台都不崩（Xlib 用 try 懒导，找不到时
start() 直接失败）；只有 Linux + X11 会话上 start() 才会真正建连接。
沙箱无 X 服务器，真实行为只能在 X11 真机上验。
"""

import os
import threading
import time
from typing import Callable, Dict, FrozenSet, Optional

from core.hotkey_engine import HotkeyEngine
from core.hotkeys import normalize_hotkeys, parse_hotkey
from core.logging import error as _log_error, info as _log_info, debug as _log_debug

try:
    from Xlib import X, XK, display as _xdisplay
    from Xlib.ext import record as _xrecord
    from Xlib.ext import xtest as _xtest  # noqa: F401（注册 xtest_fake_input）
    from Xlib.protocol import rq as _xrq
    _XLIB_AVAILABLE = True
except Exception:
    X = None
    XK = None
    _xdisplay = None
    _xrecord = None
    _xrq = None
    _XLIB_AVAILABLE = False


# ---- 纯函数（可单测，无需 X 服务器） ----
def keysym_string_to_main_key(sym: Optional[str]) -> str:
    """keysym 字符串 → 引擎主键名。未知返回 '__unknown__'（引擎按
    “其他主键”处理：清空格计数、放行、不触发）。"""
    if not sym:
        return "__unknown__"
    if len(sym) == 1:
        return sym.upper()
    if sym == "space":
        return "Space"
    return sym


def state_to_mods(state: int, mod_map: Dict[str, int]) -> FrozenSet[str]:
    """X 事件 state 位掩码 → 修饰键集合（只认 Alt/Ctrl/Shift；
    Lock/NumLock 位自动忽略，抓键的四种变体因此都能对上引擎表——
    这里若把 NumLock 也放进结果，引擎严格相等就对不上，NumLock
    开着时组合键反而触发不了，正是抓变体的意义所在）。"""
    mods = set()
    for name in ("Alt", "Ctrl", "Shift"):
        mask = mod_map.get(name, 0)
        if mask and (state & mask):
            mods.add(name)
    return frozenset(mods)


def build_modifier_map(get_mapping, keycode_to_keysym) -> Dict[str, int]:
    """从服务器修饰键表算出 Alt/Ctrl/Shift 各自的位掩码。

    get_mapping：() -> 8 个 keycode 列表（index 0=Shift,1=Lock,
    2=Control,3=Mod1,4=Mod2,5=Mod3,6=Mod4,7=Mod5）。
    keycode_to_keysym：(keycode, index) -> keysym 整数。
    找不到时返回 0（该修饰键永远不匹配，热键按缺失处理，不崩溃）。
    """
    alt_keysyms = {0xFFE9, 0xFFEA}  # Alt_L, Alt_R
    ctrl_keysyms = {0xFFE3, 0xFFE4}  # Control_L, Control_R
    shift_keysyms = {0xFFE1, 0xFFE2}  # Shift_L, Shift_R
    numlock_keysyms = {0xFF7F}  # Num_Lock
    result = {"Alt": 0, "Ctrl": 0, "Shift": 0, "NumLock": 0}
    try:
        mapping = get_mapping()
    except Exception:
        return result
    for index, keycodes in enumerate(mapping):
        mask = 1 << index
        for kc in keycodes:
            try:
                sym = keycode_to_keysym(kc, 0)
            except Exception:
                continue
            if sym in alt_keysyms and not result["Alt"]:
                result["Alt"] = mask
            elif sym in ctrl_keysyms and not result["Ctrl"]:
                result["Ctrl"] = mask
            elif sym in shift_keysyms and not result["Shift"]:
                result["Shift"] = mask
            elif sym in numlock_keysyms and not result["NumLock"]:
                result["NumLock"] = mask
    return result


def _keysym_name_to_keysym(name: str) -> int:
    """配置主键名 → keysym 整数（抓键与合成按键共用）。"""
    if name == "Space":
        text = "space"
    elif len(name) == 1 and name.isalpha():
        text = name.lower()
    else:
        text = name
    return XK.string_to_keysym(text)


class LinuxKeyboardHook:
    """Linux X11 全局热键钩子（接口对标 MacKeyboardHook 的子集）。"""

    def __init__(
        self,
        on_triple_space: Optional[Callable[[], None]] = None,
        on_selection_translate: Optional[Callable[[], None]] = None,
        on_screenshot_translate: Optional[Callable[[], None]] = None,
        on_voice_input: Optional[Callable[[], None]] = None,
        on_open_main: Optional[Callable[[], None]] = None,
        max_interval: float = 0.75,
        hotkeys=None,
    ):
        self._callbacks: Dict[str, Callable[[], None]] = {}
        if on_triple_space is not None:
            self._callbacks["triple_space"] = on_triple_space
        if on_selection_translate is not None:
            self._callbacks["selection"] = on_selection_translate
        if on_screenshot_translate is not None:
            self._callbacks["screenshot"] = on_screenshot_translate
        if on_voice_input is not None:
            self._callbacks["voice"] = on_voice_input
        if on_open_main is not None:
            self._callbacks["workbench"] = on_open_main
        self._engine = HotkeyEngine(
            self._actions_from_hotkeys(hotkeys), max_interval=max_interval
        )
        self._grab_display = None
        self._grab_thread: Optional[threading.Thread] = None
        self._record_thread: Optional[threading.Thread] = None
        self._running = False
        self._gen = 0  # 世代：stop/start 后旧 Record 线程的回调直接失效
        self.last_error = ""

    def _actions_from_hotkeys(self, hotkeys):
        normalized = normalize_hotkeys(hotkeys)
        actions = []
        for action, text in normalized.items():
            if action not in self._callbacks:
                continue  # 没回调的动作不进表，组合键直接放行（不吞键）
            parsed = parse_hotkey(text)
            if parsed is None:
                continue
            mods, _vk, normalized_text = parsed
            main = normalized_text.split("+")[-1]
            actions.append((action, frozenset(mods), main))
        return actions

    def update_hotkeys(self, hotkeys):
        self._engine.update_actions(self._actions_from_hotkeys(hotkeys))

    def set_replace_busy_check(self, fn):
        """接线替换器的忙查询：替换进行中，引擎吞掉溢出空格。"""
        self._engine.busy_check = fn
        # Record 线程读引擎表是实时的（matches_combo/handle_key_down
        # 都在锁内读当前表），改键即时生效；但 Grab 是 X 服务端状态，
        # 旧组合键仍被抓着（白白吞掉）、新组合键根本抓不到，所以钩子
        # 在跑时必须立即重建抓键线程（关旧连接唤醒旧循环、开新连接
        # 按新表抓键；Record 线程不受影响，不用重启）。
        if self._running:
            self._restart_grab()

    def _restart_grab(self):
        old_dpy = self._grab_display
        old_thread = self._grab_thread
        self._grab_display = None
        self._grab_thread = None
        if old_dpy is not None:
            try:
                old_dpy.close()
            except Exception:
                pass
        if old_thread is not None and old_thread.is_alive():
            old_thread.join(timeout=2.0)
        if not self._running:
            return
        try:
            new_dpy = _xdisplay.Display()
        except Exception as e:
            _log_error("HOOK", f"linux re-grab connect failed: {e}")
            return
        self._grab_display = new_dpy
        self._grab_thread = threading.Thread(
            target=self._grab_loop, args=(new_dpy, self._gen), daemon=True
        )
        self._grab_thread.start()

    @property
    def max_interval(self) -> float:
        return self._engine.max_interval

    @max_interval.setter
    def max_interval(self, value: float):
        self._engine.max_interval = value

    def is_running(self) -> bool:
        return self._running and self._grab_display is not None

    # ---- 键码 / 修饰键换算（需一个已连接的 display） ----
    def _keycode_to_main_key(self, dpy, keycode: int) -> str:
        try:
            sym = dpy.keycode_to_keysym(keycode, 0)
            text = XK.keysym_to_string(sym) if sym else None
        except Exception:
            text = None
        return keysym_string_to_main_key(text)

    def _mod_map(self, dpy) -> Dict[str, int]:
        return build_modifier_map(dpy.get_modifier_mapping, dpy.keycode_to_keysym)

    # ---- 启动 / 停止 ----
    def start(self) -> bool:
        if self._running:
            return True
        self.last_error = ""
        if not _XLIB_AVAILABLE:
            self.last_error = "python-xlib 未安装（Linux 包应自带；请检查安装）"
            _log_error("HOOK", f"linux hook unavailable: {self.last_error}")
            return False
        if os.environ.get("WAYLAND_DISPLAY") or os.environ.get("XDG_SESSION_TYPE") == "wayland":
            self.last_error = (
                "Wayland 会话不支持全局热键（仅 X11；请在登录时选择 X11 会话）"
            )
            _log_error("HOOK", f"linux hook refused: {self.last_error}")
            return False
        if not os.environ.get("DISPLAY"):
            self.last_error = "无 X 显示（DISPLAY 未设置）"
            _log_error("HOOK", f"linux hook unavailable: {self.last_error}")
            return False
        try:
            grab_dpy = _xdisplay.Display()
        except Exception as e:
            self.last_error = f"无法连接 X 服务器：{e}"
            _log_error("HOOK", f"linux hook connect failed: {self.last_error}")
            return False
        self._grab_display = grab_dpy
        self._running = True
        self._gen += 1
        gen = self._gen
        self._grab_thread = threading.Thread(
            target=self._grab_loop, args=(grab_dpy, gen), daemon=True
        )
        self._grab_thread.start()
        self._record_thread = threading.Thread(
            target=self._record_loop, args=(gen,), daemon=True
        )
        self._record_thread.start()
        _log_info("HOOK", "linux X11 hook started (grab + record)")
        return True

    def stop(self):
        if not self._running and self._grab_thread is None:
            return
        self._running = False
        self._gen += 1  # 旧 Record 线程回调立即失效（不再喂引擎）
        grab_dpy = self._grab_display
        self._grab_display = None
        if grab_dpy is not None:
            try:
                grab_dpy.close()  # 唤醒阻塞的 next_event（抛异常退出循环）
            except Exception:
                pass
        if self._grab_thread is not None and self._grab_thread.is_alive():
            self._grab_thread.join(timeout=2.0)
        # Record 线程在下一个按键事件到达时自行 disable 并退出；
        # 进程退出时 daemon 线程随之结束，不阻塞界面。
        self._grab_thread = None
        self._record_thread = None
        _log_info("HOOK", "linux X11 hook stopped")

    # ---- Grab 线程：组合键（抓过来 = 吞键） ----
    def _grab_loop(self, dpy, gen: int):
        try:
            root = dpy.screen().root
            mod_map = self._mod_map(dpy)
            combos = []  # (keycode, base_mask)
            for action, mods, main in self._engine._table:
                try:
                    keysym = _keysym_name_to_keysym(main)
                    keycode = dpy.keysym_to_keycode(keysym)
                except Exception:
                    keycode = 0
                if not keycode:
                    _log_debug("HOOK", f"linux grab skip {action}: no keycode for {main}")
                    continue
                mask = 0
                for m in mods:
                    mask |= mod_map.get(m, 0)
                combos.append((keycode, mask))
            lock_mask = 2  # LockMask（CapsLock）
            numlock_mask = mod_map.get("NumLock") or 16  # Mod2Mask 兜底
            for keycode, mask in combos:
                for extra in (0, lock_mask, numlock_mask, lock_mask | numlock_mask):
                    try:
                        root.grab_key(keycode, mask | extra, False, X.GrabModeAsync, X.GrabModeAsync)
                    except Exception as e:
                        _log_debug("HOOK", f"linux grab_key failed kc={keycode} mask={mask|extra}: {e}")
            root.change_attributes(event_mask=X.KeyPressMask | X.KeyReleaseMask)
            dpy.flush()
            while self._running and gen == self._gen:
                try:
                    event = dpy.next_event()
                except Exception:
                    break  # display 已关（stop）或连接断了
                if event.type == X.KeyPress:
                    name = self._keycode_to_main_key(dpy, event.detail)
                    mods = state_to_mods(event.state, mod_map)
                    action, _swallow = self._engine.handle_key_down(name, mods)
                    if action is not None:
                        cb = self._callbacks.get(action)
                        if cb is not None:
                            threading.Thread(target=cb, daemon=True).start()
                elif event.type == X.KeyRelease:
                    name = self._keycode_to_main_key(dpy, event.detail)
                    self._engine.handle_key_up(name)
        except Exception as e:
            try:
                _log_error("HOOK", f"linux grab loop failed: {e}")
            except Exception:
                pass
        finally:
            try:
                dpy.close()
            except Exception:
                pass
            # 只有当前注册的 grab 线程才有权清运行态：改键重启时旧线程
            # 收尾绝不能把新线程的运行态误清掉。
            if self._grab_thread is threading.current_thread():
                self._running = False

    # ---- Record 线程：三次空格（只旁观，不抓、不吞） ----
    def _record_loop(self, gen: int):
        try:
            dpy = _xdisplay.Display()
        except Exception as e:
            _log_error("HOOK", f"linux record connect failed: {e}")
            return
        ctx = None
        try:
            mod_map = self._mod_map(dpy)
            ctx = dpy.record_create_context(
                0,
                [_xrecord.AllClients],
                [{
                    "core_requests": (0, 0),
                    "core_replies": (0, 0),
                    "ext_requests": (0, 0, 0, 0),
                    "ext_replies": (0, 0, 0, 0),
                    "delivered_events": (0, 0),
                    "device_events": (X.KeyPress, X.KeyRelease),
                    "errors": (0, 0),
                    "client_started": False,
                    "client_died": False,
                }],
            )

            def handler(reply, data=None):
                if gen != self._gen or not self._running:
                    try:
                        dpy.record_disable_context(ctx)
                    except Exception:
                        pass
                    return
                if data is None:
                    data = getattr(reply, "data", b"")
                if getattr(reply, "category", None) != _xrecord.FromServerTime:
                    return
                if getattr(reply, "client_swapped", False):
                    return
                while data:
                    try:
                        event, data = _xrq.EventField.parse_binary_value(data, dpy, None, None)
                    except Exception:
                        try:
                            event, data = _xrq.EventField.parse_binary_value(
                                data, getattr(dpy, "display", dpy), None, None
                            )
                        except Exception:
                            return
                    if event.type not in (X.KeyPress, X.KeyRelease):
                        continue
                    name = self._keycode_to_main_key(dpy, event.detail)
                    mods = state_to_mods(event.state, mod_map)
                    if event.type == X.KeyPress:
                        # 组合键留给 Grab 线程（否则双喂抢触发权）。
                        if self._engine.matches_combo(name, mods):
                            continue
                        action, _swallow = self._engine.handle_key_down(name, mods)
                        if action == "triple_space":
                            cb = self._callbacks.get("triple_space")
                            if cb is not None:
                                threading.Thread(target=cb, daemon=True).start()
                    else:
                        self._engine.handle_key_up(name)

            dpy.record_enable_context(ctx, handler)
        except Exception as e:
            try:
                _log_error("HOOK", f"linux record loop failed: {e}")
            except Exception:
                pass
        finally:
            try:
                if ctx is not None:
                    dpy.record_disable_context(ctx)
            except Exception:
                pass
            try:
                dpy.close()
            except Exception:
                pass


# ---- XTest 合成按键（就地替换 Ctrl+A/C/V、Shift+Home、划选 Ctrl+C 用） ----
def open_display():
    """开一个 X 连接（合成按键用，用完调用方负责 close；无 X 时返回 None）。"""
    if not _XLIB_AVAILABLE:
        return None
    try:
        return _xdisplay.Display()
    except Exception:
        return None


def _keycode_for(dpy, keysym_name: str) -> int:
    try:
        return dpy.keysym_to_keycode(XK.string_to_keysym(keysym_name))
    except Exception:
        return 0


def xtest_key(dpy, keysym_name: str, delay: float = 0.02):
    """合成一次单键（按下 + 抬起）。"""
    keycode = _keycode_for(dpy, keysym_name)
    if not keycode:
        return
    dpy.xtest_fake_input(X.KeyPress, keycode)
    dpy.xtest_fake_input(X.KeyRelease, keycode)
    dpy.sync()
    time.sleep(delay)


def xtest_combo(dpy, modifier_names, keysym_name: str, delay: float = 0.02):
    """合成一次组合键（修饰键按下 → 主键按下抬起 → 修饰键抬起）。"""
    mod_codes = [c for c in (_keycode_for(dpy, m) for m in modifier_names) if c]
    keycode = _keycode_for(dpy, keysym_name)
    if not keycode:
        return
    for c in mod_codes:
        dpy.xtest_fake_input(X.KeyPress, c)
    dpy.xtest_fake_input(X.KeyPress, keycode)
    dpy.xtest_fake_input(X.KeyRelease, keycode)
    for c in reversed(mod_codes):
        dpy.xtest_fake_input(X.KeyRelease, c)
    dpy.sync()
    time.sleep(delay)


def xtest_ctrl_key(dpy, keysym_name: str):
    """合成 Ctrl+主键（Linux 的复制/全选/粘贴，对应 macOS 的 Cmd+主键）。"""
    xtest_combo(dpy, ["Control_L"], keysym_name)


def xtest_shift_home(dpy):
    """合成 Shift+Home（选到行首，对应 Windows/macOS 的行选区策略）。"""
    xtest_combo(dpy, ["Shift_L"], "Home")


def xtest_right(dpy):
    """合成 Right（收起选区，对应放弃路径的 VK_RIGHT）。"""
    xtest_key(dpy, "Right")
