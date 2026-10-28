"""
核心替换模块：负责在 Windows 当前焦点输入框中执行退格、选词、翻译和就地粘贴替换
针对 Electron / Chromium / Claude Desktop / ProseMirror 及原生 Windows 控件全兼容深度优化
"""
import os
import time
import re
import threading
import ctypes
from ctypes import wintypes
from typing import Callable, Optional
import pyperclip

from core.logging import info as _log_info, warning as _log_warning, debug as _log_debug
from core.platform import IS_WINDOWS

def _log(msg: str):
    _log_info("REPLACER", msg)

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
VK_ESCAPE = 0x1B

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

user32 = ctypes.windll.user32 if IS_WINDOWS else None
kernel32 = ctypes.windll.kernel32 if IS_WINDOWS else None
if IS_WINDOWS:
    user32.SendInput.argtypes = [wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int]
    user32.SendInput.restype = wintypes.UINT
    user32.GetClipboardSequenceNumber.restype = wintypes.DWORD
    # 下面两个是黑名单新用的 API，其他模块没用过，设 argtypes 不影响别处。
    kernel32.QueryFullProcessImageNameW.argtypes = [
        wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR,
        ctypes.POINTER(wintypes.DWORD),
    ]
    kernel32.QueryFullProcessImageNameW.restype = wintypes.BOOL

def _release_modifiers():
    """彻底释放物理与逻辑修饰键 (Alt, Ctrl, Shift)"""
    for vk in (0xA4, 0xA5, 0x12, 0xA2, 0xA3, 0x11, 0xA0, 0xA1, 0x10):
        user32.keybd_event(vk, 0, KEYEVENTF_KEYUP, 0)

def _send_key(vk: int, is_up: bool = False):
    scan = user32.MapVirtualKeyW(vk, MAPVK_VK_TO_VSC)
    flags = 0
    if vk in EXTENDED_KEYS:
        flags |= KEYEVENTF_EXTENDEDKEY
    if is_up:
        flags |= KEYEVENTF_KEYUP
    user32.keybd_event(vk, scan, flags, 0)

def _press_key(vk: int, times: int = 1, delay: float = 0.02):
    for _ in range(times):
        _send_key(vk, is_up=False)
        time.sleep(0.015)
        _send_key(vk, is_up=True)
        if delay:
            time.sleep(delay)

def _send_ctrl_c():
    _release_modifiers()
    time.sleep(0.02)
    user32.keybd_event(VK_CONTROL, 0x1D, 0, 0)
    time.sleep(0.02)
    user32.keybd_event(VK_C, 0x2E, 0, 0)
    time.sleep(0.04)
    user32.keybd_event(VK_C, 0x2E, KEYEVENTF_KEYUP, 0)
    time.sleep(0.02)
    user32.keybd_event(VK_CONTROL, 0x1D, KEYEVENTF_KEYUP, 0)
    time.sleep(0.04)

def _send_ctrl_c_input():
    """划选复制专用 Ctrl+C：走 SendInput，不走老 keybd_event。

    根因（2026-10-28，用户实测定性）：keybd_event 发出的 Ctrl+C 在 Claude
    Desktop 和新版 WinUI 记事本里完全没产生复制（失败后原地 Ctrl+V 什么
    都粘不出来），而同一路径在 Antigravity 里正常、手动 Ctrl+C 在哪都正常。
    keybd_event 是已被取代的老 API；SendInput 才是系统输入流期望的注入
    方式。分两批发送（按下组合 → 停 50ms → 抬起组合），让目标程序看到
    Ctrl 按住的状态下 C 到达。仅供划选翻译使用；就地替换的三次空格流
    程目前工作正常，继续走老 _send_ctrl_c，不动它。
    """
    if not IS_WINDOWS:
        return 0
    ctrl_scan = user32.MapVirtualKeyW(VK_CONTROL, MAPVK_VK_TO_VSC)
    c_scan = user32.MapVirtualKeyW(VK_C, MAPVK_VK_TO_VSC)

    def _inp(vk, scan, flags):
        item = INPUT()
        item.type = INPUT_KEYBOARD
        item.u.ki = KEYBDINPUT(wVk=vk, wScan=scan, dwFlags=flags, time=0, dwExtraInfo=None)
        return item

    down = (INPUT * 2)(_inp(VK_CONTROL, ctrl_scan, 0), _inp(VK_C, c_scan, 0))
    n_down = user32.SendInput(2, down, ctypes.sizeof(INPUT))
    time.sleep(0.05)
    up = (INPUT * 2)(_inp(VK_C, c_scan, KEYEVENTF_KEYUP), _inp(VK_CONTROL, ctrl_scan, KEYEVENTF_KEYUP))
    n_up = user32.SendInput(2, up, ctypes.sizeof(INPUT))
    _log(f"SendInput Ctrl+C: down={n_down}/2 up={n_up}/2")
    return n_down + n_up


VK_MASK = 0xE8  # 未分配键（AutoHotkey MenuMaskKey 同款）

def _send_mask_key():
    """注入一次掩码键 0xE8（按下+抬起），供 Alt 组合键触发时调用。

    必须在 Alt 还按着时发、且走 SendInput（带注入标记，钩子自身会
    按 flags & 0x10 过滤掉，不会循环触发）。对目标程序无可见效果，
    只改变 Alt 的“裸按”判定：此后不管 Alt 何时松开，程序都不会
    把它当成光秃秃的 Alt 而进菜单模式。
    """
    if not IS_WINDOWS:
        return
    scan = user32.MapVirtualKeyW(VK_MASK, MAPVK_VK_TO_VSC)

    def _inp(vk, scan, flags):
        item = INPUT()
        item.type = INPUT_KEYBOARD
        item.u.ki = KEYBDINPUT(wVk=vk, wScan=scan, dwFlags=flags, time=0, dwExtraInfo=None)
        return item

    down = (INPUT * 1)(_inp(VK_MASK, scan, 0))
    user32.SendInput(1, down, ctypes.sizeof(INPUT))
    up = (INPUT * 1)(_inp(VK_MASK, scan, KEYEVENTF_KEYUP))
    user32.SendInput(1, up, ctypes.sizeof(INPUT))


def _send_ctrl_v():
    _release_modifiers()
    time.sleep(0.02)
    user32.keybd_event(VK_CONTROL, 0x1D, 0, 0)
    time.sleep(0.02)
    user32.keybd_event(VK_V, 0x2F, 0, 0)
    time.sleep(0.05)
    user32.keybd_event(VK_V, 0x2F, KEYEVENTF_KEYUP, 0)
    time.sleep(0.02)
    user32.keybd_event(VK_CONTROL, 0x1D, KEYEVENTF_KEYUP, 0)
    time.sleep(0.04)

def _send_shift_home():
    _release_modifiers()
    time.sleep(0.02)
    user32.keybd_event(VK_SHIFT, 0x2A, 0, 0)
    time.sleep(0.02)
    user32.keybd_event(VK_HOME, 0x47, KEYEVENTF_EXTENDEDKEY, 0)
    time.sleep(0.04)
    user32.keybd_event(VK_HOME, 0x47, KEYEVENTF_EXTENDEDKEY | KEYEVENTF_KEYUP, 0)
    time.sleep(0.02)
    user32.keybd_event(VK_SHIFT, 0x2A, KEYEVENTF_KEYUP, 0)
    time.sleep(0.04)

def _send_ctrl_a():
    # 全选当前输入框（2026-10-28：文本域整框翻译用，替代旧的 Ctrl+Shift+Home）。
    _release_modifiers()
    time.sleep(0.02)
    user32.keybd_event(VK_CONTROL, 0x1D, 0, 0)
    time.sleep(0.015)
    user32.keybd_event(VK_A, 0x1E, 0, 0)
    time.sleep(0.04)
    user32.keybd_event(VK_A, 0x1E, KEYEVENTF_KEYUP, 0)
    time.sleep(0.015)
    user32.keybd_event(VK_CONTROL, 0x1D, KEYEVENTF_KEYUP, 0)
    time.sleep(0.04)

def _wait_for_clipboard_change(old_seq: int, timeout: float = 0.35) -> str:
    start = time.time()
    while time.time() - start < timeout:
        if user32.GetClipboardSequenceNumber() != old_seq:
            try:
                val = pyperclip.paste()
                if val:
                    return val
            except Exception as e:
                # 重试循环里的失败：记 debug，不刷屏，耗尽后返回 "" 即信号。
                _log_debug("CLIPBOARD", f"paste retry failed: {e}")
        time.sleep(0.02)
    return ""

def _safe_copy(text: str, retries: int = 3):
    for _ in range(retries):
        try:
            pyperclip.copy(text)
            return
        except Exception:
            time.sleep(0.03)

# 三次空格黑名单（2026-10-28 review 问题4）：终端里无选区的 Ctrl+C 是
# 中断信号（会中断正在跑的程序），绝不能往终端里发按键；密码框同理避开。
# VS Code 内嵌终端与编辑器同属一个窗口，类名/进程无法区分，不在覆盖内。
_TERMINAL_CLASSES = {"ConsoleWindowClass", "CASCADIA_HOSTING_WINDOW_CLASS"}
_TERMINAL_EXES = {
    "windowsterminal.exe", "wt.exe", "conhost.exe", "cmd.exe",
    "powershell.exe", "pwsh.exe", "alacritty.exe", "wezterm-gui.exe",
    "wezterm.exe", "kitty.exe", "mintty.exe", "hyper.exe",
}
ES_PASSWORD = 0x20
GWL_STYLE = -16
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000


class GUITHREADINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("hwndActive", wintypes.HWND),
        ("hwndFocus", wintypes.HWND),
        ("hwndCapture", wintypes.HWND),
        ("hwndMenuOwner", wintypes.HWND),
        ("hwndMoveSize", wintypes.HWND),
        ("hwndCaret", wintypes.HWND),
    ]

if IS_WINDOWS:
    # GUITHREADINFO 在此处才定义，故 argtypes 在这里设（前面 windll 块设不了）。
    user32.GetGUIThreadInfo.argtypes = [wintypes.DWORD, ctypes.POINTER(GUITHREADINFO)]
    user32.GetGUIThreadInfo.restype = wintypes.BOOL


def _fg_process_name(pid):
    """取前台窗口进程的可执行文件名；拿不到返回 ''（调用方放行）。"""
    if not IS_WINDOWS or not pid:
        return ""
    try:
        h = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if not h:
            return ""
        try:
            buf = ctypes.create_unicode_buffer(512)
            size = wintypes.DWORD(512)
            if kernel32.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(size)):
                return os.path.basename(buf.value).lower()
            return ""
        finally:
            kernel32.CloseHandle(h)
    except Exception:
        return ""


def _is_blacklisted_window(hwnd, cls_name, pid, thread_id):
    """终端 / 密码框返回 True（跳过就地转译，不发任何按键）。

    终端：类名或进程名命中即算。密码框：用 GetGUIThreadInfo 拿该线程
    的焦点控件，是 Edit 类且带 ES_PASSWORD 样式即算。任一 API 失败都
    放行（fail-open）：误拦会让正常输入框无法转译，漏拦只影响密码框
    那种 Ctrl+C 本来就复制不到内容的场景。
    """
    if not IS_WINDOWS:
        return False
    try:
        if (cls_name or "") in _TERMINAL_CLASSES:
            return True
        if _fg_process_name(pid) in _TERMINAL_EXES:
            return True
        info = GUITHREADINFO()
        info.cbSize = ctypes.sizeof(GUITHREADINFO)
        if user32.GetGUIThreadInfo(thread_id, ctypes.byref(info)) and info.hwndFocus:
            focus_cls = ctypes.create_unicode_buffer(256)
            if user32.GetClassNameW(info.hwndFocus, focus_cls, 256):
                if focus_cls.value in ("Edit", "RichEdit20W", "RichEdit20A", "RICHEDIT50W"):
                    style = user32.GetWindowLongW(info.hwndFocus, GWL_STYLE)
                    if style & ES_PASSWORD:
                        return True
        return False
    except Exception:
        return False


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
        if not IS_WINDOWS:
            _log_warning("REPLACER", "In-place replace is Windows-only")
            if self.notify_callback:
                self.notify_callback("error", "就地转译仅支持 Windows")
            return
        if self.is_busy:
            return
        threading.Thread(target=self._do_replace_flow, daemon=True).start()

    def _do_replace_flow(self):
        self.is_busy = True
        # 剪贴板恢复策略：只有流程中途放弃、且用户此后没动过剪贴板时，
        # 才把备份写回去；成功粘贴、或窗口切换后留给用户手动粘贴时不恢复。
        keep_clipboard = False
        have_backup = False
        original_clipboard = ""
        last_flow_seq = 0
        try:
            # 获取当前前台窗口信息，用于精准诊断
            fg = user32.GetForegroundWindow()
            title_buf = ctypes.create_unicode_buffer(512)
            user32.GetWindowTextW(fg, title_buf, 512)
            cls_buf = ctypes.create_unicode_buffer(512)
            user32.GetClassNameW(fg, cls_buf, 512)
            pid = wintypes.DWORD()
            fg_thread = user32.GetWindowThreadProcessId(fg, ctypes.byref(pid))
            _log(f"Triggered! Foreground: class='{cls_buf.value}', hwnd={fg:#x}, pid={pid.value}")

            # 黑名单先行：在发任何按键、碰剪贴板之前就拦下来。
            if _is_blacklisted_window(fg, cls_buf.value, pid.value, fg_thread):
                _log("Aborted: foreground window is blacklisted (terminal/password)")
                if self.notify_callback:
                    self.notify_callback("failed", "当前窗口不支持就地转译（终端或密码框），已跳过")
                return

            # 1. 微延时确保前台焦点应用完全接收按键，并彻底释放所有修饰键
            time.sleep(0.04)
            _release_modifiers()
            time.sleep(0.02)

            # 备份用户剪贴板
            try:
                original_clipboard = pyperclip.paste()
                have_backup = True
            except Exception as e:
                _log_debug("CLIPBOARD", f"backup failed, restore will be skipped: {e}")
            last_flow_seq = user32.GetClipboardSequenceNumber()

            # 策略一：首先尝试行内向前选区 (Shift + Home)
            # 注：不预先盲目发送退格键，因为 Shift+Home 会同时选中末尾的空格，
            # 翻译后的 Ctrl+V 会整段一次性替换包含空格的选区，彻底避免退格误删中文字符！
            old_seq = user32.GetClipboardSequenceNumber()
            _send_shift_home()
            time.sleep(0.05)
            _send_ctrl_c()

            captured = _wait_for_clipboard_change(old_seq, timeout=0.35)
            _log(f"Strategy 1 (Shift+Home) captured {len(captured) if captured else 0} chars")

            # 策略二：整个输入框（Ctrl+A）。文本域（多行输入框）里光标只在一行，
            # 只译光标行是 bug：用户要的是整个输入框的文本，不是光标行。
            # Ctrl+A 在单行输入框里等于行选区，结果不变；多行输入框里拿到全文。
            # 旧的 Ctrl+Shift+Home 只选到文档开头（光标后的文本丢了），已被替代。
            # 守卫：必须含中文且 < 2000 字，否则退回行选区——长文档不整篇替换
            # （2000 字以上的文档仍只译光标行）。取舍说明：2000 字以内的短文档
            # 也会整篇翻译；如需“文档只译行、输入框才整篇”，得另加控件类型识别。
            old_seq = user32.GetClipboardSequenceNumber()
            _send_ctrl_a()
            time.sleep(0.05)
            _send_ctrl_c()
            captured_all = _wait_for_clipboard_change(old_seq, timeout=0.35)
            _log(f"Strategy 2 (Ctrl+A) captured {len(captured_all) if captured_all else 0} chars")
            if captured_all and self.contains_chinese(captured_all) and len(captured_all) < 2000:
                captured = captured_all

            last_flow_seq = user32.GetClipboardSequenceNumber()
            clean_text = captured.strip() if captured else ""
            _log(f"Final clean_text: {len(clean_text)} chars, has_chinese={self.contains_chinese(clean_text)}")

            # 2. 校验是否需要翻译
            if not clean_text or not self.contains_chinese(clean_text):
                _press_key(VK_RIGHT)
                _log("Aborted: clean_text empty or contains no Chinese")
                return

            # 3. 调用翻译 (保持前台焦点稳定，绝不弹出夺焦 Toast 弹窗)
            _log(f"Translating text: {len(clean_text)} chars")
            translated_en = self.translate_func(clean_text)
            _log(f"Translated result: {len(translated_en) if translated_en else 0} chars")

            if not translated_en or translated_en == clean_text:
                _press_key(VK_RIGHT)
                _log("Aborted: translation returned empty or identical text")
                return

            # 4. 将英文写入剪贴板并通过就地粘贴替换已选中文本（同时覆盖原中文及末尾空格）
            _safe_copy(translated_en)
            time.sleep(0.05)
            # 粘贴前再校验前台窗口：翻译耗时里用户可能切走了窗口，
            # 直接 Ctrl+V 会把译文粘到别处。切走了就不自动粘贴，
            # 译文留在剪贴板供用户手动粘贴。
            if user32.GetForegroundWindow() != fg:
                _log("Aborted paste: foreground window changed during translation")
                if self.notify_callback:
                    self.notify_callback("failed", "窗口已切换，未自动粘贴，译文已保留在剪贴板")
                keep_clipboard = True
                return
            _send_ctrl_v()
            _log("Sent Ctrl+V to paste English translation successfully")
            # 翻译后的文本保留在剪贴板中供用户直接使用，绝不在后台强制回滚导致粘贴竞争失败
            keep_clipboard = True

        except Exception as e:
            _log(f"Exception during replace flow: {e}")
            if self.notify_callback:
                self.notify_callback("error", f"转译异常: {e}")
        finally:
            if have_backup and not keep_clipboard:
                try:
                    # 只有用户此后没动过剪贴板时才恢复，避免覆盖用户新复制的内容。
                    if user32.GetClipboardSequenceNumber() == last_flow_seq:
                        pyperclip.copy(original_clipboard)
                except Exception as e:
                    _log_warning("CLIPBOARD", f"restore failed, translation left on clipboard: {e}")
            self.is_busy = False
