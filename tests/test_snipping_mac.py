"""守卫：macOS 截图遮罩不得进原生全屏（会新建 Space，遮罩关闭后应用
被留在空黑 Space 里——用户实测 OCR 完成后关掉结果窗、应用黑屏）。
Windows 路径保持 WindowFullScreen 不变。"""
import pathlib
import unittest

SRC = pathlib.Path(__file__).resolve().parent.parent / "ui" / "snipping.py"


class SnippingMacFullscreenTest(unittest.TestCase):
    def test_mac_branch_avoids_native_fullscreen(self):
        src = SRC.read_text(encoding="utf-8")
        self.assertIn("from core.platform import IS_MAC", src)
        self.assertIn("if IS_MAC:", src)
        self.assertIn("Qt.WindowNoState", src)
        self.assertIn("Qt.WindowFullScreen", src)  # Windows 路径仍在


if __name__ == "__main__":
    unittest.main()
