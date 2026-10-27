# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller 打包配置（Win / macOS / Linux 共用一份）。

要点：
- 窗口程序（console=False），不弹黑框，与“后台静默启动”一致；
  调试日志仍写 debug_app.log，托盘里有诊断控制台可看。
- 只打包 assets/，绝不打包 history.sqlite3（用户翻译历史）、
  config.json（含 API Key）、debug_app.log、.app.pid。
- RapidOCR 是函数内懒导入，PyInstaller 静态分析扫不到，必须用
  collect_all 显式收进来，否则截图 OCR 在包里一调用就崩。
- onedir（不是 onefile）：启动快，RapidOCR 模型与 Qt 插件都能原地找到。
- macOS：工作流先用 assets/app.png 生成 app.icns（见工作流），
  有 icns 就用它，没有就用默认图标；BUNDLE 只在 macOS 生成 .app。
- Linux：不设图标（各发行版图标规范不一，托盘内仍用 assets/app.ico
  的运行时绘制兜底，见 ui/icons.py）。
"""
import os
import sys

from PyInstaller.utils.hooks import collect_all

block_cipher = None
root = os.path.abspath(SPECPATH)

datas = [("assets", "assets")]

tmp_ret = collect_all("rapidocr_onnxruntime")
datas += tmp_ret[0]
binaries = tmp_ret[1]
hiddenimports = tmp_ret[2]

tmp_ret = collect_all("onnxruntime")
datas += tmp_ret[0]
binaries += tmp_ret[1]
hiddenimports += tmp_ret[2]

if sys.platform == "win32":
    icon = os.path.join(root, "assets", "app.ico")
    if not os.path.exists(icon):
        icon = None
elif sys.platform == "darwin":
    icns = os.path.join(root, "assets", "app.icns")
    icon = icns if os.path.exists(icns) else None
else:
    icon = None

a = Analysis(
    ["main.py"],
    pathex=[root],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # 只 import QtCore/QtGui/QtWidgets；其余 Qt 模块与 tkinter/unittest
    # 从不被引用，排除后不再被收进包。Qt 的 Quick/Qml/Pdf/Svg 等
    # C++ 库不在 excludes 的管辖内，由 packaging/prune.py 在打包后删。
    excludes=[
        "tkinter",
        "unittest",
        "PySide6.QtQuick",
        "PySide6.QtQml",
        "PySide6.QtPdf",
        "PySide6.QtSvg",
        "PySide6.QtWebEngineWidgets",
        "PySide6.QtWebEngineCore",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="ManggoProClient",
    debug=False,
    bootloader_ignore_signals=False,
    # strip 只在 Linux/macOS 生效：实测 libpython3.12.so 28.5 MB -> 6.5 MB，
    # 其余 wheel 自带的 .so 本来就是 stripped，strip 后基本不变。
    # Windows 上 strip 和 UPX 一律关掉：2026-10-27 实测，Windows 构建对
    # python312.dll 又 strip 又 UPX（压成 UPX0/UPX1 段，6.9 MB -> 1.8 MB）
    # 之后，用户真机启动报 Failed to load Python DLL、LoadLibrary
    # 内存位置访问无效；旧包（不 strip、不 UPX）的 python312.dll 是
    # 正常 .text/.rdata/.data 段。瘦身省的体积没有一个能跑的包重要。
    strip=(sys.platform != "win32"),
    upx=(sys.platform != "win32"),
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=(sys.platform != "win32"),
    upx=(sys.platform != "win32"),
    upx_exclude=[],
    name="ManggoProClient",
)
if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name="ManggoProClient.app",
        icon=icon,
        bundle_identifier="top.izuna.manggoproclient",
        info_plist={
            "CFBundleName": "ManggoProClient",
            "CFBundleDisplayName": "Manggo Pro Client",
            "NSHighResolutionCapable": True,
        },
    )
