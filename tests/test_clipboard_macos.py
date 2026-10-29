"""守卫：macOS 剪贴板走 NSPasteboard，不走 pbcopy/pbpaste。

1.0.32 真机日志：合成 Cmd+C 成功，但剪贴板里是中文时读到 0 字，
纯英文 'Test' 能读到——Finder 启动的 .app 没有 LANG，pbpaste 读不出
中文。修复见 core/clipboard_macos.py。"""
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
SRC = (ROOT / "core" / "clipboard_macos.py").read_text(encoding="utf-8")
MAIN = (ROOT / "main.py").read_text(encoding="utf-8")


class MacClipboardTest(unittest.TestCase):
    def test_import_is_safe_off_mac(self):
        import core.clipboard_macos as cm
        if sys.platform != "darwin":
            self.assertFalse(cm.install())

    def test_uses_utf8_pasteboard_api(self):
        for needle in ("NSPasteboardTypeString", "stringWithUTF8String:", "UTF8String",
                       "setString:forType:", "stringForType:", "objc_autoreleasePoolPush"):
            self.assertIn(needle, SRC)
        self.assertNotIn("pbpaste", SRC.split('"""', 2)[2])

    def test_typed_msgsend_not_variadic(self):
        self.assertIn("CFUNCTYPE", SRC)

    def test_main_installs_on_mac_and_sets_utf8_locale(self):
        self.assertIn("_install_mac_clipboard", MAIN)
        self.assertIn('os.environ["LANG"] = "en_US.UTF-8"', MAIN)


if __name__ == "__main__":
    unittest.main()
