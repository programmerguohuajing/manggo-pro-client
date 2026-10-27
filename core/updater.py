"""在线更新：检查 GitHub Releases、比对版本、按平台选包、下载。

刻意保持 Qt-free（只有标准库），这样版本比对和选包逻辑不用起
Qt 就能单测；界面侧的线程与弹窗在 ui/settings_window.py 里。

更新源：GitHub Releases（仓库公开，无需 token；匿名调用限额
60 次/小时/IP，手动检查够用）。Actions Artifacts 30 天过期，
不能当更新源，所以发布走 Release（见工作流的 publish-release job）。

v1 不做静默自动安装、不做增量更新：下载完成后按平台引导用户
覆盖安装（Windows 安装版直接启动安装器；其余平台打开下载的
安装包/磁盘映像，由用户完成最后一步）。
"""

import json
import os
import platform
import sys
import tempfile
import urllib.error
import urllib.request

REPO = "programmerguohuajing/manggo-pro-client"
API_LATEST = f"https://api.github.com/repos/{REPO}/releases/latest"


class UpdateError(Exception):
    pass


def parse_version(text):
    """把 "v1.2.3" / "1.2" 解析成 (1, 2, 3)；解析不了返回 None。

    预发布后缀（如 1.0.1-beta）只比数字部分：后缀不参与比较，
    因为 Releases 的 /latest 本来就不返回预发布。
    """
    if not text:
        return None
    text = str(text).strip()
    if text.startswith("v"):
        text = text[1:]
    core = text.split("-")[0].split("+")[0]
    parts = core.split(".")
    if not parts or any(not p.isdigit() for p in parts):
        return None
    nums = [int(p) for p in parts]
    while len(nums) < 3:
        nums.append(0)
    return tuple(nums[:3])


def is_newer(remote_version, local_version) -> bool:
    """远程版是否比本地版新；任一解析失败都返回 False（不误报）。"""
    remote = parse_version(remote_version)
    local = parse_version(local_version)
    if remote is None or local is None:
        return False
    return remote > local


def fetch_latest(timeout=15):
    """返回 {"version", "tag", "body", "assets": [{"name", "url"}]}。"""
    request = urllib.request.Request(
        API_LATEST,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "ManggoProClient-Updater",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise UpdateError("还没有发布任何正式版本（仓库暂无 Release）")
        if e.code == 403:
            raise UpdateError("GitHub API 调用受限（匿名限额），请稍后再试")
        raise UpdateError(f"GitHub 请求失败（HTTP {e.code}）")
    except urllib.error.URLError as e:
        raise UpdateError(f"网络请求失败：{e.reason}")
    except (ValueError, KeyError) as e:
        raise UpdateError(f"更新信息解析失败：{e}")
    assets = [
        {"name": a.get("name", ""), "url": a.get("browser_download_url", "")}
        for a in data.get("assets", [])
        if a.get("browser_download_url")
    ]
    return {
        "version": (data.get("tag_name") or "").lstrip("v"),
        "tag": data.get("tag_name") or "",
        "body": data.get("body") or "",
        "assets": assets,
    }


def _arch_key():
    machine = platform.machine().lower()
    if machine in ("arm64", "aarch64"):
        return "arm"
    return "intel"


def select_asset(release, channel=None):
    """按当前平台 + 渠道选下载包；选不到返回 None。

    channel 影响 Windows：安装版下 Setup 安装器，覆盖安装；
    便携版下便携包 zip（运行中的 exe 锁文件，无法自己覆盖自己，
    只能下载后由用户解压覆盖）。
    """
    if channel is None:
        from core.version import get_channel

        channel = get_channel()
    wanted = None
    if sys.platform == "win32":
        wanted = (
            "ManggoProClient-Setup.exe"
            if channel == "安装版"
            else "ManggoProClient-Windows-x64.zip"
        )
    elif sys.platform == "darwin":
        wanted = (
            "ManggoProClient-macOS-AppleSilicon.dmg"
            if _arch_key() == "arm"
            else "ManggoProClient-macOS-Intel.dmg"
        )
    elif sys.platform.startswith("linux"):
        wanted = None  # 下面按前缀/后缀匹配
    for asset in release.get("assets", []):
        name = asset.get("name", "")
        if wanted is not None and name == wanted:
            return asset
        if (
            sys.platform.startswith("linux")
            and name.startswith("manggo-pro-client_")
            and name.endswith("_amd64.deb")
        ):
            return asset
    return None


def download_dir():
    """用户下载目录；没有 Downloads 文件夹时退到系统临时目录。"""
    downloads = os.path.join(os.path.expanduser("~"), "Downloads")
    if os.path.isdir(downloads):
        return downloads
    return tempfile.gettempdir()


def download(url, dest_path, progress_cb=None):
    """下载到 dest_path；progress_cb(percent) 在已知总大小时回调。"""
    request = urllib.request.Request(
        url, headers={"User-Agent": "ManggoProClient-Updater"}
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as resp:
            total = resp.headers.get("Content-Length")
            total = int(total) if total and total.isdigit() else 0
            received = 0
            with open(dest_path, "wb") as f:
                while True:
                    chunk = resp.read(65536)
                    if not chunk:
                        break
                    f.write(chunk)
                    received += len(chunk)
                    if total and progress_cb:
                        progress_cb(min(100, received * 100 // total))
    except urllib.error.URLError as e:
        raise UpdateError(f"下载失败：{e.reason}")
    return dest_path
