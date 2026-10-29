"""守卫：macOS 就地转译的抓取顺序（先清空→选区→复制→等待）。

1.0.30 真机实测：旧 _copy_and_wait 在发 Cmd+C 之后才清空剪贴板，
目标应用写入稍慢就被清空盖掉，两条策略都 captured 0 chars。
另含修饰键等待辅助的签名声明检查。"""
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
REPLACER = (ROOT / "core" / "replacer_macos.py").read_text(encoding="utf-8")
HOOK_MAC = (ROOT / "core" / "hook_macos.py").read_text(encoding="utf-8")
MAIN = (ROOT / "main.py").read_text(encoding="utf-8")


class GrabOrderTest(unittest.TestCase):
    def test_racy_helper_gone_and_wait_is_pure(self):
        self.assertNotIn("def _copy_and_wait", REPLACER)
        self.assertIn("def _wait_clipboard", REPLACER)

    def test_clear_happens_before_copy_keys(self):
        first_clear = REPLACER.index('self._copy("")')
        first_select = REPLACER.index("post_shift_cmd_left()")
        self.assertLess(first_clear, first_select)
        self.assertGreaterEqual(REPLACER.count('self._copy("")'), 2)

    def test_captured_content_is_logged(self):
        self.assertIn("captured[:30]!r", REPLACER)
        self.assertIn("captured_all[:30]!r", REPLACER)

    def test_modifier_wait_helper_declares_signatures(self):
        self.assertIn("CGEventSourceFlagsState.argtypes", HOOK_MAC)
        self.assertIn("CGEventSourceFlagsState.restype", HOOK_MAC)
        self.assertIn("wait_until_modifiers_released", MAIN)


if __name__ == "__main__":
    unittest.main()
