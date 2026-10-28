[中文](README.md) | English | [Live intro page](https://programmerguohuajing.github.io/manggo-pro-client/)

# Manggo Pro Client (Full-featured desktop translation & dictation workbench)

A lightweight, high-performance, non-intrusive desktop translation and voice workbench.

---

## 🌟 Feature overview

| Module | Hotkey / trigger | Description |
| :--- | :--- | :--- |
| **In-place translation in input boxes (Pro core feature)** | Press **Space 3 times** | Type Chinese in WeChat / Word / chat boxes, press Space 3 times, and the text is replaced in place with English (spaces removed automatically). |
| **Selection popup translation** | **Alt + Q** | Highlight any text on screen, press the hotkey, and an immersive popup translation card appears with read-aloud, copy, and vocabulary-book save. |
| **Fullscreen screenshot OCR translation** | **Alt + W** | Draw a crosshair box over the full screen; RapidOCR recognizes text locally and offline, then translates it side by side. |
| **Desktop translation workbench** | **Alt + M** / tray menu | Immersive two-column workbench for long Chinese-English texts, with multi-paragraph translation, one-click read-aloud and copy. |
| **Voice dictation input** | **Alt + Space** | Brings up a microphone pickup indicator; speech is transcribed and typed in place in real time. |
| **History & vocabulary book** | Tray 📖 button / workbench | Local SQLite archive, automatic. |
| **Offline speech synthesis (TTS)** | 🔊 button (popup / workbench) | Uses the Windows native SAPI engine: instant offline pronunciation, no network usage. |
| **Multiple translation channels (incl. Pro-grade LLMs)** | Double-click tray / tray right-click ⚙️ | Built-in key-free fast channel; one-click presets for DeepSeek-V3/R1, Qwen, OpenAI, local Ollama. |
| **Modern preferences center** | **Double-click the tray icon (bottom-right)** | Modern card + sidebar navigation layout, with triple-space sensitivity slider, style templates, and one-click testing. |

---

## ⌨️ Hotkey cheat sheet (independent, no conflicts)

- **`Space x3`**: in-place translation in input boxes (Chinese -> English)
- **`Alt + Q`**: translate highlighted text (popup after selection)
- **`Alt + W`**: fullscreen screenshot OCR + translation
- **`Alt + M`**: open the desktop translation workbench
- **`Alt + Space`**: voice dictation input
- **`Double-click the mango tray icon (bottom-right)`**: open the preferences center
- **`Ctrl + Enter`**: submit a translation in the workbench

---

## 🚀 Getting started

### Option 1: Portable package (recommended, no Python needed)

See [`packaging/README.md`](packaging/README.md) for local builds (`pyinstaller manggo-pro-client.spec`), or download the platform build from the repo's Actions page, then unzip and run:

- **Windows**: double-click `ManggoProClient.exe` (windowed app, no console window)
- **macOS**: open `ManggoProClient.app`; unsigned, so on first launch right-click → Open to allow it once
- **Linux**: run the `ManggoProClient` binary directly

### Option 2: Run from source (Python 3.12 required)

```bash
pip install -r requirements.txt
```

- **Daily use (silent background run, no console)**: `pythonw main.py`
- **Debugging (with console log output)**: `python main.py`
- The app auto-elevates (admin rights) and enforces a single instance; quit from tray right-click → Quit

### Logs & diagnostics

- Tray menu → Diagnostics console: filter by level, copy, clear logs (never pops up on its own)
- `debug_app.log` next to the program: same content, open it directly (after a system install to
  Program Files / /Applications / /usr/share, logs, config and history
  live in the user directory: Windows `%APPDATA%\ManggoProClient`,
  macOS/Linux `~/.config/manggo-pro-client`)
