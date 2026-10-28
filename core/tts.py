"""
语音朗读 (TTS)：
- Windows：原生 SAPI 语音引擎，纯离线极速播放（原有行为不变）。
- macOS：系统自带 say 命令。
- Linux：尝试 espeak / espeak-ng，未安装则记日志，不崩溃。
"""
import shutil
import subprocess
import threading

from core.logging import error as _log_error, debug as _log_debug
from core.platform import IS_LINUX, IS_MAC, IS_WINDOWS

if IS_WINDOWS:
    import pythoncom
    import win32com.client


class TTSPlayer:
    def __init__(self):
        self._lock = threading.Lock()

    def speak(self, text: str):
        """异步朗读文本"""
        if not text.strip():
            return
        threading.Thread(target=self._speak_worker, args=(text,), daemon=True).start()

    def _speak_worker(self, text: str):
        with self._lock:
            if IS_WINDOWS:
                try:
                    pythoncom.CoInitialize()
                    speaker = win32com.client.Dispatch("SAPI.SpVoice")
                    # 设置适中语速
                    speaker.Rate = 0
                    speaker.Volume = 100
                    speaker.Speak(text)
                except Exception as e:
                    _log_error("TTS", f"Error: {e}")
                finally:
                    try:
                        pythoncom.CoUninitialize()
                    except Exception as e:
                        _log_debug("TTS", f"CoUninitialize failed: {e}")
                return
            if IS_MAC:
                # 以 - 开头的文本会被 say 当成选项；say 对 -- 的支持不确定，
                # 前面补一个空格最稳妥（朗读时听不出来）。
                say_text = text if not text.startswith("-") else " " + text
                try:
                    subprocess.run(["say", say_text], check=False)
                except Exception as e:
                    _log_error("TTS", f"Error (say): {e}")
                return
            if IS_LINUX:
                engine = shutil.which("espeak-ng") or shutil.which("espeak")
                if not engine:
                    _log_error("TTS", "espeak not installed; install espeak-ng for speech on Linux")
                    return
                try:
                    # espeak 是标准 getopt 解析，-- 之后的一律按文本处理。
                    subprocess.run([engine, "--", text], check=False)
                except Exception as e:
                    _log_error("TTS", f"Error ({engine}): {e}")
                return


tts_player = TTSPlayer()
