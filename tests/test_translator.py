"""core/translator 语言判定、本地地址、失败显式化的单测（标准库 unittest，不依赖 Qt）。

跑法（仓库根目录）：python3 tests/test_translator.py
"""

import json
import os
import sys
import unittest
import urllib.error
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.translator import (
    FreeTranslator,
    LLMTranslator,
    TranslationError,
    _is_local_url,
    is_predominantly_chinese,
)


def _json_response(payload):
    resp = mock.MagicMock()
    resp.read.return_value = json.dumps(payload).encode("utf-8")
    resp.__enter__.return_value = resp
    resp.__exit__.return_value = False
    return resp


class PredominantlyChineseTest(unittest.TestCase):
    def test_chinese(self):
        self.assertTrue(is_predominantly_chinese("今天天气真好"))

    def test_english(self):
        self.assertFalse(is_predominantly_chinese("Hello world, nice to meet you"))

    def test_empty(self):
        self.assertFalse(is_predominantly_chinese("   "))

    def test_threshold(self):
        # 20% 是分界：1/10 中文不算，3/10 算。
        self.assertFalse(is_predominantly_chinese("a" * 9 + "中"))
        self.assertTrue(is_predominantly_chinese("a" * 7 + "中文中"))


class LocalUrlTest(unittest.TestCase):
    def test_local(self):
        for url in (
            "http://localhost:11434/v1",
            "http://127.0.0.1:8080",
            "http://192.168.1.5:11434",
            "http://10.0.0.2:11434",
            "http://172.16.0.9:11434",
            "http://mybox.local:11434",
        ):
            self.assertTrue(_is_local_url(url), url)

    def test_not_local(self):
        for url in (
            "https://api.deepseek.com/v1",
            "https://api.openai.com/v1",
            "http://8.8.8.8:8080",
            "not a url",
            "",
        ):
            self.assertFalse(_is_local_url(url), url)


class FreeTranslatorTest(unittest.TestCase):
    def test_all_channels_fail_raises_instead_of_returning_original(self):
        with mock.patch(
            "urllib.request.urlopen", side_effect=urllib.error.URLError("boom")
        ):
            with self.assertRaises(TranslationError):
                FreeTranslator().translate("你好世界")

    def test_mymemory_warning_text_is_not_a_translation(self):
        def fake_urlopen(request, timeout=None):
            url = request.full_url
            if "youdao" in url or "googleapis" in url:
                raise urllib.error.URLError("boom")
            return _json_response(
                {"responseData": {"translatedText": "MYMEMORY WARNING: query too long"}}
            )

        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            with self.assertRaises(TranslationError):
                FreeTranslator().translate("你好世界")

    def test_mymemory_success_still_works(self):
        def fake_urlopen(request, timeout=None):
            url = request.full_url
            if "youdao" in url or "googleapis" in url:
                raise urllib.error.URLError("boom")
            return _json_response({"responseData": {"translatedText": "Hello world"}})

        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            self.assertEqual(FreeTranslator().translate("你好世界"), "Hello world")


class LLMTranslatorTest(unittest.TestCase):
    def _llm(self, **kwargs):
        kwargs.setdefault("api_url", "https://api.deepseek.com/v1")
        kwargs.setdefault("api_key", "sk-test")
        kwargs.setdefault("model_name", "deepseek-chat")
        return LLMTranslator(**kwargs)

    def test_401_raises_and_never_falls_back(self):
        def fake_urlopen(request, timeout=None):
            raise urllib.error.HTTPError(request.full_url, 401, "Unauthorized", None, None)

        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            with mock.patch.object(
                FreeTranslator, "translate",
                side_effect=AssertionError("must not fall back on 401"),
            ):
                with self.assertRaises(TranslationError) as cm:
                    self._llm().translate("你好")
        self.assertIn("Key", str(cm.exception))

    def test_non_auth_failure_without_fallback_raises(self):
        with mock.patch(
            "urllib.request.urlopen", side_effect=urllib.error.URLError("boom")
        ):
            with self.assertRaises(TranslationError):
                self._llm(allow_public_fallback=False).translate("你好")

    def test_non_auth_failure_with_fallback_uses_free_channels(self):
        with mock.patch(
            "urllib.request.urlopen", side_effect=urllib.error.URLError("boom")
        ):
            with mock.patch.object(
                FreeTranslator, "translate", return_value="Hello"
            ):
                self.assertEqual(
                    self._llm(allow_public_fallback=True).translate("你好"), "Hello"
                )

    def test_empty_key_sends_no_authorization_header(self):
        seen = {}

        def fake_urlopen(request, timeout=None):
            seen["headers"] = dict(request.headers)
            return _json_response({"choices": [{"message": {"content": "Hello"}}]})

        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            out = self._llm(api_url="http://localhost:11434/v1", api_key="").translate("你好")
        self.assertEqual(out, "Hello")
        self.assertNotIn("Authorization", seen["headers"])


if __name__ == "__main__":
    unittest.main()
