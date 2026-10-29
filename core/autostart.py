"""开机自启：Windows 任务计划 / macOS LaunchAgent / Linux XDG 自启。

为什么不用注册表 Run：打包版带 uac_admin manifest，注册表 Run 启动
会在每次开机时弹一次 UAC（违背静默启动；点掉就等于没自启）。任务
计划在创建时一次授权（/RL HIGHEST），之后每次登录静默提权启动，
与 manifest 提权路线一致。

任务要点（托盘常驻程序不能省）：
- 触发器：用户登录时（ONLOGON / LogonTrigger）。
- 最高权限：HighestAvailable，登录时不再弹 UAC。
- 执行时限：PT0S（不限时）。默认 3 天时限会杀掉常驻托盘程序，
  schtasks /CREATE 命令行改不了这一项，必须用 XML 定义任务。
- 电池：笔记本上切换电池时不停止、不禁启动，否则合盖/拔电就掉线。
- 已在运行：忽略新实例（程序自己还有单实例互斥，双重保险）。

macOS 用 LaunchAgent（~/Library/LaunchAgents，用户级、登录启动、
不提权，所以没有 Windows 那种便携版提权风险；只在磁盘映像里运行
时拒绝，理由是路径会失效）。Linux 用 XDG 自启目录的 .desktop。
两者的实际状态都以自启文件在不在为准。
"""

import os
import shlex
import subprocess
import sys
import tempfile
from xml.sax.saxutils import escape as _xml_escape

from core.logging import error as _log_error, debug as _log_debug
from core.platform import IS_LINUX, IS_MAC, IS_WINDOWS

TASK_NAME = "ManggoProClient"


def _exe_command() -> str:
    """Exec 动作的 Command 部分：打包版是 exe 本身，源码运行是 python.exe
    （main.py 路径放 Arguments 里，见 _exe_arguments）。"""
    return sys.executable


def _exe_arguments() -> str:
    """Exec 动作的 Arguments 部分（打包版为空，源码运行是 main.py 路径）。"""
    if getattr(sys, "frozen", False):
        return ""
    main_py = os.path.normpath(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "main.py")
    )
    return f'"{main_py}"'


def _run_schtasks(args) -> subprocess.CompletedProcess:
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    return subprocess.run(
        ["schtasks"] + args,
        capture_output=True,
        text=True,
        timeout=30,
        creationflags=flags,
    )


def _task_xml() -> str:
    """任务计划 XML：时限/电池/多实例这几项命令行建任务时改不了，只能走 XML。"""
    command = _xml_escape(_exe_command())
    arguments = _xml_escape(_exe_arguments())
    args_xml = f"<Arguments>{arguments}</Arguments>" if arguments else ""
    return f"""<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Author>ManggoProClient</Author>
    <Description>Manggo Pro Client 开机自启（任务计划，最高权限，登录时静默启动）</Description>
  </RegistrationInfo>
  <Triggers>
    <LogonTrigger>
      <Enabled>true</Enabled>
    </LogonTrigger>
  </Triggers>
  <Principals>
    <Principal id="Author">
      <LogonType>InteractiveToken</LogonType>
      <RunLevel>HighestAvailable</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <AllowStartOnBatteries>true</AllowStartOnBatteries>
    <ExecutionTimeLimit>PT0S</ExecutionTimeLimit>
    <Enabled>true</Enabled>
    <Hidden>false</Hidden>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>{command}</Command>
      {args_xml}
    </Exec>
  </Actions>
</Task>
"""


def is_autostart_enabled() -> bool:
    """开机自启的实际状态：Windows 查任务计划，macOS/Linux 查自启
    文件在不在（设置页以这个为准回填勾选，配置文件只是备份）。"""
    if IS_MAC:
        return os.path.isfile(_mac_plist_path())
    if IS_LINUX:
        return os.path.isfile(_linux_desktop_path())
    if not IS_WINDOWS:
        return False
    try:
        return _run_schtasks(["/QUERY", "/TN", TASK_NAME]).returncode == 0
    except Exception:
        return False


def set_autostart_enabled(enabled: bool) -> bool:
    """创建 / 删除开机任务；返回 True 表示最终状态与要求一致。

    创建先走 XML（时限/电池/多实例可控），XML 失败再退回命令行创建
    （/SC ONLOGON /RL HIGHEST），两者都失败才返回 False。
    """
    if IS_MAC:
        return _set_mac_autostart(enabled)
    if IS_LINUX:
        return _set_linux_autostart(enabled)
    if not IS_WINDOWS:
        return False
    if enabled:
        # 便携版绝不允许开机自启（2026-10-28 review）：便携包通常解压在
        # 用户可写目录，最高权限任务会在下次登录以管理员身份跑它，
        # 同用户的程序替换 exe 就能提权；只有安装版（Program Files，
        # 非管理员写不进去）才配得上最高权限自启。删除任务不受限。
        from core.version import get_channel

        if get_channel() != "安装版":
            _log_error("AUTOSTART", "portable channel refuses autostart task")
            return False
    try:
        if not enabled:
            return _run_schtasks(["/DELETE", "/TN", TASK_NAME, "/F"]).returncode == 0
        tmp = None
        try:
            # UTF-16 带 BOM：与声明一致，也是任务计划程序自己的保存格式。
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".xml", delete=False, encoding="utf-16"
            ) as f:
                f.write(_task_xml())
                tmp = f.name
            r = _run_schtasks(["/CREATE", "/TN", TASK_NAME, "/XML", tmp, "/F"])
            if r.returncode == 0:
                return True
            _log_error("AUTOSTART", f"XML task create failed, falling back: {r.stderr.strip()[:200]}")
        finally:
            if tmp:
                try:
                    os.remove(tmp)
                except Exception as e:
                    _log_debug("AUTOSTART", f"tmp cleanup failed: {e}")
        r = _run_schtasks([
            "/CREATE", "/TN", TASK_NAME, "/TR", _exe_command_with_args(),
            "/SC", "ONLOGON", "/RL", "HIGHEST", "/F",
        ])
        if r.returncode != 0:
            _log_error("AUTOSTART", f"task create failed: {r.stderr.strip()[:200]}")
        return r.returncode == 0
    except Exception as e:
        _log_error("AUTOSTART", f"set_autostart_enabled failed: {e}")
        return False


def _exe_command_with_args() -> str:
    """命令行版 /TR 用的完整命令行（命令 + 参数拼成一行，路径加引号）。"""
    cmd = f'"{_exe_command()}"'
    args = _exe_arguments()
    return f"{cmd} {args}" if args else cmd


# ---- macOS：LaunchAgent（用户级，登录时启动，不提权） ----
MAC_LAUNCH_LABEL = "top.izuna.manggoproclient"


def _program_arguments():
    """启动参数列表（plist 的 ProgramArguments / desktop 的 Exec 共用）：
    打包版只有 exe 本身；源码运行是 python + main.py 路径。"""
    args = [_exe_command()]
    extra = _exe_arguments()
    if extra:
        args.append(extra.strip('"'))
    return args


def _mac_plist_path() -> str:
    return os.path.join(
        os.path.expanduser("~"), "Library", "LaunchAgents",
        f"{MAC_LAUNCH_LABEL}.plist",
    )


def _mac_plist_text() -> str:
    items = "\n".join(
        f"        <string>{_xml_escape(a)}</string>" for a in _program_arguments()
    )
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>{MAC_LAUNCH_LABEL}</string>
    <key>ProgramArguments</key>
    <array>
{items}
    </array>
    <key>RunAtLoad</key>
    <true/>
</dict>
</plist>
"""


def _run_quiet(cmd) -> None:
    """launchctl 装载/卸载：尽力而为，失败不算数（plist 文件在不在
    才是状态本身，launchctl 只是让本次登录立即生效）。"""
    try:
        subprocess.run(cmd, capture_output=True, timeout=15)
    except Exception as e:
        _log_debug("AUTOSTART", f"{cmd[0]} failed quietly: {e}")


def _set_mac_autostart(enabled: bool) -> bool:
    path = _mac_plist_path()
    try:
        if enabled:
            # 在磁盘映像（/Volumes）里运行时拒绝：映像随时会卸载，
            # 自启会指向一个不存在的路径（与 Windows 便携版守卫同理，
            # 但这里是路径有效性问题，不是提权问题）。
            if os.path.abspath(sys.executable).startswith("/Volumes/"):
                _log_error("AUTOSTART", "running from a disk image, refusing autostart")
                return False
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(_mac_plist_text())
            _run_quiet(["launchctl", "load", "-w", path])
        else:
            _run_quiet(["launchctl", "unload", path])
            try:
                os.remove(path)
            except FileNotFoundError:
                pass
        return os.path.isfile(path) == enabled
    except Exception as e:
        _log_error("AUTOSTART", f"set mac autostart failed: {e}")
        return False


# ---- Linux：XDG 自启目录（用户级） ----
def _linux_desktop_path() -> str:
    return os.path.join(
        os.path.expanduser("~"), ".config", "autostart",
        "manggo-pro-client.desktop",
    )


def _linux_desktop_text() -> str:
    exec_line = shlex.join(_program_arguments())
    return (
        "[Desktop Entry]\n"
        "Type=Application\n"
        "Name=Manggo Pro Client\n"
        f"Exec={exec_line}\n"
        "X-GNOME-Autostart-enabled=true\n"
        "NoDisplay=false\n"
    )


def _set_linux_autostart(enabled: bool) -> bool:
    path = _linux_desktop_path()
    try:
        if enabled:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(_linux_desktop_text())
        else:
            try:
                os.remove(path)
            except FileNotFoundError:
                pass
        return os.path.isfile(path) == enabled
    except Exception as e:
        _log_error("AUTOSTART", f"set linux autostart failed: {e}")
        return False
