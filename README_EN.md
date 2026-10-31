<div align="center">

<img src="assets/app.png" width="96" alt="Manggo Pro Client">

# Manggo Pro Client

**A full-featured desktop translation & dictation workbench**

[中文](README.md) | English | [Live intro page](https://programmerguohuajing.github.io/manggo-pro-client/)

[![Tests](https://github.com/programmerguohuajing/manggo-pro-client/actions/workflows/test.yml/badge.svg)](https://github.com/programmerguohuajing/manggo-pro-client/actions/workflows/test.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
![Platforms](https://img.shields.io/badge/desktop-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)
![Python](https://img.shields.io/badge/python-3.12-3776ab)

</div>

Lightweight, fast and non-intrusive: selection translation, screenshot OCR, voice dictation and in-place input-box translation, all from one tray icon. Android / iOS / HarmonyOS mobile clients are also in development (see [Mobile](#-mobile)).

---

## 🌟 Features

| Module | Trigger | Description |
| :--- | :--- | :--- |
| **In-place translation in input boxes** | Press **Space 3 times** | Type Chinese in WeChat / Word / any chat box, press Space 3 times, and the text is replaced in place with English (the spaces are removed). |
| **Selection popup translation** | **Alt + Q** | Highlight any text, press the hotkey, and a popup card appears with read-aloud, copy and vocabulary-book save. |
| **Screenshot OCR translation** | **Alt + W** | Draw a box on screen; RapidOCR recognizes the text locally and offline, then translates it side by side. |
| **Desktop translation workbench** | **Alt + M** / tray menu | Two-column Chinese–English workbench for long text, with multi-paragraph translation, read-aloud and copy. |
| **Voice dictation** | **Alt + Space** | Starts system dictation (Win + H on Windows); what you say is typed in place. |
| **History & vocabulary book** | Tray menu / workbench | Local SQLite archive, searchable and starrable. |
| **Offline text-to-speech** | 🔊 button | SAPI on Windows, `say` on macOS, `espeak-ng` / `espeak` on Linux; all offline. |
| **Multiple translation channels** | Settings page | A built-in key-free channel; one-click presets for DeepSeek, Qwen, OpenAI and local Ollama. |
| **Preferences center** | Double-click the tray icon | Card + sidebar layout with custom hotkeys, triple-space sensitivity, translation style templates and a one-click connection test. |

---

## 🖥️ Platform support

| Feature | Windows | macOS | Linux (X11) |
| :--- | :---: | :---: | :---: |
| In-place translation (Space ×3) | ✅ | ✅ | ✅ |
| Selection translation (`Alt + Q`, `Option + Q` on macOS) | ✅ | ✅ | ✅ |
| Screenshot OCR (`Alt + W`) | ✅ | ✅ | ✅ |
| Workbench hotkey (`Alt + M`) | ✅ | Open from tray menu | Open from tray menu |
| Voice dictation hotkey (`Alt + Space`) | ✅ | — | — |
| Workbench / history / vocabulary book / settings | ✅ | ✅ | ✅ |
| Start at login | ✅ (installed build only) | ✅ | ✅ |

Prerequisites per platform:

- **Windows**: the installer and the portable build ask for administrator rights so the app can inject keystrokes into elevated applications.
- **macOS**: grant **Accessibility** and **Input Monitoring** (global hotkeys) and **Screen Recording** (screenshot OCR) in System Settings → Privacy & Security. When a permission is missing the app says so instead of failing silently.
- **Linux**: global hotkeys work on **X11 sessions only**; on Wayland the app reports it and disables them. The clipboard needs `xclip` or `xsel`, and speech needs `espeak-ng`.

---

## ⌨️ Hotkeys

Defaults below; all of them can be changed in Settings (each needs at least one modifier key, and the 4 actions must not collide):

- **`Space ×3`**: in-place translation in input boxes (Chinese → English)
- **`Alt + Q`**: translate highlighted text
- **`Alt + W`**: screenshot OCR translation
- **`Alt + M`**: open the desktop workbench (Windows)
- **`Alt + Space`**: voice dictation (Windows)
- **`Double-click the tray icon`**: open preferences
- **`Ctrl + Enter`**: submit a translation in the workbench

---

## 🚀 Download & install

Get the build for your platform from the [Releases](https://github.com/programmerguohuajing/manggo-pro-client/releases) page:

| Platform | File | Notes |
| :--- | :--- | :--- |
| Windows | `ManggoProClient-Setup.exe` | Installer with a setup wizard; supports start at login and in-place updates. |
| Windows | `ManggoProClient-Windows-x64.zip` | Portable build; unzip and double-click `ManggoProClient.exe`. |
| macOS (Intel) | `ManggoProClient-macOS-Intel.dmg` | Drag to Applications. |
| macOS (Apple silicon) | `ManggoProClient-macOS-AppleSilicon.dmg` | Drag to Applications. |
| Linux | `manggo-pro-client_<version>_amd64.deb` | Install with `sudo dpkg -i`; adds a menu entry. |
| Linux | `ManggoProClient-Linux-x64.tar.gz` | Unpack and run `ManggoProClient`. |

> The macOS build is not notarized by Apple. On first launch, **right-click → Open** to allow it once.

Every Release ships a `SHA256SUMS` file. The in-app "Check for updates" verifies the downloaded file against it by filename and refuses the install on a mismatch or a missing entry. You can also verify manually:

```bash
sha256sum -c SHA256SUMS --ignore-missing
```

### Run from source (Python 3.12 required)

```bash
pip install -r requirements.txt
python main.py        # with console logs, for debugging
pythonw main.py       # Windows: silent background run, no console window
```

- On Windows, running from source prompts and relaunches itself with administrator rights; the app enforces a single instance, so quit from the tray menu → Quit.
- For local packaging see [`packaging/README.md`](packaging/README.md) (`pyinstaller manggo-pro-client.spec`).

---

## 🔒 Translation channels & privacy

- **The built-in free channel sends your text to third parties**: it calls Youdao's public endpoint, Google's web translation relay and MyMemory's public API in turn, so selected text and OCR text go to these providers. OCR itself runs locally and offline, but the recognized text is then sent by the translation channel.
- **The LLM channel only talks to the API address you enter.** When the LLM call fails, the app does **not** fall back to the free channel by default (that would send your text to public endpoints); you can turn the fallback on in Settings. The local Ollama preset needs no API key.
- **API key storage**: on Windows the key is stored encrypted with DPAPI (bound to the current user and machine); on macOS / Linux it is currently stored in plain text in `config.json`, so mind the file permissions.
- **Logs**: the diagnostics console and `debug_app.log` exist for troubleshooting; before sharing them in a bug report, check them for anything you don't want to publish.

---

## 📱 Mobile

The mobile clients live in [`mobile/`](mobile/README.md): **Flutter for Android / iOS** and a native **ArkTS / ArkUI** client for **HarmonyOS NEXT**, sharing one API contract and one set of design tokens. They are under active development:

| Platform | Status |
| :--- | :--- |
| Android | All six screens done; the **triple-space translation keyboard** (`InputMethodService`) is implemented; CI publishes a rolling APK ([`android-latest`](https://github.com/programmerguohuajing/manggo-pro-client/releases/tag/android-latest)). |
| iOS | All six screens done; CI produces an unsigned IPA (`ios-latest`, re-sign it yourself or install with Sideloadly); the keyboard extension is not implemented yet. |
| HarmonyOS NEXT | ArkTS / ArkUI project skeleton in place, built with DevEco Studio; the input-method extension is not implemented yet. |

More in [`mobile/docs/`](mobile/docs/): [tri-platform keyboard design](mobile/docs/ime-tri-platform.md), [iOS builds in CI](mobile/docs/ios-ci.md), [CI feasibility matrix](mobile/docs/ci-matrix.md), [online updates & mirrors](mobile/docs/online-update.md). These documents are written in Chinese.

---

## 🗂️ Data & log locations

- When the program directory is writable (portable build), history `history.sqlite3`, config `config.json` and log `debug_app.log` live next to the program.
- When installed somewhere read-only (Program Files, `/Applications`, `/usr/share`), they move to the user directory automatically: `%APPDATA%\ManggoProClient` on Windows, `~/.config/manggo-pro-client` on macOS / Linux.
- Tray menu → **Diagnostics console** lets you filter by level, copy and clear logs (it never pops up on its own).

---

## 🧪 Development & tests

```bash
python3 -m unittest discover -s tests -v
```

The tests use the standard library only (no Qt needed), and CI ([`test.yml`](.github/workflows/test.yml)) runs them on every push and pull request. Layout:

```
main.py            entry point and coordinator
core/              translation, key hooks (Windows / macOS / Linux), replacers, OCR, TTS, updater
ui/                PySide6 UI: workbench, popup, screenshot, settings, tray, diagnostics console
tests/             unit tests
packaging/         PyInstaller, Inno Setup and deb packaging scripts
mobile/            Flutter (Android / iOS) and HarmonyOS clients
docs/              GitHub Pages intro site (Chinese / English)
```

---

## 📄 License

The project code is released under the [MIT License](LICENSE). Packaged builds include PySide6 (Qt for Python), distributed under LGPL-3.0; see [`assets/PySide6-LGPL-3.0.txt`](assets/PySide6-LGPL-3.0.txt).
