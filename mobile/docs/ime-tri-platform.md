# 三连空格翻译：三端输入法实现方案

## 需求

在**任意 App** 的输入框里输入文本，连按三次空格，自动把光标所在行的内容翻译并**原地替换**。

这不是 App 内的输入框功能，而是**系统输入法（IME）**能力：只有输入法才能读取「别的 App」的输入框内容并改写它。

三端都必须各自实现一个输入法，用户手动启用并切换：

| 平台 | 实现基类 | 启用路径 | 当前状态 |
| --- | --- | --- | --- |
| Android | `InputMethodService` | 设置 → 系统 → 语言和输入法 → 启用 + 切换 | ✅ 已实现并真机验证 |
| iOS | `UIInputViewController`（Keyboard Extension） | 设置 → 通用 → 键盘 → 添加新键盘 → 允许完全访问 | ✅ 已实现，CI 出包带 appex |
| HarmonyOS NEXT | `InputMethodExtensionAbility` | 设置 → 系统 → 输入法 → 启用 | ✅ 已实现，待 DevEco 编译 |

## Android（已落地）

代码位置 `mobile/android/app/src/main/kotlin/com/manggo/manggo_pro/ime/`：

| 文件 | 职责 |
| --- | --- |
| `ManggoImeService.kt` | 输入法主体：自绘 QWERTY 键盘 + 三连空格触发翻译 |
| `DemoTranslator.kt` | 双向本地词表（含汉字走中→英，纯拉丁走英→中） |

关键实现点：

1. **读取当前行**
   ```kotlin
   val before = ic.getTextBeforeCursor(1000, 0)?.toString().orEmpty()
   val line = before.substringAfterLast('\n')
   ```
   只取光标所在行，避免把整段多行文本一起翻掉。

2. **原地替换**
   ```kotlin
   ic.deleteSurroundingText(line.length, 0)   // 删原文（含触发用的尾部空格）
   ic.commitText(translated, 1)               // 写译文
   ```

3. **三连空格判定**
   空格键第 1、2 次照常 `commitText(" ")`，第 3 次不输入空格而是触发翻译；
   两次空格间隔超过 1500ms 会重置计数，避免误触发。

4. **隐私**：密码类输入框直接跳过，不读不译
   ```kotlin
   TYPE_TEXT_VARIATION_PASSWORD / VISIBLE_PASSWORD / WEB_PASSWORD
   ```

5. **必须重写 `onEvaluateInputViewShown()` 返回 true**
   基类在检测到实体键盘（模拟器、平板键盘、外接键盘）时会返回 false，
   导致输入法界面**完全不显示**。这是实测踩到的坑（`mInputShown=true` 但
   `mIsInputViewShown=false`）。

6. **注册**：`AndroidManifest.xml` 里 service 需要
   `android:permission="android.permission.BIND_INPUT_METHOD"` +
   `<action android:name="android.view.InputMethod" />` +
   `android.view.im` 元数据指向 `res/xml/method.xml`。

启用（adb）：

```bash
adb shell ime enable com.manggo.manggo_pro/.ime.ManggoImeService
adb shell ime set    com.manggo.manggo_pro/.ime.ManggoImeService
adb shell ime list -s          # 确认已列出
adb shell settings get secure default_input_method   # 确认已切换
```

> 注意：`ime set` 之后偶发不生效，需要再执行一次或用
> `settings put secure default_input_method ...`。

## iOS（已落地，CI 出包验证）

代码位置 `mobile/ios/ManggoKeyboard/`：

| 文件 | 职责 |
| --- | --- |
| `KeyboardViewController.swift` | 键盘 UI（`UIInputViewController`）+ 三连空格触发 |
| `KeyboardTranslator.swift` | 翻译接口 + 离线词表，逻辑与 Android 的 `RemoteTranslator` 一致 |
| `Info.plist` | `NSExtension` 声明，`RequestsOpenAccess = YES` |

工程侧改动（`Runner.xcodeproj/project.pbxproj`）：

- 新增 `ManggoKeyboard` target，`productType = com.apple.product-type.app-extension`，
  bundle id `com.manggo.manggoPro.ManggoKeyboard`
- Runner target 增加 `Embed App Extensions` 拷贝阶段（`dstSubfolderSpec = 13`）与 target 依赖
- 扩展的 Build Configuration 复用 `Flutter/Debug.xcconfig` / `Release.xcconfig`，
  这样 `CFBundleShortVersionString` / `CFBundleVersion` 与主 App 完全一致
- CI 打包前会断言 `build/ios/iphoneos/Runner.app/PlugIns/ManggoKeyboard.appex` 存在，
  缺了直接红叉（否则装到手机上根本没有这个键盘）

启用（必须在设备上手动做，iOS 不允许 App 代劳）：

1. 设置 → 通用 → 键盘 → 键盘 → 添加新键盘 → 选 **Manggo**
2. 点刚加上的 **Manggo**，打开「允许完全访问」——**不开就没网**，三连空格只会提示
   「需开启「允许完全访问」」

行为对齐点：

| 行为 | 实现方式 |
| --- | --- |
| 三连空格（1.5s 窗口） | `onSpace()` 计数，第 3 次不插入空格直接翻译 |
| 只翻当前行 | `documentContextBeforeInput` 按 `\n` 取最后一段 |
| 先请求后替换 | 译完校验 `now.hasSuffix(line)`，原文没变才 `deleteBackward()` 逐字删 |
| 密码框 | iOS 系统层就不把 secure 内容交给键盘，读到的为空 → 提示「此输入框不支持读取」 |
| 状态文案 | 与 Android 同一套：`空格 ×3 翻译这一段` / `翻译中…` / `已翻译 ✓` / `已翻译 ✓（离线词表）` / `翻译失败，请检查网络` / `内容已变化，已取消` |

与 Android 的两点差异：

- 多一个 **🌐** 键调 `advanceToNextInputMode()`，否则用户切不回别的键盘
- 部分 App（尤其 WebView 内）的 `documentContextBeforeInput` 返回 nil，此时只能提示不支持；
  Android 侧可以稳定拿到 1000 字符

> 安装仍未签名，见 `ios-ci.md`：Windows 上用 Sideloadly 重签，或配好 4 个 Secrets 出 ad-hoc 包。

## HarmonyOS NEXT（已落地，需 DevEco 编译）

代码位置 `mobile/harmony/entry/src/main/`：

| 文件 | 职责 |
| --- | --- |
| `ets/inputmethod/ManggoImeAbility.ets` | `InputMethodExtensionAbility`，接 `InputClient` + 创建软键盘面板 |
| `ets/inputmethod/KeyboardTranslator.ets` | 翻译接口（`@kit.NetworkKit`）+ 离线词表 |
| `ets/inputmethod/ImeBridge.ets` | Ability 与面板页面之间的桥（共享 `InputClient`） |
| `ets/pages/KeyboardPanel.ets` | ArkUI 自绘键盘 + 三连空格逻辑 |
| `profile/input_method_config.json` | 输入法元信息（名称、图标、语言、版本） |

`module.json5` 的注册要点：

```json5
"requestPermissions": [{ "name": "ohos.permission.INTERNET", ... }],
"extensionAbilities": [{
  "name": "ManggoImeAbility",
  "srcEntry": "./ets/inputmethod/ManggoImeAbility.ets",
  "type": "inputMethod",
  "exported": true,
  "metadata": [{ "name": "ohos.extension.input_method",
                 "resource": "$profile:input_method_config" }]
}]
```

启用：设置 → 系统 → 输入法 → 更多输入法 → 启用「Manggo 翻译键盘」→ 切换。

读写输入框走 `InputClient`：

```ts
const before = await client.getForward(1000);     // 光标前文本
await client.deleteForward(line.length);          // 删除光标前文本
await client.insertText(translated);
await client.sendKeyFunction({ keyCode: 2054 });  // 回车
```

> **这块代码没有在本机编译过**（Windows 上没有 DevEco / HarmonyOS SDK）。
> 如果 `panel.PanelInfo` / `inputMethodAbility.on('inputStart')` 的签名与你装的 SDK 版本不一致，
> 需要改的地方集中在 `ManggoImeAbility.ets` 一个文件里，其余逻辑与 UI 不依赖这些 API 细节。
> 另外 `getForward` / `deleteForward` 在 OHOS 里的语义是「光标前」，
> 与 Android 的 `getTextBeforeCursor` 对齐，接入时建议先用一个输入框验证删除方向。

## 三端一致性对照

| 能力 | Android | iOS | HarmonyOS |
| --- | --- | --- | --- |
| 自绘 QWERTY | ✅ | ✅ | ✅ |
| 三连空格 1.5s 窗口 | ✅ | ✅ | ✅ |
| 只翻当前行 | ✅ | ✅ | ✅ |
| 原文校验失败则放弃替换 | ✅ | ✅ | ✅ |
| 真实网络翻译 | ✅ | ✅ | ✅ |
| 离线词表兜底 | ✅ | ✅ | ✅ |
| 状态文案 | ✅ | ✅ | ✅ |
| 密码框保护 | ✅ 读 `inputType` | ⚠️ 系统不给内容 | ⚠️ 依赖 InputClient 返回空 |
| 编译验证 | ✅ 真机 | ✅ CI 出包 | ❌ 待 DevEco |
