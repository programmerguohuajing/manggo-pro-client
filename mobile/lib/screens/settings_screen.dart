import 'package:flutter/material.dart';
import 'package:manggo_pro/app_theme.dart';
import 'package:manggo_pro/models/language.dart';
import 'package:manggo_pro/screens/language_select_screen.dart';
import 'package:manggo_pro/services/app_settings.dart';
import 'package:manggo_pro/services/platform_service.dart';
import 'package:manggo_pro/services/update_service.dart';
import 'package:manggo_pro/widgets/update_dialog.dart';

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

  /// 当前安装包版本（从原生侧读取，避免和 pubspec 写死的数字不一致）
  int _verCode = 0;
  String _verName = '';
  bool _checkingUpdate = false;

  @override
  void initState() {
    super.initState();
    PlatformService.appVersion().then((v) {
      if (v == null || !mounted) return;
      setState(() {
        _verCode = v.code;
        _verName = v.name;
      });
    });
  }

  /// 检查在线更新。国内网络下会并发尝试多个加速镜像，具体逻辑在 UpdateService。
  Future<void> _checkUpdate() async {
    if (_checkingUpdate) return;
    setState(() => _checkingUpdate = true);
    final check = await UpdateService.check();
    if (!mounted) return;
    setState(() => _checkingUpdate = false);

    if (check.failed) {
      // 检查失败必须留下可读的原因。之前用 toast，1.4 秒就消失，
      // 用户（包括排查问题的自己）根本来不及看清是网络问题还是源挂了。
      await showDialog<void>(
        context: context,
        builder: (dialogContext) => AlertDialog(
          title: const Text('检查更新失败'),
          content: Text(check.error!),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(dialogContext),
              child: const Text('知道了'),
            ),
          ],
        ),
      );
      return;
    }
    if (!check.hasUpdate) {
      _toast('已是最新版本 ${check.currentName} (${check.currentCode})');
      return;
    }
    final done = await showDialog<bool>(
      context: context,
      builder: (_) => UpdateDialog(check: check),
    );
    if (done == true) {
      // 安装器已经拉起，用户确认后系统会覆盖安装
      if (mounted) setState(() {});
    }
  }

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
    final version = _verName.isEmpty
        ? '版本未知'
        : '版本 $_verName${_verCode > 0 ? ' ($_verCode)' : ''}';
    showDialog<void>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: const Text('关于 Manggo Pro'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(version),
            const SizedBox(height: 8),
            const Text('文本翻译 · 拍照取词 · 生词本 · 翻译输入法',
                style: TextStyle(fontSize: 13, color: Color(0xFF8A9099))),
            const SizedBox(height: 8),
            const Text('连按三次空格即可在任意 App 内翻译并替换当前行',
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
                  title: '检查更新',
                  subtitle: _checkingUpdate
                      ? '正在检查，国内网络会自动尝试加速镜像…'
                      : (_verCode > 0
                          ? '当前版本 $_verName ($_verCode)'
                          : '在线获取最新版本'),
                  trailing: _checkingUpdate
                      ? const SizedBox(
                          width: 18,
                          height: 18,
                          child: CircularProgressIndicator(
                              strokeWidth: 2, color: Manggo.primary),
                        )
                      : const Icon(Icons.refresh_rounded),
                  onTap: _checkingUpdate ? null : _checkUpdate,
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
