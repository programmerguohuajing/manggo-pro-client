"""macOS Accessibility (AX) 静默文本通道：不发按键、不动剪贴板，
直接读写当前焦点元素的文本。

为什么需要它：剪贴板流程靠合成 Cmd+C / Cmd+A / Cmd+V 驱动目标
应用，这些都是菜单快捷键——macOS 会让对应的「编辑」菜单随每一个
快捷键闪烁一次，一次替换要发近十个，菜单栏全程闪个不停（用户
1.0.37 视频反馈，文本编辑与 Typora 皆然）。AX 路径直接读焦点
元素的 AXValue / 选区、把选区设到目标区段、写入译文，全程没有
一个组合键，也完全不碰剪贴板（顺带不再覆盖用户剪贴板内容）。

支持度如实说明：AX 在不同应用上的可写性参差不齐（原生
NSTextView 最稳，Electron/Chromium 看版本）。所以本模块只做
「尝试 + 回读校验」：写完必须回读全文与预期逐字一致才算成功，
选区写入不达标再试整值写入，两者都不行就返回 False，由调用方
完整回退到剪贴板流程——行为最差也与没有本模块时一致。

索引约定：AX 的文本范围是 UTF-16 码元下标，本模块内部用 Python
字符下标计算区段；当目标文本前文含非 BMP 字符（emoji 等）时
选区写入的下标可能偏移——回读校验会拦下这种不一致并转整值
写入（整值写入只认字符串本身，与下标单位无关），不会写错。

签名纪律（与 hook_macos 同规矩）：每个带指针参数的函数都在实际
使用的句柄实例上声明 argtypes/restype；声明不跨 CDLL 实例共享。
本模块只在 macOS 被调用方 import 使用，其他平台 import 不崩。
"""

import ctypes
import ctypes.util
import time
from typing import Callable, Optional

from core.logging import debug as _log_debug, info as _log_info

_AXVALUE_CF_RANGE = 4  # kAXValueTypeCFRange
_KCF_UTF8 = 0x08000100  # kCFStringEncodingUTF8
_AX_OK = 0

_ATTR_FOCUSED = "AXFocusedUIElement"
_ATTR_VALUE = "AXValue"
_ATTR_SELECTED_RANGE = "AXSelectedTextRange"
_ATTR_SELECTED_TEXT = "AXSelectedText"


def _load(name):
    path = ctypes.util.find_library(name)
    if not path:
        return None
    try:
        return ctypes.CDLL(path)
    except Exception:
        return None


class _CFRange(ctypes.Structure):
    _fields_ = [("location", ctypes.c_long), ("length", ctypes.c_long)]


def _services():
    lib = _load("ApplicationServices")
    if lib is None:
        return None
    lib.AXUIElementCreateSystemWide.restype = ctypes.c_void_p
    lib.AXUIElementCreateSystemWide.argtypes = []
    lib.AXUIElementCopyAttributeValue.restype = ctypes.c_int
    lib.AXUIElementCopyAttributeValue.argtypes = [
        ctypes.c_void_p, ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p)
    ]
    lib.AXUIElementSetAttributeValue.restype = ctypes.c_int
    lib.AXUIElementSetAttributeValue.argtypes = [
        ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p
    ]
    lib.AXValueCreate.restype = ctypes.c_void_p
    lib.AXValueCreate.argtypes = [ctypes.c_int, ctypes.c_void_p]
    lib.AXValueGetValue.restype = ctypes.c_bool
    lib.AXValueGetValue.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p]
    return lib


def _cf():
    lib = _load("CoreFoundation")
    if lib is None:
        return None
    lib.CFStringCreateWithCString.restype = ctypes.c_void_p
    lib.CFStringCreateWithCString.argtypes = [
        ctypes.c_void_p, ctypes.c_char_p, ctypes.c_uint32
    ]
    lib.CFStringGetLength.restype = ctypes.c_long
    lib.CFStringGetLength.argtypes = [ctypes.c_void_p]
    lib.CFStringGetCString.restype = ctypes.c_bool
    lib.CFStringGetCString.argtypes = [
        ctypes.c_void_p, ctypes.c_char_p, ctypes.c_long, ctypes.c_uint32
    ]
    lib.CFGetTypeID.restype = ctypes.c_ulong
    lib.CFGetTypeID.argtypes = [ctypes.c_void_p]
    lib.CFStringGetTypeID.restype = ctypes.c_ulong
    lib.CFStringGetTypeID.argtypes = []
    lib.CFRelease.argtypes = [ctypes.c_void_p]
    return lib


class _Ax:
    """一次 AX 会话：持有框架句柄与全部自有 CF 引用，close 时统一释放。"""

    def __init__(self):
        self.ax = _services()
        self.cf = _cf()
        if self.ax is None or self.cf is None:
            raise RuntimeError("AX frameworks unavailable")
        self._owned = []

    def own(self, ref):
        if ref:
            self._owned.append(ref)
        return ref

    def close(self):
        for ref in reversed(self._owned):
            try:
                self.cf.CFRelease(ref)
            except Exception:
                pass
        self._owned = []

    def cfstr(self, text: str):
        return self.own(
            self.cf.CFStringCreateWithCString(None, text.encode("utf-8"), _KCF_UTF8)
        )

    def to_str(self, ref) -> Optional[str]:
        if not ref:
            return None
        try:
            if self.cf.CFGetTypeID(ref) != self.cf.CFStringGetTypeID():
                return None
            size = int(self.cf.CFStringGetLength(ref)) * 4 + 2
            buf = ctypes.create_string_buffer(size)
            if not self.cf.CFStringGetCString(ref, buf, size, _KCF_UTF8):
                return None
            return buf.value.decode("utf-8", errors="replace")
        except Exception:
            return None

    def get_attr(self, element, name):
        """返回 (err, value_ref)；value_ref 归本会话持有。"""
        out = ctypes.c_void_p()
        err = self.ax.AXUIElementCopyAttributeValue(
            element, self.cfstr(name), ctypes.byref(out)
        )
        if err != _AX_OK or not out.value:
            return err, None
        return err, self.own(out.value)

    def set_attr(self, element, name, value_ref) -> int:
        return self.ax.AXUIElementSetAttributeValue(
            element, self.cfstr(name), value_ref
        )

    def focused(self):
        system = self.own(self.ax.AXUIElementCreateSystemWide())
        if not system:
            return None
        err, el = self.get_attr(system, _ATTR_FOCUSED)
        return el if err == _AX_OK else None

    def get_range(self, element):
        err, ref = self.get_attr(element, _ATTR_SELECTED_RANGE)
        if err != _AX_OK or not ref:
            return None
        rng = _CFRange()
        if not self.ax.AXValueGetValue(ref, _AXVALUE_CF_RANGE, ctypes.byref(rng)):
            return None
        return int(rng.location), int(rng.length)

    def make_range(self, loc, length):
        return self.own(
            self.ax.AXValueCreate(_AXVALUE_CF_RANGE, ctypes.byref(_CFRange(loc, length)))
        )

    def read_value(self, element) -> Optional[str]:
        err, ref = self.get_attr(element, _ATTR_VALUE)
        if err != _AX_OK:
            return None
        return self.to_str(ref)

    def reread_equals(self, element, expected: str) -> bool:
        # 个别应用应用 AX 写入略有延迟，给三次短轮询。
        for i in range(3):
            if self.read_value(element) == expected:
                return True
            if i < 2:
                time.sleep(0.03)
        return False


def plan_replace(value: str, sel_loc: int, sel_len: int,
                 contains_chinese: Callable[[str], bool]):
    """纯逻辑：决定替换区段与待译文本（与剪贴板流程同语义）。

    优先全文（短于 2000 字且含中文时整段替换，与剪贴板流程的最终
    偏好一致）；否则用光标所在行（行首到光标）。替换区段包含区段
    内的空格——触发用的三个空格在区段内，会被译文一并顶掉，与
    粘贴替换的效果一致。无中文可译时返回 None。
    """
    caret = sel_loc + max(sel_len, 0)
    caret = min(max(caret, 0), len(value))
    if len(value) < 2000 and contains_chinese(value):
        start, length, text = 0, len(value), value
    else:
        line_start = value.rfind("\n", 0, caret) + 1
        start, length = line_start, caret - line_start
        text = value[line_start:caret]
    clean = text.strip()
    if not clean or not contains_chinese(clean):
        return None
    return {"start": start, "length": length, "clean": clean}


def read_focused_selection() -> Optional[str]:
    """读焦点元素的选中文本（划选翻译的静默抓取）；失败返回 None。"""
    try:
        s = _Ax()
    except Exception:
        return None
    try:
        el = s.focused()
        if el is None:
            return None
        err, ref = s.get_attr(el, _ATTR_SELECTED_TEXT)
        text = s.to_str(ref) if err == _AX_OK else None
        if text:
            return text
        # 退而求其次：全文 + 选区范围切片。
        sel = s.get_range(el)
        value = s.read_value(el)
        if sel is not None and value is not None and sel[1] > 0:
            piece = value[sel[0]:sel[0] + sel[1]]
            return piece or None
        return None
    except Exception as e:
        _log_debug("AX", f"read_focused_selection failed: {e}")
        return None
    finally:
        s.close()


def try_replace_focused(translate_func: Callable[[str], str],
                        contains_chinese: Callable[[str], bool]) -> bool:
    """AX 静默替换：成功 True；不适用/失败 False（调用方回退剪贴板流程）。"""
    try:
        s = _Ax()
    except Exception:
        return False
    try:
        el = s.focused()
        if el is None:
            _log_debug("AX", "no focused element")
            return False
        value = s.read_value(el)
        if value is None:
            _log_debug("AX", "focused element value unreadable")
            return False
        sel = s.get_range(el)
        if sel is None:
            _log_debug("AX", "selection range unreadable")
            return False
        plan = plan_replace(value, sel[0], sel[1], contains_chinese)
        if plan is None:
            _log_debug("AX", "nothing to translate in focused element")
            return False
        translated = translate_func(plan["clean"])
        if not translated or translated == plan["clean"]:
            _log_debug("AX", "translation empty or identical")
            return False
        start, length = plan["start"], plan["length"]
        expected = value[:start] + translated + value[start + length:]
        # 写入一：把选区设到目标区段，再写 AXSelectedText（等价于对
        # 选区打字，不经剪贴板、不发组合键）。
        ok = False
        range_ref = s.make_range(start, length)
        if range_ref and s.set_attr(el, _ATTR_SELECTED_RANGE, range_ref) == _AX_OK:
            text_ref = s.cfstr(translated)
            if text_ref and s.set_attr(el, _ATTR_SELECTED_TEXT, text_ref) == _AX_OK:
                ok = s.reread_equals(el, expected)
        if not ok:
            # 写入二：整值写入（有些应用只认 AXValue 可写）。
            value_ref = s.cfstr(expected)
            if value_ref and s.set_attr(el, _ATTR_VALUE, value_ref) == _AX_OK:
                ok = s.reread_equals(el, expected)
        if not ok:
            _log_debug("AX", "write did not verify against reread")
            return False
        # 光标放到译文末尾（尽力而为，失败不影响替换结果）。
        caret_ref = s.make_range(start + len(translated), 0)
        if caret_ref:
            s.set_attr(el, _ATTR_SELECTED_RANGE, caret_ref)
        _log_info("AX", f"ax replaced {length} chars with {len(translated)} chars (silent)")
        return True
    except Exception as e:
        _log_debug("AX", f"try_replace_focused failed: {e}")
        return False
    finally:
        s.close()
