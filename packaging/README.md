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

## 产物形态（v1）

这是便携包，不是系统安装器：解压即用，不写注册表 / 不进 Applications
自动安装。Windows 是 `ManggoProClient.exe` 所在文件夹的 zip，
macOS 是 `ManggoProClient.app` 的 zip，Linux 是文件夹的 tar.gz。
如需真正的安装器（Windows Inno Setup、macOS DMG、Linux deb），下一步再加。

macOS 产物未签名（仓库里没有 Apple Developer 证书）：首次打开请右键
`.app` -> 打开，点“打开”放行一次；之后正常双击即可。

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

## 绝不打包的东西

`history.sqlite3`（用户翻译历史）、`config.json`（可能含 API Key）、
`debug_app.log`、`.app.pid` 都不在 PyInstaller 的 datas 里。
首次启动会在程序目录旁新建空历史库；Windows 上仍会按原逻辑从原版
Manggo 同步一次历史。
