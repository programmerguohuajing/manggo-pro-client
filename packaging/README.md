# 打包说明

## 现状：先说清楚边界

本项目起家于 Windows，之前是 Windows 专属。现在的跨平台是分层做的，
不是“全功能平移”：

| 功能 | Windows | macOS | Linux |
| --- | --- | --- | --- |
| 界面（主窗口 / 悬浮窗 / 托盘 / 设置 / 诊断控制台） | ✅ | ✅ | ✅ |
| 翻译通道（免费 / 大模型） | ✅ | ✅ | ✅ |
| 历史记录与生词本 | ✅ | ✅ | ✅ |
| 截图 OCR（RapidOCR） | ✅ | ✅（需屏幕录制权限） | ✅（X11；Wayland 下截图受限） |
| 语音朗读 | ✅ SAPI | ✅ 系统 say | ⚠️ 需装 espeak-ng |
| 全局热键 Alt+Q/W/M/Space | ✅ | ❌ | ❌ |
| 三次空格就地转译 | ✅ | ❌ | ❌ |
| 划选翻译（剪贴板抓取） | ✅ | ❌ | ❌ |
| Win+H 语音听写 | ✅ | ❌ | ❌ |
| 管理员提权 / 单实例互斥体 | ✅ | 单实例改用 PID 检查 | 单实例改用 PID 检查 |

macOS / Linux 上 Win 专属功能入口不会崩溃：托盘三次空格显示“已暂停”，
点划选翻译 / 语音听写会给一句“仅支持 Windows”提示，设置“关于”页也如实标注。

macOS 是两个独立包，不是 universal2 合并包：
- `ManggoProClient-macOS-Intel.zip`：Intel 处理器（x86_64，macos-15-intel 构建）
- `ManggoProClient-macOS-AppleSilicon.zip`：Apple Silicon（arm64，macos-latest 构建）

## 产物形态：便携包 + 系统安装器

每次构建每平台出两份产物，便携包和安装器装的是同一份程序：

| 平台 | 便携包 | 安装器 |
| --- | --- | --- |
| Windows x64 | `ManggoProClient-Windows-x64.zip` | `ManggoProClient-Setup.exe`（Inno Setup） |
| macOS Intel | `ManggoProClient-macOS-Intel.zip` | `ManggoProClient-macOS-Intel.dmg` |
| macOS Apple Silicon | `ManggoProClient-macOS-AppleSilicon.zip` | `ManggoProClient-macOS-AppleSilicon.dmg` |
| Linux x64 | `ManggoProClient-Linux-x64.tar.gz` | `manggo-pro-client_<版本>_amd64.deb` |

安装方式与卸载：

- Windows：双击 Setup，下一步装到 Program Files，开始菜单 + 桌面
  快捷方式，控制面板 -> 程序和功能可卸载。需要管理员权限。
- macOS：打开 DMG，把 `ManggoProClient.app` 拖到 Applications 即装好，
  删掉 .app 即卸载。未签名（仓库里没有 Apple Developer 证书），
  首次打开请右键 .app -> 打开，点“打开”放行一次；之后正常双击即可。
- Linux：`sudo dpkg -i manggo-pro-client_<版本>_amd64.deb`（依赖
  libgl1、libegl1、libxkbcommon0、libdbus-1-3、libfontconfig1），
  装到 `/usr/share/manggo-pro-client`，应用程序菜单有图标，
  `sudo apt remove manggo-pro-client` 可卸载。

版本号唯一来源是 `packaging/VERSION`（当前 1.0.0），安装器文件名和
元数据都读它；发版时改这一个文件就行。

## 数据文件放在哪（系统安装后）

历史记录、配置、日志、单实例 pid 默认写程序目录旁（便携包行为不变）。
装到系统目录（Program Files、/Applications、/usr/share）后普通用户
写不进安装目录时，`core/paths.py` 会自动把它们落到用户目录：
Windows 是 `%APPDATA%\ManggoProClient`，mac/Linux 是
`~/.config/manggo-pro-client`；如果程序旁已有同名文件而用户目录
还没有，首次会顺手拷一份过去，便携包换系统安装时历史和配置不丢。

## 本地构建

```bash
pip install -r requirements-build.txt
pyinstaller manggo-pro-client.spec
# Windows: dist/ManggoProClient/ManggoProClient.exe
# macOS:   dist/ManggoProClient.app
# Linux:   dist/ManggoProClient/ManggoProClient
```

## CI 构建

推到 `build/packages` 分支即触发 `.github/workflows/build-packages.yml`，
四路并行：Windows x64、macOS Intel、macOS Apple Silicon、Linux x64，
产物在 Actions 页的 Artifacts 里保留 30 天。也可手动 Run workflow。

## 体积：为什么 100+ MB，以及瘦了多少

先说结论：100+ MB 不是代码多，是依赖重。Linux 包实测（解压后 547 MB，
tar.gz 214 MB）的构成：

| 块 | 解压后 | 说明 |
| --- | --- | --- |
| opencv（cv2 + opencv_python.libs） | 约 192 MB | RapidOCR 的依赖，含 ffmpeg 编解码和 Qt5 库 |
| PySide6（Qt 库 + 插件 + 翻译） | 约 121 MB | 界面框架本身 |
| onnxruntime | 约 63 MB | RapidOCR 推理引擎 |
| numpy | 约 41 MB | cv2 / onnxruntime 都要它 |
| libpython + 标准库 | 约 44 MB | Python 解释器本体 |
| RapidOCR 模型 + 代码 | 约 16 MB | 中文检测 + 识别两个 .onnx 模型 |
| Pillow / shapely / pyclipper / yaml 等 | 约 30 MB | 其余依赖 |

已做的瘦身（工作流里 Build 之后自动跑 `packaging/prune.py`）：

- `strip=True`：实测 `libpython3.12.so` 从 28.5 MB 压到 6.5 MB；
  wheel 自带的 .so 本来就是 stripped，strip 后基本不变。
- 删 Qt 死重：Quick / Qml / Pdf / Svg / VirtualKeyboard 库和对应插件、
  全部 99 个 Qt 翻译文件（应用从未装 QTranslator，一个都不会被加载）、
  qpdf/qsvg/qtga/qtiff/qwbmp/qwebp/qicns 图片插件、eglfs/linuxfb/vnc
  等嵌入式平台后端。应用只 import QtCore/QtGui/QtWidgets，
  ldd 确认 QtGui/QtWidgets 不链接这些库，删了不影响启动。
- 依赖改 `PySide6-Essentials`：元包还会拉 WebEngine/Pdf/Addons，
  Essentials 只含界面要用的模块。
- Windows 不用 UPX、不 strip：2026-10-27 实测，UPX 后的 python312.dll
  （UPX0/UPX1 段，6.9 MB → 1.8 MB）在用户真机上启动报
  Failed to load Python DLL、LoadLibrary 内存位置访问无效，
  所以 spec 里 Windows 的 strip/UPX 一律关掉，宁可包大一点；
  Linux/macOS 上 strip 照常（PyInstaller 本来就在非 Windows 上禁用 UPX）。
- 压缩级别拉满：mac 用 `zip -9`，Linux 用 `gzip -9`。

刻意没动、也别再动的部分：opencv 的 ffmpeg/Qt5 库。ldd 证明
cv2.abi3.so 启动时就直接链接它们，删了截图 OCR 会起不来；
RapidOCR 声明的依赖就是完整版 opencv-python，换 headless 要
--no-deps 手动钉依赖，省得不多、断得容易。

所以这轮瘦身的目标是“去掉纯死重”，不是“压到几十 MB”：
Qt + Python + numpy + onnxruntime + cv2 的底子就在那儿，
不砍功能的话 100 MB 量级是下限。真想进 50 MB 以内，
只能动结构：把截图 OCR 一整条线（cv2 + onnxruntime + RapidOCR + numpy，
解压后约 310 MB）拆成首次使用时按需下载的插件，主包只剩界面 + 翻译——
那是另一个决定，用户拍板了再做。

## 绝不打包的东西

`history.sqlite3`（用户翻译历史）、`config.json`（可能含 API Key）、
`debug_app.log`、`.app.pid` 都不在 PyInstaller 的 datas 里。
首次启动会在程序目录旁新建空历史库。
