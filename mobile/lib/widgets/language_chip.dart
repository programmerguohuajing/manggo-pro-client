import 'package:flutter/material.dart';
import 'package:manggo_pro/app_theme.dart';

/// 翻译主页顶部的语言选择条（源/目标语言）。点击弹出语言选择屏。
class LanguageChip extends StatelessWidget {
  final String label;
  final VoidCallback onTap;

  const LanguageChip({super.key, required this.label, required this.onTap});

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return Expanded(
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(Manggo.radiusMd),
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 11),
          decoration: BoxDecoration(
            color: isDark ? const Color(0xFF1C1E22) : const Color(0xFFFFFFFF),
            border: Border.all(
              color: isDark ? const Color(0x1AFFFFFF) : const Color(0x14000000),
            ),
            borderRadius: BorderRadius.circular(Manggo.radiusMd),
          ),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Flexible(
                child: Text(
                  label,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                      fontSize: 15, fontWeight: FontWeight.w600),
                ),
              ),
              const Icon(Icons.keyboard_arrow_down_rounded, size: 18),
            ],
          ),
        ),
      ),
    );
  }
}
