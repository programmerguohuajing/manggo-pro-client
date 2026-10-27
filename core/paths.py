"""程序数据文件路径：便携行为不变，系统安装兜底。

背景：历史记录、配置、日志、单实例 pid 一直写在程序目录旁边。
便携包解压到用户自己的目录时没问题，但系统安装器装到
Program Files、/Applications、/usr/share 后，普通用户写不进
安装目录——数据库建表会直接抛错导致启动失败，配置也存不住。

规则（刻意保守）：
- 程序目录可写时，路径与原来一模一样（便携包行为、老数据零迁移）；
- 程序目录不可写时，才落到用户目录（Windows：%APPDATA%\\ManggoProClient，
  mac/Linux：~/.config/manggo-pro-client），并且如果程序旁已有
  同名文件而用户目录还没有，首次顺手拷一份过去（便携包换系统
  安装时，历史和配置不会丢）。
"""

import os
import shutil
import tempfile


def _dir_writable(directory: str) -> bool:
    """目录是否真的可写：实际建一个临时文件再删掉。

    不能用 os.access(directory, os.W_OK)：Windows 上它只看文件属性，
    不看 ACL——Program Files 下的目录它也返回 True，但实际建文件会
    被拒绝。2026-10-27 实测：v1.0.0 安装版就是这么在启动时崩的
    （sqlite3.OperationalError: unable to open database file，
    main.py:35 -> database.py:141），因为 data_file 误判 _internal
    可写，没走到用户目录兜底。
    """
    try:
        fd, tmp = tempfile.mkstemp(prefix=".manggo-write-test-", dir=directory)
    except Exception:
        return False
    try:
        os.close(fd)
    finally:
        try:
            os.remove(tmp)
        except Exception:
            pass
    return True


def _user_data_dir() -> str:
    if os.name == "nt":
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
        return os.path.join(base, "ManggoProClient")
    return os.path.join(os.path.expanduser("~"), ".config", "manggo-pro-client")


def data_file(preferred_path: str) -> str:
    """给定首选路径（程序旁），返回实际可用的数据文件路径。"""
    directory = os.path.dirname(preferred_path)
    if _dir_writable(directory):
        return preferred_path
    user_dir = _user_data_dir()
    try:
        os.makedirs(user_dir, exist_ok=True)
    except Exception:
        return preferred_path
    user_path = os.path.join(user_dir, os.path.basename(preferred_path))
    if not os.path.exists(user_path) and os.path.exists(preferred_path):
        try:
            shutil.copy2(preferred_path, user_path)
        except Exception:
            pass
    return user_path
