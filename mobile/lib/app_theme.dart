import 'package:flutter/material.dart';

/// Manggo Pro 设计令牌（与桌面端 PySide6 品牌色一致）
/// Primary 芒果绿 #2ECC71 / Accent 芒果橙 #EA580C
class Manggo {
  // 品牌色
  static const primary = Color(0xFF2ECC71);
  static const primaryPress = Color(0xFF27AE60);
  static const primaryDeep = Color(0xFF1E8449);
  static const onPrimary = Color(0xFFFFFFFF);
  static const accent = Color(0xFFEA580C);
  static const accentBg = Color(0xFFFFF7ED);
  static const primarySoft = Color(0xFFEAFBF0);

  // 翻译 FAB 渐变（180deg, primaryPress -> primaryDeep）
  static const fabGradient = LinearGradient(
    begin: Alignment.topCenter,
    end: Alignment.bottomCenter,
    colors: [primaryPress, primaryDeep],
  );

  // 圆角（Material 3 微调，贴近高保真稿）
  static const radiusLg = 24.0;
  static const radiusMd = 18.0;
  static const radiusSm = 13.0;

  static ThemeData lightTheme = ThemeData(
    useMaterial3: true,
    brightness: Brightness.light,
    fontFamily: 'PingFang SC',
    colorScheme: const ColorScheme.light(
      primary: primary,
      onPrimary: onPrimary,
      surface: Color(0xFFFFFFFF),
      surfaceContainerHighest: Color(0xFFF4F6F7),
      secondary: accent,
      onSecondary: onPrimary,
      error: Color(0xFFE5484D),
    ),
    scaffoldBackgroundColor: const Color(0xFFFFFFFF),
    dividerColor: const Color(0x14000000),
    cardColor: const Color(0xFFFFFFFF),
    textTheme: const TextTheme(
      bodyLarge:
          TextStyle(color: Color(0xFF10131A), fontSize: 15.5, height: 1.6),
      bodyMedium: TextStyle(color: Color(0xFF5B626B), fontSize: 14),
      titleLarge: TextStyle(
          color: Color(0xFF10131A), fontSize: 20, fontWeight: FontWeight.w700),
      labelSmall: TextStyle(color: Color(0xFF8A9099), fontSize: 11.5),
    ),
    iconTheme: const IconThemeData(color: Color(0xFF5B626B)),
    appBarTheme: const AppBarTheme(
      backgroundColor: Color(0xFFFFFFFF),
      elevation: 0,
      foregroundColor: Color(0xFF10131A),
    ),
    bottomNavigationBarTheme: const BottomNavigationBarThemeData(
      backgroundColor: Color(0xFFFFFFFF),
      elevation: 0,
    ),
  );

  static ThemeData darkTheme = ThemeData(
    useMaterial3: true,
    brightness: Brightness.dark,
    fontFamily: 'PingFang SC',
    colorScheme: const ColorScheme.dark(
      primary: primary,
      onPrimary: onPrimary,
      surface: Color(0xFF1C1E22),
      surfaceContainerHighest: Color(0xFF262A2F),
      secondary: accent,
      onSecondary: onPrimary,
      error: Color(0xFFFF6B6B),
    ),
    scaffoldBackgroundColor: const Color(0xFF0B0C0E),
    dividerColor: const Color(0x1AFFFFFF),
    cardColor: const Color(0xFF1C1E22),
    textTheme: const TextTheme(
      bodyLarge:
          TextStyle(color: Color(0xFFEDEFF1), fontSize: 15.5, height: 1.6),
      bodyMedium: TextStyle(color: Color(0xCCEDEFF1), fontSize: 14),
      titleLarge: TextStyle(
          color: Color(0xFFEDEFF1), fontSize: 20, fontWeight: FontWeight.w700),
      labelSmall: TextStyle(color: Color(0x9EEDEFF1), fontSize: 11.5),
    ),
    iconTheme: const IconThemeData(color: Color(0xCCEDEFF1)),
    appBarTheme: const AppBarTheme(
      backgroundColor: Color(0xFF0B0C0E),
      elevation: 0,
      foregroundColor: Color(0xFFEDEFF1),
    ),
    bottomNavigationBarTheme: const BottomNavigationBarThemeData(
      backgroundColor: Color(0xFF0B0C0E),
      elevation: 0,
    ),
  );
}
