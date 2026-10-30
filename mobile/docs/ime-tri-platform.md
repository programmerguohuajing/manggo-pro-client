# 三连空格翻译：三端输入法实现方案

## 需求

在**任意 App** 的输入框里输入文本，连按三次空格，自动把光标所在行的内容翻译并**原地替换**。

这不是 App 内的输入框功能，而是**系统输入法（IME）**能力：只有输入法才能读取「别的 App」的输入框内容并改写它。

三端都必须各自实现一个输入法，用户手动启用并切换：

| 平台 | 实现基类 | 启用路径 | 当前状态 |
| --- | --- | --- | --- |
| Android | `InputMethodService` | 设置 → 系统 → 语言和输入法 → 启用 + 切换 | ✅ 已实现并真机验证 |
| iOS | `UIInputViewController`（Keyboard Extension） | 设置 → 通用 → 键盘 → 添加新键盘 → 允许完全访问 | ⏳ 需 Xcode 工程与签名 |
| HarmonyOS NEXT | `InputMethodExtensionAbility` | 设置 → 系统 → 输入法 → 启用 | ⏳ 需 DevEco + IME Kit |

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

## iOS（待实现，需 macOS + Xcode）

1. 在 Xcode 工程里新增 **Keyboard Extension** target（`ManggoKeyboard`）。
2. `Info.plist` 里 `NSExtensionPointIdentifier` = `com.apple.keyboard-service`，
   `RequestsOpenAccess` = YES（不加完全访问权限无法访问网络，也无法读取部分输入框内容）。
3. 核心逻辑：
   ```swift
   // 读取光标前文本
   let ctx = textDocumentProxy.documentContextBeforeInput ?? ""
   let line = ctx.components(separatedBy: "\n").last ?? ""
   // 删除原文并写入译文
   for _ in 0..<line.count { textDocumentProxy.deleteBackward() }
   textDocumentProxy.insertText(translated)
   ```
4. 三连空格判定与 Android 一致，`deleteBackward()` 只作用于当前光标位置。
5. 局限：iOS 不允许键盘扩展读取 `secureTextEntry` 字段（系统层面就取不到）。
6. 需要 Apple 开发者账号做签名，且用户必须在「设置 → 通用 → 键盘」里手动添加并授予完全访问。

## HarmonyOS NEXT（待实现，需 DevEco Studio）

1. 新建 `InputMethodExtensionAbility`（IME Kit）。
2. 在 `module.json5` 里声明 `extensionAbilities`，`type` 为 `inputMethod`，
   并配置 `metadata` 指向 `input_method_config`。
3. 通过 IME Kit 的 `InputClient` 拿文本与写回：
   ```ts
   const client = await inputMethodAbility.getInputClient();
   const before = await client.getForward(1000);   // 光标前文本
   await client.deleteForward(line.length);
   await client.insertText(translated);
   ```
4. 键盘 UI 用 ArkUI 自定义，三连空格判定与 Android 一致。

## 接入真实翻译服务

三端当前都用本地词表，替换点很集中：

- Android：`DemoTranslator.translate()` → 改成异步请求，在回调里 `commitText`
- iOS：同上，在 `URLSession` 回调里操作 `textDocumentProxy`
- HarmonyOS：在 Promise 回调里操作 `InputClient`

先删原文再请求会有一小段空白；更稳的做法是**先请求、成功后一次性替换**，
把「翻译中…」显示在键盘的空格键上（Android 已这么做）。
