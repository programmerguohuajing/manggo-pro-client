# 在线更新与国内加速

App 内「设置 → 检查更新」可以直接下载并安装新版本。核心难点不是下载，而是**国内网络访问 GitHub 不稳定**，所以整条链路是按"多源冗余"设计的。

## 一、发布侧（CI 自动完成）

`.github/workflows/android.yml` 在 master 上每次构建后执行两件事：

1. **versionCode 自动递增**
   ```bash
   sed -i -E "s/^version: ([0-9.]+)\+[0-9]+/version: \1+${run_number}/" pubspec.yaml
   ```
   `pubspec.yaml` 里原本固定写 `1.0.0+1`。如果不动它，每次构建出来的 versionCode 都是 1，
   App 端 `最新 > 当前` 永远不成立，在线更新等于没做。现在用 `github.run_number`
   保证单调递增。

2. **滚动发布到 GitHub Release**
   - tag 固定为 `android-latest`，每次先删再建（覆盖式，不会堆积几百个 tag）
   - 资产包含 APK 与 `version.json`

`version.json` 结构：

```json
{
  "versionName": "1.0.0",
  "versionCode": 512,
  "apkName": "ManggoPro-1.0.0-512-app-release.apk",
  "apkUrl": "https://github.com/<owner>/<repo>/releases/download/android-latest/<文件名>",
  "size": 51436626,
  "sha256": "…",
  "publishedAt": "2026-10-30T13:40:00Z",
  "notes": "构建 #512 · 提交 abc1234"
}
```

`apkUrl` 写的是 GitHub 原始地址，**不是**镜像地址——镜像前缀由 App 端拼接，
这样换镜像不需要改发布产物。

## 二、App 侧

`lib/services/update_service.dart`：

- **检查更新**：把 `version.json` 的原始地址套上各镜像前缀，**并发发起**，谁先返回 200 且能解析就用谁。
  失败的镜像不会拖慢整体（受 8s 连接超时约束），全部失败才报错。
- **下载**：优先复用刚命中的镜像（`_preferred`），失败再按列表逐个回退。
  下载完用原生流式算 SHA-256 校验，防止镜像返回错误页或被截断的旧文件。
- **安装**：下载到 `cacheDir/updates/`，经 FileProvider 交给系统安装器。
  Android 8+ 若未授权「安装未知应用」，返回 `need_permission` 并跳设置页。

界面在 `lib/widgets/update_dialog.dart`，下载过程中会显示进度和**当前使用的加速源**，
用户能看出是在走镜像还是在回退重试。

## 三、镜像现状（2026-10 实测）

直连、不走系统代理，用一个仓库文件的 raw 地址逐个测：

| 前缀 | 结果 |
|---|---|
| `https://gh-proxy.com/` | ✅ 200，约 2.6s |
| `https://ghfast.top/` | ❌ 超时 |
| `https://ghproxy.net/` | ❌ 超时 |
| `https://github.moeyy.xyz/` | ❌ 连接失败 |
| `https://hub.gitmirror.com/` | ❌ 连接失败 |
| `https://ghproxy.cc/` | ❌ 无响应 |
| `https://gh.llkk.cc/` | ❌ 超时 |
| `https://gh.xxooo.cf/` | ❌ 无响应 |

结论：**公共加速站寿命很短，不能单点依赖**。代码里保留多家只是做冗余，
真正上线前应该换自有分发。

## 四、换成自有 CDN

只需要改 `UpdateService.mirrors` 一处，规则是能用 `<前缀><原始 GitHub URL>` 拼出下载地址：

```dart
static const List<String> mirrors = <String>[
  'https://dl.your-domain.com/gh/',   // 自己的反代
  'https://gh-proxy.com/',
  '',
];
```

常见做法：

- **Cloudflare R2 + 自定义域名**：CI 里多一步 `aws s3 cp`（R2 兼容 S3 协议），
  把 APK 和 version.json 同步到桶里，App 直连自己的域名。国内访问 Cloudflare
  自定义域名一般可用，且不受 GitHub 限速影响。
- **对象存储（阿里云 OSS / 腾讯云 COS）**：国内速度最好，需要备案域名。
  CI 里加一步 `ossutil cp` 即可，`apkUrl` 换成 CDN 地址。

换 CDN 后 `version.json` 里的 `apkUrl` 也要改成新地址（或者让镜像前缀拼自己的域名，
两种方式选一种，别同时用）。

## 五、已知限制

- **签名必须一致**：覆盖安装要求新包用同一个签名。当前 CI 未配置
  `ANDROID_KEYSTORE_BASE64` 时用 debug 签名，每次 runner 生成的 debug key 不同，
  换一次构建就会 `INSTALL_FAILED_UPDATE_INCOMPATIBLE`。**正式分发前必须在
  仓库 Secrets 里配置固定的 release keystore。**
- 下载不支持断点续传：镜像之间不共享分片，中断后从头再来。
- 只在 Android 上实现了。iOS 受系统限制不能自行安装，只能跳 App Store；
  HarmonyOS 需要走应用市场的更新通道。
