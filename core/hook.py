"""
全局低级键盘钩子：
- 划词悬浮翻译: Alt + Q (绝不占用 Alt+D)
- 截图 OCR 识别: Alt + W (绝不占用 Alt+X)
- 语音听写输入: Alt + Space
- 呼出桌面工作台: Alt + M
- 输入框就地转译: 连续 3 次空格 (Pro 核心)
注：Alt+D 与 Alt+X 已完全释放，原封不动放行给外部应用。
"""
import ctypes
from ctypes import wintypes
import time
import os
import threading
from typing import Callable, Optional

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

LOG_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "debug_app.log")

def _log(msg: str):
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{time.strftime('%H:%M:%S')}.{int(time.time()*1000)%1000:03d}] {msg}\n")
    except Exception:
        pass

WH_KEYBOARD_LL = 13
WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101
WM_SYSKEYDOWN = 0x0104
WM_SYSKEYUP = 0x0105

VK_SPACE = 0x20
VK_SHIFT = 0x10
VK_CONTROL = 0x11
VK_MENU = 0x12  # Alt

VK_Q = 0x51     # Q (划词翻译，绝不占用 Alt+D)
VK_W = 0x57     # W (截图 OCR 翻译，绝不占用 Alt+X)
VK_M = 0x4D     # M (呼出主工作台)

class KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("vkCode", wintypes.DWORD),
        ("scanCode", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(wintypes.ULONG))
    ]

HOOKPROC = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_int, wintypes.WPARAM, ctypes.POINTER(KBDLLHOOKSTRUCT))

class GlobalKeyboardHook:
    def __init__(
        self,
        on_triple_space: Optional[Callable[[], None]] = None,
        on_selection_translate: Optional[Callable[[], None]] = None,
        on_screenshot_translate: Optional[Callable[[], None]] = None,
        on_voice_input: Optional[Callable[[], None]] = None,
        on_open_main: Optional[Callable[[], None]] = None,
        max_interval: float = 0.55
    ):
        self.on_triple_space = on_triple_space
        self.on_selection_translate = on_selection_translate
        self.on_screenshot_translate = on_screenshot_translate
        self.on_voice_input = on_voice_input
        self.on_open_main = on_open_main
        self.max_interval = max_interval

        self.space_count = 0
        self.last_space_time = 0.0
        self.last_key_was_char = False
        self.alt_pressed = False
        self.shift_pressed = False

        self.hook_id = None
        self._thread = None
        self._running = False
        self._hook_proc_ref = None

    def _hook_callback(self, nCode, wParam, lParam):
        if nCode >= 0:
            vk_code = lParam.contents.vkCode
            flags = lParam.contents.flags
            is_down = wParam in (WM_KEYDOWN, WM_SYSKEYDOWN)

            # 过滤由我们自身 SendInput 注入的事件，避免循环干扰
            if flags & 0x10:
                return user32.CallNextHookEx(self.hook_id, nCode, wParam, lParam)

            if is_down:
                now = time.time()
                # 检查 Alt 状态：结合 flags 的 LLKHF_ALTDOWN (0x20) 以及 GetAsyncKeyState 双重校验
                alt_down = bool((flags & 0x20) or (user32.GetAsyncKeyState(VK_MENU) & 0x8000))
                ctrl_down = bool(user32.GetAsyncKeyState(VK_CONTROL) & 0x8000)
                shift_down = bool(user32.GetAsyncKeyState(VK_SHIFT) & 0x8000)

                # 全量记录键盘击键日志便于诊断
                _log(f"Key: vk={vk_code:#x}, alt={alt_down}, ctrl={ctrl_down}, shift={shift_down}")

                # 1. 快捷键: 划词翻译 (严格仅使用 Alt+Q，绝不占用 Alt+D)
                if alt_down and vk_code == VK_Q:
                    _log(">>> Hotkey Selection Translate (Alt+Q) triggered! <<<")
                    if self.on_selection_translate:
                        threading.Thread(target=self.on_selection_translate, daemon=True).start()
                    return 1

                # 2. 快捷键: 截图 OCR 翻译 (严格仅使用 Alt+W，绝不占用 Alt+X)
                if alt_down and vk_code == VK_W:
                    _log(">>> Hotkey Screenshot OCR (Alt+W) triggered! <<<")
                    if self.on_screenshot_translate:
                        threading.Thread(target=self.on_screenshot_translate, daemon=True).start()
                    return 1

                # 3. 快捷键: Alt + M (呼出桌面工作台)
                if alt_down and vk_code == VK_M:
                    _log(">>> Hotkey Alt+M triggered! <<<")
                    if self.on_open_main:
                        threading.Thread(target=self.on_open_main, daemon=True).start()
                    return 1

                # 4. 快捷键: Alt + Space (语音听写输入)
                if alt_down and vk_code == VK_SPACE:
                    _log(">>> Hotkey Alt+Space triggered! <<<")
                    if self.on_voice_input:
                        threading.Thread(target=self.on_voice_input, daemon=True).start()
                    return 1

                # 5. 核心 Pro 特性: 连续三次空格就地转译 (无 Alt / Ctrl 干扰)
                if vk_code == VK_SPACE and not alt_down and not ctrl_down:
                    delta = now - self.last_space_time if self.last_space_time > 0 else 0
                    if self.last_space_time > 0 and delta <= self.max_interval:
                        self.space_count += 1
                    else:
                        self.space_count = 1
                    self.last_space_time = now
                    _log(f"[HOOK] Space pressed! space_count={self.space_count}, delta={delta:.3f}s, max_inv={self.max_interval}")

                    if self.space_count >= 3:
                        _log(">>> [HOOK] TRIPLE SPACE TRIGGERED! Calling replacer... <<<")
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
                        _log(f"[HOOK] Reset space_count (from {self.space_count}) on key vk={vk_code:#x}")
                    self.space_count = 0
                    self.last_space_time = 0.0

        return user32.CallNextHookEx(self.hook_id, nCode, wParam, lParam)

    def _run_hook_loop(self):
        self._hook_proc_ref = HOOKPROC(self._hook_callback)
        self.hook_id = user32.SetWindowsHookExW(
            WH_KEYBOARD_LL,
            self._hook_proc_ref,
            0,
            0
        )
        if not self.hook_id:
            _log(f"SetWindowsHookExW failed with error: {kernel32.GetLastError()}")
            return
        _log(f"Hook installed successfully: hook_id={self.hook_id}")

        msg = wintypes.MSG()
        while self._running:
            b_ret = user32.GetMessageW(ctypes.byref(msg), 0, 0, 0)
            if b_ret <= 0:
                break
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))

        if self.hook_id:
            user32.UnhookWindowsHookEx(self.hook_id)
            self.hook_id = None
        _log("Hook loop finished")

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_hook_loop, daemon=True)
        self._thread.start()

    def stop(self):
        if not self._running:
            return
        self._running = False
        if self._thread and self._thread.is_alive():
            user32.PostThreadMessageW(self._thread.ident, 0x0012, 0, 0)
