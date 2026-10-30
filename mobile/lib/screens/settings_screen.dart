import 'package:flutter/material.dart';
import 'package:manggo_pro/app_theme.dart';
import 'package:manggo_pro/models/language.dart';
import 'package:manggo_pro/screens/language_select_screen.dart';
import 'package:manggo_pro/services/app_settings.dart';
import 'package:manggo_pro/services/platform_service.dart';

class SettingsScreen extends StatefulWidget {
  final bool dark;
  final ValueChanged<bool> onToggleDark;

  const SettingsScreen(
      {super.key, required this.dark, required this.onToggleDark});

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  /// 语音播报开关（真正决定播报按钮是否出声）
  bool _speechOn = AppSettings.speechEnabled.value;

  /// 默认翻译语言对
  Language _from = Language.zh;
  Language _to = Language.en;

  void _toast(String message) {
    final messenger = ScaffoldMessenger.maybeOf(context);
    if (messenger == null) return;
    messenger.hideCurrentSnackBar();
    messenger.showSnackBar(SnackBar(
      content: Text(message),
      duration: const Duration(milliseconds: 1400),
      behavior: SnackBarBehavior.floating,
    ));
  }

  /// 跳到系统输入法管理页，让用户启用并切到 Manggo 翻译输入法
  Future<void> _openImeSettings() async {
    final ok = await PlatformService.openImeSettings();
    if (!ok) _toast('当前平台暂不支持，请到系统设置里手动开启键盘');
  }

  /// 选择默认翻译语言：先选源语言再选目标语言
  Future<void> _pickDefaultLanguages() async {
    final from = await Navigator.of(context).push<Language>(
      MaterialPageRoute(builder: (_) => const LanguageSelectScreen()),
    );
    if (from == null || !mounted) return;
    final to = await Navigator.of(context).push<Language>(
      MaterialPageRoute(builder: (_) => const LanguageSelectScreen()),
    );
    if (to == null || !mounted) return;
    setState(() {
      _from = from;
      _to = to;
    });
    _toast('默认语言已改为 ${from.name} → ${to.name}');
  }

  void _showAbout() {
    showDialog<void>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: const Text('关于 Manggo Pro'),
        content: const Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('版本 1.0.0'),
            SizedBox(height: 8),
            Text('文本翻译 · 拍照取词 · 生词本 · 翻译输入法',
                style: TextStyle(fontSize: 13, color: Color(0xFF8A9099))),
            SizedBox(height: 8),
            Text('连按三次空格即可在任意 App 内翻译并替换当前行',
                style: TextStyle(fontSize: 13, color: Color(0xFF8A9099))),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(dialogContext),
            child: const Text('知道了'),
          ),
        ],
      ),
    );
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
                    value: widget.dark,
                    activeColor: Manggo.primary,
                    onChanged: widget.onToggleDark,
                  ),
                ),
                _row(
                  title: '语音播报',
                  subtitle: _speechOn ? '点击译文旁的喇叭即可朗读' : '已关闭，播报按钮不可用',
                  trailing: Switch(
                    value: _speechOn,
                    activeColor: Manggo.primary,
                    onChanged: (v) {
                      setState(() => _speechOn = v);
                      AppSettings.speechEnabled.value = v;
                      if (v) {
                        PlatformService.speak('Speech enabled', lang: 'en');
                      } else {
                        PlatformService.stopSpeak();
                      }
                    },
                  ),
                ),
                _row(
                  title: '默认翻译语言',
                  subtitle: '${_from.name} → ${_to.name}',
                  trailing: const Icon(Icons.chevron_right_rounded),
                  onTap: _pickDefaultLanguages,
                ),
                _row(
                  title: 'Manggo 输入法',
                  subtitle: '连按三次空格，任意 App 里翻译并替换整行',
                  trailing: const Icon(Icons.chevron_right_rounded),
                  onTap: _openImeSettings,
                ),
                _row(
                  title: '关于 Manggo Pro',
                  trailing: const Icon(Icons.chevron_right_rounded),
                  onTap: _showAbout,
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
