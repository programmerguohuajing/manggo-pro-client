# -*- coding: utf-8 -*-
"""检查更新按钮可见性的守卫（源码级）。

该按钮此前没挂任何样式，macOS 上渲染成一行裸文字，用户看不出
可点击。守卫保证它挂着主题的带边框次按钮 class。
"""
import os
import unittest

ROOT = os.path.join(os.path.dirname(__file__), "..")
SRC = open(os.path.join(ROOT, "ui", "settings_window.py"), encoding="utf-8").read()


class CheckUpdateButtonTest(unittest.TestCase):
    def test_button_has_bordered_class(self):
        idx = SRC.index('btn_check_update = QPushButton("检查更新")')
        after = SRC[idx:idx + 400]
        self.assertIn('btn_check_update.setProperty("class", "SecondaryBtn")', after)


if __name__ == "__main__":
    unittest.main()
