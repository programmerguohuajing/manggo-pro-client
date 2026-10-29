# -*- coding: utf-8 -*-
"""托盘 macOS 点击行为的守卫测试（源码级：沙箱无 Qt）。

macOS 不投递 QSystemTrayIcon 的 DoubleClick，且挂了原生上下文
菜单后连 activated 都不投递——守卫保证：Mac 不挂原生菜单、走
手动弹菜单 + 双击合成；其他平台的原生行为（setContextMenu +
DoubleClick 直达）原样保留。
"""
import os
import unittest

ROOT = os.path.join(os.path.dirname(__file__), "..")
SRC = open(os.path.join(ROOT, "ui", "tray.py"), encoding="utf-8").read()


class TrayMacClickTest(unittest.TestCase):
    def test_mac_skips_native_context_menu(self):
        self.assertIn("if not IS_MAC:\n            self.tray_icon.setContextMenu(menu)", SRC)
        self.assertIn("self._menu = menu", SRC)

    def test_manual_double_click_synthesis(self):
        self.assertIn("_MAC_CLICK_MENU_DELAY_MS", SRC)
        self.assertIn("def _show_tray_menu(self):", SRC)
        self.assertIn("QSystemTrayIcon.Context", SRC)
        self.assertIn("QSystemTrayIcon.Trigger", SRC)
        self.assertIn("self._click_timer.isActive()", SRC)

    def test_native_double_click_kept(self):
        self.assertIn("QSystemTrayIcon.DoubleClick", SRC)
        self.assertIn("self.open_settings_requested.emit()", SRC)


if __name__ == "__main__":
    unittest.main()
