import 'package:flutter/material.dart';
import 'package:manggo_pro/app_theme.dart';

/// 翻译主页的双卡片（源文 / 译文）。
class TranslateCard extends StatelessWidget {
  final String header;
  final String text;
  final bool editable;
  final TextEditingController? controller;

  const TranslateCard({
    super.key,
    required this.header,
    required this.text,
    this.editable = false,
    this.controller,
  });

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return Container(
      padding: const EdgeInsets.all(15),
      decoration: BoxDecoration(
        color: isDark ? const Color(0xFF1C1E22) : const Color(0xFFFFFFFF),
        border: Border.all(
          color: isDark ? const Color(0x1AFFFFFF) : const Color(0x14000000),
        ),
        borderRadius: BorderRadius.circular(Manggo.radiusMd),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                header,
                style: const TextStyle(
                  fontSize: 11.5,
                  fontWeight: FontWeight.w600,
                  color: Color(0xFF8A9099),
                  letterSpacing: 0.4,
                ),
              ),
              Row(
                children: const [
                  Icon(Icons.volume_up_outlined,
                      size: 18, color: Color(0xFF8A9099)),
                  SizedBox(width: 16),
                  Icon(Icons.content_copy_outlined,
                      size: 18, color: Color(0xFF8A9099)),
                  SizedBox(width: 16),
                  Icon(Icons.star_border_rounded,
                      size: 18, color: Color(0xFF8A9099)),
                ],
              ),
            ],
          ),
          const SizedBox(height: 8),
          editable
              ? TextField(
                  controller: controller,
                  maxLines: null,
                  decoration: const InputDecoration(
                    border: InputBorder.none,
                    hintText: '输入要翻译的内容…',
                    isCollapsed: true,
                  ),
                  style: const TextStyle(fontSize: 15.5, height: 1.6),
                )
              : Text(
                  text,
                  style: const TextStyle(fontSize: 15.5, height: 1.6),
                ),
        ],
      ),
    );
  }
}
