import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:manggo_pro/app_theme.dart';
import 'package:manggo_pro/screens/translate_screen.dart';
import 'package:manggo_pro/screens/history_screen.dart';
import 'package:manggo_pro/screens/vocab_screen.dart';
import 'package:manggo_pro/screens/settings_screen.dart';
import 'package:manggo_pro/screens/ocr_screen.dart';
import 'package:manggo_pro/widgets/app_dock.dart';

void main() => runApp(const ManggoApp());

class ManggoApp extends StatefulWidget {
  const ManggoApp({super.key});

  @override
  State<ManggoApp> createState() => _ManggoAppState();
}

class _ManggoAppState extends State<ManggoApp> {
  ThemeMode _themeMode = ThemeMode.system;
  int _tab = 0;

  bool get _isDark {
    final platformDark =
        WidgetsBinding.instance.platformDispatcher.platformBrightness ==
            Brightness.dark;
    return _themeMode == ThemeMode.dark ||
        (_themeMode == ThemeMode.system && platformDark);
  }

  void _onThemeChanged(bool dark) =>
      setState(() => _themeMode = dark ? ThemeMode.dark : ThemeMode.light);

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Manggo Pro',
      debugShowCheckedModeBanner: false,
      theme: Manggo.lightTheme,
      darkTheme: Manggo.darkTheme,
      themeMode: _themeMode,
      home: AnnotatedRegion<SystemUiOverlayStyle>(
        // 状态栏图标明暗跟随主题，避免浅色底上白字看不清
        value: _isDark ? SystemUiOverlayStyle.light : SystemUiOverlayStyle.dark,
        child: Scaffold(
          // 安全区由各屏幕自己处理：浅色页用 SafeArea 避让状态栏，
          // OCR 页需要深色背景全屏铺到状态栏之后，故不在此统一加。
          body: Stack(
            children: [
              IndexedStack(
                index: _tab,
                children: [
                  const TranslateScreen(),
                  const HistoryScreen(),
                  const VocabScreen(),
                  SettingsScreen(dark: _isDark, onToggleDark: _onThemeChanged),
                  const OcrScreen(),
                ],
              ),
              // 顶部渐隐遮罩：列表从状态栏下方滚过时柔和淡出，
              // 避免出现被硬裁掉的半行文字。OCR 页自带深色底，无需遮罩。
              if (_tab != 4)
                Positioned(
                  top: 0,
                  left: 0,
                  right: 0,
                  height: MediaQuery.of(context).padding.top + 14,
                  child: IgnorePointer(
                    child: DecoratedBox(
                      decoration: BoxDecoration(
                        gradient: LinearGradient(
                          begin: Alignment.topCenter,
                          end: Alignment.bottomCenter,
                          colors: [
                            Theme.of(context).scaffoldBackgroundColor,
                            Theme.of(context)
                                .scaffoldBackgroundColor
                                .withOpacity(0.86),
                            Theme.of(context)
                                .scaffoldBackgroundColor
                                .withOpacity(0),
                          ],
                          stops: const [0.0, 0.62, 1.0],
                        ),
                      ),
                    ),
                  ),
                ),
            ],
          ),
          bottomNavigationBar: AppDock(
            currentIndex: _tab,
            onTap: (i) => setState(() => _tab = i),
          ),
        ),
      ),
    );
  }
}
