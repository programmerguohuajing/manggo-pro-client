#!/usr/bin/env python3
"""打包后瘦身：删掉 PyInstaller 收进来、但本应用用不到的死重。

用法：python packaging/prune.py dist/ManggoProClient
      python packaging/prune.py dist/ManggoProClient.app   （macOS）

删什么、为什么（均以 Linux 包实测 + ldd/readelf 验证，见 packaging/README.md）：
- Qt 翻译文件 *.qm：应用从未安装 QTranslator，99 个翻译文件一个都不会
  被加载，QMessageBox 等标准按钮本来就是英文。
- Qt 库 Quick / Qml / Pdf / Svg / VirtualKeyboard：应用只 import
  QtCore/QtGui/QtWidgets，QtGui/QtWidgets 的 NEEDED 里没有这些库；
  只有它们自己的插件引用它们，所以库和插件成对删。
- Qt 插件：qpdf/qsvg/qtga/qtiff/qwbmp/qwebp/qicns 图片格式（应用只用
  .ico/.png，PNG 是 Qt6 内置格式，不靠插件）、eglfs/linuxfb/vnc/minimalegl
  嵌入式平台后端（桌面包用 xcb/wayland/cocoa/windows）、
  egldeviceintegrations、Wayland 客户端装饰（删了走服务端装饰）、
  虚拟键盘输入法插件（桌面用 ibus/fcitx，ibus 插件保留）。
- 刻意不删：opencv 的 ffmpeg/Qt5 库 —— cv2.abi3.so 启动时就直接链接
  它们，删了截图 OCR 会起不来；onnxruntime、numpy、ICU 数据同理。

只按文件名匹配（跨 Win/mac/Linux 的 .dll/.dylib/.so 命名都覆盖），
删之前先算总大小，删完打印省了多少；找不到也不报错。
"""

import fnmatch
import sys
from pathlib import Path

# 文件名通配（不区分大小写比对，Windows 上 DLL 名大小写不一）
LIB_PATTERNS = [
    "libQt6Quick*", "Qt6Quick*",
    "libQt6Qml*", "Qt6Qml*",
    "libQt6Pdf*", "Qt6Pdf*",
    "libQt6Svg*", "Qt6Svg*",
    "libQt6VirtualKeyboard*", "Qt6VirtualKeyboard*",
]
PLUGIN_PATTERNS = [
    # imageformats（保留 qjpeg/qico/qgif；PNG 内置）
    "libqpdf*", "qpdf*",
    "libqsvg*", "qsvg*",
    "libqtga*", "qtga*",
    "libqtiff*", "qtiff*",
    "libqwbmp*", "qwbmp*",
    "libqwebp*", "qwebp*",
    "libqicns*", "qicns*",
    # 嵌入式平台后端
    "libqeglfs*", "qeglfs*",
    "libqlinuxfb*", "qlinuxfb*",
    "libqvnc*", "qvnc*",
    "libqminimalegl*", "qminimalegl*",
    # egldeviceintegrations 整目录
    "libqeglfs-*-integration*", "qeglfs-*-integration*",
    # Wayland 客户端装饰（服务端装饰兜底）
    "libadwaita*", "adwaita*",
    "libbradient*", "bradient*",
    # 虚拟键盘输入法插件（ibus 插件不在此列，保留）
    "libqtvirtualkeyboardplugin*", "qtvirtualkeyboardplugin*",
    # svg 图标引擎（图标是 .ico/.png，不用 svg）
    "libqsvgicon*", "qsvgicon*",
]


def _match(name: str, patterns) -> bool:
    lower = name.lower()
    return any(fnmatch.fnmatchcase(lower, p.lower()) for p in patterns)


def main() -> int:
    # Windows runner 的 stdout 默认是 cp1252，中文汇总一打印就
    # UnicodeEncodeError（2026-10-27 实测：删完了、打印时崩，整个 job 失败）。
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass
    if len(sys.argv) != 2:
        print("用法：python packaging/prune.py <dist 目录或 .app>")
        return 2
    root = Path(sys.argv[1])
    if not root.exists():
        print(f"prune：{root} 不存在，跳过")
        return 0

    def _size(p: Path) -> int:
        return sum(f.stat().st_size for f in p.rglob("*") if f.is_file())

    before = _size(root)
    removed = []

    # 1. 翻译文件：任何 translations 目录下的 *.qm 全删
    for f in root.rglob("*.qm"):
        if "translations" in f.parts:
            removed.append(f)

    # 2. Qt 库 + 插件：按文件名删
    for f in root.rglob("*"):
        if not f.is_file():
            continue
        if _match(f.name, LIB_PATTERNS) or _match(f.name, PLUGIN_PATTERNS):
            if f not in removed:
                removed.append(f)

    freed = 0
    for f in removed:
        try:
            freed += f.stat().st_size
            f.unlink()
        except OSError as exc:  # 删不掉就留着，别让打包失败
            print(f"prune：删不掉 {f}：{exc}")

    after = _size(root)
    print(
        f"prune：删 {len(removed)} 个文件，"
        f"{before / 1048576:.1f} MB -> {after / 1048576:.1f} MB，"
        f"省 {freed / 1048576:.1f} MB"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
