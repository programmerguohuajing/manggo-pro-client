"""
全局低级键盘钩子：监听连续三次空格（Triple-Space）并触发原地转译
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
WM_SYSKEYDOWN = 0x0104
VK_SPACE = 0x20

# 定义低级键盘钩子结构体
class KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("vkCode", wintypes.DWORD),
        ("scanCode", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(wintypes.ULONG))
    ]

# 钩子回调原型
HOOKPROC = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_int, wintypes.WPARAM, ctypes.POINTER(KBDLLHOOKSTRUCT))

class GlobalKeyboardHook:
    def __init__(self, on_triple_space: Callable[[], None], max_interval: float = 0.55):
        self.on_triple_space = on_triple_space
        self.max_interval = max_interval
        self.space_timestamps = []
        self.hook_id = None
        self._thread = None
        self._running = False
        self._hook_proc_ref = None  # 防止回调函数被 Python GC 回收

    def _hook_callback(self, nCode, wParam, lParam):
        if nCode >= 0 and wParam in (WM_KEYDOWN, WM_SYSKEYDOWN):
            vk_code = lParam.contents.vkCode
            now = time.time()

            if vk_code == VK_SPACE:
                # 过滤超时的时间戳
                self.space_timestamps = [t for t in self.space_timestamps if now - t <= self.max_interval]
                self.space_timestamps.append(now)

                if len(self.space_timestamps) >= 3:
                    # 触发连续三次空格！
                    self.space_timestamps.clear()
                    # 异步通知，绝不阻塞钩子线程
                    threading.Thread(target=self.on_triple_space, daemon=True).start()
            else:
                # 按下了空格之外的键，重置连击计时器
                self.space_timestamps.clear()

        return user32.CallNextHookEx(self.hook_id, nCode, wParam, lParam)

    def _run_hook_loop(self):
        self._hook_proc_ref = HOOKPROC(self._hook_callback)
        self.hook_id = user32.SetWindowsHookExW(
            WH_KEYBOARD_LL,
            self._hook_proc_ref,
            kernel32.GetModuleHandleW(None),
            0
        )
        if not self.hook_id:
            print("[Hook] Failed to install keyboard hook")
            return

        print("[Hook] Global keyboard hook installed successfully. Listening for triple-space...")
        msg = wintypes.MSG()
        while self._running:
            # 消息循环，保证低级钩子正常分发事件
            b_ret = user32.GetMessageW(ctypes.byref(msg), 0, 0, 0)
            if b_ret <= 0:
                break
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))

        if self.hook_id:
            user32.UnhookWindowsHookEx(self.hook_id)
            self.hook_id = None
            print("[Hook] Keyboard hook uninstalled.")

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
            # 发送 WM_QUIT 退出消息泵
            user32.PostThreadMessageW(self._thread.ident, 0x0012, 0, 0)
