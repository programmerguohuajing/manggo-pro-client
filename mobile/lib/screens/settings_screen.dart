import 'package:flutter/material.dart';
import 'package:manggo_pro/app_theme.dart';

class SettingsScreen extends StatelessWidget {
  final bool dark;
  final ValueChanged<bool> onToggleDark;

  const SettingsScreen({super.key, required this.dark, required this.onToggleDark});

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
                          style: const TextStyle(fontSize: 12, color: Color(0xFF8A9099))),
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
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
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
                _row(title: '语音播报', trailing: const Icon(Icons.chevron_right_rounded)),
                _row(title: '默认翻译语言', subtitle: '中文 → 英语',
                    trailing: const Icon(Icons.chevron_right_rounded)),
                _row(title: '关于 Manggo Pro',
                    trailing: const Icon(Icons.chevron_right_rounded)),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
