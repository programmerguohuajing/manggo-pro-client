import 'package:flutter/material.dart';
import 'package:manggo_pro/app_theme.dart';

class _DockItem {
  final IconData icon;
  final String label;
  const _DockItem(this.icon, this.label);
}

const List<_DockItem> _items = [
  _DockItem(Icons.translate_rounded, '翻译'),
  _DockItem(Icons.history_rounded, '历史'),
  _DockItem(Icons.bookmark_outline_rounded, '生词本'),
  _DockItem(Icons.settings_rounded, '设置'),
  _DockItem(Icons.camera_alt_rounded, '拍照'),
];

/// 底部 Dock：选中态只高亮图标（绿色），无背景胶囊。
class AppDock extends StatelessWidget {
  final int currentIndex;
  final ValueChanged<int> onTap;

  const AppDock({super.key, required this.currentIndex, required this.onTap});

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final unselected = isDark ? Colors.white54 : const Color(0xFF8A9099);

    return Container(
      decoration: BoxDecoration(
        color: Theme.of(context).scaffoldBackgroundColor,
        border: Border(
          top: BorderSide(
            color: isDark ? const Color(0x1AFFFFFF) : const Color(0x14000000),
          ),
        ),
      ),
      child: SafeArea(
        top: false,
        child: SizedBox(
          height: 64,
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceAround,
            children: List.generate(_items.length, (i) {
              final selected = i == currentIndex;
              final color = selected ? Manggo.primary : unselected;
              return InkWell(
                onTap: () => onTap(i),
                child: SizedBox(
                  width: 64,
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Icon(_items[i].icon, color: color, size: 24),
                      const SizedBox(height: 4),
                      Text(
                        _items[i].label,
                        style: TextStyle(
                          fontSize: 11,
                          color: color,
                          fontWeight: selected ? FontWeight.w600 : FontWeight.normal,
                        ),
                      ),
                    ],
                  ),
                ),
              );
            }),
          ),
        ),
      ),
    );
  }
}
