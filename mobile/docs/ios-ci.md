# iOS 在 GitHub Actions 出包

结论：**可以。** GitHub 托管 runner 里有真实的 macOS 机器（`macos-15`，Apple Silicon），Xcode、CocoaPods、Command Line Tools 全部预装，`xcodebuild archive` / `-exportArchive` 能完整跑通，出包结果和在你本机 Mac 上打的一模一样。

Windows 不能出 iOS 包，但**不是不能出包**——只是把编译这一步交给 GitHub 的 macOS runner。

---

## 两种产出，按需选

| 方式 | 需要 Apple 开发者账号 | 能否直接装机 | 用途 |
| --- | --- | --- | --- |
| 未签名 IPA | ❌ 不需要 | ❌ 需重签 | 内部验证、给测试同学用 Sideloadly / AltStore 自签后安装 |
| 已签名 IPA | ✅ 需要（付费 $99/年） | ✅ 可以 | ad-hoc 内测分发、App Store 上架、TestFlight |

未签名包零配置，push 代码就会自动产出。签名包配好 4 个 Secrets 即可。

---

## 一、零配置路径（未签名）

推送到 `main` / `master` 且改动 `mobile/**` 时自动触发，或在 Actions 页面手动 `Run workflow` 选 `unsigned`。

产物有两个出口，拿哪个都行：

1. **Actions 运行详情页底部 Artifacts** → `ios-unsigned-ipa`
2. **Release 固定直链**（推荐，免登录、可镜像加速）：
   ```
   https://github.com/programmerguohuajing/manggo-pro-client/releases/download/ios-latest/ManggoPro-<版本>-<构建号>-ios-unsigned.ipa
   ```
   同目录下还有 `version.json`，字段：`versionName / versionCode / bundleId / ipaName / ipaUrl / size / sha256 / signed / publishedAt / notes`，结构和 Android 的 `android-latest` 一致，后面接 App 内更新可以直接复用。

Release tag 固定 `ios-latest`，每次先删再建，覆盖式发布，不会堆几百个 tag。

这个 IPA 是标准 zip 结构（`Payload/Runner.app`），可以：
- 用 Sideloadly / AltStore / TrollStore 在自己设备上重签安装
- 用它验证编译链路是否健康

**注意**：iOS 15+ 未签名 IPA 无法直接双击安装，必须有签名环节。

---

## 一之二、Windows 上把未签名 IPA 装进 iPhone（Sideloadly）

整个流程不需要 Mac，也不需要开发者账号（用你自己的 Apple ID 免费签名）：

1. 装 [Sideloadly](https://sideloadly.io/) 和 iTunes（或仅装 Apple 移动设备驱动），数据线连 iPhone，设备上点「信任」
2. Sideloadly 里选设备 → `IPA` 选刚下载的文件 → `Apple ID` 填自己的（免费即可）→ Start
3. 首次会要 Apple ID 密码和一次双重认证验证码（输在 Sideloadly 弹窗里，不是网页）
4. 装完去 iPhone「设置 → 通用 → VPN 与设备管理」信任该开发者证书
5. iOS 16+ 还要打开「设置 → 隐私与安全性 → 开发者模式」，重启后确认

限制：免费账号签名 **7 天过期**，过期后 App 打不开，重跑一次 Sideloadly 即可（不用卸载重装，覆盖安装）。想长期有效就得用付费开发者账号出 ad-hoc 包（见下一节）。

---

## 二、签名路径（可上架 / TestFlight）

### 1. 准备材料（在 Mac 上操作）

在 [Apple Developer 后台](https://developer.apple.com/account/resources/certificates) 创建证书：

- 类型选 **Apple Distribution**（上架）或 **Apple Development**（真机调试）
- 下载 `.cer`，双击导入 Keychain，在「钥匙串访问」里右键导出为 `.p12`（设一个密码）
- 在 **Identifiers** 里注册 App ID：`com.manggo.manggoPro`
- 在 **Profiles** 里创建 Provisioning Profile，绑定上面的 App ID 和证书，下载 `.mobileprovision`

### 2. 转成 base64（Windows 上也能做）

```powershell
[Convert]::ToBase64String([IO.File]::ReadAllBytes("C:\path\cert.p12")) | Set-Clipboard
[Convert]::ToBase64String([IO.File]::ReadAllBytes("C:\path\profile.mobileprovision")) | Set-Clipboard
```

macOS 上：

```bash
base64 -i cert.p12 | pbcopy
base64 -i profile.mobileprovision | pbcopy
```

### 3. 写入 GitHub Secrets

仓库 → Settings → Secrets and variables → Actions → New repository secret：

| Secret | 必填 | 说明 |
| --- | --- | --- |
| `IOS_CERT_P12` | ✅ | 证书 p12 的 base64 |
| `IOS_CERT_PASSWORD` | ✅ | 导出 p12 时设的密码 |
| `IOS_PROVISION_PROFILE` | ✅ | mobileprovision 的 base64 |
| `IOS_TEAM_ID` | ✅ | 开发者账号 Team ID（后台右上角，10 位） |
| `ASC_KEY_ID` | 可选 | App Store Connect API Key ID（传 TestFlight 用） |
| `ASC_ISSUER_ID` | 可选 | ASC Issuer ID（UUID 格式） |
| `ASC_PRIVATE_KEY` | 可选 | ASC API Key 的 `.p8` 全文 |

可选 Repository variable：`IOS_BUNDLE_ID`（默认 `com.manggo.manggoPro`）

四个必填项齐了，`detect-signing` job 会自动切到签名构建；缺一个就自动退回只出未签名包，不会红叉。

### 4. 触发

Actions → iOS Build → Run workflow：

- `export_method`：`ad-hoc`（内测设备）/ `app-store`（上架）/ `development`（真机调试）
- `upload_testflight`：勾上则导出后直接传 TestFlight（必须 `app-store` + 配了 ASC 三个 secret）

---

## 三、workflow 干了什么

```
detect-signing      探测 secrets 齐不齐
    ├─ build-unsigned   flutter build ios --no-codesign → 打包 Payload → IPA
    └─ build-signed     导入 p12 到临时 keychain
                        安装 mobileprovision（按 UUID 命名，Xcode 只认这个）
                        xcodebuild archive（Manual 签名 + PROFILE_NAME）
                        xcodebuild -exportArchive（ExportOptions.plist）
                        → IPA → 可选 altool 上传 TestFlight
publish            有签名包发签名包，没有发未签名包 → Release ios-latest + version.json
```

几个容易踩的点已经在文件里处理掉了：

1. **`app-store` 在 Xcode 16 改名 `app-store-connect`** —— 脚本按 Xcode 主版本自动映射。
2. **profile 文件名必须是它自己的 UUID** —— 用 `uuidgen` 命名会导致 Xcode 找不到 profile，这里从 plist 里读 `UUID` 再命名。
3. **`DEVELOPMENT_TEAM` 在 Flutter 模板的 pbxproj 里是空的** —— 通过命令行 `DEVELOPMENT_TEAM=...` 覆盖，不改工程文件。
4. **`app-store-connect` 需要 Xcode 16+** —— 所以 runner 选 `macos-15`，不要用 `macos-13`。
5. **没有 Podfile 时 `pod install` 会报错** —— 已加 `[ -f Podfile ]` 判断，当前纯 Dart 依赖直接跳过。

---

## 四、成本与限制

- **公开仓库**：macOS runner 免费，无限额度（合理使用）。
- **私有仓库**：macOS runner 按 **10 倍** 计费（用 1 分钟扣 10 分钟额度），Free 计划每月 2000 分钟 ≈ 200 分钟 macOS 构建。首次构建含 `flutter precache` 约 8–12 分钟，缓存命中后 4–6 分钟。
- **单次上限**：单 job 最长 6 小时，本项目远够。
- **上架本身仍要人工**：IPA 传到 App Store Connect 后，App 元数据、截图、隐私清单、审核提交还是得在网页后台做（可用 `fastlane deliver` 自动化）。

---

## 五、想更省事？两个升级方向

- **fastlane match**：证书和 profile 存私有 Git 仓库，CI 自动拉取，不用手动转 base64。适合多人协作、多 bundle id。
- **Xcode 自动签名 + ASC API Key**：`xcodebuild -allowProvisioningUpdates -authenticationKeyPath ...`，让 Xcode 云端自动生成证书，连 p12 都不用管。缺点是需要 ASC API Key 且首次要跑通。

需要我把 fastlane 那套配起来，说一声。
