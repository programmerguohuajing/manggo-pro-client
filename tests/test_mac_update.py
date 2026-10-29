# -*- coding: utf-8 -*-
"""macOS 自更新（updater 纯逻辑）与打包配置的守卫测试。

ditto 解压与交换脚本的实际执行只能在 macOS 真机验证；这里守的是
可在任何平台判定的部分：附件选择、bundle 路径解析、脚本要素、
spec 的 LSUIElement、设置界面的接线。
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core import updater

ROOT = os.path.join(os.path.dirname(__file__), "..")


class BundlePathTest(unittest.TestCase):
    def test_parses_bundle(self):
        self.assertEqual(
            updater.app_bundle_from_executable(
                "/Applications/ManggoProClient.app/Contents/MacOS/ManggoProClient"
            ),
            "/Applications/ManggoProClient.app",
        )

    def test_rejects_non_bundle(self):
        self.assertIsNone(updater.app_bundle_from_executable("/usr/local/bin/python3"))
        self.assertIsNone(updater.app_bundle_from_executable(""))
        self.assertIsNone(
            updater.app_bundle_from_executable("/opt/Foo.app/Contents/Helpers/tool")
        )


class ZipAssetTest(unittest.TestCase):
    RELEASE = {
        "assets": [
            {"name": "ManggoProClient-macOS-Intel.dmg", "url": "u1"},
            {"name": "ManggoProClient-macOS-Intel.zip", "url": "u2"},
            {"name": "ManggoProClient-macOS-AppleSilicon.zip", "url": "u3"},
        ]
    }

    def test_picks_zip_for_arch(self):
        original = updater._arch_key
        try:
            updater._arch_key = lambda: "intel"
            self.assertEqual(
                updater.select_mac_zip_asset(self.RELEASE)["name"],
                "ManggoProClient-macOS-Intel.zip",
            )
            updater._arch_key = lambda: "arm"
            self.assertEqual(
                updater.select_mac_zip_asset(self.RELEASE)["name"],
                "ManggoProClient-macOS-AppleSilicon.zip",
            )
        finally:
            updater._arch_key = original

    def test_missing_zip_returns_none(self):
        self.assertIsNone(updater.select_mac_zip_asset({"assets": []}))


class SwapScriptTest(unittest.TestCase):
    def test_script_has_safety_steps(self):
        script = updater.build_mac_swap_script(
            4321,
            "/tmp/w/stage/ManggoProClient.app",
            "/Applications/ManggoProClient.app",
            "/tmp/w/swap.log",
        )
        self.assertIn("PID=4321", script)
        self.assertIn("kill -0", script)          # 等应用退出
        self.assertIn(".bak", script)             # 旧版备份
        self.assertIn("ditto", script)            # 覆盖
        self.assertIn("restoring backup", script) # 失败恢复
        self.assertIn("com.apple.quarantine", script)
        self.assertIn('open "$DST"', script)      # 重新打开


class PackagingAndWiringTest(unittest.TestCase):
    def test_spec_lsui_element(self):
        spec = open(os.path.join(ROOT, "manggo-pro-client.spec"), encoding="utf-8").read()
        self.assertIn('"LSUIElement": True', spec)

    def test_settings_wiring(self):
        src = open(os.path.join(ROOT, "ui", "settings_window.py"), encoding="utf-8").read()
        self.assertIn('"download_mac"', src)
        self.assertIn("_handle_mac_self_update", src)
        self.assertIn("select_mac_zip_asset", src)


if __name__ == "__main__":
    unittest.main()
