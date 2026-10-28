"""core/hotkeys 解析与校验的单测（标准库 unittest，不依赖 Qt）。

跑法（仓库根目录）：python3 tests/test_hotkeys.py
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.hotkeys import (
    DEFAULT_HOTKEYS,
    normalize_hotkeys,
    parse_hotkey,
    validate_hotkeys,
)


class ParseHotkeyTest(unittest.TestCase):
    def test_basic(self):
        mods, vk, label = parse_hotkey("Alt+Q")
        self.assertEqual(mods, frozenset({"Alt"}))
        self.assertEqual(vk, ord("Q"))
        self.assertEqual(label, "Alt+Q")

    def test_modifier_order_normalized(self):
        # 修饰键按 Alt、Ctrl、Shift 顺序，主键大写。
        self.assertEqual(parse_hotkey("Shift+Ctrl+q")[2], "Ctrl+Shift+Q")

    def test_control_alias_and_space(self):
        self.assertEqual(parse_hotkey("Control+Space")[2], "Alt+Space".replace("Alt+", "Ctrl+"))
        self.assertEqual(parse_hotkey("Alt+Space")[2], "Alt+Space")

    def test_function_keys_and_digits(self):
        self.assertEqual(parse_hotkey("Alt+F12")[1], 0x6F + 12)
        self.assertEqual(parse_hotkey("Ctrl+5")[1], ord("5"))

    def test_invalid(self):
        self.assertIsNone(parse_hotkey("Q"))  # 没有修饰键
        self.assertIsNone(parse_hotkey("Win+Q"))  # Win 不支持
        self.assertIsNone(parse_hotkey("Alt+Foo"))  # 主键非法
        self.assertIsNone(parse_hotkey("Alt+"))  # 空主键
        self.assertIsNone(parse_hotkey("Alt++Q"))  # 空段
        self.assertIsNone(parse_hotkey(""))
        self.assertIsNone(parse_hotkey(None))


class NormalizeHotkeysTest(unittest.TestCase):
    def test_missing_falls_back_to_defaults(self):
        out = normalize_hotkeys({})
        self.assertEqual(out, DEFAULT_HOTKEYS)

    def test_invalid_falls_back_to_its_default(self):
        out = normalize_hotkeys({"selection": "Q", "screenshot": "Alt+W",
                                 "workbench": "Alt+M", "voice": "Alt+Space"})
        self.assertEqual(out["selection"], "Alt+Q")

    def test_duplicate_gets_an_unused_default(self):
        # 先到的 selection 占住 Alt+W；后到的 screenshot 重复，
        # 先回退到自己的默认值（还是 Alt+W，仍重复），再找第一个
        # 没被用的默认值 Alt+Q 顶上。
        out = normalize_hotkeys({"selection": "Alt+W", "screenshot": "Alt+W",
                                 "workbench": "Alt+M", "voice": "Alt+Space"})
        self.assertEqual(len(set(out.values())), 4)
        self.assertEqual(out["selection"], "Alt+W")
        self.assertEqual(out["screenshot"], "Alt+Q")

    def test_non_dict_falls_back_to_defaults(self):
        self.assertEqual(normalize_hotkeys(None), DEFAULT_HOTKEYS)
        self.assertEqual(normalize_hotkeys("Alt+Q"), DEFAULT_HOTKEYS)


class ValidateHotkeysTest(unittest.TestCase):
    def test_valid(self):
        self.assertIsNone(validate_hotkeys(dict(DEFAULT_HOTKEYS)))

    def test_duplicate_reports_both_actions(self):
        cfg = dict(DEFAULT_HOTKEYS)
        cfg["screenshot"] = "Alt+Q"
        err = validate_hotkeys(cfg)
        self.assertIn("重复", err)

    def test_invalid_reports_action(self):
        cfg = dict(DEFAULT_HOTKEYS)
        cfg["voice"] = "Space"
        err = validate_hotkeys(cfg)
        self.assertIn("无效", err)


if __name__ == "__main__":
    unittest.main()
