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
_ATTR_PARENT = "AXParent"

# AX 读写会让个别 Electron 应用崩溃（用户实测：在飞书输入框里
# 触发就地转译后飞书崩溃）。崩溃报告定性之前，这些应用整体跳过
# AX（含读选区），一律回退剪贴板流程——慢一点，但不碰它的 AX
# 实现。进程名取可执行文件基名（飞书国际版叫 Lark）。
_AX_APP_DENYLIST = {"Feishu", "Lark"}
_ATTR_ROLE = "AXRole"


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
    lib.AXUIElementGetPid.restype = ctypes.c_int
    lib.AXUIElementGetPid.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_int)]
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

    def get_pid(self, element) -> int:
        pid = ctypes.c_int(0)
        try:
            if self.ax.AXUIElementGetPid(element, ctypes.byref(pid)) == _AX_OK:
                return int(pid.value)
        except Exception:
            pass
        return 0

    def read_role(self, element) -> Optional[str]:
        err, ref = self.get_attr(element, _ATTR_ROLE)
        return self.to_str(ref) if err == _AX_OK else None

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


def _app_name(pid) -> str:
    """pid -> 进程名（日志归因用，如 Typora/TextEdit）；失败给 '?'。"""
    if not pid:
        return "?"
    try:
        import subprocess
        out = subprocess.run(
            ["/bin/ps", "-p", str(pid), "-o", "comm="],
            capture_output=True, text=True, timeout=2,
        )
        name = (out.stdout or "").strip()
        return name.rsplit("/", 1)[-1] or "?"
    except Exception:
        return "?"


def _element_chain(s, el, max_hops=4):
    """焦点元素及其 AXParent 链（近到远）。Electron/Chromium 应用
    的焦点元素常是编辑区的子节点，全文与选区挂在上层元素上，
    只看焦点元素本身会误判“读不到”。"""
    chain = [el]
    cur = el
    for _ in range(max_hops):
        err, parent = s.get_attr(cur, _ATTR_PARENT)
        if err != _AX_OK or not parent:
            break
        chain.append(parent)
        cur = parent
    return chain


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
        if _app_name(s.get_pid(el)) in _AX_APP_DENYLIST:
            _log_debug("AX", "read_focused_selection skipped: denylisted app")
            return None
        # 焦点元素与其父链逐个试：Electron 应用的选区文本常挂在
        # 上层元素上，只问焦点元素本身会漏。
        for node in _element_chain(s, el, max_hops=3):
            err, ref = s.get_attr(node, _ATTR_SELECTED_TEXT)
            text = s.to_str(ref) if err == _AX_OK else None
            if text:
                return text
            # 退而求其次：全文 + 选区范围切片。
            sel = s.get_range(node)
            value = s.read_value(node)
            if sel is not None and value is not None and sel[1] > 0:
                piece = value[sel[0]:sel[0] + sel[1]]
                if piece:
                    return piece
        return None
    except Exception as e:
        _log_debug("AX", f"read_focused_selection failed: {e}")
        return None
    finally:
        s.close()


def try_replace_focused(translate_func: Callable[[str], str],
                        contains_chinese: Callable[[str], bool]):
    """AX 静默替换，三态返回：

    - True：已替换且回读校验通过；
    - None：焦点字段可读、但没有可译内容（无中文，或译文为空 /
      与原文相同）。剪贴板流程抓到的必然是同一份文本、同样会
      放弃，调用方应直接结束——不要再走一遍只会白闪菜单栏的
      剪贴板流程（1.0.38 真机：译完后再次触发，先闪一轮 Cmd+A/C
      才报 aborted，正是这种空转）；
    - False：读不到值 / 选区，或写入不被目标应用接受，调用方
      回退剪贴板流程。

    失败与空转的原因一律 INFO 打出（应用名、元素角色、AX 错误
    码），不再埋进 DEBUG——1.0.38 的日志只看得到“not applicable”，
    分不清是读不到、没选区还是写不进。
    """
    try:
        s = _Ax()
    except Exception:
        return False
    try:
        el0 = s.focused()
        if el0 is None:
            _log_info("AX", "ax not applicable: no focused element")
            return False
        app = _app_name(s.get_pid(el0))
        if app in _AX_APP_DENYLIST:
            _log_info("AX", f"ax skipped: app={app} on denylist, clipboard flow")
            return False
        picked = None
        roles = []
        for el in _element_chain(s, el0):
            roles.append(s.read_role(el) or "?")
            value = s.read_value(el)
            if value:
                picked = (el, value)
                break
            if value == "" and picked is None:
                # 先记下空值元素；链上再没有带文本的就用它（空字段
                # 本来就无可译内容，走 None 空转出口）。
                picked = (el, "")
        if picked is None:
            _log_info("AX", f"ax not applicable: value unreadable (app={app}, roles={roles})")
            return False
        el, value = picked
        sel = s.get_range(el)
        if sel is None:
            # 全文计划（<2000 字且含中文）根本不需要选区参与——
            # plan_replace 在该分支只用全文。选区读不到不再一票
            # 否决短文档；长文档仍回退（行计划离不开真实光标）。
            if len(value) < 2000 and contains_chinese(value):
                sel = (len(value), 0)
            else:
                _log_info("AX", f"ax not applicable: selection range unreadable "
                                f"(app={app}, value={len(value)} chars)")
                return False
        plan = plan_replace(value, sel[0], sel[1], contains_chinese)
        if plan is None:
            _log_info("AX", f"ax idle: field readable, nothing to translate "
                            f"(app={app}, value={len(value)} chars)")
            return None
        translated = translate_func(plan["clean"])
        if not translated or translated == plan["clean"]:
            _log_info("AX", "ax idle: translation empty or identical")
            return None
        start, length = plan["start"], plan["length"]
        expected = value[:start] + translated + value[start + length:]
        # 写入一：把选区设到目标区段，再写 AXSelectedText（等价于对
        # 选区打字，不经剪贴板、不发组合键）。
        ok = False
        err_sel = None
        range_ref = s.make_range(start, length)
        if range_ref:
            err = s.set_attr(el, _ATTR_SELECTED_RANGE, range_ref)
            if err == _AX_OK:
                text_ref = s.cfstr(translated)
                if text_ref:
                    err_sel = s.set_attr(el, _ATTR_SELECTED_TEXT, text_ref)
                    if err_sel == _AX_OK:
                        ok = s.reread_equals(el, expected)
            else:
                err_sel = err
        err_val = None
        if not ok:
            # 写入二：整值写入（有些应用只认 AXValue 可写）。
            value_ref = s.cfstr(expected)
            if value_ref:
                err_val = s.set_attr(el, _ATTR_VALUE, value_ref)
                if err_val == _AX_OK:
                    ok = s.reread_equals(el, expected)
        if not ok:
            _log_info("AX", f"ax write failed: app={app} roles={roles} "
                            f"seltext_err={err_sel} value_err={err_val}")
            return False
        # 光标放到译文末尾（尽力而为，失败不影响替换结果）。
        caret_ref = s.make_range(start + len(translated), 0)
        if caret_ref:
            s.set_attr(el, _ATTR_SELECTED_RANGE, caret_ref)
        _log_info("AX", f"ax replaced {length} chars with {len(translated)} chars (silent)")
        return True
    except Exception as e:
        _log_info("AX", f"ax attempt raised: {e}")
        return False
    finally:
        s.close()
