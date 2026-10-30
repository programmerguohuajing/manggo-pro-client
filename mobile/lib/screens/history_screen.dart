import 'package:flutter/material.dart';
import 'package:manggo_pro/app_theme.dart';

class HistoryScreen extends StatelessWidget {
  const HistoryScreen({super.key});

  static const _items = [
    {'src': '你好，世界', 'dst': 'Hello, world', 'time': '刚刚'},
    {'src': '今天天气真好', 'dst': 'The weather is nice today', 'time': '10 分钟前'},
    {'src': '请帮我翻译这段', 'dst': 'Please translate this for me', 'time': '昨天'},
    {'src': '谢谢你的帮助', 'dst': 'Thank you for your help', 'time': '昨天'},
    {'src': '我们几点见面', 'dst': 'What time shall we meet', 'time': '周一'},
  ];

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      bottom: false,
      child: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('历史记录',
                style: TextStyle(fontSize: 24, fontWeight: FontWeight.w700)),
            const SizedBox(height: 6),
            const Text('本地存储 · 失败不写入',
                style: TextStyle(color: Color(0xFF8A9099), fontSize: 12)),
            const SizedBox(height: 14),
            ..._items.map((it) => _item(context, it)),
          ],
        ),
      ),
    );
  }

  Widget _item(BuildContext context, Map<String, String> it) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(15),
      decoration: BoxDecoration(
        color: Theme.of(context).cardColor,
        border: Border.all(color: Theme.of(context).dividerColor),
        borderRadius: BorderRadius.circular(Manggo.radiusMd),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(it['src']!,
              style:
                  const TextStyle(fontSize: 15.5, fontWeight: FontWeight.w600)),
          const SizedBox(height: 6),
          Text(it['dst']!,
              style: const TextStyle(fontSize: 14, color: Color(0xFF8A9099))),
          const SizedBox(height: 8),
          Align(
            alignment: Alignment.centerRight,
            child: Text(it['time']!,
                style: const TextStyle(fontSize: 11, color: Color(0xFF8A9099))),
          ),
        ],
      ),
    );
  }
}
