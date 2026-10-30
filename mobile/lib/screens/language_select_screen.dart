import 'package:flutter/material.dart';
import 'package:manggo_pro/app_theme.dart';
import 'package:manggo_pro/models/language.dart';
import 'package:manggo_pro/widgets/flag.dart';

class LanguageSelectScreen extends StatelessWidget {
  const LanguageSelectScreen({super.key});

  Widget _row(BuildContext context, Language lang, {bool checked = false}) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return InkWell(
      onTap: () => Navigator.of(context).pop(lang),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 15, vertical: 14),
        decoration: BoxDecoration(
          border: Border(
            bottom: BorderSide(color: isDark ? const Color(0x0AFFFFFF) : const Color(0x0A000000)),
          ),
        ),
        child: Row(
          children: [
            Flag(lang.flag, size: 24),
            const SizedBox(width: 12),
            Expanded(child: Text(lang.name, style: const TextStyle(fontSize: 15.5))),
            if (checked)
              const Icon(Icons.check_rounded, color: Manggo.primary, size: 20),
          ],
        ),
      ),
    );
  }

  Widget _section(String title) => Padding(
        padding: const EdgeInsets.fromLTRB(16, 14, 16, 6),
        child: Text(title,
            style: const TextStyle(
                fontSize: 13, fontWeight: FontWeight.w600, color: Color(0xFF8A9099))),
      );

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return Scaffold(
      appBar: AppBar(
        leading: IconButton(
          icon: const Icon(Icons.arrow_back_ios_new_rounded, size: 20),
          onPressed: () => Navigator.of(context).pop(),
        ),
        title: const Text('选择语言', style: TextStyle(fontSize: 18, fontWeight: FontWeight.w700)),
      ),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 10, 16, 12),
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 11),
              decoration: BoxDecoration(
                color: isDark ? const Color(0xFF262A2F) : const Color(0xFFF4F6F7),
                border: Border.all(color: isDark ? const Color(0x1AFFFFFF) : const Color(0x14000000)),
                borderRadius: BorderRadius.circular(13),
              ),
              child: const Row(
                children: [
                  Icon(Icons.search, size: 18, color: Color(0xFF8A9099)),
                  SizedBox(width: 9),
                  Text('搜索语言', style: TextStyle(color: Color(0xFF8A9099), fontSize: 14)),
                ],
              ),
            ),
          ),
          Expanded(
            child: ListView(
              children: [
                _section('常用'),
                Container(
                  margin: const EdgeInsets.symmetric(horizontal: 16),
                  decoration: BoxDecoration(
                    color: Theme.of(context).cardColor,
                    border: Border.all(color: Theme.of(context).dividerColor),
                    borderRadius: BorderRadius.circular(Manggo.radiusMd),
                  ),
                  child: Column(
                    children: [
                      _row(context, Language.zh, checked: true),
                      _row(context, Language.en, checked: true),
                      _row(context, Language.ja),
                      _row(context, Language.ko),
                    ],
                  ),
                ),
                _section('其他'),
                Container(
                  margin: const EdgeInsets.symmetric(horizontal: 16),
                  decoration: BoxDecoration(
                    color: Theme.of(context).cardColor,
                    border: Border.all(color: Theme.of(context).dividerColor),
                    borderRadius: BorderRadius.circular(Manggo.radiusMd),
                  ),
                  child: Column(
                    children: [
                      _row(context, Language.fr),
                      _row(context, Language.de),
                      _row(context, Language.es),
                      _row(context, Language.ru),
                    ],
                  ),
                ),
                const SizedBox(height: 16),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
