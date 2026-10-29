# -*- coding: utf-8 -*-
"""AX 三态与 Typora 覆盖的守卫测试。

ax_macos 只依赖 ctypes/标准库（框架在调用时才加载），沙箱可直接
import 并真测 plan_replace 纯逻辑；其余为源码守卫：三态返回、
父链查找、选区缺失时短文档不一票否决、失败原因 INFO 化、
replacer 侧的空转跳过与忙标志竞态修复。
"""
import os
import sys
import unittest

ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, ROOT)

from core import ax_macos  # noqa: E402


def _has_cjk(text):
    return any("\u4e00" <= ch <= "\u9fa5" for ch in text)


class PlanReplaceTest(unittest.TestCase):
    def test_whole_value_preferred_for_short_chinese(self):
        plan = ax_macos.plan_replace("你好世界", 4, 0, _has_cjk)
        self.assertEqual(plan, {"start": 0, "length": 4, "clean": "你好世界"})

    def test_no_chinese_returns_none(self):
        self.assertIsNone(ax_macos.plan_replace("hello", 5, 0, _has_cjk))

    def test_line_plan_for_long_text(self):
        value = "x" * 2100 + "\n你好"
        plan = ax_macos.plan_replace(value, len(value), 0, _has_cjk)
        self.assertEqual(plan["clean"], "你好")
        self.assertEqual(plan["start"], 2101)

    def test_line_without_chinese_returns_none(self):
        value = "abc\ndef"
        self.assertIsNone(ax_macos.plan_replace(value, 7, 0, _has_cjk))


class AxSourceTest(unittest.TestCase):
    SRC = open(os.path.join(ROOT, "core", "ax_macos.py"), encoding="utf-8").read()

    def test_tristate_and_reason_logging(self):
        self.assertIn("ax idle: field readable, nothing to translate", self.SRC)
        self.assertIn("ax not applicable: value unreadable", self.SRC)
        self.assertIn("ax not applicable: selection range unreadable", self.SRC)
        self.assertIn("ax write failed:", self.SRC)
        self.assertIn("seltext_err=", self.SRC)

    def test_parent_chain_and_pid_signatures(self):
        self.assertIn('def _element_chain(', self.SRC)
        self.assertIn('_ATTR_PARENT = "AXParent"', self.SRC)
        self.assertIn("lib.AXUIElementGetPid.argtypes", self.SRC)
        self.assertIn("lib.AXUIElementGetPid.restype", self.SRC)

    def test_short_doc_survives_missing_range(self):
        self.assertIn("sel = (len(value), 0)", self.SRC)


class ReplacerTriStateTest(unittest.TestCase):
    SRC = open(os.path.join(ROOT, "core", "replacer_macos.py"), encoding="utf-8").read()

    def test_idle_skips_clipboard_flow(self):
        self.assertIn("ax_result is None", self.SRC)
        self.assertIn("clipboard flow skipped", self.SRC)
        self.assertIn("ax_result is True", self.SRC)

    def test_busy_set_before_thread_spawn(self):
        trig = self.SRC.split("def trigger_triple_space_replace")[1].split("def ")[0]
        self.assertLess(trig.index("self.is_busy = True"),
                        trig.index("threading.Thread"))
        # 全文只应剩这一处置位（_do_replace_flow 里的旧置位已删）
        self.assertEqual(self.SRC.count("self.is_busy = True"), 1)


if __name__ == "__main__":
    unittest.main()
