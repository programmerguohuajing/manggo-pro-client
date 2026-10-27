#!/usr/bin/env python3
"""把 Linux 便携包目录打成 .deb 安装包。

用法：python3 packaging/make-deb.py --version 1.0.0 \
         --dist dist/ManggoProClient --out manggo-pro-client_1.0.0_amd64.deb

布局（Debian 惯例）：
  /usr/share/manggo-pro-client/   程序文件（便携包 dist 目录原样搬入）
  /usr/bin/manggo-pro-client      启动包装（exec 到上面那个目录的可执行文件）
  /usr/share/applications/manggo-pro-client.desktop
  /usr/share/icons/hicolor/256x256/apps/manggo-pro-client.png

注意：程序的数据文件（history.sqlite3、config.json、debug_app.log、
.app.pid）平时写程序目录旁；装到 /usr/share 后普通用户写不进，
core/paths.py 会自动把它们落到 ~/.config/manggo-pro-client，
所以 deb 不需要、也不应该把安装目录 chmod 成全局可写。
"""

import argparse
import os
import shutil
import stat
import subprocess
import sys

DESKTOP = """[Desktop Entry]
Name=Manggo Pro Client
Comment=Selection translation, OCR and dictation assistant
Exec=/usr/bin/manggo-pro-client
Icon=manggo-pro-client
Terminal=false
Type=Application
Categories=Utility;
"""

WRAPPER = """#!/bin/sh
exec /usr/share/manggo-pro-client/ManggoProClient "$@"
"""


def build(version: str, dist: str, out: str, icon: str) -> None:
    staging = out + ".staging"
    if os.path.exists(staging):
        shutil.rmtree(staging)
    app_dir = os.path.join(staging, "usr", "share", "manggo-pro-client")
    shutil.copytree(dist, app_dir, symlinks=True)
    # 主可执行文件确保可执行位（zip/复制后也可能丢，copytree 保留模式，
    # 但这里显式保证一次）。
    exe = os.path.join(app_dir, "ManggoProClient")
    os.chmod(exe, os.stat(exe).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    bin_path = os.path.join(staging, "usr", "bin", "manggo-pro-client")
    os.makedirs(os.path.dirname(bin_path), exist_ok=True)
    with open(bin_path, "w", encoding="utf-8") as f:
        f.write(WRAPPER)
    os.chmod(bin_path, 0o755)

    desktop_path = os.path.join(
        staging, "usr", "share", "applications", "manggo-pro-client.desktop"
    )
    os.makedirs(os.path.dirname(desktop_path), exist_ok=True)
    with open(desktop_path, "w", encoding="utf-8") as f:
        f.write(DESKTOP)

    if icon and os.path.exists(icon):
        icon_path = os.path.join(
            staging,
            "usr",
            "share",
            "icons",
            "hicolor",
            "256x256",
            "apps",
            "manggo-pro-client.png",
        )
        os.makedirs(os.path.dirname(icon_path), exist_ok=True)
        shutil.copyfile(icon, icon_path)

    debian = os.path.join(staging, "DEBIAN")
    os.makedirs(debian, exist_ok=True)
    # dpkg-deb 对 DEBIAN 目录权限有硬要求（0755–0775），不能随 umask；
    # runner 默认 umask 是 022 没问题，但沙箱/其他环境可能是 027。
    os.chmod(debian, 0o755)
    control = f"""Package: manggo-pro-client
Version: {version}
Section: utils
Priority: optional
Architecture: amd64
Maintainer: programmerguohuajing <jingguohua@jxzm.net>
Depends: libgl1, libegl1, libxkbcommon0, libdbus-1-3, libfontconfig1
Description: Manggo Pro Client
 Selection translation, OCR and dictation assistant for the desktop.
 This package installs the portable build system-wide; per-user data
 (history, config, logs) lives under ~/.config/manggo-pro-client.
"""
    control_path = os.path.join(debian, "control")
    with open(control_path, "w", encoding="utf-8") as f:
        f.write(control)
    os.chmod(control_path, 0o644)
    os.chmod(desktop_path, 0o644)

    # 统一权限，不随打包环境的 umask 走：目录 755，可执行文件 755，
    # 其他文件 644。否则 umask 027 的环境打出的包，装到 /usr/share 后
    # 普通用户读不到程序文件（DEBIAN 目录的权限上面已单独处理）。
    for root, dirs, files in os.walk(staging):
        for d in dirs:
            os.chmod(os.path.join(root, d), 0o755)
        for name in files:
            path = os.path.join(root, name)
            mode = os.stat(path).st_mode
            os.chmod(path, 0o755 if mode & 0o111 else 0o644)
    os.chmod(exe, 0o755)

    subprocess.run(["dpkg-deb", "--build", staging, out], check=True)
    shutil.rmtree(staging)
    print(f"built {out} ({os.path.getsize(out)} bytes)")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", required=True)
    parser.add_argument("--dist", required=True, help="Linux 便携包目录")
    parser.add_argument("--out", required=True, help="输出 .deb 路径")
    parser.add_argument("--icon", default="assets/app.png")
    args = parser.parse_args()
    if not os.path.isdir(args.dist):
        print(f"dist 目录不存在：{args.dist}", file=sys.stderr)
        return 1
    build(args.version, args.dist, args.out, args.icon)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
