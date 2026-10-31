<div align="center">

<img src="assets/app.png" width="96" alt="Manggo Pro Client">

# Manggo Pro Client

**桌面全功能翻译与听写工作台**

中文 | [English](README_EN.md) | [在线介绍页](https://programmerguohuajing.github.io/manggo-pro-client/)

[![Tests](https://github.com/programmerguohuajing/manggo-pro-client/actions/workflows/test.yml/badge.svg)](https://github.com/programmerguohuajing/manggo-pro-client/actions/workflows/test.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
![Platforms](https://img.shields.io/badge/desktop-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)
![Python](https://img.shields.io/badge/python-3.12-3776ab)

</div>

轻量、高性能、免侵入：划选翻译、截图 OCR、语音听写、输入框就地转译，常驻系统托盘，一个程序全部搞定。同时提供 Android / iOS / HarmonyOS 移动端（开发中，见[移动端](#-移动端)）。

---

## 🌟 核心功能

| 功能模块 | 触发方式 | 说明 |
| :--- | :--- | :--- |
| **输入框就地转译** | 连按 **3 次空格** | 在微信 / Word / 聊天框打完中文，连按 3 次空格，自动消除空格并就地替换为英文。 |
| **划选文本悬浮翻译** | **Alt + Q** | 划选任意文本后按下，弹出悬浮翻译卡片，支持朗读、复制、生词本收藏。 |
| **全屏截图 OCR 翻译** | **Alt + W** | 十字光标框选屏幕区域，RapidOCR 本地离线识别文字并自动对照翻译。 |
| **桌面翻译工作台** | **Alt + M** / 托盘菜单 | 双栏长文本中英互译，支持多段翻译、一键朗读与复制。 |
| **语音听写输入** | **Alt + Space** | 唤起系统听写（Windows 上调用 Win + H），说话即上屏。 |
| **历史记录 & 生词本** | 托盘菜单 / 工作台 | 本地 SQLite 自动存档，可搜索、可星标。 |
| **离线语音朗读** | 🔊 按钮 | Windows 用 SAPI，macOS 用 `say`，Linux 用 `espeak-ng` / `espeak`，全部离线。 |
| **多翻译通道** | 设置页 | 内置免 Key 通道；一键预设 DeepSeek、通义千问、OpenAI、本地 Ollama。 |
| **偏好设置中心** | 双击托盘图标 | 卡片式 + 侧边导航，可自定义热键、连击灵敏度、翻译风格模板，并一键测试连接。 |

---

## 🖥️ 平台支持

| 功能 | Windows | macOS | Linux（X11） |
| :--- | :---: | :---: | :---: |
| 输入框就地转译（连按 3 次空格） | ✅ | ✅ | ✅ |
| 划选翻译（`Alt + Q`，macOS 为 `Option + Q`） | ✅ | ✅ | ✅ |
| 截图 OCR（`Alt + W`） | ✅ | ✅ | ✅ |
| 工作台热键（`Alt + M`） | ✅ | 从托盘菜单打开 | 从托盘菜单打开 |
| 语音听写热键（`Alt + Space`） | ✅ | — | — |
| 翻译工作台 / 历史 / 生词本 / 设置 | ✅ | ✅ | ✅ |
| 开机自启 | ✅（仅安装版） | ✅ | ✅ |

各平台的前置条件：

- **Windows**：安装包与便携包会请求管理员权限，用来向管理员权限的应用注入按键。
- **macOS**：需要在「系统设置 → 隐私与安全性」中授予 **辅助功能**、**输入监控**（全局热键），以及 **屏幕录制**（截图 OCR）。缺权限时程序会明确提示，而不是静默失效。
- **Linux**：全局热键只支持 **X11 会话**，Wayland 会话下会提示并停用；剪贴板需要 `xclip` 或 `xsel`，朗读需要 `espeak-ng`。

---

## ⌨️ 快捷键

默认快捷键如下，均可在设置页自定义（至少带一个修饰键，4 个动作不能重复）：

- **`连续 3 次空格`**：输入框就地转译（中文 → 英文）
- **`Alt + Q`**：划选文本翻译
- **`Alt + W`**：截图 OCR 翻译
- **`Alt + M`**：呼出桌面翻译工作台（Windows）
- **`Alt + Space`**：语音听写输入（Windows）
- **`双击托盘图标`**：打开偏好设置
- **`Ctrl + Enter`**：在工作台中提交翻译

---

## 🚀 下载与安装

到 [Releases](https://github.com/programmerguohuajing/manggo-pro-client/releases) 页下载对应平台的包：

| 平台 | 文件 | 说明 |
| :--- | :--- | :--- |
| Windows | `ManggoProClient-Setup.exe` | 安装版，带安装向导，支持开机自启与覆盖更新。 |
| Windows | `ManggoProClient-Windows-x64.zip` | 便携版，解压后双击 `ManggoProClient.exe`。 |
| macOS（Intel） | `ManggoProClient-macOS-Intel.dmg` | 拖到「应用程序」。 |
| macOS（Apple 芯片） | `ManggoProClient-macOS-AppleSilicon.dmg` | 拖到「应用程序」。 |
| Linux | `manggo-pro-client_<版本>_amd64.deb` | `sudo dpkg -i` 安装，菜单里出现图标。 |
| Linux | `ManggoProClient-Linux-x64.tar.gz` | 解压后直接运行 `ManggoProClient`。 |

> macOS 版没有经过 Apple 公证，首次打开请 **右键 → 打开** 放行一次。

每个 Release 都附带 `SHA256SUMS`；程序内「检查更新」下载后会按文件名比对 SHA256，不一致或缺失都会拒绝安装。你也可以手动校验：

```bash
sha256sum -c SHA256SUMS --ignore-missing
```

### 从源码运行（需要 Python 3.12）

```bash
pip install -r requirements.txt
python main.py        # 带控制台日志，便于排查
pythonw main.py       # Windows：后台静默运行，无黑框
```

- Windows 下源码运行会提示并以管理员身份重启自己；程序保证单实例，退出请用托盘右键 → 退出。
- 本地打包见 [`packaging/README.md`](packaging/README.md)（`pyinstaller manggo-pro-client.spec`）。

---

## 🔒 翻译通道与隐私

- **内置免费通道会把文本发给第三方**：依次调用有道公共接口、Google 网页翻译中继和 MyMemory 公开接口，选中文本与 OCR 文本会发给这三家。OCR 识别本身是本地离线的，但识别出的文字随后会被翻译通道发送。
- **大模型通道只发给你填写的 API 地址**。大模型失败时 **默认不会** 回退到免费通道（回退会把文本发给公共接口），需要时可在设置页手动开启。本地 Ollama 预设不需要填 Key。
- **API Key 的保存**：Windows 上以 DPAPI 加密保存（绑定当前用户与本机）；macOS / Linux 目前以明文保存在 `config.json` 中，请注意文件权限。
- **日志**：诊断控制台与 `debug_app.log` 用于排查问题，反馈问题前请先检查其中是否含有你不想公开的内容。

---

## 📱 移动端

移动端位于 [`mobile/`](mobile/README.md)，技术路线为 **Android / iOS 用 Flutter**，**HarmonyOS NEXT 用 ArkTS / ArkUI** 原生客户端，三端共用接口契约与设计令牌。目前处于开发阶段：

| 平台 | 状态 |
| :--- | :--- |
| Android | 六屏界面已完成；**三连空格翻译输入法**（`InputMethodService`）已实现；CI 滚动发布 APK（[`android-latest`](https://github.com/programmerguohuajing/manggo-pro-client/releases/tag/android-latest)）。 |
| iOS | 六屏界面已完成；CI 产出未签名 IPA（`ios-latest`，需自行重签或用 Sideloadly 安装）；键盘扩展待实现。 |
| HarmonyOS NEXT | ArkTS / ArkUI 工程骨架已建，需 DevEco Studio 构建；输入法扩展待实现。 |

更多说明见 [`mobile/docs/`](mobile/docs/)：[三端输入法方案](mobile/docs/ime-tri-platform.md)、[iOS 出包](mobile/docs/ios-ci.md)、[CI 可行性矩阵](mobile/docs/ci-matrix.md)、[在线更新与国内加速](mobile/docs/online-update.md)。

---

## 🗂️ 数据与日志位置

- 程序目录可写（便携包）时，历史记录 `history.sqlite3`、配置 `config.json`、日志 `debug_app.log` 都放在程序目录旁。
- 装到不可写位置（Program Files、`/Applications`、`/usr/share`）时，自动改放用户目录：Windows 是 `%APPDATA%\ManggoProClient`，macOS / Linux 是 `~/.config/manggo-pro-client`。
- 托盘菜单 → **诊断控制台** 可按级别过滤、复制、清空日志（不会自动弹出）。

---

## 🧪 开发与测试

```bash
python3 -m unittest discover -s tests -v
```

单测只依赖标准库，不需要装 Qt；CI（[`test.yml`](.github/workflows/test.yml)）在每次推送和 PR 上都会运行。目录概览：

```
main.py            程序入口与协调器
core/              翻译、热键钩子（Windows / macOS / Linux）、替换器、OCR、TTS、更新器
ui/                PySide6 界面：工作台、悬浮窗、截图、设置、托盘、诊断控制台
tests/             单元测试
packaging/         PyInstaller、Inno Setup、deb 打包脚本
mobile/            Flutter（Android / iOS）与 HarmonyOS 客户端
docs/              GitHub Pages 介绍站点（中 / 英）
```

---

## 📄 许可证

项目代码采用 [MIT 许可证](LICENSE)。打包产物包含 PySide6（Qt for Python），按 LGPL-3.0 分发，许可证文本见 [`assets/PySide6-LGPL-3.0.txt`](assets/PySide6-LGPL-3.0.txt)。
