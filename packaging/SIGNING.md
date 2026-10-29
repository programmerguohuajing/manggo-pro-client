# macOS 自签签名说明

## 为什么签名

macOS 的 TCC 授权（辅助功能、输入监控、屏幕录制）按应用的签名身份
记账。未签名 / 临时（ad-hoc）签名时，每次打包的身份（CDHash）都
不同，系统把新版本当成新应用，旧授权失效——用户每次更新都要在
三个隐私列表里把应用删掉再重新添加。2026-10-29 用户选定自签方案：
所有版本用同一张自签证书签名，身份固定，授权跨版本保留。

## 证书

- 主题：CN=ManggoProClient Signing, O=jingguohua（自签，非 Apple 颁发）
- SHA-1 指纹：6CB75FAA040EC071C55DD37CC6AA16AAA1234D0B
- 有效期：2026-10-29 – 2036-10-26
- 密钥用法：Digital Signature；扩展用途：Code Signing
- 私钥与口令只存在 GitHub 仓库 Secrets 里：
  MACOS_SIGN_P12_BASE64（.p12 的 base64）、MACOS_SIGN_P12_PASSWORD。
  绝不写入仓库、日志或聊天。

## CI 怎么用

build-packages.yml 的两个 macOS job 在 PyInstaller 构建 + Prune
之后、打包之前执行：把 .p12 导入临时钥匙串，按 SHA-1 身份对
ManggoProClient.app 做 codesign --force --deep --timestamp=none，
再 codesign --verify 验证并打印 codesign -dv 供日志核对，最后删
钥匙串。签名必须在 Prune 之后：签名后再删改 .app 内的文件会
破坏签名封印。

## 局限（自签 ≠ 开发者证书）

- Gatekeeper 仍会把下载的构建提示为“已损坏”（未公证），装好后
  仍需 xattr -cr /Applications/ManggoProClient.app 才能打开；
  自签只解决授权跨版本保留，解决不了这个。
- 身份可信度只到仓库 Secrets 的保管水平：拿到私钥的人能以此
  身份签名。仓库或 Secrets 泄露时按下面轮换。

## 轮换（换证书）

1. 本地重新生成自签证书（openssl req -x509，扩展同上，有效期 10 年）；
2. 更新仓库的两个 Secrets；
3. 发新版本。换证书的那一版，用户仍需把三项授权删+重加一次
   （身份变了）；之后恢复跨版本保留。
