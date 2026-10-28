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

from core.logging import debug as _log_debug, info as _log_info, warning as _log_warning
from core.platform import IS_WINDOWS
from core.replacer import _send_mask_key
from core.hotkeys import (
    ACTION_ORDER,
    normalize_hotkeys,
    parse_hotkey,
)

user32 = ctypes.windll.user32 if IS_WINDOWS else None
kernel32 = ctypes.windll.kernel32 if IS_WINDOWS else None

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

        # 运行时状态只在这里初始化一次。之前这些写在 update_hotkeys 里，
        # 设置页一保存就把 _running / hook_id / _thread 清零：钩子线程其实
        # 还在跑，托盘“暂停”因 _running=False 直接 return 停不掉，“恢复”
        # 又会再起一个钩子线程，导致同一组合键触发两次。
        self.space_count = 0
        self.last_space_time = 0.0
        self.last_key_was_char = False
        self.alt_pressed = False
        self.shift_pressed = False
        # 已触发、尚未抬起的组合键主键：按住不放时键盘自动重复的 keydown
        # 只吞掉、不再重复触发回调。
        self._held_hotkey_vks = set()

        self.hook_id = None
        self._thread = None
        self._running = False
        self._hook_proc_ref = None
        # 动作 -> (修饰键集合, 主键虚拟键码, 回调, 显示用组合键)
        self._hotkey_table = []
        self.hotkeys: Dict[str, str] = {}
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

                # 全量记录键盘击键日志便于诊断
                _log_debug("HOOK", f"Key: vk={vk_code:#x}, alt={alt_down}, ctrl={ctrl_down}, shift={shift_down}")

                # 组合键：修饰键集合必须严格相等才触发，避免 Alt+Shift+Q
                # 之类的按键同时触发 Alt+Q 的动作。
                for mods, vk, callback, label in self._hotkey_table:
                    if vk_code == vk and mods_down == mods:
                        if vk_code in self._held_hotkey_vks:
                            # 自动重复：吞掉，不重复触发
                            return 1
                        self._held_hotkey_vks.add(vk_code)
                        if "Alt" in mods:
                            # Alt 仍按着时插入菜单屏蔽键，Alt 抬起时目标程序
                            # 不会进入菜单模式（见 replacer._send_mask_key）。
                            try:
                                _send_mask_key()
                            except Exception as e:
                                _log_warning("HOOK", f"mask key failed: {e}")
                        _log_info("HOOK", f">>> Hotkey {label} triggered! <<<")
                        if callback:
                            threading.Thread(target=callback, daemon=True).start()
                        return 1

                # 连续三次空格就地转译 (无 Alt / Ctrl 干扰)
                if vk_code == VK_SPACE and not alt_down and not ctrl_down:
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
                        _log_info("HOOK", f"[HOOK] Reset space_count (from {self.space_count}) on key vk={vk_code:#x}")
                    self.space_count = 0
                    self.last_space_time = 0.0
            elif vk_code in self._held_hotkey_vks:
                # 组合键主键抬起：复位，下次按下可再次触发
                self._held_hotkey_vks.discard(vk_code)

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
            _log_info("HOOK", f"SetWindowsHookExW failed with error: {kernel32.GetLastError()}")
            return
        _log_info("HOOK", f"Hook installed successfully: hook_id={self.hook_id}")

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
        _log_info("HOOK", "Hook loop finished")

    def start(self):
        if not IS_WINDOWS:
            # macOS / Linux 没有 WH_KEYBOARD_LL：钩子不安装，界面与翻译仍可用。
            _log_warning("HOOK", "Global hotkeys are Windows-only; hook disabled on this platform")
            return
        if self._running:
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
