import 'package:flutter/material.dart';
import 'package:manggo_pro/app_theme.dart';
import 'package:manggo_pro/models/language.dart';
import 'package:manggo_pro/widgets/flag.dart';

/// 语言选择页。
///
/// 之前的「搜索语言」只是一个静态 Row，既没有输入框也没有点击响应——
/// 点了没反应，等于死控件。这里换成真正的 TextField，实时按名称/语言码过滤。
class LanguageSelectScreen extends StatefulWidget {
  /// 当前已选语言码，用于打勾
  final String? current;

  const LanguageSelectScreen({super.key, this.current});

  @override
  State<LanguageSelectScreen> createState() => _LanguageSelectScreenState();
}

class _LanguageSelectScreenState extends State<LanguageSelectScreen> {
  final _controller = TextEditingController();
  String _query = '';

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  List<Language> _filter(List<Language> source) {
    final q = _query.trim().toLowerCase();
    if (q.isEmpty) return source;
    return source
        .where((l) =>
            l.name.toLowerCase().contains(q) ||
            l.code.toLowerCase().contains(q))
        .toList();
  }

  Widget _row(BuildContext context, Language lang) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return InkWell(
      onTap: () => Navigator.of(context).pop(lang),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 15, vertical: 14),
        decoration: BoxDecoration(
          border: Border(
            bottom: BorderSide(
                color:
                    isDark ? const Color(0x0AFFFFFF) : const Color(0x0A000000)),
          ),
        ),
        child: Row(
          children: [
            Flag(lang.flag, size: 24),
            const SizedBox(width: 12),
            Expanded(
                child: Text(lang.name, style: const TextStyle(fontSize: 15.5))),
            if (lang.code == widget.current)
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
                fontSize: 13,
                fontWeight: FontWeight.w600,
                color: Color(0xFF8A9099))),
      );

  Widget _group(BuildContext context, List<Language> items) => Container(
        margin: const EdgeInsets.symmetric(horizontal: 16),
        decoration: BoxDecoration(
          color: Theme.of(context).cardColor,
          border: Border.all(color: Theme.of(context).dividerColor),
          borderRadius: BorderRadius.circular(Manggo.radiusMd),
        ),
        child: Column(children: items.map((l) => _row(context, l)).toList()),
      );

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final common = _filter(Language.common);
    final others = _filter(Language.others);
    final none = common.isEmpty && others.isEmpty;
    return Scaffold(
      appBar: AppBar(
        leading: IconButton(
          icon: const Icon(Icons.arrow_back_ios_new_rounded, size: 20),
          onPressed: () => Navigator.of(context).pop(),
        ),
        title: const Text('选择语言',
            style: TextStyle(fontSize: 18, fontWeight: FontWeight.w700)),
      ),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 10, 16, 12),
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 14),
              decoration: BoxDecoration(
                color:
                    isDark ? const Color(0xFF262A2F) : const Color(0xFFF4F6F7),
                border: Border.all(
                    color: isDark
                        ? const Color(0x1AFFFFFF)
                        : const Color(0x14000000)),
                borderRadius: BorderRadius.circular(13),
              ),
              child: Row(
                children: [
                  const Icon(Icons.search, size: 18, color: Color(0xFF8A9099)),
                  const SizedBox(width: 9),
                  Expanded(
                    child: TextField(
                      controller: _controller,
                      textInputAction: TextInputAction.search,
                      onChanged: (v) => setState(() => _query = v),
                      style: const TextStyle(fontSize: 14),
                      decoration: const InputDecoration(
                        hintText: '搜索语言',
                        hintStyle:
                            TextStyle(color: Color(0xFF8A9099), fontSize: 14),
                        isDense: true,
                        border: InputBorder.none,
                        contentPadding: EdgeInsets.symmetric(vertical: 12),
                      ),
                    ),
                  ),
                  if (_query.isNotEmpty)
                    GestureDetector(
                      onTap: () {
                        _controller.clear();
                        setState(() => _query = '');
                      },
                      child: const Icon(Icons.cancel,
                          size: 17, color: Color(0xFF8A9099)),
                    ),
                ],
              ),
            ),
          ),
          Expanded(
            child: none
                ? const Center(
                    child: Text('没有匹配的语言',
                        style:
                            TextStyle(color: Color(0xFF8A9099), fontSize: 13)),
                  )
                : ListView(
                    children: [
                      if (common.isNotEmpty) ...[
                        _section('常用'),
                        _group(context, common),
                      ],
                      if (others.isNotEmpty) ...[
                        _section('其他'),
                        _group(context, others),
                      ],
                      const SizedBox(height: 16),
                    ],
                  ),
          ),
        ],
      ),
    );
  }
}
