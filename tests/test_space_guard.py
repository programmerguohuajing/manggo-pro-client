# -*- coding: utf-8 -*-
"""四次空格清空原文的防护测试。

引擎是纯逻辑、用注入时间驱动：三次空格触发后 0.35 秒内的空格
（同一次手势的溢出）与替换进行中（busy_check）的空格都被吞掉，
不落字、不计数；其余空格行为与原来一致。另有源码守卫：两个
后端钩子的接线、主程序接线、替换器翻译前收起选区、修复失败
恢复原文、飞书 AX 黑名单。
"""
import os
import sys
import unittest

ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, ROOT)

from core.hotkey_engine import HotkeyEngine  # noqa: E402


def _press(engine, t):
    result = engine.handle_key_down("Space", frozenset(), now=t)
    engine.handle_key_up("Space")
    return result


class OverflowSpaceTest(unittest.TestCase):
    def setUp(self):
        self.engine = HotkeyEngine([], max_interval=0.75)

    def test_triple_triggers_then_fourth_swallowed(self):
        self.assertEqual(_press(self.engine, 1.0), (None, False))
        self.assertEqual(_press(self.engine, 1.2), (None, False))
        self.assertEqual(_press(self.engine, 1.4), ("triple_space", False))
        # 第四下：触发后 0.1 秒，同一手势的溢出，必须吞掉。
        self.assertEqual(_press(self.engine, 1.5), (None, True))

    def test_space_after_window_counts_again(self):
        for t in (1.0, 1.2, 1.4):
            _press(self.engine, t)
        # 0.6 秒后保护窗已过，又没有替换在进行：正常计数。
        self.assertEqual(_press(self.engine, 2.0), (None, False))
        self.assertEqual(_press(self.engine, 2.2), (None, False))
        self.assertEqual(_press(self.engine, 2.4), ("triple_space", False))

    def test_busy_check_swallows_for_whole_flow(self):
        self.engine.busy_check = lambda: True
        self.assertEqual(_press(self.engine, 10.0), (None, True))
        self.engine.busy_check = lambda: False
        self.assertEqual(_press(self.engine, 10.2), (None, False))


def _read(*parts):
    return open(os.path.join(ROOT, *parts), encoding="utf-8").read()


class WiringSourceTest(unittest.TestCase):
    def test_hooks_expose_setter(self):
        for parts in (("core", "hook_macos.py"), ("core", "hook_linux.py")):
            self.assertIn("def set_replace_busy_check", _read(*parts), parts)

    def test_main_wires_busy_check(self):
        self.assertIn("set_replace_busy_check(lambda: self.replacer.is_busy)",
                      _read("main.py"))

    def test_replacer_collapses_selection_before_translate(self):
        src = _read("core", "replacer_macos.py")
        self.assertLess(src.index("抓取结束先收起选区再去翻译"),
                        src.index("translated_en = self.translate_func(clean_text)"))

    def test_repair_failure_restores_original(self):
        src = _read("core", "replacer_macos.py")
        self.assertIn("def _restore_original(", src)
        self.assertIn("return self._restore_original(", src)
        self.assertIn("原文已放回剪贴板", src)

    def test_ax_denylist(self):
        src = _read("core", "ax_macos.py")
        self.assertIn('_AX_APP_DENYLIST = {"Feishu", "Lark"}', src)
        self.assertIn("ax skipped: app=", src)
        self.assertIn("read_focused_selection skipped: denylisted app", src)


if __name__ == "__main__":
    unittest.main()
