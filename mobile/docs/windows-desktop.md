# Windows 桌面端（Flutter desktop）环境说明

## 1. 这条 `flutter doctor` 告警要不要管

```
X Visual Studio is missing necessary components. Please re-run the Visual Studio installer
  for the "Desktop development with C++" workload, and include these components:
  MSVC v142 - VS 2019 C++ x64/x86 build tools
  C++ CMake tools for Windows
  Windows 10 SDK
```

**本项目三端移动工程（iOS / Android / HarmonyOS）完全不需要它。**

`flutter doctor` 在 Windows 主机上会无条件检查这一项，它唯一的用途是 `flutter build windows`，
也就是把 Flutter 应用编成 Windows 桌面程序。本项目：

| 目标 | 工具链 | 是否需要 VS C++ |
| --- | --- | --- |
| Android | Gradle + Android SDK + JDK17 | 不需要 |
| iOS | Xcode（GitHub Actions 的 macOS runner） | 不需要 |
| HarmonyOS NEXT | DevEco Studio + HarmonyOS SDK | 不需要 |
| Windows desktop | MSVC + CMake + Windows SDK | **需要** |

`mobile/` 下没有 `windows/` 目录，也没有任何 Windows 构建入口，因此默认可以忽略。

## 2. 本机实测状态（2026-10-30）

| 项 | 状态 |
| --- | --- |
| Visual Studio Community 2026 18.6 | 已安装于 `D:\Program Files\Microsoft Visual Studio\18\Community` |
| 实例 ID | `60fa063b` |
| `Workload.NativeDesktop` | 未安装 |
| `Component.VC.Tools.x86.x64` | 未安装 |
| `Component.VC.CMake.Project` | 未安装 |
| Windows 11 SDK | 未安装（`C:\Program Files (x86)\Windows Kits` 不存在） |

## 3. 安装方式

### 方式 A：一键脚本（推荐）

右键 `mobile/tool/install_vs_cpp.cmd` → **以管理员身份运行**。

脚本会：检测管理员权限 → 用 `vswhere` 定位 VS 实例 → `setup.exe modify --add Workload.NativeDesktop --includeRecommended`
→ 用 `vswhere` 校验三个组件是否就位。

体积约 **7–8 GB**，耗时 10–30 分钟，需联网。

### 方式 B：手动命令

在**以管理员身份运行**的终端里执行：

```cmd
"C:\Program Files (x86)\Microsoft Visual Studio\Installer\setup.exe" modify ^
  --installPath "D:\Program Files\Microsoft Visual Studio\18\Community" ^
  --add Microsoft.VisualStudio.Workload.NativeDesktop ^
  --includeRecommended --norestart
```

### 方式 C：图形界面

打开 **Visual Studio Installer** → 找到 Community 2026 → **修改** → 勾选
「使用 C++ 的桌面开发」→ 右下角「修改」。

## 4. 关于 doctor 文案里的 "MSVC v142 / VS 2019 / Windows 10 SDK"

这三项是 Flutter 硬编码的旧文案，**不需要照着装**：

- `v142` 是 VS 2019 的工具集，VS 2026 自带的是 v143/v144 系列，装不了也不需要装 v142
- 装 `Workload.NativeDesktop` 时 `--includeRecommended` 会自动带上当前 VS 版本匹配的
  MSVC、CMake，以及 Windows 11 SDK（向下兼容 Windows 10 目标）

装完 `flutter doctor` 这一项就会变绿，无需理会文案里的具体版本号。

## 5. 装完之后：想跑桌面版怎么办

工程目前没有 `windows/` 平台目录，需要生成一次：

```cmd
cd D:\codex\manggo-pro-client\mobile
flutter create --platforms=windows .
flutter run -d windows
```

`flutter create .` 只会补齐缺失的平台目录，不会覆盖 `lib/`、`pubspec.yaml` 和已有的
`android/`、`ios/`、`harmony/`。

## 6. 如果只想本地预览 UI，其实不必装 VS

Windows 版 Flutter 桌面端主要用于**快速预览 UI**（热重载秒级）。但本机已有 Android 模拟器在跑：

```
emulator-5556   device
emulator-5558   device
```

直接 `flutter run -d emulator-5556`（或 `-d emulator-5558`）就能看到界面，而且**渲染效果比 Windows 桌面端更接近真机**
（安全区、状态栏、触摸手势、字体渲染都按移动端走）。装 VS C++ 的唯一收益是获得
Windows 桌面版产品形态，不装完全不影响三端移动开发与出包。

## 7. 不装也不想看到红叉

```cmd
flutter config --no-enable-windows-desktop
```

执行后 `flutter doctor` 不再检查 Visual Studio 这一项。需要时再 `--enable-windows-desktop` 打开。
