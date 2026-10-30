import 'package:flutter/material.dart';
import 'package:manggo_pro/app_theme.dart';

/// 翻译主页的双卡片（源文 / 译文）。
///
/// 右上角三个图标都可点击：播报、复制、收藏。未传入回调时退化为不可点，
/// 避免调用方漏接线时出现「点了没反应却不自知」。
class TranslateCard extends StatelessWidget {
  final String header;
  final String text;
  final bool editable;
  final TextEditingController? controller;
  final VoidCallback? onSpeak;
  final VoidCallback? onCopy;
  final VoidCallback? onFavorite;
  final bool favorited;

  const TranslateCard({
    super.key,
    required this.header,
    required this.text,
    this.editable = false,
    this.controller,
    this.onSpeak,
    this.onCopy,
    this.onFavorite,
    this.favorited = false,
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
              Flexible(
                child: Text(
                  header,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    fontSize: 11.5,
                    fontWeight: FontWeight.w600,
                    color: Color(0xFF8A9099),
                    letterSpacing: 0.4,
                  ),
                ),
              ),
              Row(
                children: [
                  _CardAction(
                    icon: Icons.volume_up_outlined,
                    onTap: onSpeak,
                    tooltip: '播报',
                  ),
                  _CardAction(
                    icon: Icons.content_copy_outlined,
                    onTap: onCopy,
                    tooltip: '复制',
                  ),
                  _CardAction(
                    icon: favorited
                        ? Icons.star_rounded
                        : Icons.star_border_rounded,
                    onTap: onFavorite,
                    tooltip: favorited ? '取消收藏' : '收藏',
                    color: favorited ? Manggo.accent : const Color(0xFF8A9099),
                  ),
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
                    hintText: '输入要翻译的内容，连按三次空格即翻译…',
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

/// 卡片右上角的小图标按钮，点击区域按 40x40 放大，图标保持 18。
class _CardAction extends StatelessWidget {
  final IconData icon;
  final VoidCallback? onTap;
  final String tooltip;
  final Color color;

  const _CardAction({
    required this.icon,
    required this.onTap,
    required this.tooltip,
    this.color = const Color(0xFF8A9099),
  });

  @override
  Widget build(BuildContext context) {
    return Tooltip(
      message: tooltip,
      child: InkResponse(
        onTap: onTap,
        radius: 20,
        child: Container(
          width: 34,
          height: 30,
          alignment: Alignment.center,
          child: Icon(icon, size: 18, color: color),
        ),
      ),
    );
  }
}
