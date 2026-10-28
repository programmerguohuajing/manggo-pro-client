"""
翻译引擎模块：支持内置免费通道与大模型 Pro 通道，支持中英双向互译与语言自动检测
"""
from core.logging import error as _log_error, debug as _log_debug
import ipaddress
import json
import re
import urllib.error
import urllib.parse
import urllib.request
from typing import Optional, Dict, Any


class TranslationError(Exception):
    """翻译失败：调用方必须把原因展示给用户，绝不能悄悄返回原文冒充译文。"""


def _is_local_url(url: str) -> bool:
    """本地大模型地址（Ollama 等）不需要 API Key：localhost、回环/私网 IP、.local。"""
    try:
        host = urllib.parse.urlparse(url or "").hostname or ""
    except Exception:
        return False
    if not host:
        return False
    if host == "localhost" or host.endswith(".local"):
        return True
    try:
        ip = ipaddress.ip_address(host)
        return ip.is_loopback or ip.is_private
    except ValueError:
        return False

def is_predominantly_chinese(text: str) -> bool:
    zh_chars = len(re.findall(r'[\u4e00-\u9fa5]', text))
    total_chars = len(text.strip())
    if total_chars == 0:
        return False
    return (zh_chars / total_chars) > 0.2

class BaseTranslator:
    def translate(self, text: str, source_lang: str = "auto", target_lang: str = "auto") -> str:
        raise NotImplementedError

class FreeTranslator(BaseTranslator):
    """
    内置开箱即用的免费翻译引擎（基于公用翻译接口，无需 API Key）
    """
    def __init__(self):
        self.user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

    def translate(self, text: str, source_lang: str = "auto", target_lang: str = "auto") -> str:
        clean_text = text.strip()
        if not clean_text:
            return ""

        # 智能判定目标语言
        if target_lang == "auto":
            target_lang = "en" if is_predominantly_chinese(clean_text) else "zh-CN"

        # 1. 优先尝试国内极速通道 (有道公共引擎，国内直连毫秒级响应)
        try:
            yd_url = "https://aidemo.youdao.com/trans"
            data = urllib.parse.urlencode({"q": clean_text, "from": "Auto", "to": "Auto"}).encode("utf-8")
            req = urllib.request.Request(yd_url, data=data, headers={"User-Agent": self.user_agent})
            with urllib.request.urlopen(req, timeout=2.5) as resp:
                res = json.loads(resp.read().decode("utf-8"))
                trans_arr = res.get("translation", [])
                if trans_arr and trans_arr[0]:
                    return trans_arr[0].strip()
        except Exception as e:
            _log_debug("TRANSLATOR", f"free channel Youdao failed: {e}")

        # 2. 尝试 Google 网页翻译中继接口
        try:
            url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl={source_lang}&tl={target_lang}&dt=t&q={urllib.parse.quote(clean_text)}"
            req = urllib.request.Request(url, headers={"User-Agent": self.user_agent})
            with urllib.request.urlopen(req, timeout=2.5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                result = "".join([segment[0] for segment in data[0] if segment[0]])
                if result:
                    return result.strip()
        except Exception as e:
            _log_debug("TRANSLATOR", f"free channel Google failed: {e}")

        # 3. 备选：MyMemory 免费公开接口
        try:
            sl = "zh" if target_lang == "en" else "en"
            tl = target_lang if target_lang != "zh-CN" else "zh"
            url = f"https://api.mymemory.translated.net/get?q={urllib.parse.quote(clean_text)}&langpair={sl}|{tl}"
            req = urllib.request.Request(url, headers={"User-Agent": self.user_agent})
            with urllib.request.urlopen(req, timeout=2.5) as resp:
                res = json.loads(resp.read().decode("utf-8"))
                trans = res.get("responseData", {}).get("translatedText", "")
                # MYMEMORY 前缀的都是接口报错文本（含超限、WARNING 等），不是译文。
                if trans and not trans.strip().upper().startswith("MYMEMORY"):
                    return trans.strip()
        except Exception as e:
            _log_debug("TRANSLATOR", f"free channel MyMemory failed: {e}")

        # 全部通道失败时抛错，不返回原文：界面与历史绝不能把原文当译文。
        raise TranslationError(
            "免费通道全部失败（有道、Google、MyMemory 均无响应），请检查网络后重试"
        )

class LLMTranslator(BaseTranslator):
    """
    大模型 Pro 通道：支持 DeepSeek, 通义千问, OpenAI, 本地 Ollama 等
    """
    def __init__(self, api_url: str, api_key: str, model_name: str, style_prompt: str = "",
                 allow_public_fallback: bool = False):
        self.api_url = api_url.rstrip("/")
        if not self.api_url.endswith("/chat/completions"):
            self.api_url = f"{self.api_url}/chat/completions"
        self.api_key = api_key
        self.model_name = model_name
        # 公共通道回退默认关闭（2026-10-28 review 问题6）：大模型失败时
        # 不再悄悄改用免费通道，否则 Key 错误时“测试连接”也会显示成功。
        self.allow_public_fallback = allow_public_fallback
        self.style_prompt = style_prompt or "You are an expert bilingual translator. Translate the given text accurately and naturally. If the text is Chinese, translate it to English. If it is English, translate it to Chinese. Output ONLY the translation without any quotes or explanations."

    def translate(self, text: str, source_lang: str = "auto", target_lang: str = "auto") -> str:
        clean_text = text.strip()
        if not clean_text:
            return ""

        if target_lang == "auto":
            target_lang = "English" if is_predominantly_chinese(clean_text) else "Simplified Chinese"
        else:
            # 主窗口下拉框传来的是语言码（en/zh-CN），提示词里要用人话。
            target_lang = {
                "en": "English",
                "zh-CN": "Simplified Chinese",
                "zh": "Simplified Chinese",
            }.get(target_lang, target_lang)

        sys_prompt = f"{self.style_prompt} Please translate into {target_lang}."

        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": clean_text}
            ],
            "temperature": 0.3
        }

        headers = {
            "Content-Type": "application/json",
            "User-Agent": "ManggoProClient/1.0",
        }
        # 本地地址允许不填 Key：空 Key 时不发空 Bearer 头。
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        req = urllib.request.Request(
            self.api_url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                res = json.loads(resp.read().decode("utf-8"))
                out = res["choices"][0]["message"]["content"].strip()
                if (out.startswith('"') and out.endswith('"')) or (out.startswith("'") and out.endswith("'")):
                    out = out[1:-1].strip()
                return out
        except urllib.error.HTTPError as e:
            # Key 错误是配置问题，绝不能回退掩盖：用户必须看到它。
            if e.code in (401, 403):
                raise TranslationError(
                    f"大模型 API Key 无效或未授权（HTTP {e.code}），请检查密钥"
                )
            err = e
        except Exception as e:
            err = e
        if self.allow_public_fallback:
            _log_error("LLM", f"LLM failed ({err}), falling back to free channels (option on)")
            return FreeTranslator().translate(clean_text, source_lang, target_lang)
        raise TranslationError(
            f"大模型通道失败：{err}（公共通道回退未启用，可在设置中开启）"
        )

class TranslationManager:
    """
    统一管理翻译通道与自动路由
    """
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.free_translator = FreeTranslator()
        self._init_engine()

    def _init_engine(self):
        engine_type = self.config.get("engine", "free")
        if engine_type == "llm":
            # 选了大模型就用大模型：Key 为空时本地地址直接跑（Ollama 不用 Key），
            # 云端地址会在调用时报 401 显式错误——绝不再悄悄用免费通道冒充大模型。
            self.active_translator = LLMTranslator(
                api_url=self.config.get("llm_api_url", "https://api.deepseek.com/v1"),
                api_key=self.config.get("llm_api_key", ""),
                model_name=self.config.get("llm_model", "deepseek-chat"),
                style_prompt=self.config.get("llm_prompt", ""),
                allow_public_fallback=bool(self.config.get("allow_public_fallback", False)),
            )
        else:
            self.active_translator = self.free_translator

    def update_config(self, new_config: Dict[str, Any]):
        self.config.update(new_config)
        self._init_engine()

    def translate(self, text: str, source_lang: str = "auto", target_lang: str = "auto") -> str:
        return self.active_translator.translate(text, source_lang, target_lang)

    def translate_to_en(self, text: str) -> str:
        return self.active_translator.translate(text, target_lang="en")
