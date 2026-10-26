"""
翻译引擎模块：支持内置免费通道与大模型 Pro 通道
"""
import json
import re
import urllib.parse
import urllib.request
from typing import Optional, Dict, Any

class BaseTranslator:
    def translate(self, text: str, target_lang: str = "en") -> str:
        raise NotImplementedError

class FreeTranslator(BaseTranslator):
    """
    内置开箱即用的免费翻译引擎（基于公用翻译接口，无需 API Key）
    """
    def __init__(self):
        self.user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

    def translate(self, text: str, target_lang: str = "en") -> str:
        clean_text = text.strip()
        if not clean_text:
            return ""

        # 尝试 Google 网页翻译中继接口
        try:
            url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl={target_lang}&dt=t&q={urllib.parse.quote(clean_text)}"
            req = urllib.request.Request(url, headers={"User-Agent": self.user_agent})
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                result = "".join([segment[0] for segment in data[0] if segment[0]])
                if result:
                    return result.strip()
        except Exception:
            pass

        # 备选：MyMemory 免费公开接口
        try:
            langpair = f"zh|{target_lang}" if any('\u4e00' <= char <= '\u9fff' for char in clean_text) else f"auto|{target_lang}"
            url = f"https://api.mymemory.translated.net/get?q={urllib.parse.quote(clean_text)}&langpair={langpair}"
            req = urllib.request.Request(url, headers={"User-Agent": self.user_agent})
            with urllib.request.urlopen(req, timeout=5) as resp:
                res = json.loads(resp.read().decode("utf-8"))
                trans = res.get("responseData", {}).get("translatedText", "")
                if trans and "MYMEMORY WARNING" not in trans:
                    return trans.strip()
        except Exception:
            pass

        return clean_text

class LLMTranslator(BaseTranslator):
    """
    大模型 Pro 通道：支持 DeepSeek, 通义千问, OpenAI, 本地 Ollama 等
    """
    def __init__(self, api_url: str, api_key: str, model_name: str, style_prompt: str = ""):
        self.api_url = api_url.rstrip("/")
        if not self.api_url.endswith("/chat/completions"):
            self.api_url = f"{self.api_url}/chat/completions"
        self.api_key = api_key
        self.model_name = model_name
        self.style_prompt = style_prompt or "Translate the following Chinese text into natural, idiomatic English. Return ONLY the translation without any explanation, markdown or quotes."

    def translate(self, text: str, target_lang: str = "en") -> str:
        clean_text = text.strip()
        if not clean_text:
            return ""

        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": self.style_prompt},
                {"role": "user", "content": clean_text}
            ],
            "temperature": 0.3
        }

        req = urllib.request.Request(
            self.api_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
                "User-Agent": "ManggoProClient/1.0"
            }
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                res = json.loads(resp.read().decode("utf-8"))
                out = res["choices"][0]["message"]["content"].strip()
                # 剥离多余的双引号包裹
                if (out.startswith('"') and out.endswith('"')) or (out.startswith("'") and out.endswith("'")):
                    out = out[1:-1].strip()
                return out
        except Exception as e:
            print(f"[LLM] Error: {e}")
            # 降级到免费源
            return FreeTranslator().translate(clean_text, target_lang)

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
        if engine_type == "llm" and self.config.get("llm_api_key"):
            self.active_translator = LLMTranslator(
                api_url=self.config.get("llm_api_url", "https://api.deepseek.com/v1"),
                api_key=self.config.get("llm_api_key", ""),
                model_name=self.config.get("llm_model", "deepseek-chat"),
                style_prompt=self.config.get("llm_prompt", "")
            )
        else:
            self.active_translator = self.free_translator

    def update_config(self, new_config: Dict[str, Any]):
        self.config.update(new_config)
        self._init_engine()

    def translate_to_en(self, text: str) -> str:
        return self.active_translator.translate(text, target_lang="en")
