# Manggo Pro 三端环境准备脚本（Windows PowerShell）
# 用法：在 mobile 目录执行  powershell -ExecutionPolicy Bypass -File tool\setup_windows.ps1
$ErrorActionPreference = 'Stop'

# 国内镜像（pub / engine 资源）
$env:PUB_HOSTED_URL = 'https://pub.flutter-io.cn'
$env:FLUTTER_STORAGE_BASE_URL = 'https://storage.flutter-io.cn'

Write-Host '==> flutter config: android sdk' -ForegroundColor Cyan
flutter config --android-sdk "$env:LOCALAPPDATA\Android\sdk"

Write-Host '==> flutter precache (android + ios engine artifacts)' -ForegroundColor Cyan
flutter precache --android --ios

Write-Host '==> flutter pub get' -ForegroundColor Cyan
flutter pub get

Write-Host '==> flutter doctor' -ForegroundColor Cyan
flutter doctor -v

Write-Host '==> build android debug apk' -ForegroundColor Cyan
flutter build apk --debug

Write-Host '完成。iOS 需在 macOS + Xcode 执行：flutter build ios --debug' -ForegroundColor Green
Write-Host '鸿蒙需在 DevEco Studio 打开 mobile/harmony 并配置签名后 Build HAP' -ForegroundColor Green
