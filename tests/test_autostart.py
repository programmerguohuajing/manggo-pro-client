# -*- coding: utf-8 -*-
"""开机自启多平台后端的守卫测试。

Windows 任务计划路径无法在沙箱验证（既有行为，不在本文件范围）；
这里守 macOS plist 与 Linux desktop 的纯生成逻辑、Linux 后端在
临时 HOME 下的开关回环，以及设置界面/主程序的接线。
"""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core import autostart

ROOT = os.path.join(os.path.dirname(__file__), "..")


class MacPlistTest(unittest.TestCase):
    def test_plist_text(self):
        text = autostart._mac_plist_text()
        self.assertIn("top.izuna.manggoproclient", text)
        self.assertIn("RunAtLoad", text)
        self.assertIn("<array>", text)
        self.assertIn(sys.executable, text)

    def test_program_arguments(self):
        args = autostart._program_arguments()
        self.assertEqual(args[0], sys.executable)
        if not getattr(sys, "frozen", False):
            self.assertTrue(args[1].endswith("main.py"))
            self.assertNotIn('"', args[1])


class LinuxDesktopTest(unittest.TestCase):
    def test_desktop_text(self):
        text = autostart._linux_desktop_text()
        self.assertIn("[Desktop Entry]", text)
        self.assertIn("Exec=", text)
        self.assertIn("X-GNOME-Autostart-enabled=true", text)

    def test_roundtrip_in_temp_home(self):
        old = os.environ.get("HOME")
        with tempfile.TemporaryDirectory() as home:
            os.environ["HOME"] = home
            try:
                self.assertFalse(autostart.is_autostart_enabled())
                self.assertTrue(autostart.set_autostart_enabled(True))
                self.assertTrue(autostart.is_autostart_enabled())
                self.assertTrue(autostart.set_autostart_enabled(False))
                self.assertFalse(autostart.is_autostart_enabled())
            finally:
                if old is None:
                    os.environ.pop("HOME", None)
                else:
                    os.environ["HOME"] = old


class WiringTest(unittest.TestCase):
    def _read(self, *parts):
        return open(os.path.join(ROOT, *parts), encoding="utf-8").read()

    def test_settings_builds_autostart_row_for_mac(self):
        src = self._read("ui", "settings_window.py")
        self.assertIn("LaunchAgent", src)
        self.assertIn("全局热键钩子 (CGEventTap)", src)

    def test_main_applies_autostart_beyond_windows(self):
        self.assertIn("or IS_MAC or IS_LINUX", self._read("main.py"))

    def test_hotkeys_editable_beyond_windows(self):
        src = self._read("ui", "settings_window.py")
        self.assertIn("editable_actions", src)
        self.assertIn('{"selection", "screenshot"}', src)

    def test_settings_scrollbar_styled(self):
        src = self._read("ui", "theme.py")
        self.assertIn("QScrollBar::handle:vertical", src)
        self.assertIn("QScrollBar::add-line:vertical", src)


if __name__ == "__main__":
    unittest.main()
