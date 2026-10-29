# -*- coding: utf-8 -*-
"""macOS AX 静默通道的守卫测试。

AX 的真实读写只能在 macOS 真机验证；这里守三件可在任何平台判定
的事：plan_replace 的纯逻辑（区段选择与剪贴板流程同语义）、每个
带指针参数的 C 函数都在所用句柄上声明了签名（指针截断防线）、
调用方接线（替换器 AX 优先、划选 AX 先读）。
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core import ax_macos

ROOT = os.path.join(os.path.dirname(__file__), "..")
HAS_CN = lambda t: any("一" <= ch <= "鿿" for ch in t)


def _read(*parts):
    return open(os.path.join(ROOT, *parts), encoding="utf-8").read()


class PlanReplaceTest(unittest.TestCase):
    def test_short_doc_uses_all(self):
        value = "测试   "
        plan = ax_macos.plan_replace(value, len(value), 0, HAS_CN)
        self.assertEqual(
            plan, {"start": 0, "length": len(value), "clean": "测试"}
        )

    def test_short_multiline_uses_all(self):
        value = "测试\n换行测试   "
        plan = ax_macos.plan_replace(value, len(value), 0, HAS_CN)
        self.assertEqual(plan["start"], 0)
        self.assertEqual(plan["length"], len(value))
        self.assertEqual(plan["clean"], "测试\n换行测试")

    def test_long_doc_uses_current_line(self):
        long_line = "英" * 2100
        value = long_line + "\n测试  "
        caret = len(value)
        plan = ax_macos.plan_replace(value, caret, 0, HAS_CN)
        self.assertEqual(plan["start"], len(long_line) + 1)
        self.assertEqual(plan["clean"], "测试")

    def test_no_chinese_returns_none(self):
        self.assertIsNone(ax_macos.plan_replace("hello world", 11, 0, HAS_CN))

    def test_line_without_chinese_returns_none(self):
        # 短文档永远走全文（与剪贴板流程的偏好一致）；行分支只在
        # 长文档时启用，此时光标行无中文才放弃。
        long_line = "测" * 2100
        value = long_line + "\nhello   "
        self.assertIsNone(ax_macos.plan_replace(value, len(value), 0, HAS_CN))

    def test_caret_clamped(self):
        plan = ax_macos.plan_replace("测试", 99, 0, HAS_CN)
        self.assertEqual(plan["clean"], "测试")


class SignatureGuardTest(unittest.TestCase):
    SRC = _read("core", "ax_macos.py")

    def test_every_pointer_function_declares_signatures(self):
        for fname in (
            "AXUIElementCopyAttributeValue",
            "AXUIElementSetAttributeValue",
            "AXValueCreate",
            "AXValueGetValue",
            "CFStringCreateWithCString",
            "CFStringGetLength",
            "CFStringGetCString",
            "CFGetTypeID",
            "CFRelease",
        ):
            self.assertIn(f"{fname}.argtypes", self.SRC, fname)
        for fname in (
            "AXUIElementCreateSystemWide",
            "AXUIElementCopyAttributeValue",
            "AXUIElementSetAttributeValue",
            "AXValueCreate",
            "AXValueGetValue",
            "CFStringCreateWithCString",
            "CFStringGetLength",
            "CFStringGetCString",
            "CFGetTypeID",
            "CFStringGetTypeID",
        ):
            self.assertIn(f"{fname}.restype", self.SRC, fname)


class WiringTest(unittest.TestCase):
    def test_replacer_tries_ax_before_clipboard(self):
        src = _read("core", "replacer_macos.py")
        self.assertIn("try_replace_focused", src)
        self.assertLess(
            src.index("try_replace_focused"), src.index("strategy 1")
        )

    def test_selection_tries_ax_first(self):
        src = _read("main.py")
        self.assertIn("read_focused_selection", src)
        self.assertIn("Captured via AX", src)


if __name__ == "__main__":
    unittest.main()
