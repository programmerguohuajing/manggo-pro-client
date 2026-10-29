# -*- coding: utf-8 -*-
"""Electron 混合模式（B 方案）的守卫测试。

应用类型判定是纯文件系统逻辑（造一个假 .app 目录结构真测）；
混合分支、RESULT_ABORT 协议与 replacer 侧的整体停止为源码守卫。
"""
import os
import sys
import tempfile
import unittest

ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, ROOT)

from core import ax_macos  # noqa: E402


def _fake_app(tmp, with_electron):
    bundle = os.path.join(tmp, "Foo.app")
    macos_dir = os.path.join(bundle, "Contents", "MacOS")
    os.makedirs(macos_dir)
    if with_electron:
        os.makedirs(os.path.join(
            bundle, "Contents", "Frameworks", "Electron Framework.framework"))
    return os.path.join(macos_dir, "Foo")


class KindDetectionTest(unittest.TestCase):
    def test_electron_framework_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            exe = _fake_app(tmp, with_electron=True)
            self.assertEqual(ax_macos._kind_for_exe_path(exe), "electron")

    def test_plain_app_is_native(self):
        with tempfile.TemporaryDirectory() as tmp:
            exe = _fake_app(tmp, with_electron=False)
            self.assertEqual(ax_macos._kind_for_exe_path(exe), "native")

    def test_non_bundle_path_is_native(self):
        self.assertEqual(ax_macos._kind_for_exe_path("/usr/bin/foo"), "native")
        self.assertEqual(ax_macos._kind_for_exe_path(""), "native")


class HybridSourceTest(unittest.TestCase):
    SRC = open(os.path.join(ROOT, "core", "ax_macos.py"), encoding="utf-8").read()
    REPLACER = open(os.path.join(ROOT, "core", "replacer_macos.py"), encoding="utf-8").read()

    def test_hybrid_branch_and_protocol(self):
        self.assertIn('RESULT_ABORT = "abort"', self.SRC)
        self.assertIn('detect_app_kind(s.get_pid(el0)) == "electron"', self.SRC)
        self.assertIn("def _hybrid_paste(", self.SRC)
        # 混合模式绝不能出现 AX 文本写入的两个 set 调用点在该函数内：
        hybrid = self.SRC.split("def _hybrid_paste(")[1].split("def try_replace_focused")[0]
        self.assertNotIn("_ATTR_SELECTED_TEXT, text_ref", hybrid)
        self.assertIn('post_cmd_key("V")', hybrid)
        self.assertIn('post_cmd_key("Z")', hybrid)

    def test_replacer_stops_on_abort(self):
        self.assertIn("ax_macos.RESULT_ABORT", self.REPLACER)
        self.assertIn("document state unconfirmed, stopping", self.REPLACER)


if __name__ == "__main__":
    unittest.main()
