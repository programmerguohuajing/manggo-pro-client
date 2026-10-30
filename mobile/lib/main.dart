import 'package:flutter/material.dart';
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
        WidgetsBinding.instance.platformDispatcher.platformBrightness == Brightness.dark;
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
      home: Scaffold(
        body: IndexedStack(
          index: _tab,
          children: [
            const TranslateScreen(),
            const HistoryScreen(),
            const VocabScreen(),
            SettingsScreen(dark: _isDark, onToggleDark: _onThemeChanged),
            const OcrScreen(),
          ],
        ),
        bottomNavigationBar: AppDock(
          currentIndex: _tab,
          onTap: (i) => setState(() => _tab = i),
        ),
      ),
    );
  }
}
