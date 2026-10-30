# 三端安装包在 CI 上的可行性

| 平台 | 产物 | GitHub 托管 runner | 状态 |
| --- | --- | --- | --- |
| Android | APK / AAB | ✅ `ubuntu-latest` 直接可跑 | 已配置（`android.yml`） |
| iOS | IPA | ✅ `macos-15` 直接可跑 | 已跑通（`ios.yml`） |
| HarmonyOS NEXT | HAP | ❌ 托管 runner 跑不了 | 需 self-hosted runner |

前两个已经实跑验证过，第三个卡在华为的工具链授权上，不是配置问题。

---

## Android

`.github/workflows/android.yml`

- runner：`ubuntu-latest`，预装 Android SDK（`ANDROID_SDK_ROOT=/usr/local/lib/android/sdk`）
- JDK：`actions/setup-java@v4` + temurin 17（Flutter 3.47 要求 17）
- 产物：`build/app/outputs/flutter-apk/*.apk`，手动触发可选 `appbundle` / `both`
- 签名：
  - 没配密钥 → 用 debug key 签名，**可以直接装机**，但不能上架 Google Play
  - 配了密钥 → 走正式签名，可上架

### 配正式签名（可选）

1. 生成 keystore：

```bash
keytool -genkey -v -keystore upload-keystore.jks \
  -keyalg RSA -keysize 2048 -validity 10000 -alias upload
```

2. 转 base64 填入 Secrets：

| Secret | 内容 |
| --- | --- |
| `ANDROID_KEYSTORE_BASE64` | `upload-keystore.jks` 的 base64 |
| `ANDROID_STORE_PASSWORD` | keystore 密码 |
| `ANDROID_KEY_PASSWORD` | key 密码 |
| `ANDROID_KEY_ALIAS` | 别名（如 `upload`） |

转换命令：

```powershell
[Convert]::ToBase64String([IO.File]::ReadAllBytes("upload-keystore.jks")) | Set-Clipboard
```

> `android/key.properties` 和 `*.jks` 已在 `mobile/android/.gitignore` 中忽略，不会误提交。

---

## iOS

`.github/workflows/ios.yml`

- runner：`macos-15`（Apple Silicon，Xcode 16.4）
- 未签名 IPA：零配置，push 自动出
- 已签名 IPA：需 `IOS_CERT_P12` / `IOS_CERT_PASSWORD` / `IOS_PROVISION_PROFILE` / `IOS_TEAM_ID`
- 可选直传 TestFlight：`ASC_KEY_ID` / `ASC_ISSUER_ID` / `ASC_PRIVATE_KEY`

详细步骤见 [`ios-ci.md`](./ios-ci.md)。

---

## HarmonyOS NEXT：为什么托管 runner 不行

三个硬约束，逐条都是死路：

1. **SDK 需要华为开发者账号授权下载**
   DevEco Studio 与 HarmonyOS SDK 的下载、`hvigor` 依赖、`ohpm` 源全部要求登录华为开发者账号并接受许可协议。GitHub 托管 runner 无法在无人值守的情况下完成这一步，也没有公开的免登录下载地址。

2. **官方没有 Linux 版工具链**
   DevEco Studio 只提供 Windows 和 macOS 版。GitHub 托管 runner 里只有 `ubuntu-latest`（免费不限量）和 `windows-latest` / `macos-15`（也要装 DevEco，但同样卡在第 1 条）。用 Linux runner 装不了。

3. **签名材料必须在 DevEco 里生成**
   HAP 签名需要 `.p12`（密钥库）+ `.cer`（证书）+ `.p7b`（Profile），由 DevEco 的 `Project Structure → Signing Configs` 用华为账号自动申请。虽然拿到之后可以 base64 存进 Secrets，但首次获取绕不开人工登录。

### 可行方案：self-hosted runner

用你自己一台已装好 DevEco + HarmonyOS SDK 的 Windows 机器，注册成 GitHub self-hosted runner，由它来出 HAP。

**注册 runner**（在 GitHub 仓库 → Settings → Actions → Runners → New self-hosted runner，按提示执行），然后在机器上保证：

- DevEco Studio 5.x 已安装
- `hvigorw` / `ohpm` 在 PATH 中
- 该机器已完成过一次手动签名（`mobile/harmony/build-profile.json5` 里有 `signingConfigs`）

**workflow 模板**（放到 `.github/workflows/harmony.yml`，把 `runs-on` 改成你 runner 的标签）：

```yaml
name: HarmonyOS Build

on:
  workflow_dispatch:

jobs:
  build-hap:
    # 改成你 self-hosted runner 的标签，例如 [self-hosted, windows, harmony]
    runs-on: [self-hosted, windows]
    timeout-minutes: 40
    steps:
      - uses: actions/checkout@v4

      - name: Show toolchain
        shell: pwsh
        run: |
          hvigorw --version
          ohpm --version

      - name: Install dependencies
        working-directory: mobile/harmony
        shell: pwsh
        run: ohpm install --all

      - name: Build HAP
        working-directory: mobile/harmony
        shell: pwsh
        run: |
          hvigorw clean --no-daemon
          hvigorw assembleHap --mode module -p product=default -p buildMode=release --no-daemon

      - uses: actions/upload-artifact@v4
        with:
          name: harmony-hap
          path: mobile/harmony/entry/build/default/outputs/**/*.hap
          retention-days: 14
```

### 什么情况下可以不用 CI

鸿蒙这一端目前的定位是**本地出包**：DevEco 里 `Build → Build Hap(s)` 一键完成，签名由 IDE 自动管理，比在 CI 里折腾省事得多。三端里只有它需要这一步手动操作，另外两端已经全自动。

---

## 一句话总结

- **Android / iOS**：push 即出包，全自动，免费（仓库是 public）。
- **HarmonyOS**：托管 runner 做不了，要么 self-hosted runner，要么在 DevEco 里手动 Build HAP。
