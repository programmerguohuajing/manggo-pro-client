"""core/hook 回调 ctypes 转换的回归单测（标准库 unittest，不依赖 Qt/Windows）。

背景（1.0.15 全系统无法输入）：hook 回调收到 lParam 是
POINTER(KBDLLHOOKSTRUCT) 对象；CallNextHookEx 的第 4 参数一旦声明
成 LPARAM（c_ssize_t），ctypes 就无法转换该对象而抛 ArgumentError，
回调一抛异常，ctypes 便返回未初始化的垃圾值（实测非 0），Windows
随即把当次按键吞掉 —— 于是装上 1.0.15 后所有软件都打不出字，
退出软件才恢复。本文件把这条机制钉死，外加回调永不吞键的兜底。

跑法（仓库根目录）：python3 tests/test_hook_ctypes.py
"""

import ctypes
import os
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# core.hook 经 core.replacer 依赖 pyperclip（运行时才用），而单测要求
# 纯标准库（CI 的 test job 不装依赖），这里先 stub 掉，只保证 import 通过。
import types

if "pyperclip" not in sys.modules:
    _stub = types.ModuleType("pyperclip")
    _stub.copy = lambda text: None
    _stub.paste = lambda: ""
    sys.modules["pyperclip"] = _stub

from core.hook import GlobalKeyboardHook, KBDLLHOOKSTRUCT


class PointerConversionTest(unittest.TestCase):
    def test_pointer_to_void_p_yields_address(self):
        """POINTER -> c_void_p 能正确转成所指结构体的地址。"""
        kb = KBDLLHOOKSTRUCT(0x41, 0x1E, 0, 12345, None)
        lParam = ctypes.pointer(kb)
        sink = ctypes.CFUNCTYPE(None, ctypes.c_void_p)(lambda v: None)
        got = []
        sink = ctypes.CFUNCTYPE(None, ctypes.c_void_p)(got.append)
        sink(lParam)
        self.assertEqual(got[0], ctypes.addressof(kb))

    def test_pointer_to_ssize_t_raises(self):
        """POINTER -> c_ssize_t（LPARAM）无法转换，会抛 ArgumentError。

        这就是 1.0.15 的直接死因：CallNextHookEx 的 lParam 绝不能
        声明成 LPARAM。
        """
        kb = KBDLLHOOKSTRUCT(0x41, 0x1E, 0, 12345, None)
        lParam = ctypes.pointer(kb)
        sink = ctypes.CFUNCTYPE(None, ctypes.c_ssize_t)(lambda v: None)
        with self.assertRaises(ctypes.ArgumentError):
            sink(lParam)


class CallNextArgtypesTest(unittest.TestCase):
    def test_callnext_lparam_is_void_p_not_lparam(self):
        """core/hook.py 里 CallNextHookEx 的第 4 参数必须是 c_void_p。"""
        path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "core",
            "hook.py",
        )
        src = open(path, encoding="utf-8").read()
        m = re.search(
            r"CallNextHookEx\.argtypes\s*=\s*\[(.*?)\]",
            src,
            re.DOTALL,
        )
        self.assertIsNotNone(m, "找不到 CallNextHookEx.argtypes 声明")
        block = m.group(1)
        self.assertNotIn("LPARAM", block)
        self.assertIn("c_void_p", block)


class CallNextRestypeTest(unittest.TestCase):
    def test_callnext_restype_is_ssize_t_not_void_p(self):
        """core/hook.py 里 CallNextHookEx 的 restype 必须是 c_ssize_t。

        1.0.19 真因：restype=c_void_p 时，C 返回 0（放行）会被转成
        Python None；回调把 None 返回给 c_long 的 HOOKPROC 时 ctypes
        转换失败，调用方读到垃圾非 0，Windows 吞键。
        """
        path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "core",
            "hook.py",
        )
        src = open(path, encoding="utf-8").read()
        m = re.search(
            r"CallNextHookEx\.restype\s*=\s*(\S+)",
            src,
        )
        self.assertIsNotNone(m, "找不到 CallNextHookEx.restype 声明")
        self.assertEqual(m.group(1), "ctypes.c_ssize_t")


class CallbackGuardTest(unittest.TestCase):
    def test_callback_returns_zero_on_inner_error(self):
        """内层回调抛任何异常，外层 wrapper 必须返回 0（放行），绝不吞键。"""
        hook = GlobalKeyboardHook()

        def boom(nCode, wParam, lParam):
            raise RuntimeError("simulated inner failure")

        hook._hook_callback_inner = boom
        self.assertEqual(hook._hook_callback(0, 0x0100, None), 0)


if __name__ == "__main__":
    unittest.main()
