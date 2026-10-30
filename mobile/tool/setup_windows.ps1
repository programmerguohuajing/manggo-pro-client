# Manggo Pro 三端环境准备脚本（Windows PowerShell）
# 用法：在 mobile 目录执行  powershell -ExecutionPolicy Bypass -File tool\setup_windows.ps1
$ErrorActionPreference = 'Stop'

# 国内镜像（pub / engine 资源）
# 同时写入用户级环境变量，重开终端后依然生效（否则每开一个新窗口都要重设）
$env:PUB_HOSTED_URL = 'https://pub.flutter-io.cn'
$env:FLUTTER_STORAGE_BASE_URL = 'https://storage.flutter-io.cn'
[Environment]::SetEnvironmentVariable('PUB_HOSTED_URL', $env:PUB_HOSTED_URL, 'User')
[Environment]::SetEnvironmentVariable('FLUTTER_STORAGE_BASE_URL', $env:FLUTTER_STORAGE_BASE_URL, 'User')

Write-Host '==> 镜像连通性自检' -ForegroundColor Cyan
$probes = @(
    @{ n = 'pub 镜像';     u = 'https://pub.flutter-io.cn/api/packages/flutter_svg' },
    @{ n = 'engine 镜像';  u = 'https://storage.flutter-io.cn/flutter_infra_release/releases/releases_windows.json' },
    @{ n = 'maven 阿里云'; u = 'https://maven.aliyun.com/repository/google/com/android/tools/build/gradle/maven-metadata.xml' },
    @{ n = 'gradle 腾讯云'; u = 'https://mirrors.cloud.tencent.com/gradle/gradle-9.3.1-all.zip' }
)
foreach ($p in $probes) {
    try {
        $r = Invoke-WebRequest -Uri $p.u -Method Head -TimeoutSec 15 -UseBasicParsing
        Write-Host ("   OK   {0}  ({1})" -f $p.n, $r.StatusCode) -ForegroundColor Green
    } catch {
        Write-Host ("   FAIL {0}  {1}" -f $p.n, $p.u) -ForegroundColor Yellow
    }
}

# Gradle 走阿里云镜像（见 android/settings.gradle.kts）；CI/海外网络可设 off
if (-not $env:GRADLE_MIRROR) { $env:GRADLE_MIRROR = 'on' }

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
