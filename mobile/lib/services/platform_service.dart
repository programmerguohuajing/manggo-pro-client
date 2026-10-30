import 'package:flutter/services.dart';

/// 跨平台能力封装：语音播报、系统分享、输入法设置。
///
/// Android 侧在 MainActivity.kt 的 `manggo/platform` MethodChannel 里实现；
/// iOS / HarmonyOS 尚未实现时调用会抛 MissingPluginException，这里统一吞掉，
/// 保证不会因为某个平台没实现而崩掉整个交互。
class PlatformService {
  static const MethodChannel _channel = MethodChannel('manggo/platform');

  /// 语音播报（TTS）。[lang] 用 BCP-47，如 en / zh / ja。
  static Future<bool> speak(String text, {String lang = 'en'}) async {
    if (text.trim().isEmpty) return false;
    return _invoke('speak', {'text': text, 'lang': lang});
  }

  /// 停止播报
  static Future<bool> stopSpeak() => _invoke('stopSpeak', const {});

  /// 调起系统分享面板
  static Future<bool> share(String text, {String subject = 'Manggo Pro'}) {
    if (text.trim().isEmpty) return Future.value(false);
    return _invoke('share', {'text': text, 'subject': subject});
  }

  /// 打开系统「输入法管理」页，用于启用 Manggo 翻译输入法
  static Future<bool> openImeSettings() => _invoke('openImeSettings', const {});

  /// 直接弹出输入法切换面板
  static Future<bool> showImePicker() => _invoke('showImePicker', const {});

  // ---------------- 在线更新 ----------------

  /// 当前安装包版本。返回 (versionCode, versionName)，取不到时返回 null。
  static Future<({int code, String name})?> appVersion() async {
    try {
      final map = await _channel
          .invokeMapMethod<String, dynamic>('appVersion', const {});
      if (map == null) return null;
      return (
        code: (map['versionCode'] as num?)?.toInt() ?? 0,
        name: map['versionName'] as String? ?? '',
      );
    } on MissingPluginException {
      return null;
    } on PlatformException {
      return null;
    }
  }

  /// 计算文件 SHA-256（原生流式计算，避免把几十 MB 读进内存）
  static Future<String?> sha256(String path) async {
    try {
      return await _channel.invokeMethod<String>('sha256', {'path': path});
    } on MissingPluginException {
      return null;
    } on PlatformException {
      return null;
    }
  }

  /// 是否已允许「安装未知应用」
  static Future<bool> canInstallPackages() =>
      _invoke('canInstallPackages', const {});

  /// 跳系统设置让用户授权安装未知应用
  static Future<bool> openInstallPermission() =>
      _invoke('openInstallPermission', const {});

  /// 拉起系统安装器。返回 'ok' / 'need_permission' / null(失败)
  static Future<String?> installApk(String path) async {
    try {
      return await _channel.invokeMethod<String>('installApk', {'path': path});
    } on MissingPluginException {
      return null;
    } on PlatformException {
      return null;
    }
  }

  static Future<bool> _invoke(String method, Map<String, dynamic> args) async {
    try {
      final ok = await _channel.invokeMethod<bool>(method, args);
      return ok ?? false;
    } on MissingPluginException {
      return false;
    } on PlatformException {
      return false;
    }
  }
}
