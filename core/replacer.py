"""
核心替换模块：负责在 Windows 当前焦点输入框中执行退格、选词、翻译和就地粘贴替换
针对 Electron / Chromium / Claude Desktop / ProseMirror 及原生 Windows 控件全兼容深度优化
"""
import time
import re
import threading
import ctypes
from ctypes import wintypes
from typing import Callable, Optional
import pyperclip

# Windows 虚拟键码常量
VK_BACK = 0x08
VK_SPACE = 0x20
VK_SHIFT = 0x10
VK_CONTROL = 0x11
VK_MENU = 0x12
VK_HOME = 0x24
VK_RIGHT = 0x27
VK_A = 0x41
VK_C = 0x43
VK_V = 0x56

INPUT_KEYBOARD = 1
KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_KEYUP = 0x0002
MAPVK_VK_TO_VSC = 0

# 导航键等扩展键清单（必须传递 KEYEVENTF_EXTENDEDKEY 避免被 NumLock 识别为小键盘数字）
EXTENDED_KEYS = {VK_HOME, VK_RIGHT, 0x23, 0x25, 0x26, 0x28, 0x2D, 0x2E}

class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(wintypes.ULONG))
    ]

class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [
        ("uMsg", wintypes.DWORD),
        ("wParamL", wintypes.WORD),
        ("wParamH", wintypes.WORD)
    ]

class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(wintypes.ULONG))
    ]

class _INPUT_UNION(ctypes.Union):
    _fields_ = [
        ("mi", MOUSEINPUT),
        ("ki", KEYBDINPUT),
        ("hi", HARDWAREINPUT)
    ]

class INPUT(ctypes.Structure):
    _fields_ = [
        ("type", wintypes.DWORD),
        ("u", _INPUT_UNION)
    ]

user32 = ctypes.windll.user32

def _send_key(vk: int, is_up: bool = False):
    """
    使用 SendInput 配合硬件扫描码注入键位事件，确保 Chromium/Electron/ProseMirror 正确解析 DomCode
    """
    scan = user32.MapVirtualKeyW(vk, MAPVK_VK_TO_VSC)
    flags = 0
    if vk in EXTENDED_KEYS:
        flags |= KEYEVENTF_EXTENDEDKEY
    if is_up:
        flags |= KEYEVENTF_KEYUP
    
    inp = INPUT()
    inp.type = INPUT_KEYBOARD
    inp.u.ki = KEYBDINPUT(
        wVk=vk,
        wScan=scan,
        dwFlags=flags,
        time=0,
        dwExtraInfo=None
    )
    user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))

def _press_key(vk: int, times: int = 1, delay: float = 0.02):
    for _ in range(times):
        _send_key(vk, is_up=False)
        time.sleep(0.015)
        _send_key(vk, is_up=True)
        if delay:
            time.sleep(delay)

def _send_combo(mod_vk: int, key_vk: int, hold_delay: float = 0.03, after_delay: float = 0.06):
    _send_key(mod_vk, is_up=False)
    time.sleep(0.02)
    _send_key(key_vk, is_up=False)
    time.sleep(hold_delay)
    _send_key(key_vk, is_up=True)
    time.sleep(0.015)
    _send_key(mod_vk, is_up=True)
    if after_delay:
        time.sleep(after_delay)

def _send_ctrl_c():
    _send_combo(VK_CONTROL, VK_C, hold_delay=0.03, after_delay=0.06)

def _send_ctrl_v():
    _send_combo(VK_CONTROL, VK_V, hold_delay=0.03, after_delay=0.06)

def _send_ctrl_a():
    _send_combo(VK_CONTROL, VK_A, hold_delay=0.03, after_delay=0.06)

def _send_shift_home():
    _send_combo(VK_SHIFT, VK_HOME, hold_delay=0.03, after_delay=0.06)

def _send_ctrl_shift_home():
    _send_key(VK_CONTROL, is_up=False)
    time.sleep(0.015)
    _send_key(VK_SHIFT, is_up=False)
    time.sleep(0.02)
    _send_key(VK_HOME, is_up=False)
    time.sleep(0.03)
    _send_key(VK_HOME, is_up=True)
    time.sleep(0.015)
    _send_key(VK_SHIFT, is_up=True)
    time.sleep(0.015)
    _send_key(VK_CONTROL, is_up=True)
    time.sleep(0.06)

def _safe_paste(timeout: float = 0.35, ignore_val: str = "") -> str:
    start = time.time()
    while time.time() - start < timeout:
        try:
            val = pyperclip.paste()
            if val and val != ignore_val:
                return val
        except Exception:
            pass
        time.sleep(0.025)
    try:
        val = pyperclip.paste()
        return val if val != ignore_val else ""
    except Exception:
        return ""

def _safe_copy(text: str, retries: int = 3):
    for _ in range(retries):
        try:
            pyperclip.copy(text)
            return
        except Exception:
            time.sleep(0.03)

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
            # 1. 微延时确保前台焦点应用完全接收并落入第 3 个空格
            time.sleep(0.05)

            # 2. 消除刚刚输入的 3 个空格
            _press_key(VK_BACK, times=3, delay=0.025)
            # 留出时延让 Chromium/Electron/ProseMirror DOM 树重新排版
            time.sleep(0.06)

            # 备份用户剪贴板
            original_clipboard = ""
            try:
                original_clipboard = pyperclip.paste()
            except Exception:
                pass

            # 准备文本捕获标记
            token = f"__MANGGO_CAP_{time.time()}__"
            _safe_copy(token)
            time.sleep(0.02)

            # 策略一：首先尝试行内向前选区 (Shift + Home)
            _send_shift_home()
            time.sleep(0.07)  # 留出充足时间让 Blink/Electron Selection 状态跨进程同步
            _send_ctrl_c()
            time.sleep(0.06)

            captured = _safe_paste(timeout=0.35, ignore_val=token)

            # 策略二：如果 Shift + Home 没有提取到中文（例如 Claude/Web 等富文本多行或者段落内换行容器），
            # 依次尝试 Ctrl + Shift + Home 向前全选，或 Ctrl + A 全选当前输入框内容
            if not captured or not self.contains_chinese(captured):
                _send_ctrl_shift_home()
                time.sleep(0.07)
                _send_ctrl_c()
                time.sleep(0.06)
                captured_para = _safe_paste(timeout=0.35, ignore_val=token)
                if captured_para and self.contains_chinese(captured_para):
                    captured = captured_para
                else:
                    # 尝试 Ctrl + A (针对 Claude 纯输入气泡，全选当前草稿)
                    _send_ctrl_a()
                    time.sleep(0.07)
                    _send_ctrl_c()
                    time.sleep(0.06)
                    captured_all = _safe_paste(timeout=0.35, ignore_val=token)
                    if captured_all and self.contains_chinese(captured_all):
                        captured = captured_all

            clean_text = captured.strip() if captured else ""

            # 3. 校验是否需要翻译
            if not clean_text or not self.contains_chinese(clean_text):
                # 未选中或不含中文，取消选中状态（按下扩展键 Right 将光标移回末尾）
                _press_key(VK_RIGHT)
                _safe_copy(original_clipboard)
                if self.notify_callback:
                    if clean_text:
                        self.notify_callback("info", f"未包含中文: {clean_text[:12]}")
                    else:
                        self.notify_callback("info", "未检测到输入文字")
                return

            if self.notify_callback:
                self.notify_callback("translating", f"正在转译: {clean_text[:15]}...")

            # 4. 调用翻译
            translated_en = self.translate_func(clean_text)

            if not translated_en or translated_en == clean_text:
                _press_key(VK_RIGHT)
                _safe_copy(original_clipboard)
                if self.notify_callback:
                    self.notify_callback("failed", "转译未得到有效结果")
                return

            # 5. 将英文写入剪贴板并通过就地粘贴替换已选中文本
            _safe_copy(translated_en)
            time.sleep(0.04)
            _send_ctrl_v()

            if self.notify_callback:
                self.notify_callback("success", f"已转译为英文: {translated_en[:20]}...")

            # 延迟 0.6 秒确保 Chromium 等重型富文本宿主完全消费剪贴板后，再恢复用户原剪贴板
            time.sleep(0.6)
            _safe_copy(original_clipboard)

        except Exception as e:
            if self.notify_callback:
                self.notify_callback("error", f"转译异常: {e}")
        finally:
            self.is_busy = False
