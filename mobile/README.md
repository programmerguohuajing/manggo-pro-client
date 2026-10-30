# Manggo Pro · 移动端三端（按《移动端三平台开发计划》）

技术路线遵循开发计划：**Android / iOS 用 Flutter（Dart 共用界面与业务）**，**HarmonyOS NEXT 用 ArkTS/ArkUI 原生客户端**，三端共享接口契约、语言数据模型与设计令牌。

设计令牌与桌面端品牌色一致：**Primary 芒果绿 #2ECC71 / Accent 芒果橙 #EA580C**，含浅色与深色双主题。

## 目录结构

```
mobile/
├─ pubspec.yaml                  # Flutter 依赖（flutter_svg）
├─ lib/                          # Flutter：Android + iOS 共用
│  ├─ main.dart                 # ThemeMode + IndexedStack + AppDock
│  ├─ app_theme.dart            # 设计令牌 + 浅/深 ThemeData（Manggo）
│  ├─ models/language.dart      # 语言数据模型
│  ├─ widgets/                  # flag / app_dock / language_chip / translate_card
│  └─ screens/                  # 六屏：translate / language_select / history / vocab / settings / ocr
├─ test/widget_test.dart        # 冒烟测试
├─ android/                     # Flutter Android 原生工程（已生成）
├─ ios/                         # Flutter iOS 原生工程（已生成，需 macOS 构建）
├─ harmony/                     # HarmonyOS NEXT ArkTS/ArkUI 工程（DevEco 打开）
│  ├─ AppScope/app.json5
│  ├─ build-profile.json5 / hvigorfile.ts / oh-package.json5
│  └─ entry/src/main/
│     ├─ module.json5
│     ├─ ets/entryability/EntryAbility.ets
│     ├─ ets/common/Theme.ets, Language.ets
│     └─ ets/pages/Index.ets + 六屏（Translate/LanguageSelect/History/Vocab/Settings/Ocr）
└─ tool/setup_windows.ps1       # 一键准备（镜像 + precache + pub get + doctor + apk）
```

## 本地环境现状（本机已核实）

| 项 | 状态 |
| --- | --- |
| Flutter SDK 3.47.9 | 已装于 `C:\Users\A\develop`（未在 PATH，需自行加入） |
| Dart SDK 3.13.7 | Flutter 自带，可用 |
| Android SDK | 已装 `%LOCALAPPDATA%\Android\sdk`（platform-tools / build-tools 36 / cmdline-tools） |
| Java | Zulu 11（Gradle 可用） |
| Dart 依赖 | 已 `dart pub get` 完成（38 个包） |
| 代码类型检查 | 已用 `frontend_server` 对 Flutter 3.47.9 全量编译通过，**0 error** |
| Android / iOS 工程 | 已由 `flutter create` 生成 |
| 鸿蒙工程 | ArkTS/ArkUI 骨架已建（需 DevEco Studio + HarmonyOS SDK 才能构建 HAP） |

> 注意：当前自动化会话中 **Dart 创建子进程会被系统拒绝**（`ERROR_PIPE_BUSY 231`），因此 `flutter pub get / build / doctor` 在本会话内无法完整执行；`dart pub get` 与内核编译已验证可用。请在你自己的 PowerShell 终端执行下列命令。

## 三端运行

### Android（Windows 可直接构建）
```powershell
cd mobile
powershell -ExecutionPolicy Bypass -File tool\setup_windows.ps1
# 或手动：
flutter pub get
flutter build apk --debug
```

### iOS（必须 macOS + Xcode）
```bash
cd mobile
flutter pub get
flutter build ios --debug       # 或 flutter run
```

### HarmonyOS NEXT（DevEco Studio）
1. 安装 DevEco Studio 5.x 与 HarmonyOS NEXT SDK（需华为开发者账号）。
2. `File → Open` 选择 `mobile/harmony`，等待 `Sync`。
3. `Project Structure → Signing Configs` 配置自动签名（需登录账号）。
4. 选择模拟器/真机 → `Run 'entry'`，或 `Build → Build Hap(s)`。

## 已实现（三端一致）
- 六屏：翻译主页、语言选择、历史、生词本、设置、OCR 拍照。
- 品牌色 + 浅/深双主题；底部导航选中仅高亮图标（无背景胶囊）。
- 翻译主页：语言条 + 交换 + 双卡片 + 居中绿色 FAB（文A）+ 快捷操作。
- 语言选择：搜索 + 常用/其他分组 + 勾选；鸿蒙端用国家代码徽标（避免 emoji 旗帜兼容问题），Flutter 端用内置 SVG 旗帜。

## 待接入（示例数据占位）
- 真实翻译 API / 可取消的请求状态机、错误映射。
- TTS、OCR 相机插件与权限流程（各端分别适配）。
- 历史/生词本本地持久化（SQLite / Preferences）。
- 安全存储（iOS Keychain、Android Keystore、鸿蒙 SDK 安全存储）。
