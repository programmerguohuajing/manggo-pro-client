"""Linux X11 后端单测（标准库 unittest，不需要 X 服务器）。

- 纯函数（keysym 换算、state 换算、修饰键表）用桩 display 测；
- 后端在无 X 环境下 start() 必须优雅返回 False（不崩溃）；
- pyperclip 在沙箱缺失时打桩（CI 里有真实 pyperclip，走真包）。

跑法（仓库根目录）：python3 tests/test_hook_linux.py
"""

import os
import sys
import types
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import pyperclip  # noqa: F401
except ImportError:
    _stub = types.ModuleType("pyperclip")
    _stub.paste = lambda: ""
    _stub.copy = lambda t: None
    sys.modules["pyperclip"] = _stub

from core.hook_linux import (
    LinuxKeyboardHook,
    build_modifier_map,
    keysym_string_to_main_key,
    state_to_mods,
)
from core.hotkey_engine import HotkeyEngine
from core.replacer_linux import LinuxReplacer


class KeysymTest(unittest.TestCase):
    def test_letters_upper(self):
        self.assertEqual(keysym_string_to_main_key("q"), "Q")
        self.assertEqual(keysym_string_to_main_key("Q"), "Q")

    def test_space_and_function(self):
        self.assertEqual(keysym_string_to_main_key("space"), "Space")
        self.assertEqual(keysym_string_to_main_key("F1"), "F1")

    def test_unknown(self):
        self.assertEqual(keysym_string_to_main_key(None), "__unknown__")
        self.assertEqual(keysym_string_to_main_key(""), "__unknown__")


class ModsTest(unittest.TestCase):
    MOD_MAP = {"Alt": 8, "Ctrl": 4, "Shift": 1, "NumLock": 16}

    def test_exact(self):
        self.assertEqual(state_to_mods(8, self.MOD_MAP), frozenset({"Alt"}))

    def test_lock_bits_ignored(self):
        # Lock(2) / NumLock(16) 不进引擎判定，抓键四变体都能对上表。
        self.assertEqual(state_to_mods(8 | 2, self.MOD_MAP), frozenset({"Alt"}))
        self.assertEqual(state_to_mods(4 | 16, self.MOD_MAP), frozenset({"Ctrl"}))

    def test_build_modifier_map(self):
        mapping = [[50], [66], [37], [64], [77], [], [], []]
        keysyms = {50: 0xFFE1, 37: 0xFFE3, 64: 0xFFE9, 77: 0xFF7F}
        result = build_modifier_map(
            lambda: mapping, lambda kc, idx: keysyms.get(kc, 0)
        )
        self.assertEqual(result["Shift"], 1)
        self.assertEqual(result["Ctrl"], 4)
        self.assertEqual(result["Alt"], 8)
        self.assertEqual(result["NumLock"], 16)


class EngineComboTest(unittest.TestCase):
    def test_matches_combo(self):
        e = HotkeyEngine([("selection", frozenset({"Alt"}), "Q")])
        self.assertTrue(e.matches_combo("Q", frozenset({"Alt"})))
        self.assertFalse(e.matches_combo("Q", frozenset({"Alt", "Shift"})))
        self.assertFalse(e.matches_combo("W", frozenset({"Alt"})))


class HookGracefulTest(unittest.TestCase):
    def test_start_without_x_returns_false(self):
        h = LinuxKeyboardHook(
            on_triple_space=lambda: None,
            on_selection_translate=lambda: None,
            on_screenshot_translate=lambda: None,
            hotkeys={"selection": "Alt+Q", "screenshot": "Alt+W"},
        )
        # 沙箱无 Xlib、CI 无 DISPLAY：两种环境都应优雅失败，不抛异常。
        self.assertFalse(h.start())
        self.assertTrue(h.last_error)

    def test_update_hotkeys_without_running_is_safe(self):
        h = LinuxKeyboardHook(
            on_triple_space=lambda: None,
            on_screenshot_translate=lambda: None,
            hotkeys={"selection": "Alt+Q"},
        )
        h.update_hotkeys({"selection": "Alt+Q", "screenshot": "Alt+W"})
        self.assertTrue(h._engine.matches_combo("W", frozenset({"Alt"})))

    def test_replacer_constructs(self):
        r = LinuxReplacer(translate_func=lambda t: t)
        self.assertTrue(r.contains_chinese("你好abc"))
        self.assertFalse(r.contains_chinese("hello"))


if __name__ == "__main__":
    unittest.main()
