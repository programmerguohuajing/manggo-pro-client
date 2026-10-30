import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:manggo_pro/app_theme.dart';

class SettingsScreen extends StatelessWidget {
  final bool dark;
  final ValueChanged<bool> onToggleDark;

  const SettingsScreen(
      {super.key, required this.dark, required this.onToggleDark});

  /// 与 Android 端 MainActivity 里的 MethodChannel 对应
  static const MethodChannel _imeChannel = MethodChannel('manggo/ime');

  /// 跳到系统输入法管理页，让用户启用并切到 Manggo 翻译输入法
  Future<void> _openImeSettings() async {
    try {
      await _imeChannel.invokeMethod<bool>('openImeSettings');
    } on MissingPluginException {
      // iOS / HarmonyOS 需各自实现（键盘扩展 / InputMethodExtensionAbility）
    } on PlatformException {
      // 通道存在但调用失败，忽略即可，不打断用户
    }
  }

  Widget _row({
    required String title,
    String? subtitle,
    Widget? trailing,
    VoidCallback? onTap,
  }) {
    return InkWell(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
        decoration: const BoxDecoration(
          border: Border(bottom: BorderSide(color: Color(0x0A000000))),
        ),
        child: Row(
          children: [
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(title, style: const TextStyle(fontSize: 15.5)),
                  if (subtitle != null)
                    Padding(
                      padding: const EdgeInsets.only(top: 3),
                      child: Text(subtitle,
                          style: const TextStyle(
                              fontSize: 12, color: Color(0xFF8A9099))),
                    ),
                ],
              ),
            ),
            if (trailing != null) trailing,
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final topInset = MediaQuery.of(context).padding.top;
    return SingleChildScrollView(
      padding: EdgeInsets.fromLTRB(16, 16 + topInset, 16, 16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text('设置',
              style: TextStyle(fontSize: 24, fontWeight: FontWeight.w700)),
          const SizedBox(height: 14),
          Container(
            decoration: BoxDecoration(
              color: Theme.of(context).cardColor,
              border: Border.all(color: Theme.of(context).dividerColor),
              borderRadius: BorderRadius.circular(Manggo.radiusMd),
            ),
            child: Column(
              children: [
                _row(
                  title: '深色外观',
                  subtitle: '跟随系统或手动开启',
                  trailing: Switch(
                    value: dark,
                    activeColor: Manggo.primary,
                    onChanged: onToggleDark,
                  ),
                ),
                _row(
                    title: '语音播报',
                    trailing: const Icon(Icons.chevron_right_rounded)),
                _row(
                    title: '默认翻译语言',
                    subtitle: '中文 → 英语',
                    trailing: const Icon(Icons.chevron_right_rounded)),
                _row(
                  title: 'Manggo 输入法',
                  subtitle: '连按三次空格，任意 App 里翻译并替换整行',
                  trailing: const Icon(Icons.chevron_right_rounded),
                  onTap: _openImeSettings,
                ),
                _row(
                    title: '关于 Manggo Pro',
                    trailing: const Icon(Icons.chevron_right_rounded)),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
