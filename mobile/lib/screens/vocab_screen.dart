import 'package:flutter/material.dart';
import 'package:manggo_pro/app_theme.dart';
import 'package:manggo_pro/services/app_settings.dart';
import 'package:manggo_pro/services/platform_service.dart';
import 'package:manggo_pro/services/vocab_store.dart';

class VocabScreen extends StatefulWidget {
  const VocabScreen({super.key});

  @override
  State<VocabScreen> createState() => _VocabScreenState();
}

class _VocabScreenState extends State<VocabScreen> {
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
    final starred = VocabStore.toggleStar(word);
    _toast(starred ? '已标记为重点复习' : '已取消标记');
  }

  void _remove(String word) {
    VocabStore.remove(word);
    _toast('已删除 $word');
  }

  @override
  Widget build(BuildContext context) {
    final topInset = MediaQuery.of(context).padding.top;
    return ValueListenableBuilder<List<VocabEntry>>(
      valueListenable: VocabStore.entries,
      builder: (context, words, _) {
        final starredCount = words.where((w) => w.starred).length;
        return SingleChildScrollView(
          padding: EdgeInsets.fromLTRB(16, 16 + topInset, 16, 16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                crossAxisAlignment: CrossAxisAlignment.baseline,
                textBaseline: TextBaseline.alphabetic,
                children: [
                  const Text('生词本',
                      style:
                          TextStyle(fontSize: 24, fontWeight: FontWeight.w700)),
                  const SizedBox(width: 8),
                  Text(
                    '${words.length} 条 · $starredCount 条重点',
                    style:
                        const TextStyle(fontSize: 12, color: Color(0xFF8A9099)),
                  ),
                ],
              ),
              const SizedBox(height: 6),
              const Text('长按可删除 · 点击星标加入重点复习',
                  style: TextStyle(color: Color(0xFF8A9099), fontSize: 12)),
              const SizedBox(height: 14),
              if (words.isEmpty)
                const Padding(
                  padding: EdgeInsets.symmetric(vertical: 44),
                  child: Center(
                    child: Text('生词本是空的\n在翻译页点星标即可加入',
                        textAlign: TextAlign.center,
                        style: TextStyle(
                            color: Color(0xFF8A9099),
                            fontSize: 13,
                            height: 1.6)),
                  ),
                )
              else
                ...words.map((w) => _item(context, w)),
            ],
          ),
        );
      },
    );
  }

  Widget _item(BuildContext context, VocabEntry w) {
    return GestureDetector(
      onLongPress: () => _remove(w.word),
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
                  Text(w.word,
                      style: const TextStyle(
                          fontSize: 15.5, fontWeight: FontWeight.w600)),
                  const SizedBox(height: 4),
                  Text(w.meaning,
                      style: const TextStyle(
                          fontSize: 13, color: Color(0xFF8A9099))),
                ],
              ),
            ),
            IconButton(
              tooltip: '播报',
              icon: const Icon(Icons.volume_up_outlined,
                  color: Color(0xFF8A9099)),
              onPressed: () => _speak(w.word),
            ),
            IconButton(
              tooltip: w.starred ? '取消标记' : '标记重点复习',
              icon: Icon(
                w.starred ? Icons.star_rounded : Icons.star_border_rounded,
                color: w.starred ? Manggo.accent : const Color(0xFF8A9099),
              ),
              onPressed: () => _toggleStar(w.word),
            ),
          ],
        ),
      ),
    );
  }
}
