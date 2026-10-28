"""在线更新：检查 GitHub Releases、比对版本、按平台选包、下载。

刻意保持 Qt-free（只有标准库），这样版本比对和选包逻辑不用起
Qt 就能单测；界面侧的线程与弹窗在 ui/settings_window.py 里。

更新源（按顺序尝试，全部走匿名请求，仓库公开、无需 token）：
1. GitHub Releases 直连（匿名调用限额 60 次/小时/IP，手动检查够用）；
2. gh-proxy.com 代理的同一 Releases 接口（实测可用）；
3. jsDelivr data API 查版本（实测与 GitHub 最新 tag 一致），下载地址
   按发行版附件命名规则构造，下载时优先走代理。
只有 404 是定性结论（确实没有 Release），直接报错；网络失败、
403/5xx、解析失败都换下一个源。Actions Artifacts 30 天过期，
不能当更新源，所以发布走 Release（见工作流的 publish-release job）。

国内直连 GitHub 常常失败，所以检查与下载都有镜像回退：检查走
上面的源链，下载对每个地址再展开直连 + 各代理的候选顺序。
CNB 镜像目前不存在（cnb.cool 上查不到同名仓库），建好镜像后
再接 CNB 源；ghfast.top 只代理下载、不代理 API，所以只进下载候选。

v1 不做静默自动安装、不做增量更新：下载完成后按平台引导用户
覆盖安装（Windows 安装版直接启动安装器；其余平台打开下载的
安装包/磁盘映像，由用户完成最后一步）。

完整性（2026-10-28 review 问题3）：
- 每个 Release 附带 SHA256SUMS（CI 在 publish 时生成，第 9 个附件），
  下载后按文件名比对 SHA256，不一致或缺失都删文件并拒绝安装。
- 同时核对 Content-Length：实收字节与声明不符视为截断，换下一个镜像。
- 读取阶段的超时（TimeoutError / OSError）与连接失败一样，都会切到
  下一个源，不会直接崩掉整个更新。
- 信任模型说清楚：校验文件优先走 GitHub 直连（小文件，直连成功时
  校验是强的）；只有代理可用时，校验只能防损坏/截断，防不住代理
  本身同时伪造安装包与校验文件。Authenticode 签名需要代码签名证书，
  目前没有证书，先不做，等拿到证书再给安装器加签。
"""

import hashlib
import json
import os
import platform
import sys
import tempfile
import urllib.error
import urllib.request

REPO = "programmerguohuajing/manggo-pro-client"
API_LATEST = f"https://api.github.com/repos/{REPO}/releases/latest"
# 实测可用的加速源（2026-10-28 沙箱验证）：
# - gh-proxy.com：API 与下载都能代理；
# - ghfast.top：只能代理下载，API 返回的不是 JSON，只进下载候选；
# - jsDelivr data API：版本与 GitHub 最新 tag 一致，但只能提供仓库
#   文件、不能提供 Release 附件，所以只做版本源。
# mirror.ghproxy.com / ghproxy.net / proxy.ghproxy.com 同期实测不可用，
# 不放进默认链。
PROXY_PREFIXES = ("https://gh-proxy.com/", "https://ghfast.top/")
JSDELIVR_DATA = f"https://data.jsdelivr.com/v1/packages/gh/{REPO}"


class UpdateError(Exception):
    pass


class _Fallback(Exception):
    """该源不可用，换下一个源；不是最终错误。"""


class _DefinitiveDownloadError(UpdateError):
    """下载地址定性不存在（404），换镜像也没有意义，直接报错。"""


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


def _fetch_api_release(url, timeout):
    """从一个 Releases /latest 接口取 Release；不可用时报 _Fallback。

    只有 404 是定性结论（确实没有 Release，或者仓库是私有的——
    GitHub 对匿名用户隐藏私有仓库，一律返回 404，两者无法区分，
    所以文案不把话说死），直接报 UpdateError；网络失败、403/5xx、
    解析失败都只是该源不可用，交给调用方换下一个源。
    """
    request = urllib.request.Request(
        url,
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
            raise UpdateError("无法读取公开的 Release 信息（可能暂无 Release，或仓库未公开）")
        raise _Fallback(f"HTTP {e.code}")
    except (urllib.error.URLError, OSError) as e:
        # OSError 含 TimeoutError：读取阶段的超时不走 URLError 包装，
        # 直接以 TimeoutError 抛出，不捕获它就切不到下一个源。
        raise _Fallback(f"网络请求失败：{getattr(e, 'reason', e)}")
    except (ValueError, KeyError) as e:
        raise _Fallback(f"更新信息解析失败：{e}")
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


def _constructed_asset(tag, channel=None):
    """按发行版附件命名规则，给当前平台构造一个附件（jsDelivr 源用）。

    jsDelivr data API 只给版本号，不给附件列表；但附件名是发布工作流
    定的（见 select_asset 的匹配规则），所以能按平台 + 渠道 + 架构
    反推出来。未知平台返回 None，调用方按“没有当前平台的安装包”处理。
    """
    if channel is None:
        from core.version import get_channel

        channel = get_channel()
    version = tag.lstrip("v")
    if sys.platform == "win32":
        name = (
            "ManggoProClient-Setup.exe"
            if channel == "安装版"
            else "ManggoProClient-Windows-x64.zip"
        )
    elif sys.platform == "darwin":
        name = (
            "ManggoProClient-macOS-AppleSilicon.dmg"
            if _arch_key() == "arm"
            else "ManggoProClient-macOS-Intel.dmg"
        )
    elif sys.platform.startswith("linux"):
        name = f"manggo-pro-client_{version}_amd64.deb"
    else:
        return None
    direct = f"https://github.com/{REPO}/releases/download/{tag}/{name}"
    # 走到 jsDelivr 源，说明直连与代理 API 都已失败，下载优先走代理。
    return {"name": name, "url": PROXY_PREFIXES[0] + direct}


def _fetch_jsdelivr_release(timeout):
    """从 jsDelivr data API 取最新版本；返回与 _fetch_api_release 同形的 dict。

    data API 的 versions 按版本号排，但不保证顺序，所以取解析后最大
    的一个；body 拿不到，置空（界面只在有新版时展示它，可空）。
    """
    request = urllib.request.Request(
        JSDELIVR_DATA,
        headers={"User-Agent": "ManggoProClient-Updater"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise _Fallback(f"HTTP {e.code}")
    except (urllib.error.URLError, OSError) as e:
        raise _Fallback(f"网络请求失败：{getattr(e, 'reason', e)}")
    except (ValueError, KeyError) as e:
        raise _Fallback(f"更新信息解析失败：{e}")
    best = None
    for entry in data.get("versions", []) or []:
        parsed = parse_version(entry.get("version", ""))
        if parsed is not None and (best is None or parsed > best[0]):
            best = (parsed, entry["version"])
    if best is None:
        raise _Fallback("jsDelivr 暂无该仓库版本")
    tag = "v" + best[1]
    asset = _constructed_asset(tag)
    return {
        "version": best[1],
        "tag": tag,
        "body": "",
        "assets": [asset] if asset is not None else [],
    }


def fetch_latest(timeout=10):
    """按 直连 → gh-proxy → jsDelivr 的顺序查最新 Release。

    返回 {"version", "tag", "body", "assets": [{"name", "url"}], "via": 源名}。
    timeout 是每个源的单次超时（秒），不是总超时；最坏约 30 秒，
    检查跑在界面线程之外，不会冻住界面。
    """
    strategies = [
        ("GitHub 直连", lambda: _fetch_api_release(API_LATEST, timeout)),
        ("gh-proxy", lambda: _fetch_api_release(PROXY_PREFIXES[0] + API_LATEST, timeout)),
        ("jsDelivr", lambda: _fetch_jsdelivr_release(timeout)),
    ]
    reasons = []
    for name, fn in strategies:
        try:
            release = fn()
        except UpdateError:
            raise
        except _Fallback as e:
            reasons.append(f"{name}：{e}")
            continue
        release["via"] = name
        return release
    raise UpdateError(f"无法连接更新服务器（已尝试直连与镜像）：{'；'.join(reasons)}")


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


def _download_candidates(url):
    """把一个下载地址展开成候选顺序：原地址优先，其次直连，其次各代理。

    检查走哪个源，下载就优先走哪个源（原地址已经是那个源的形式）；
    原地址失败时再试其他形式。去重，保证每个地址最多试一次。
    """
    base = url
    for prefix in PROXY_PREFIXES:
        if url.startswith(prefix):
            base = url[len(prefix):]
            break
    candidates = []
    for candidate in [url, base] + [prefix + base for prefix in PROXY_PREFIXES]:
        if candidate and candidate not in candidates:
            candidates.append(candidate)
    return candidates


def _download_one(url, dest_path, progress_cb=None):
    """从单个地址下载；失败时报 UpdateError（404 则报定性错误）。"""
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
            if total and received != total:
                # 截断的下载以前会判成功；现在视为失败，交给调用方换镜像。
                raise UpdateError(
                    f"下载不完整：声明 {total} 字节，实收 {received} 字节：{url}"
                )
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise _DefinitiveDownloadError(f"下载地址不存在（HTTP 404）：{url}")
        raise UpdateError(f"下载失败（HTTP {e.code}）：{url}")
    except (urllib.error.URLError, OSError) as e:
        # 读取阶段的 TimeoutError 不包在 URLError 里，不捕获就切不到下一个镜像。
        raise UpdateError(f"下载失败：{getattr(e, 'reason', e)}")
    return dest_path


SHA256SUMS_NAME = "SHA256SUMS"


def sha256sums_url(tag):
    """某 tag 的 SHA256SUMS 直连地址（Release 的第 9 个附件）。"""
    return f"https://github.com/{REPO}/releases/download/{tag}/{SHA256SUMS_NAME}"


def parse_sha256sums(text):
    """解析 sha256sum 输出：{文件名: 小写 hex}。

    兼容 `hash  name` 与 `hash *name` 两种格式；文件名含空格也能解析
    （hash 固定 64 位 hex，取第一段，余下整段是文件名）。
    非法行跳过。"""
    result = {}
    for line in (text or "").splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split(None, 1)
        if len(parts) != 2:
            continue
        digest, name = parts[0].lower(), parts[1].strip().lstrip("*")
        if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
            continue
        if name:
            result[name] = digest
    return result


def _sha256_of_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(65536)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _fetch_text_candidates(url, timeout=15):
    """按 [直连, 各代理] 的顺序取一个小文本文件（SHA256SUMS 用）。

    校验文件优先走直连：文件小，直连成功时校验是强的；直连 404 说明
    该版本根本没附校验文件，是定性结论；直连网络失败才走代理。
    全部失败时报 UpdateError（不静默放行）。"""
    direct = url
    for prefix in PROXY_PREFIXES:
        if url.startswith(prefix):
            direct = url[len(prefix):]
            break
    candidates = [direct] + [prefix + direct for prefix in PROXY_PREFIXES]
    errors = []
    for candidate in candidates:
        request = urllib.request.Request(
            candidate, headers={"User-Agent": "ManggoProClient-Updater"}
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as resp:
                return resp.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            if candidate == direct and e.code == 404:
                raise UpdateError(
                    "该版本未附带 SHA256SUMS 校验文件，拒绝安装"
                    "（请从 GitHub Releases 页手动下载）"
                )
            errors.append(f"{candidate}：HTTP {e.code}")
        except (urllib.error.URLError, OSError) as e:
            errors.append(f"{candidate}：{getattr(e, 'reason', e)}")
    raise UpdateError(f"无法下载 SHA256SUMS 校验文件：{'；'.join(errors)}")


def download_and_verify(url, dest_path, tag, progress_cb=None):
    """下载并做 SHA256 校验；任一环节失败都删文件并报错，绝不放行。

    tag 为空时无法定位校验文件，直接拒绝（调用方必须传 Release 的 tag）。
    """
    if not tag:
        raise UpdateError("缺少版本信息，无法校验安装包，拒绝安装")
    download(url, dest_path, progress_cb)
    try:
        sums_text = _fetch_text_candidates(sha256sums_url(tag))
        sums = parse_sha256sums(sums_text)
        name = os.path.basename(dest_path)
        expected = sums.get(name)
        if expected is None:
            raise UpdateError(
                f"SHA256SUMS 中没有 {name} 的记录，拒绝安装"
            )
        actual = _sha256_of_file(dest_path)
        if actual != expected:
            raise UpdateError(
                "校验失败：下载的文件与发布时的 SHA256 不一致"
                "（可能被篡改或下载不完整），已删除该文件"
            )
    except UpdateError:
        try:
            os.remove(dest_path)
        except OSError:
            pass
        raise
    return dest_path


def download(url, dest_path, progress_cb=None):
    """按候选顺序下载到 dest_path；progress_cb(percent) 在已知总大小时回调。

    全部候选失败时删掉残缺文件再报错，避免用户拿到一半的安装包。
    """
    errors = []
    for candidate in _download_candidates(url):
        try:
            return _download_one(candidate, dest_path, progress_cb)
        except _DefinitiveDownloadError:
            raise
        except UpdateError as e:
            errors.append(str(e))
    try:
        os.remove(dest_path)
    except OSError:
        pass
    raise UpdateError(f"下载失败（已尝试 {len(errors)} 个地址）：{'；'.join(errors)}")
