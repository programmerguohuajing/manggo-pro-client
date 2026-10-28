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

隐私：逐键日志已删除（2026-10-28 review），正文一律只记长度不记内容；
日志文件满 5MB 自动轮转（保留 3 个备份）；内存缓冲分两档，DEBUG 不挤占
INFO 及以上（控制台“全部”仍可看到 DEBUG）。
"""
import os
import sys
import threading
import time
from collections import deque
from typing import List, Dict

from core.paths import data_file as _data_file

LOG_FILE = _data_file(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "debug_app.log"))

LEVELS = {"DEBUG": 10, "INFO": 20, "WARNING": 30, "ERROR": 40}
MAX_BUFFER = 1000
MAX_DEBUG_BUFFER = 500
MAX_LOG_BYTES = 5 * 1024 * 1024
LOG_BACKUPS = 3

_lock = threading.Lock()
# INFO 及以上与 DEBUG 分开缓冲：DEBUG 量大时不再把 INFO/ERROR 挤出环形缓冲。
# 两档各按到达顺序编号，get_records() 按编号合并，保证时间顺序。
_buffer: deque = deque(maxlen=MAX_BUFFER)
_debug_buffer: deque = deque(maxlen=MAX_DEBUG_BUFFER)
_seq = [0]


def _rotate_if_needed() -> None:
    """日志文件超限时轮转：当前 -> .1 -> .2 -> .3，失败静默（绝不拖垮日志本身）。"""
    try:
        if not os.path.exists(LOG_FILE):
            return
        if os.path.getsize(LOG_FILE) <= MAX_LOG_BYTES:
            return
        for i in range(LOG_BACKUPS - 1, 0, -1):
            src = f"{LOG_FILE}.{i}"
            if os.path.exists(src):
                try:
                    os.replace(src, f"{LOG_FILE}.{i + 1}")
                except OSError:
                    pass
        try:
            os.replace(LOG_FILE, f"{LOG_FILE}.1")
        except OSError:
            pass
    except OSError:
        pass


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
        _seq[0] += 1
        record["seq"] = _seq[0]
        if level == "DEBUG":
            _debug_buffer.append(record)
        else:
            _buffer.append(record)
        _rotate_if_needed()
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
    """返回缓冲快照（调用方只读，不改缓冲）：两档按到达顺序合并。"""
    with _lock:
        merged = list(_buffer) + list(_debug_buffer)
    merged.sort(key=lambda r: r["seq"])
    return merged


def format_record(record: Dict[str, str]) -> str:
    return _format(record)


def clear_buffer() -> None:
    with _lock:
        _buffer.clear()
        _debug_buffer.clear()


def log_file_path() -> str:
    return LOG_FILE
