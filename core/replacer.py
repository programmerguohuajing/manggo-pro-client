"""
核心替换模块：负责在 Windows 当前焦点输入框中执行退格、选词、翻译和就地粘贴替换
"""
import time
import re
import threading
import ctypes
from typing import Callable, Optional
import win32api
import win32con
import pyperclip

# Windows 虚拟键码常量
VK_BACK = 0x08
VK_SPACE = 0x20
VK_SHIFT = 0x10
VK_CONTROL = 0x11
VK_HOME = 0x24
VK_RIGHT = 0x27
VK_C = 0x43
VK_V = 0x56

KEYEVENTF_KEYUP = 0x0002

def _key_down(vk_code: int):
    ctypes.windll.user32.keybd_event(vk_code, 0, 0, 0)

def _key_up(vk_code: int):
    ctypes.windll.user32.keybd_event(vk_code, 0, KEYEVENTF_KEYUP, 0)

def _press_key(vk_code: int, times: int = 1, delay: float = 0.02):
    for _ in range(times):
        _key_down(vk_code)
        time.sleep(0.01)
        _key_up(vk_code)
        if delay:
            time.sleep(delay)

def _send_ctrl_c():
    _key_down(VK_CONTROL)
    time.sleep(0.02)
    _press_key(VK_C, delay=0.02)
    time.sleep(0.02)
    _key_up(VK_CONTROL)
    time.sleep(0.05)

def _send_ctrl_v():
    _key_down(VK_CONTROL)
    time.sleep(0.02)
    _press_key(VK_V, delay=0.02)
    time.sleep(0.02)
    _key_up(VK_CONTROL)
    time.sleep(0.05)

def _send_shift_home():
    _key_down(VK_SHIFT)
    time.sleep(0.02)
    _press_key(VK_HOME, delay=0.02)
    time.sleep(0.02)
    _key_up(VK_SHIFT)
    time.sleep(0.05)

class InPlaceReplacer:
    """
    就地转译替换器
    """
    def __init__(self, translate_func: Callable[[str], str], notify_callback: Optional[Callable[[str, str], None]] = None):
        self.translate_func = translate_func
        self.notify_callback = notify_callback
        self.is_busy = False

    def contains_chinese(self, text: str) -> bool:
        return bool(re.search(r'[\u4e00-\u9fa5]', text))

    def trigger_triple_space_replace(self):
        """
        触发三次空格快速转译逻辑（在独立子线程中运行）
        """
        if self.is_busy:
            return
        threading.Thread(target=self._do_replace_flow, daemon=True).start()

    def _do_replace_flow(self):
        self.is_busy = True
        try:
            # 1. 消除刚刚输入的 3 个空格
            _press_key(VK_BACK, times=3, delay=0.02)
            time.sleep(0.05)

            # 备份用户剪贴板
            original_clipboard = ""
            try:
                original_clipboard = pyperclip.paste()
            except Exception:
                pass

            # 2. 检查是否有用户先前鼠标高亮选中的文本
            # 先用一个独特哨兵标记清空剪贴板
            sentinel = f"__MANGGO_CAPTURE_{time.time()}__"
            pyperclip.copy(sentinel)
            time.sleep(0.02)

            _send_ctrl_c()
            captured = pyperclip.paste()

            selected_mode = False
            # 如果复制到了不是哨兵的文本，说明用户事先已经选中文本
            if captured and captured != sentinel:
                selected_mode = True
                text_to_translate = captured
            else:
                # 否则说明用户是在句尾未选中文本状态，发送 Shift + Home 选中当前行光标前文本
                _send_shift_home()
                _send_ctrl_c()
                captured_line = pyperclip.paste()
                if captured_line and captured_line != sentinel:
                    text_to_translate = captured_line
                else:
                    text_to_translate = ""

            clean_text = text_to_translate.strip()
            # 3. 校验是否需要翻译
            if not clean_text or not self.contains_chinese(clean_text):
                # 如果没有选中或不含中文，取消选中状态（按下 Right 键将光标移至末尾）
                if not selected_mode and clean_text:
                    _press_key(VK_RIGHT)
                # 恢复用户原剪贴板
                try:
                    pyperclip.copy(original_clipboard)
                except Exception:
                    pass
                return

            if self.notify_callback:
                self.notify_callback("translating", f"正在转译: {clean_text[:15]}...")

            # 4. 调用翻译
            translated_en = self.translate_func(clean_text)

            if not translated_en or translated_en == clean_text:
                if not selected_mode:
                    _press_key(VK_RIGHT)
                if self.notify_callback:
                    self.notify_callback("failed", "转译未得到有效结果")
                return

            # 5. 将英文写入剪贴板并粘贴替换
            pyperclip.copy(translated_en)
            time.sleep(0.04)
            _send_ctrl_v()

            if self.notify_callback:
                self.notify_callback("success", f"已转译为英文: {translated_en[:20]}...")

            # 延迟恢复剪贴板
            time.sleep(0.6)
            try:
                pyperclip.copy(original_clipboard)
            except Exception:
                pass

        except Exception as e:
            print(f"[Replacer] Error during in-place translation: {e}")
            if self.notify_callback:
                self.notify_callback("error", f"转译异常: {e}")
        finally:
            self.is_busy = False
