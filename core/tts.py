"""
语音朗读 (TTS) 模块：调用 Windows 原生 SAPI 语音引擎，纯离线极速播放
"""
import threading
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
            try:
                pythoncom.CoInitialize()
                speaker = win32com.client.Dispatch("SAPI.SpVoice")
                # 设置适中语速
                speaker.Rate = 0
                speaker.Volume = 100
                speaker.Speak(text)
            except Exception as e:
                print(f"[TTS] Error: {e}")
            finally:
                pythoncom.CoUninitialize()

tts_player = TTSPlayer()
