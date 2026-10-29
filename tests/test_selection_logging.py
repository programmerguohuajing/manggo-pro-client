"""守卫：划选抓取路径必须全程有日志（用户实测：失败时控制台空白、
无从分辨授权/投递/剪贴板）。含 AXIsProcessTrusted 的签名声明检查
（ctypes 指针/签名纪律：声明要落在实际使用的句柄上）。"""
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
MAIN = (ROOT / "main.py").read_text(encoding="utf-8")
HOOK_MAC = (ROOT / "core" / "hook_macos.py").read_text(encoding="utf-8")


class SelectionLoggingTest(unittest.TestCase):
    def test_mac_selection_logs_start_attempts_and_failure(self):
        self.assertIn("[SELECTION] mac capture start", MAIN)
        self.assertIn("accessibility_trusted", MAIN)
        self.assertIn("[SELECTION] mac capture failed", MAIN)
        self.assertIn("post_ok", MAIN)

    def test_linux_selection_logs_failure(self):
        self.assertIn("[SELECTION] linux capture failed", MAIN)

    def test_ax_trusted_helper_declares_its_signatures(self):
        self.assertIn("AXIsProcessTrusted.argtypes", HOOK_MAC)
        self.assertIn("AXIsProcessTrusted.restype", HOOK_MAC)
        self.assertIn("def is_accessibility_trusted", HOOK_MAC)

    def test_post_key_reports_success(self):
        self.assertIn("return ok", HOOK_MAC)
        self.assertIn("return post_key(keycode, flags=kCGEventFlagMaskCommand)", HOOK_MAC)


if __name__ == "__main__":
    unittest.main()
