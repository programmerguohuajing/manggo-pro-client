import 'package:flutter/material.dart';
import 'package:manggo_pro/app_theme.dart';
import 'package:manggo_pro/services/app_settings.dart';
import 'package:manggo_pro/services/platform_service.dart';

class VocabScreen extends StatefulWidget {
  const VocabScreen({super.key});

  @override
  State<VocabScreen> createState() => _VocabScreenState();
}

class _VocabScreenState extends State<VocabScreen> {
  /// 可删除的列表（长按删除），初始为示例数据
  final List<Map<String, String>> _words = [
    {'word': 'serendipity', 'mean': '意外发现美好事物的能力'},
    {'word': 'ubuntu', 'mean': '人道精神；我因你而存在（祖鲁谚语）'},
    {'word': 'schadenfreude', 'mean': '幸灾乐祸'},
    {'word': 'hinode', 'mean': '日出（日语：日の出）'},
  ];

  /// 已标记为重点复习的词
  final Set<String> _starred = {
    'serendipity',
    'ubuntu',
    'schadenfreude',
    'hinode',
  };

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

  Future<void> _speak(String word) async {
    if (!AppSettings.speechEnabled.value) {
      _toast('语音播报已在设置中关闭');
      return;
    }
    final ok = await PlatformService.speak(word, lang: 'en');
    if (!ok) _toast('当前设备不支持语音播报');
  }

  void _toggleStar(String word) {
    setState(() {
      if (!_starred.remove(word)) _starred.add(word);
    });
    _toast(_starred.contains(word) ? '已标记为重点复习' : '已取消标记');
  }

  void _remove(String word) {
    setState(() => _words.removeWhere((w) => w['word'] == word));
    _toast('已删除 $word');
  }

  @override
  Widget build(BuildContext context) {
    final topInset = MediaQuery.of(context).padding.top;
    return SingleChildScrollView(
      padding: EdgeInsets.fromLTRB(16, 16 + topInset, 16, 16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text('生词本',
              style: TextStyle(fontSize: 24, fontWeight: FontWeight.w700)),
          const SizedBox(height: 6),
          const Text('长按可删除 · 点击星标加入重点复习',
              style: TextStyle(color: Color(0xFF8A9099), fontSize: 12)),
          const SizedBox(height: 14),
          if (_words.isEmpty)
            const Padding(
              padding: EdgeInsets.symmetric(vertical: 44),
              child: Center(
                child: Text('生词本是空的',
                    style: TextStyle(color: Color(0xFF8A9099), fontSize: 13)),
              ),
            )
          else
            ..._words.map((w) => _item(context, w)),
        ],
      ),
    );
  }

  Widget _item(BuildContext context, Map<String, String> w) {
    final word = w['word']!;
    final starred = _starred.contains(word);
    return GestureDetector(
      onLongPress: () => _remove(word),
      child: Container(
        margin: const EdgeInsets.only(bottom: 12),
        padding: const EdgeInsets.fromLTRB(15, 10, 4, 10),
        decoration: BoxDecoration(
          color: Theme.of(context).cardColor,
          border: Border.all(color: Theme.of(context).dividerColor),
          borderRadius: BorderRadius.circular(Manggo.radiusMd),
        ),
        child: Row(
          children: [
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(word,
                      style: const TextStyle(
                          fontSize: 15.5, fontWeight: FontWeight.w600)),
                  const SizedBox(height: 4),
                  Text(w['mean']!,
                      style: const TextStyle(
                          fontSize: 13, color: Color(0xFF8A9099))),
                ],
              ),
            ),
            IconButton(
              tooltip: '播报',
              icon: const Icon(Icons.volume_up_outlined,
                  color: Color(0xFF8A9099)),
              onPressed: () => _speak(word),
            ),
            IconButton(
              tooltip: starred ? '取消标记' : '标记重点复习',
              icon: Icon(
                starred ? Icons.star_rounded : Icons.star_border_rounded,
                color: starred ? Manggo.accent : const Color(0xFF8A9099),
              ),
              onPressed: () => _toggleStar(word),
            ),
          ],
        ),
      ),
    );
  }
}
