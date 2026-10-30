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
