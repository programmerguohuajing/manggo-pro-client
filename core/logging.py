"""
统一日志：替代原来三处各写一份的日志出口。

原来：
- core/hook.py、core/replacer.py 各有一份 _log，往同一个 debug_app.log 写，
  格式还不一样（一个无模块名，一个带 [REPLACER]）；
- core/translator.py、core/tts.py、core/database.py、ui/settings_window.py
  用 print，静默启动（pythonw）下根本看不到，调试 bat 下又跟钩子日志分家。

现在：所有模块走这里。同一条记录同时进三处——
- debug_app.log（路径、文件名与原来完全一致）；
- 内存环形缓冲（上限 1000 条，供诊断控制台展示，控制台默认过滤掉 DEBUG）；
- 控制台标准输出（仅 INFO 及以上；DEBUG 只落文件与缓冲，不刷屏调试 bat）。

注意：钩子逐键日志仍保留在文件里（排热键问题时需要），级别为 DEBUG，
诊断控制台默认不显示，选“全部”才可见；这只是展示过滤，不是关掉记录。
"""
import os
import sys
import threading
import time
from collections import deque
from typing import List, Dict

LOG_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "debug_app.log")

LEVELS = {"DEBUG": 10, "INFO": 20, "WARNING": 30, "ERROR": 40}
MAX_BUFFER = 1000

_lock = threading.Lock()
_buffer: deque = deque(maxlen=MAX_BUFFER)


def _format(record: Dict[str, str]) -> str:
    return f"[{record['time']}] [{record['level']}] [{record['module']}] {record['message']}"


def log(level: str, module: str, message: str) -> None:
    level = level if level in LEVELS else "INFO"
    record = {
        "time": f"{time.strftime('%H:%M:%S')}.{int(time.time() * 1000) % 1000:03d}",
        "level": level,
        "module": module,
        "message": str(message),
    }
    line = _format(record)
    with _lock:
        _buffer.append(record)
        try:
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except Exception:
            pass
    if LEVELS[level] >= LEVELS["INFO"]:
        try:
            print(line, flush=True)
        except Exception:
            pass


def debug(module: str, message: str) -> None:
    log("DEBUG", module, message)


def info(module: str, message: str) -> None:
    log("INFO", module, message)


def warning(module: str, message: str) -> None:
    log("WARNING", module, message)


def error(module: str, message: str) -> None:
    log("ERROR", module, message)


def get_records() -> List[Dict[str, str]]:
    """返回缓冲快照（调用方只读，不改缓冲）。"""
    with _lock:
        return list(_buffer)


def format_record(record: Dict[str, str]) -> str:
    return _format(record)


def clear_buffer() -> None:
    with _lock:
        _buffer.clear()


def log_file_path() -> str:
    return LOG_FILE
