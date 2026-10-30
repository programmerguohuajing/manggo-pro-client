import 'package:flutter/material.dart';
import 'package:manggo_pro/app_theme.dart';

class VocabScreen extends StatelessWidget {
  const VocabScreen({super.key});

  static const _words = [
    {'word': 'serendipity', 'mean': '意外发现美好事物的能力'},
    {'word': 'ubuntu', 'mean': '人道精神；我因你而存在（祖鲁谚语）'},
    {'word': 'schadenfreude', 'mean': '幸灾乐祸'},
    {'word': 'hinode', 'mean': '日出（日语：日の出）'},
  ];

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text('生词本',
              style: TextStyle(fontSize: 24, fontWeight: FontWeight.w700)),
          const SizedBox(height: 6),
          const Text('长按可删除 · 点击可加入复习', style: TextStyle(color: Color(0xFF8A9099), fontSize: 12)),
          const SizedBox(height: 14),
          ..._words.map((w) => _item(context, w)),
        ],
      ),
    );
  }

  Widget _item(BuildContext context, Map<String, String> w) {
    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(15),
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
                Text(w['word']!, style: const TextStyle(fontSize: 15.5, fontWeight: FontWeight.w600)),
                const SizedBox(height: 4),
                Text(w['mean']!, style: const TextStyle(fontSize: 13, color: Color(0xFF8A9099))),
              ],
            ),
          ),
          IconButton(
            icon: const Icon(Icons.volume_up_outlined, color: Color(0xFF8A9099)),
            onPressed: () {},
          ),
          IconButton(
            icon: const Icon(Icons.star_rounded, color: Manggo.accent),
            onPressed: () {},
          ),
        ],
      ),
    );
  }
}
