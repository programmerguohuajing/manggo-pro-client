"""core/hotkey_engine 的单测（标准库 unittest，不依赖 Qt/平台库）。

跑法（仓库根目录）：python3 tests/test_hotkey_engine.py
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.hotkey_engine import HotkeyEngine


def _engine():
    return HotkeyEngine(
        [
            ("selection", frozenset({"Alt"}), "Q"),
            ("screenshot", frozenset({"Alt"}), "W"),
        ],
        max_interval=0.75,
    )


class ComboTest(unittest.TestCase):
    def test_exact_match_triggers_and_swallows(self):
        e = _engine()
        action, swallow = e.handle_key_down("Q", frozenset({"Alt"}), now=100.0)
        self.assertEqual(action, "selection")
        self.assertTrue(swallow)

    def test_extra_modifier_does_not_trigger(self):
        e = _engine()
        action, swallow = e.handle_key_down("Q", frozenset({"Alt", "Shift"}), now=100.0)
        self.assertIsNone(action)
        self.assertFalse(swallow)

    def test_missing_modifier_does_not_trigger(self):
        e = _engine()
        action, swallow = e.handle_key_down("Q", frozenset(), now=100.0)
        self.assertIsNone(action)
        self.assertFalse(swallow)

    def test_held_repeat_swallows_without_retrigger(self):
        e = _engine()
        action, _ = e.handle_key_down("Q", frozenset({"Alt"}), now=100.0)
        self.assertEqual(action, "selection")
        action, swallow = e.handle_key_down("Q", frozenset({"Alt"}), is_repeat=True, now=100.1)
        self.assertIsNone(action)
        self.assertTrue(swallow)
        # 抬起后再按：可重新触发。
        e.handle_key_up("Q")
        action, _ = e.handle_key_down("Q", frozenset({"Alt"}), now=100.2)
        self.assertEqual(action, "selection")

    def test_modifier_keys_do_not_reset_space_count(self):
        e = _engine()
        e.handle_key_down("Space", frozenset(), now=100.0)
        self.assertEqual(e.space_count, 1)
        e.handle_key_down("Shift", frozenset({"Shift"}), now=100.1)
        self.assertEqual(e.space_count, 1)


class TripleSpaceTest(unittest.TestCase):
    def test_three_spaces_within_interval_trigger(self):
        e = _engine()
        for t in (100.0, 100.3, 100.6):
            action, swallow = e.handle_key_down("Space", frozenset(), now=t)
            e.handle_key_up("Space")
        self.assertEqual(action, "triple_space")
        self.assertFalse(swallow)  # 空格本身不吞

    def test_interval_exceeded_resets_to_one(self):
        e = _engine()
        e.handle_key_down("Space", frozenset(), now=100.0)
        e.handle_key_up("Space")
        e.handle_key_down("Space", frozenset(), now=101.0)  # 超过 0.75s
        self.assertEqual(e.space_count, 1)

    def test_other_key_resets_count(self):
        e = _engine()
        e.handle_key_down("Space", frozenset(), now=100.0)
        e.handle_key_up("Space")
        e.handle_key_down("A", frozenset(), now=100.1)
        self.assertEqual(e.space_count, 0)

    def test_space_with_alt_or_ctrl_does_not_count(self):
        e = _engine()
        e.handle_key_down("Space", frozenset({"Alt"}), now=100.0)
        e.handle_key_up("Space")
        self.assertEqual(e.space_count, 0)
        e.handle_key_down("Space", frozenset({"Ctrl"}), now=100.1)
        e.handle_key_up("Space")
        self.assertEqual(e.space_count, 0)

    def test_held_space_repeat_does_not_count(self):
        e = _engine()
        e.handle_key_down("Space", frozenset(), now=100.0)
        action, _ = e.handle_key_down("Space", frozenset(), is_repeat=True, now=100.1)
        self.assertIsNone(action)
        self.assertEqual(e.space_count, 1)

    def test_update_actions_rebuilds_table(self):
        e = _engine()
        e.update_actions([("screenshot", frozenset({"Alt"}), "W")])
        action, _ = e.handle_key_down("Q", frozenset({"Alt"}), now=100.0)
        self.assertIsNone(action)
        action, _ = e.handle_key_down("W", frozenset({"Alt"}), now=100.1)
        self.assertEqual(action, "screenshot")


if __name__ == "__main__":
    unittest.main()
