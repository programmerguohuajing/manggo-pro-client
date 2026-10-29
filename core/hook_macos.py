"""macOS 全局热键后端：CGEventTap 事件抽头 + CGEvent 合成按键。

对应 Windows 的 WH_KEYBOARD_LL 钩子（core/hook.py），判定逻辑
复用 core/hotkey_engine（平台无关），这里只做 macOS 的事件翻译：

- 监听：CGEventTap（kCGHIDEventTap，KeyDown / KeyUp / FlagsChanged）。
  修饰键映射：Option → 'Alt'（配置里的 Alt 在 Mac 上就是 Option），
  Ctrl → 'Ctrl'，Shift → 'Shift'；Cmd 不进热键判定。
- 吞键：组合键命中时回调返回 NULL（事件被吞，不再落到目标程序）；
  其他事件原样返回。triple_space 的空格本身不吞（见引擎约定）。
- 合成按键（供划选 Cmd+C、就地替换 Cmd+A/C/V、Shift+Cmd+Left 用）：
  CGEventCreateKeyboardEvent + CGEventPost，flags 由调用方显式指定，
  与物理修饰键状态无关——所以合成 Cmd+C 时即使 Option 还按着，
  目标程序收到的也是干净的 Cmd+C，不需要像 Windows 那样等修饰键松开。
- 注入回环：合成事件是 Cmd 系（Cmd+C/A/V），触发条件是 Option 系
  （Option+Q/W），修饰键集合永远对不上，不可能自触发，无需像
  Windows 那样过滤 LLKHF_INJECTED。
- 回调返回值约定（与 Windows 的 1.0.19 教训区分清楚）：
  CGEventTap 回调的返回值本身就是指针（CGEventRef），返回 NULL
  表示吞键是文档行为；这里 restype=c_void_p、返回 None 即 NULL
  是正确的，不是 Windows HOOKPROC 那种“整数 0 被转成 None”的 bug。
  不要把 Windows 的 c_ssize_t 规则套到这里。

权限：CGEventTapCreate 返回 NULL 即表示缺辅助功能（+ 输入监控）
权限，start() 直接返回 False 并记 last_error，调用方（main.py）
据此弹权限提示；绝不静默“钩子装上了却没反应”。

本模块 import 在任何平台都不崩（库用 find_library 懒加载，
找不到时 start() 直接失败）；只有 macOS 上 start() 才会真正建抽头。
"""

import ctypes
import ctypes.util
import threading
import time
from typing import Callable, Dict, FrozenSet, Optional

from core.hotkey_engine import HotkeyEngine
from core.hotkeys import normalize_hotkeys, parse_hotkey
from core.logging import error as _log_error, info as _log_info

# ---- macOS 常量（HIToolbox / CGEventTypes，写死避免 import 私有头文件）----
kCGHIDEventTap = 0
kCGHeadInsertEventTap = 0
kCGEventTapOptionDefault = 0
kCGEventKeyDown = 10
kCGEventKeyUp = 11
kCGEventFlagsChanged = 12
kCGEventTapDisabledByTimeout = -2  # 0xFFFFFFFE as c_int
kCGEventTapDisabledByUserInput = -1  # 0xFFFFFFFF as c_int
kCGKeyboardEventKeycode = 9
kCGKeyboardEventAutorepeat = 21
kCGEventFlagMaskShift = 1 << 17
kCGEventFlagMaskControl = 1 << 18
kCGEventFlagMaskAlternate = 1 << 19  # Option
kCGEventFlagMaskCommand = 1 << 20
kCGHIDEventTapPost = 0  # CGEventPost 的 tap 位置：HID 层

# ANSI 物理键位 → 配置主键名（Events.h kVK_ANSI_*；与键盘布局无关，
# 指物理键位置，自定义热键 Q/W 之外也按同一张表走）。
_MAC_KEYCODE_TO_NAME = {
    0: "A", 11: "B", 8: "C", 2: "D", 14: "E", 3: "F", 5: "G", 4: "H",
    34: "I", 38: "J", 40: "K", 37: "L", 46: "M", 45: "N", 31: "O", 35: "P",
    12: "Q", 15: "R", 1: "S", 17: "T", 32: "U", 9: "V", 13: "W", 7: "X",
    16: "Y", 6: "Z",
    18: "1", 19: "2", 20: "3", 21: "4", 23: "5", 22: "6", 26: "7",
    28: "8", 25: "9", 29: "0",
    49: "Space",
    122: "F1", 120: "F2", 99: "F3", 118: "F4", 96: "F5", 97: "F6",
    98: "F7", 100: "F8", 101: "F9", 109: "F10", 103: "F11", 111: "F12",
}
_NAME_TO_MAC_KEYCODE = {v: k for k, v in _MAC_KEYCODE_TO_NAME.items()}
# 合成按键用的键码（与上面同一张表，单独列出常用的几个）。
KEYCODE_LEFT = 123
KEYCODE_RIGHT = 124
KEYCODE_DELETE = 51  # kVK_Delete（修复路径清空全文用）


def _load_lib(name):
    path = ctypes.util.find_library(name)
    if not path:
        return None
    try:
        return ctypes.CDLL(path)
    except Exception:
        return None


class MacKeyboardHook:
    """macOS 全局热键钩子（接口对标 GlobalKeyboardHook 的子集）。

    回调约定与 Windows 一致：on_triple_space / on_selection_translate /
    on_screenshot_translate（另起线程触发）；on_voice_input /
    on_open_main 为 None 时对应组合键直接放行（首批范围外）。
    """

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
        self._cg = None
        self._cf = None
        self._tap = None
        self._callback_ref = None
        self._thread: Optional[threading.Thread] = None
        # 注意命名：CFRunLoop 引用不能叫 _run_loop——那是线程方法的名字，
        # 同名属性会在 __init__ 里把方法遮蔽掉（1.0.27 实测：线程拿到
        # target=None 空转退出，钩子等满 2 秒 abort）。
        self._cf_run_loop = None
        self._loop_ready = threading.Event()
        self._running = False
        self.last_error = ""

    # ---- 配置 → 引擎判定表（与 Windows 的 update_hotkeys 同款语义） ----
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


    @property
    def max_interval(self) -> float:
        return self._engine.max_interval

    @max_interval.setter
    def max_interval(self, value: float):
        self._engine.max_interval = value

    def is_running(self) -> bool:
        return self._running and self._tap is not None

    # ---- 事件抽头回调（绝不能抛异常：抛了就按放行处理） ----
    def _tap_callback(self, proxy, etype, event, refcon):
        try:
            return self._tap_callback_inner(proxy, etype, event)
        except Exception as e:
            try:
                _log_error("HOOK", f"mac tap callback failed, passing through: {e}")
            except Exception:
                pass
            return event

    def _tap_callback_inner(self, proxy, etype, event):
        cg = self._cg
        # 抽头被系统停用（超时 / 用户输入）：按文档重开，否则热键悄悄全死。
        if etype in (kCGEventTapDisabledByTimeout, kCGEventTapDisabledByUserInput):
            cg.CGEventTapEnable(self._tap, True)
            return event
        if etype == kCGEventFlagsChanged:
            return event  # 修饰键本身：不触发、不计数（引擎同款排除）
        if etype not in (kCGEventKeyDown, kCGEventKeyUp):
            return event

        keycode = cg.CGEventGetIntegerValueField(event, kCGKeyboardEventKeycode)
        flags = cg.CGEventGetFlags(event)
        mods = set()
        if flags & kCGEventFlagMaskAlternate:
            mods.add("Alt")
        if flags & kCGEventFlagMaskControl:
            mods.add("Ctrl")
        if flags & kCGEventFlagMaskShift:
            mods.add("Shift")
        name = _MAC_KEYCODE_TO_NAME.get(keycode)
        # 未知键码：按“其他主键”处理（清空格计数、放行），不触发组合键。
        main_key = name if name is not None else "__unknown__"

        if etype == kCGEventKeyDown:
            is_repeat = bool(
                cg.CGEventGetIntegerValueField(event, kCGKeyboardEventAutorepeat)
            )
            action, swallow = self._engine.handle_key_down(
                main_key, frozenset(mods), is_repeat=is_repeat
            )
            if action is not None:
                cb = self._callbacks.get(action)
                if cb is not None:
                    threading.Thread(target=cb, daemon=True).start()
            return None if swallow else event
        # KeyUp：只清按住态，永不吞键。
        self._engine.handle_key_up(main_key)
        return event

    # ---- 启动 / 停止（抽头创建本身就是权限自检） ----
    def start(self) -> bool:
        if self._running:
            return True
        self.last_error = ""
        self._cg = _load_lib("CoreGraphics")
        self._cf = _load_lib("CoreFoundation")
        if self._cg is None or self._cf is None:
            self.last_error = "CoreGraphics/CoreFoundation 不可用"
            _log_error("HOOK", f"mac tap unavailable: {self.last_error}")
            return False
        cg, cf = self._cg, self._cf
        cg.CGEventTapCreate.restype = ctypes.c_void_p
        cg.CGEventTapCreate.argtypes = [
            ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_uint64,
            ctypes.c_void_p, ctypes.c_void_p,
        ]
        cg.CGEventGetIntegerValueField.restype = ctypes.c_int64
        cg.CGEventGetIntegerValueField.argtypes = [ctypes.c_void_p, ctypes.c_int]
        cg.CGEventGetFlags.restype = ctypes.c_uint64
        cg.CGEventGetFlags.argtypes = [ctypes.c_void_p]
        cg.CGEventTapEnable.argtypes = [ctypes.c_void_p, ctypes.c_bool]
        cg.CFMachPortCreateRunLoopSource.restype = ctypes.c_void_p
        cg.CFMachPortCreateRunLoopSource.argtypes = [
            ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int
        ]
        # 这一行漏了就会在 stop() 时崩：无 argtypes 时 ctypes 把
        # 64 位指针按 C int（32 位）传递，截断后的地址必然非法
        # （1.0.26 实测崩溃报告：CFMachPortInvalidate SIGSEGV）。
        cg.CFMachPortInvalidate.argtypes = [ctypes.c_void_p]
        cf.CFRunLoopGetCurrent.restype = ctypes.c_void_p
        cf.CFRunLoopAddSource.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p]
        cf.CFRunLoopRun.argtypes = []
        cf.CFRunLoopStop.argtypes = [ctypes.c_void_p]
        cf.CFRelease.argtypes = [ctypes.c_void_p]

        mask = (
            (1 << kCGEventKeyDown)
            | (1 << kCGEventKeyUp)
            | (1 << kCGEventFlagsChanged)
        )
        callback_type = ctypes.CFUNCTYPE(
            ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int,
            ctypes.c_void_p, ctypes.c_void_p,
        )
        self._callback_ref = callback_type(self._tap_callback)
        tap = cg.CGEventTapCreate(
            kCGHIDEventTap, kCGHeadInsertEventTap, kCGEventTapOptionDefault,
            mask, self._callback_ref, None,
        )
        if not tap:
            self.last_error = (
                "未能创建全局按键监听：请在系统设置 → 隐私与安全性 → "
                "辅助功能与输入监控中允许 ManggoProClient；如果列表里已经"
                "勾选了，请先用 − 删除、再用 + 重新添加（应用更新后二进制"
                "变化，旧授权会失效），然后重启应用。"
            )
            _log_error(
                "HOOK",
                f"mac CGEventTapCreate failed: {self.last_error} "
                f"(accessibility_trusted={is_accessibility_trusted()})",
            )
            self._callback_ref = None
            return False
        self._tap = tap
        self._loop_ready.clear()
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        if not self._loop_ready.wait(timeout=2.0):
            _log_error("HOOK", "mac run loop did not start in 2s, aborting tap")
            self.stop()
            self.last_error = "按键监听线程未能启动"
            return False
        _log_info("HOOK", "mac event tap installed")
        return True

    def _run_loop(self):
        cg, cf = self._cg, self._cf
        try:
            source = cg.CFMachPortCreateRunLoopSource(None, self._tap, 0)
            if not source:
                _log_error("HOOK", "mac CFMachPortCreateRunLoopSource failed")
                self._running = False
                self._loop_ready.set()
                return
            self._cf_run_loop = cf.CFRunLoopGetCurrent()
            # 运行循环 mode 必须传真正的 CFString（kCFRunLoopCommonModes，
            # 抽头事件在所有 common mode 下都投递）；它以导出变量形式存在，
            # 用 in_dll 取地址，绝不能传 NULL（NULL 不是合法 mode）。
            try:
                mode = ctypes.c_void_p.in_dll(cf, "kCFRunLoopCommonModes")
            except Exception:
                mode = ctypes.c_void_p.in_dll(cf, "kCFRunLoopDefaultMode")
            cf.CFRunLoopAddSource(self._cf_run_loop, source, mode)
            cf.CFRelease(source)
            cg.CGEventTapEnable(self._tap, True)
            self._loop_ready.set()
            _log_info("HOOK", "mac run loop running (event tap live)")
            cf.CFRunLoopRun()
        except Exception as e:
            try:
                _log_error("HOOK", f"mac run loop failed: {e}")
            except Exception:
                pass
            self._loop_ready.set()
        finally:
            self._running = False

    def stop(self):
        if not self._running and self._thread is None:
            return
        self._running = False
        if self._cf_run_loop is not None and self._cf is not None:
            try:
                self._cf.CFRunLoopStop(self._cf_run_loop)
            except Exception:
                pass
        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        if self._tap is not None and self._cg is not None:
            try:
                self._cg.CFMachPortInvalidate(self._tap)
                self._cf.CFRelease(self._tap)
            except Exception:
                pass
        self._tap = None
        self._cf_run_loop = None
        self._callback_ref = None
        self._thread = None
        _log_info("HOOK", "mac event tap stopped")


# ---- CGEvent 合成按键（划选 Cmd+C、就地替换 Cmd+A/C/V、Shift+Cmd+Left 用） ----
def _cf_lib():
    """CoreFoundation 句柄（带 CFRelease 签名声明）。

    注意：argtypes 是挂在 CDLL 实例的函数对象上的，给 self._cf 声明
    过不等于给新 load 的句柄声明过——post_key 此前就栽在这里
    （新句柄无声明，CFRelease 的指针参数被截断）。
    """
    lib = _load_lib("CoreFoundation")
    if lib is None:
        raise RuntimeError("CoreFoundation 不可用")
    lib.CFRelease.argtypes = [ctypes.c_void_p]
    return lib


def _cg_lib():
    lib = _load_lib("CoreGraphics")
    if lib is None:
        raise RuntimeError("CoreGraphics 不可用")
    lib.CGEventCreateKeyboardEvent.restype = ctypes.c_void_p
    lib.CGEventCreateKeyboardEvent.argtypes = [
        ctypes.c_void_p, ctypes.c_uint16, ctypes.c_bool
    ]
    lib.CGEventSetFlags.argtypes = [ctypes.c_void_p, ctypes.c_uint64]
    lib.CGEventPost.argtypes = [ctypes.c_int, ctypes.c_void_p]
    return lib


def is_accessibility_trusted():
    """当前进程是否被系统信任为辅助功能（AXIsProcessTrusted）。

    事件抽头与合成事件投递都受这个信任状态管辖：未信任时系统静默
    丢弃合成事件，抽头也建不起来。用它能把"授权没绑到当前二进制"
    和其他失败分开。返回 True/False；框架不可用时返回 None（未知）。
    签名纪律：无参数、返回 Boolean，在本函数自己 load 的句柄上声明。
    """
    lib = _load_lib("ApplicationServices")
    if lib is None:
        return None
    try:
        lib.AXIsProcessTrusted.argtypes = []
        lib.AXIsProcessTrusted.restype = ctypes.c_bool
        return bool(lib.AXIsProcessTrusted())
    except Exception:
        return None


def wait_until_modifiers_released(timeout: float = 1.2) -> float:
    """等物理 Option/Ctrl 松开；返回实际等待秒数，超时返回 -1.0。

    Option+Q 触发划选时，回调触发后用户往往还按着 Option；立刻
    合成 Cmd+C，部分应用会把它理解成 Option+Cmd+C（不复制）。
    先等修饰键松开再投递，与 Windows 版等修饰键抬起的教训同理。
    签名纪律：CGEventSourceFlagsState 在本函数自己的句柄上声明
    （无指针参数，但 restype 是 64 位 flags，必须显式声明）。
    """
    lib = _load_lib("CoreGraphics")
    if lib is None:
        return 0.0
    try:
        lib.CGEventSourceFlagsState.argtypes = [ctypes.c_int]
        lib.CGEventSourceFlagsState.restype = ctypes.c_uint64
    except Exception:
        return 0.0
    mask = kCGEventFlagMaskAlternate | kCGEventFlagMaskControl
    start = time.time()
    while True:
        try:
            flags = lib.CGEventSourceFlagsState(1)  # kCGEventSourceStateHIDSystemState
        except Exception:
            return 0.0
        if not (flags & mask):
            return time.time() - start
        if time.time() - start >= timeout:
            return -1.0
        time.sleep(0.02)


def post_key(keycode: int, flags: int = 0, delay: float = 0.02):
    """合成一次按键（按下 + 抬起），flags 显式指定，与物理修饰键无关。

    返回 True 仅当按下与抬起两个事件都成功创建并投递；事件创建
    失败（NULL）返回 False——此前是静默 continue，调用方无从判断
    合成键到底发出去没有。
    """
    lib = _cg_lib()
    cf = _cf_lib()
    ok = True
    for down in (True, False):
        ev = lib.CGEventCreateKeyboardEvent(None, keycode, down)
        if not ev:
            ok = False
            continue
        if flags:
            lib.CGEventSetFlags(ev, flags)
        lib.CGEventPost(kCGHIDEventTapPost, ev)
        if cf is not None:
            cf.CFRelease(ev)
        time.sleep(delay)
    return ok


def post_cmd_key(name: str):
    """合成 Cmd+主键（如 Cmd+C / Cmd+A / Cmd+V）。"""
    keycode = _NAME_TO_MAC_KEYCODE.get(name)
    if keycode is None:
        raise ValueError(f"unknown key name for Cmd combo: {name}")
    return post_key(keycode, flags=kCGEventFlagMaskCommand)


def post_shift_cmd_left():
    """合成 Shift+Cmd+Left（macOS 的“选到行首”，对应 Windows Shift+Home）。"""
    post_key(KEYCODE_LEFT, flags=kCGEventFlagMaskShift | kCGEventFlagMaskCommand)


def post_right():
    """合成 Right（收起选区，对应 Windows 放弃路径的 VK_RIGHT）。"""
    post_key(KEYCODE_RIGHT)


def post_delete():
    """合成 Delete（无修饰键）。仅在选区已被回读证明覆盖全文时
    用于修复清空——无选区时它只删一个字符，所以调用点必须先证明。"""
    return post_key(KEYCODE_DELETE)
