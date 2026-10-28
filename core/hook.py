"""
全局低级键盘钩子（仅 Windows，WH_KEYBOARD_LL）：
- 4 个组合键动作：划选翻译、截图 OCR、工作台、语音听写，组合键可在
  设置页自定义，默认 Alt+Q / Alt+W / Alt+M / Alt+Space，见 core/hotkeys.py。
- 输入框就地转译：连续 3 次空格。
组合键触发要求修饰键集合严格相等（例如设了 Alt+Shift+Q 就不会被
Alt+Q 误触），触发后返回 1 吞掉该次按键，避免字符落到输入框里。
"""
import ctypes
from ctypes import wintypes
import time
import threading
from typing import Callable, Dict, Optional

from core.logging import debug as _log_debug, info as _log_info, warning as _log_warning, error as _log_error
from core.platform import IS_WINDOWS
from core.replacer import _send_mask_key
from core.hotkeys import (
    ACTION_ORDER,
    normalize_hotkeys,
    parse_hotkey,
)

user32 = ctypes.windll.user32 if IS_WINDOWS else None
kernel32 = ctypes.windll.kernel32 if IS_WINDOWS else None
if IS_WINDOWS:
    # ctypes 默认 restype 是 c_int，64 位下 HWND/LRESULT 会被截断，
    # GetMessageW 的 -1（出错）也会被 BOOL 化成 True 导致死循环；
    # 这里按 Win32 签名写死（2026-10-28 review 小问题）。
    # GetAsyncKeyState 也被 replacer.py 用，SHORT 是正确签名，两边都受益。
    user32.SetWindowsHookExW.argtypes = [
        ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD,
    ]
    user32.SetWindowsHookExW.restype = ctypes.c_void_p
    # 注意：lParam 在回调里是 POINTER(KBDLLHOOKSTRUCT) 对象，ctypes
    # 无法把它转成 LPARAM（c_ssize_t），会抛 ArgumentError；回调一抛
    # 异常，ctypes 就返回未初始化的垃圾值（实测非 0），Windows 随即
    # 吞掉该按键 —— 1.0.15 全系统无法输入就是这么来的。
    # 所以这里第 4 个参数必须是 c_void_p（指针可正确转成地址）。
    user32.CallNextHookEx.argtypes = [
        ctypes.c_void_p, ctypes.c_int, wintypes.WPARAM, ctypes.c_void_p,
    ]
    user32.CallNextHookEx.restype = ctypes.c_void_p
    user32.UnhookWindowsHookEx.argtypes = [ctypes.c_void_p]
    user32.UnhookWindowsHookEx.restype = wintypes.BOOL
    user32.GetMessageW.argtypes = [
        ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint, ctypes.c_uint,
    ]
    user32.GetMessageW.restype = ctypes.c_int
    user32.TranslateMessage.argtypes = [ctypes.c_void_p]
    user32.TranslateMessage.restype = wintypes.BOOL
    user32.DispatchMessageW.argtypes = [ctypes.c_void_p]
    user32.DispatchMessageW.restype = ctypes.c_void_p
    user32.PostThreadMessageW.argtypes = [
        wintypes.DWORD, ctypes.c_uint, wintypes.WPARAM, wintypes.LPARAM,
    ]
    user32.PostThreadMessageW.restype = wintypes.BOOL
    user32.GetAsyncKeyState.argtypes = [ctypes.c_int]
    user32.GetAsyncKeyState.restype = wintypes.SHORT
    kernel32.GetLastError.argtypes = []
    kernel32.GetLastError.restype = wintypes.DWORD

WH_KEYBOARD_LL = 13
WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101
WM_SYSKEYDOWN = 0x0104
WM_SYSKEYUP = 0x0105

VK_SPACE = 0x20
VK_SHIFT = 0x10
VK_CONTROL = 0x11
VK_MENU = 0x12  # Alt

class KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("vkCode", wintypes.DWORD),
        ("scanCode", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(wintypes.ULONG))
    ]

HOOKPROC = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_int, wintypes.WPARAM, ctypes.POINTER(KBDLLHOOKSTRUCT)) if IS_WINDOWS else None

class GlobalKeyboardHook:
    def __init__(
        self,
        on_triple_space: Optional[Callable[[], None]] = None,
        on_selection_translate: Optional[Callable[[], None]] = None,
        on_screenshot_translate: Optional[Callable[[], None]] = None,
        on_voice_input: Optional[Callable[[], None]] = None,
        on_open_main: Optional[Callable[[], None]] = None,
        max_interval: float = 0.55,
        hotkeys: Optional[Dict[str, str]] = None,
    ):
        self.on_triple_space = on_triple_space
        self.on_selection_translate = on_selection_translate
        self.on_screenshot_translate = on_screenshot_translate
        self.on_voice_input = on_voice_input
        self.on_open_main = on_open_main
        self.max_interval = max_interval
        # 动作 -> (修饰键集合, 主键虚拟键码, 回调, 显示用组合键)
        self._hotkey_table = []
        self.hotkeys: Dict[str, str] = {}
        # 钩子线程生命周期专属状态，由 start/stop 专管；update_hotkeys
        # 只换判定表，绝不碰这几项——否则保存设置会杀死运行中的钩子，
        # 托盘暂停失效、恢复时再起一个钩子导致同一组合键触发两次。
        self.hook_id = None
        self._thread = None
        self._running = False
        self._hook_proc_ref = None
        # 已按下未抬起的主键集合：按住自动重复只吞不触发，抬起时清除。
        self._down_hotkeys = set()
        # 空格是否正按住：低层钩子拿不到重复标记，靠这个状态过滤
        # 按住空格的自动重复（此前只有热键有防重复，空格没有，按住
        # 空格会直接攒满 3 次触发就地转译）。
        self._space_down = False
        self.update_hotkeys(hotkeys)

    def update_hotkeys(self, hotkeys: Optional[Dict[str, str]]) -> None:
        """重建组合键判定表；配置保存后调用即生效，无需重启钩子线程。

        非法、重复的配置由 normalize_hotkeys 回退成一套可用的组合键，
        这里不做二次校验，钩子永远按一张合法的表工作。
        """
        callbacks = {
            "selection": self.on_selection_translate,
            "screenshot": self.on_screenshot_translate,
            "workbench": self.on_open_main,
            "voice": self.on_voice_input,
        }
        normalized = normalize_hotkeys(hotkeys)
        table = []
        for action in ACTION_ORDER:
            parsed = parse_hotkey(normalized[action])
            if parsed is None:
                continue
            mods, vk, label = parsed
            table.append((mods, vk, callbacks[action], label))
        self._hotkey_table = table
        self.hotkeys = normalized
        _log_info("HOOK", f"Hotkeys updated: {normalized}")

        self.space_count = 0
        self.last_space_time = 0.0
        self.last_key_was_char = False
        self.alt_pressed = False
        self.shift_pressed = False
        # 注意：这里绝不重置 hook_id/_thread/_running/_hook_proc_ref。
        # 钩子线程生命周期归 start/stop 管；保存设置时重置它们会杀死
        # 运行中的钩子（线程还在跑但 _running 已是 False），托盘暂停
        # 因 stop() 提前返回而失效，恢复时 start() 又起一个新钩子，
        # 同一组合键触发两次。

    def _hook_callback(self, nCode, wParam, lParam):
        # 防御：回调绝不能抛异常。ctypes 回调一抛异常就返回未初始化
        # 的垃圾值（实测非 0），Windows 会把当次按键吞掉；1.0.15 的
        # 全系统无法输入就是一次回调异常造成的。异常时记日志并放行。
        try:
            return self._hook_callback_inner(nCode, wParam, lParam)
        except Exception:
            try:
                _log_error("HOOK", "hook callback failed, passing key through")
            except Exception:
                pass
            return 0

    def _hook_callback_inner(self, nCode, wParam, lParam):
        if nCode >= 0:
            vk_code = lParam.contents.vkCode
            flags = lParam.contents.flags
            is_down = wParam in (WM_KEYDOWN, WM_SYSKEYDOWN)

            # 过滤由我们自身 SendInput 注入的事件，避免循环干扰
            if flags & 0x10:
                return user32.CallNextHookEx(self.hook_id, nCode, wParam, lParam)

            if is_down:
                now = time.time()
                # 修饰键状态：Alt 结合 flags 的 LLKHF_ALTDOWN (0x20) 以及
                # GetAsyncKeyState 双重校验，Ctrl / Shift 只用 GetAsyncKeyState。
                mods_down = set()
                if (flags & 0x20) or (user32.GetAsyncKeyState(VK_MENU) & 0x8000):
                    mods_down.add("Alt")
                if user32.GetAsyncKeyState(VK_CONTROL) & 0x8000:
                    mods_down.add("Ctrl")
                if user32.GetAsyncKeyState(VK_SHIFT) & 0x8000:
                    mods_down.add("Shift")
                alt_down = "Alt" in mods_down
                ctrl_down = "Ctrl" in mods_down
                shift_down = "Shift" in mods_down


                # 组合键：修饰键集合必须严格相等才触发，避免 Alt+Shift+Q
                # 之类的按键同时触发 Alt+Q 的动作。
                for mods, vk, callback, label in self._hotkey_table:
                    if vk_code == vk and mods_down == mods:
                        _log_info("HOOK", f">>> Hotkey {label} triggered! <<<")
                        key = (tuple(sorted(mods)), vk)
                        if key in self._down_hotkeys:
                            # 按住主键不放的自动重复：只吞掉，不再重复触发。
                            return 1
                        self._down_hotkeys.add(key)
                        # 菜单屏蔽键：Alt 组合键触发时 Alt 还按着；先注入
                        # 一次未分配键 0xE8 的按下+抬起，此后不管 Alt 何时
                        # 松开，对目标程序来说都不再是“光秃秃的 Alt”，
                        # 不会进菜单模式（AutoHotkey MenuMaskKey 同款）。
                        if "Alt" in mods:
                            _send_mask_key()
                        if callback:
                            threading.Thread(target=callback, daemon=True).start()
                        return 1

                # 连续三次空格就地转译 (无 Alt / Ctrl 干扰)
                if vk_code == VK_SPACE and not alt_down and not ctrl_down and not self._space_down:
                    self._space_down = True
                    delta = now - self.last_space_time if self.last_space_time > 0 else 0
                    if self.last_space_time > 0 and delta <= self.max_interval:
                        self.space_count += 1
                    else:
                        self.space_count = 1
                    self.last_space_time = now
                    _log_info("HOOK", f"[HOOK] Space pressed! space_count={self.space_count}, delta={delta:.3f}s, max_inv={self.max_interval}")

                    if self.space_count >= 3:
                        _log_info("HOOK", ">>> [HOOK] TRIPLE SPACE TRIGGERED! Calling replacer... <<<")
                        self.space_count = 0
                        self.last_space_time = 0.0
                        if self.on_triple_space:
                            threading.Thread(target=self.on_triple_space, daemon=True).start()
                elif vk_code not in (
                    0x10, 0x11, 0x12, 0x5B, 0x5C, # Shift, Ctrl, Alt, Win
                    0xA0, 0xA1, 0xA2, 0xA3, 0xA4, 0xA5, # L/R Shift, Ctrl, Alt
                    0xE5 # VK_PROCESSKEY
                ):
                    if self.space_count > 0:
                        _log_info("HOOK", f"[HOOK] Reset space_count (from {self.space_count})")
                    self.space_count = 0
                    self.last_space_time = 0.0

            elif wParam in (WM_KEYUP, WM_SYSKEYUP):
                # 主键抬起：清除按住态，下次按下可重新触发。
                if self._down_hotkeys:
                    self._down_hotkeys = {k for k in self._down_hotkeys if k[1] != vk_code}
                if vk_code == VK_SPACE:
                    self._space_down = False

        return user32.CallNextHookEx(self.hook_id, nCode, wParam, lParam)

    def _run_hook_loop(self):
        self._hook_proc_ref = HOOKPROC(self._hook_callback)
        my_id = user32.SetWindowsHookExW(
            WH_KEYBOARD_LL,
            self._hook_proc_ref,
            0,
            0
        )
        if not my_id:
            _log_info("HOOK", f"SetWindowsHookExW failed with error: {kernel32.GetLastError()}")
            # 安装失败必须把 _running 清掉，否则状态卡在“运行中”却没有钩子，
            # 之后也无法重装、没有任何提示（2026-10-28 review 小问题）。
            self._running = False
            return
        self.hook_id = my_id
        _log_info("HOOK", f"Hook installed successfully: hook_id={my_id}")

        msg = wintypes.MSG()
        while self._running:
            b_ret = user32.GetMessageW(ctypes.byref(msg), 0, 0, 0)
            if b_ret <= 0:
                break
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))

        # 只卸自己装的钩子：如果 stop 后立刻 start 起了新钩子，旧线程收尾
        # 绝不能把新钩子的 id 卸掉（2026-10-28 review 小问题）。
        user32.UnhookWindowsHookEx(my_id)
        if self.hook_id == my_id:
            self.hook_id = None
        _log_info("HOOK", "Hook loop finished")

    def start(self):
        if not IS_WINDOWS:
            # macOS / Linux 没有 WH_KEYBOARD_LL：钩子不安装，界面与翻译仍可用。
            _log_warning("HOOK", "Global hotkeys are Windows-only; hook disabled on this platform")
            return
        if self._running:
            return
        # 旧线程可能还在收尾：等它退干净再装新钩子，否则两个线程共用
        # hook_id，旧线程收尾会卸掉新钩子；1 秒等不到就放弃重装。
        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=1.0)
            if self._thread.is_alive():
                _log_info("HOOK", "previous hook thread did not exit, start aborted")
                return
        self._running = True
        self._thread = threading.Thread(target=self._run_hook_loop, daemon=True)
        self._thread.start()

    def stop(self):
        if not self._running:
            return
        self._running = False
        if IS_WINDOWS and self._thread and self._thread.is_alive():
            user32.PostThreadMessageW(self._thread.ident, 0x0012, 0, 0)
            # 有界等待旧线程收尾，让 start() 的“等旧线程”逻辑多数时候
            # 不用等；等不到也不阻塞界面。
            self._thread.join(timeout=1.0)


def hook_self_check(hook) -> tuple:
    """启动前自检：装钩子之前先证明钩子不会吞键，任一点失败都拒绝装钩子。

    1.0.15 的教训：钩子一旦装错（CallNextHookEx 的 lParam 声明成
    LPARAM，POINTER 转不过去抛 ArgumentError），回调一抛异常就返回
    垃圾值吞键，全系统打不出字。所以这里在装钩子之前验证两点：
    1) Windows 下 CallNextHookEx 的 lParam 声明必须是 c_void_p；
    2) 回调 wrapper 必须兜底：内层抛任何异常时外层返回 0（放行）。
    第 2 点用探针验证：临时把内层换成必抛的函数，调外层必须得 0，
    验完原样恢复，不碰真实 user32、不注任何按键，任何平台都可跑。
    返回 (ok, 明细字符串)。
    """
    problems = []
    if IS_WINDOWS:
        try:
            argtypes = user32.CallNextHookEx.argtypes
        except Exception as e:
            problems.append(f"CallNextHookEx argtypes 不可读：{e}")
            argtypes = None
        if argtypes is not None and (len(argtypes) < 4 or argtypes[3] is not ctypes.c_void_p):
            problems.append("CallNextHookEx lParam 声明不是 c_void_p（1.0.15 同款错误）")
    original_inner = hook._hook_callback_inner

    def _boom(nCode, wParam, lParam):
        raise RuntimeError("self-check probe")

    try:
        hook._hook_callback_inner = _boom
        try:
            ret = hook._hook_callback(0, WM_KEYDOWN, None)
        except Exception as e:
            problems.append(f"回调 wrapper 未兜底异常：{e}")
            ret = None
        if ret is not None and ret != 0:
            problems.append(f"回调 wrapper 在内层异常时返回 {ret}（应为 0 放行）")
    finally:
        hook._hook_callback_inner = original_inner
    if problems:
        return False, "；".join(problems)
    return True, "CallNextHookEx lParam=c_void_p；回调 wrapper 异常时返回 0"
