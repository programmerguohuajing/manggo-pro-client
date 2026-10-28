"""程序版本号与安装渠道：唯一来源是仓库根目录的 packaging/VERSION。

关于页以前写死的 "v2.0 Pro Edition" 是假版本，已作废；现在这里读
真实版本。打包时 spec 把 packaging/VERSION 以 datas 打进程序，
所以源码运行和打包运行都能读到（打包后文件位置因平台而异，
这里按多个候选位置依次找，第一个存在即用）。
"""

import os
import sys


def _candidate_paths():
    candidates = []
    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            candidates.append(os.path.join(meipass, "VERSION"))
        exe_dir = os.path.dirname(sys.executable)
        candidates.append(os.path.join(exe_dir, "VERSION"))
        candidates.append(os.path.join(exe_dir, "_internal", "VERSION"))
        candidates.append(os.path.join(exe_dir, "..", "Resources", "VERSION"))
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    candidates.append(os.path.join(project_root, "packaging", "VERSION"))
    return candidates


def get_version() -> str:
    """返回如 "1.0.0"；读不到时返回 "未知"（不编造版本号）。"""
    for path in _candidate_paths():
        try:
            with open(path, "r", encoding="utf-8") as f:
                version = f.read().strip()
            if version:
                return version
        except Exception:
            continue
    return "未知"


def get_channel() -> str:
    """安装渠道：安装版 / 便携版 / 源码运行（按程序实际路径判断）。"""
    if not getattr(sys, "frozen", False):
        return "源码运行"
    exe = os.path.abspath(sys.executable)
    if sys.platform == "win32":
        # 以前是子串 "program files" in 路径：便携版放在
        # "C:\Program Files Backup\..." 这类目录下会被误判成安装版
        # （2026-10-28 review 小问题）。现在按规范化后的路径分量比：
        # 程序目录等于 Program Files 目录本身，或在其子目录下，才算安装版。
        exe_dir = os.path.normcase(os.path.normpath(os.path.dirname(exe)))
        candidates = []
        for var in ("ProgramFiles", "ProgramFiles(x86)"):
            pf = os.environ.get(var)
            if pf:
                candidates.append(pf)
        drive = os.path.splitdrive(exe)[0] or "C:"
        candidates.append(os.path.join(drive, os.sep, "Program Files"))
        candidates.append(os.path.join(drive, os.sep, "Program Files (x86)"))
        for pf in candidates:
            pf_norm = os.path.normcase(os.path.normpath(pf))
            if exe_dir == pf_norm or exe_dir.startswith(pf_norm + os.sep):
                return "安装版"
        return "便携版"
    if sys.platform == "darwin":
        if exe.startswith("/Applications/"):
            return "安装版"
        return "便携版"
    if exe.startswith("/usr/share/"):
        return "安装版"
    return "便携版"


__version__ = get_version()
