"""core/updater 镜像回退的单测（标准库 unittest，不依赖 Qt/pytest）。

跑法（仓库根目录）：python3 tests/test_updater.py
"""
import json
import os
import sys
import tempfile
import unittest
import urllib.error
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import updater


def _json_response(payload):
    resp = mock.MagicMock()
    resp.read.return_value = json.dumps(payload).encode("utf-8")
    resp.__enter__.return_value = resp
    resp.__exit__.return_value = False
    return resp


def _api_payload(tag="v1.0.10"):
    return {
        "tag_name": tag,
        "body": "notes",
        "assets": [
            {
                "name": "ManggoProClient-Setup.exe",
                "browser_download_url": (
                    f"https://github.com/{updater.REPO}/releases/download/{tag}/"
                    "ManggoProClient-Setup.exe"
                ),
            },
        ],
    }


class CandidatesTest(unittest.TestCase):
    def test_direct_url_expands_to_proxies(self):
        direct = "https://github.com/x/y/releases/download/v1.0.10/f.exe"
        self.assertEqual(
            updater._download_candidates(direct),
            [
                direct,
                "https://gh-proxy.com/" + direct,
                "https://ghfast.top/" + direct,
            ],
        )

    def test_proxied_url_tries_proxy_first_then_direct(self):
        direct = "https://github.com/x/y/releases/download/v1.0.10/f.exe"
        proxied = "https://gh-proxy.com/" + direct
        self.assertEqual(
            updater._download_candidates(proxied),
            [proxied, direct, "https://ghfast.top/" + direct],
        )


class FetchTest(unittest.TestCase):
    def test_direct_success(self):
        with mock.patch(
            "urllib.request.urlopen",
            return_value=_json_response(_api_payload()),
        ) as m:
            release = updater.fetch_latest()
        self.assertEqual(release["version"], "1.0.10")
        self.assertEqual(release["via"], "GitHub 直连")
        self.assertEqual(m.call_count, 1)

    def test_direct_failure_falls_back_to_proxy(self):
        calls = []

        def fake_urlopen(request, timeout=None):
            calls.append(request.full_url)
            if request.full_url.startswith("https://api.github.com"):
                raise urllib.error.URLError("boom")
            return _json_response(_api_payload())

        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            release = updater.fetch_latest()
        self.assertEqual(release["version"], "1.0.10")
        self.assertEqual(release["via"], "gh-proxy")
        self.assertEqual(len(calls), 2)

    def test_404_stops_without_fallback(self):
        def fake_urlopen(request, timeout=None):
            raise urllib.error.HTTPError(request.full_url, 404, "Not Found", None, None)

        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen) as m:
            with self.assertRaises(updater.UpdateError):
                updater.fetch_latest()
            self.assertEqual(m.call_count, 1)

    def test_jsdelivr_picks_max_version_and_constructs_asset(self):
        def fake_urlopen(request, timeout=None):
            if "data.jsdelivr.com" in request.full_url:
                return _json_response(
                    {"versions": [{"version": "1.0.9"}, {"version": "1.0.10"}]}
                )
            raise urllib.error.URLError("boom")

        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            release = updater.fetch_latest()
        self.assertEqual(release["version"], "1.0.10")
        self.assertEqual(release["via"], "jsDelivr")
        self.assertEqual(len(release["assets"]), 1)
        # 下载优先走代理。
        self.assertTrue(release["assets"][0]["url"].startswith("https://gh-proxy.com/"))
        if sys.platform.startswith("linux"):
            self.assertEqual(
                release["assets"][0]["name"], "manggo-pro-client_1.0.10_amd64.deb"
            )

    def test_all_sources_fail_reports_tried_sources(self):
        with mock.patch(
            "urllib.request.urlopen", side_effect=urllib.error.URLError("boom")
        ):
            with self.assertRaisesRegex(updater.UpdateError, "已尝试直连与镜像"):
                updater.fetch_latest()


class ConstructedAssetTest(unittest.TestCase):
    def test_windows_installer_and_portable(self):
        with mock.patch.object(sys, "platform", "win32"):
            self.assertEqual(
                updater._constructed_asset("v1.0.10", channel="安装版")["name"],
                "ManggoProClient-Setup.exe",
            )
            self.assertEqual(
                updater._constructed_asset("v1.0.10", channel="便携版")["name"],
                "ManggoProClient-Windows-x64.zip",
            )

    def test_macos_arm_and_intel(self):
        with mock.patch.object(sys, "platform", "darwin"):
            with mock.patch.object(updater, "_arch_key", return_value="arm"):
                self.assertEqual(
                    updater._constructed_asset("v1.0.10", channel="安装版")["name"],
                    "ManggoProClient-macOS-AppleSilicon.dmg",
                )
            with mock.patch.object(updater, "_arch_key", return_value="intel"):
                self.assertEqual(
                    updater._constructed_asset("v1.0.10", channel="安装版")["name"],
                    "ManggoProClient-macOS-Intel.dmg",
                )

    def test_linux_deb(self):
        with mock.patch.object(sys, "platform", "linux"):
            asset = updater._constructed_asset("v1.0.10", channel="安装版")
        self.assertEqual(asset["name"], "manggo-pro-client_1.0.10_amd64.deb")
        self.assertIn("/releases/download/v1.0.10/", asset["url"])


class DownloadTest(unittest.TestCase):
    def _ok_response(self, body=b"data"):
        resp = mock.MagicMock()
        resp.headers.get.return_value = str(len(body))
        resp.read.side_effect = [body, b""]
        resp.__enter__.return_value = resp
        resp.__exit__.return_value = False
        return resp

    def test_first_candidate_failure_falls_to_next(self):
        seen = []

        def fake_urlopen(request, timeout=None):
            seen.append(request.full_url)
            if len(seen) == 1:
                raise urllib.error.URLError("boom")
            return self._ok_response()

        with tempfile.TemporaryDirectory() as tmp:
            dest = os.path.join(tmp, "f.exe")
            with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
                out = updater.download("https://github.com/x/f.exe", dest)
            self.assertEqual(out, dest)
            with open(dest, "rb") as f:
                self.assertEqual(f.read(), b"data")
        self.assertEqual(len(seen), 2)

    def test_404_stops_without_trying_mirrors(self):
        def fake_urlopen(request, timeout=None):
            raise urllib.error.HTTPError(request.full_url, 404, "Not Found", None, None)

        with tempfile.TemporaryDirectory() as tmp:
            dest = os.path.join(tmp, "f.exe")
            with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen) as m:
                with self.assertRaises(updater.UpdateError):
                    updater.download("https://github.com/x/f.exe", dest)
                self.assertEqual(m.call_count, 1)
            self.assertFalse(os.path.exists(dest))

    def test_all_candidates_fail_removes_partial_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = os.path.join(tmp, "f.exe")
            with open(dest, "wb") as f:
                f.write(b"stale")
            with mock.patch(
                "urllib.request.urlopen", side_effect=urllib.error.URLError("boom")
            ):
                with self.assertRaises(updater.UpdateError):
                    updater.download("https://github.com/x/f.exe", dest)
            self.assertFalse(os.path.exists(dest))


if __name__ == "__main__":
    unittest.main()
