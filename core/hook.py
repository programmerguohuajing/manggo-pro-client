"""
全局低级键盘钩子：全面兼容原版 Manggo 全套经典快捷键体系
- 划词悬浮翻译: Alt + D (原版默认) / Alt + Q
- 截图 OCR 识别: Alt + X (原版默认) / Alt + W
- 语音听写输入: Alt + Space (原版默认)
- 桌面工作台: Alt + Shift + D
- 原地转译: 连续 3 次空格 (Pro 核心)
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

VK_D = 0x44     # D (原版划词 / 工作台)
VK_Q = 0x51     # Q (划词备选)
VK_X = 0x58     # X (原版截图 OCR)
VK_W = 0x57     # W (截图备选)

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

                # 原版快捷键 1: Alt + Space (语音听写输入)
                if self.alt_pressed and vk_code == VK_SPACE:
                    if self.on_voice_input:
                        threading.Thread(target=self.on_voice_input, daemon=True).start()
                    return 1

                # 原版快捷键 2: Alt + X 或 Alt + W (截图 OCR 翻译)
                if self.alt_pressed and vk_code in (VK_X, VK_W):
                    if self.on_screenshot_translate:
                        threading.Thread(target=self.on_screenshot_translate, daemon=True).start()
                    return 1

                # 原版快捷键 3: Alt + Shift + D (呼出桌面翻译工作台)
                if self.alt_pressed and self.shift_pressed and vk_code == VK_D:
                    if self.on_open_main:
                        threading.Thread(target=self.on_open_main, daemon=True).start()
                    return 1

                # 原版快捷键 4: Alt + D (原版默认划词) 或 Alt + Q (划词备选)
                if self.alt_pressed and not self.shift_pressed and vk_code in (VK_D, VK_Q):
                    if self.on_selection_translate:
                        threading.Thread(target=self.on_selection_translate, daemon=True).start()
                    return 1

                # 原版核心 Pro 特性: 连续三次空格就地转译 (非修饰键按下状态)
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
                    # 用户按下了非修饰键的其他普通键，重置空格连击
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
