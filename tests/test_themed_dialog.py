# -*- coding: utf-8 -*-
"""主题化弹窗的守卫测试（源码级：沙箱无 Qt，与既有 UI 测试同例）。

守三件事：主题弹窗组件齐全（五种状态 + 三个入口函数）、所有原
QMessageBox 调用点都已切换（含截图里的保存成功）、没有文件再
引用原生 QMessageBox。
"""
import os
import unittest

ROOT = os.path.join(os.path.dirname(__file__), "..")


def _read(*parts):
    return open(os.path.join(ROOT, *parts), encoding="utf-8").read()


class ThemedDialogSourceTest(unittest.TestCase):
    SRC = _read("ui", "themed_dialog.py")

    def test_kinds_and_helpers(self):
        for kind in ('"info"', '"success"', '"warning"', '"error"', '"question"'):
            self.assertIn(kind, self.SRC)
        for fn in ("def info(", "def success(", "def warning(",
                   "def error(", "def question(", "def choose("):
            self.assertIn(fn, self.SRC)

    def test_uses_theme_tokens_and_button_classes(self):
        self.assertIn("theme.WINDOW_STYLESHEET", self.SRC)
        self.assertIn('"PrimaryBtn"', self.SRC)
        self.assertIn('"SecondaryBtn"', self.SRC)
        self.assertIn('setObjectName("DialogBody")', self.SRC)


class CallSiteSwapTest(unittest.TestCase):
    def test_no_native_messagebox_left(self):
        for parts in (("ui", "settings_window.py"),
                      ("ui", "history_window.py"),
                      ("main.py",)):
            self.assertNotIn("QMessageBox", _read(*parts), parts)

    def test_known_sites_swapped(self):
        settings = _read("ui", "settings_window.py")
        self.assertIn('themed_dialog.success(self, "保存成功"', settings)
        self.assertIn('themed_dialog.error(self, "保存失败"', settings)
        self.assertIn('yes_text="退出并更新"', settings)
        self.assertIn('yes_text="退出并安装"', settings)
        self.assertIn("themed_dialog.choose(", settings)
        history = _read("ui", "history_window.py")
        self.assertIn('themed_dialog.success(self, "导入完成"', history)
        self.assertIn('yes_text="确认清空"', history)


if __name__ == "__main__":
    unittest.main()
