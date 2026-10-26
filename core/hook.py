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
import threading
from typing import Callable, Optional

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

WH_KEYBOARD_LL = 13
WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101
WM_SYSKEYDOWN = 0x0104
WM_SYSKEYUP = 0x0105

VK_SPACE = 0x20
VK_SHIFT = 0x10
VK_CONTROL = 0x11
VK_MENU = 0x12  # Alt

VK_Q = 0x51     # Q (划词翻译)
VK_W = 0x57     # W (截图 OCR 翻译)
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
        self.alt_pressed = False
        self.shift_pressed = False

        self.hook_id = None
        self._thread = None
        self._running = False
        self._hook_proc_ref = None

    def _hook_callback(self, nCode, wParam, lParam):
        if nCode >= 0:
            vk_code = lParam.contents.vkCode
            is_down = wParam in (WM_KEYDOWN, WM_SYSKEYDOWN)
            is_up = wParam in (WM_KEYUP, WM_SYSKEYUP)

            # 追踪 Alt 与 Shift 修饰键状态
            if vk_code in (VK_MENU, 0xA4, 0xA5):
                self.alt_pressed = is_down
            if vk_code in (VK_SHIFT, 0xA0, 0xA1):
                self.shift_pressed = is_down

            if is_down:
                now = time.time()

                # 1. 快捷键: Alt + Q (划词翻译) —— 绝不占用 Alt+D
                if self.alt_pressed and vk_code == VK_Q:
                    if self.on_selection_translate:
                        threading.Thread(target=self.on_selection_translate, daemon=True).start()
                    return 1

                # 2. 快捷键: Alt + W (截图 OCR 翻译) —— 绝不占用 Alt+X
                if self.alt_pressed and vk_code == VK_W:
                    if self.on_screenshot_translate:
                        threading.Thread(target=self.on_screenshot_translate, daemon=True).start()
                    return 1

                # 3. 快捷键: Alt + M (呼出桌面工作台) —— 绝不占用 Alt+D
                if self.alt_pressed and vk_code == VK_M:
                    if self.on_open_main:
                        threading.Thread(target=self.on_open_main, daemon=True).start()
                    return 1

                # 4. 快捷键: Alt + Space (语音听写输入)
                if self.alt_pressed and vk_code == VK_SPACE:
                    if self.on_voice_input:
                        threading.Thread(target=self.on_voice_input, daemon=True).start()
                    return 1

                # 5. 核心 Pro 特性: 连续三次空格就地转译 (非修饰键状态)
                if vk_code == VK_SPACE and not self.alt_pressed:
                    if self.last_space_time > 0 and (now - self.last_space_time) <= self.max_interval:
                        self.space_count += 1
                    else:
                        self.space_count = 1
                    self.last_space_time = now

                    if self.space_count >= 3:
                        self.space_count = 0
                        self.last_space_time = 0.0
                        if self.on_triple_space:
                            threading.Thread(target=self.on_triple_space, daemon=True).start()
                elif vk_code not in (0x10, 0x11, 0x12, 0x5B, 0x5C, 0xA0, 0xA1, 0xA2, 0xA3, 0xA4, 0xA5):
                    # 按下了非修饰键的其他普通键，重置空格连击
                    self.space_count = 0
                    self.last_space_time = 0.0

        return user32.CallNextHookEx(self.hook_id, nCode, wParam, lParam)

    def _run_hook_loop(self):
        self._hook_proc_ref = HOOKPROC(self._hook_callback)
        # WH_KEYBOARD_LL 全局钩子要求 hMod 为 0 (NULL)
        self.hook_id = user32.SetWindowsHookExW(
            WH_KEYBOARD_LL,
            self._hook_proc_ref,
            0,
            0
        )
        if not self.hook_id:
            return

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
