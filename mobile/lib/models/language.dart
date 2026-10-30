class Language {
  final String code; // BCP-47，如 'zh' / 'en'
  final String name; // 显示名
  final String flag; // 对应 Flag 组件的内置旗帜 key（见 widgets/flag.dart）

  const Language(this.code, this.name, this.flag);

  static const zh = Language('zh', '中文（简体）', 'cn');
  static const en = Language('en', 'English', 'gb');
  static const ja = Language('ja', '日本語', 'jp');
  static const ko = Language('ko', '한국어', 'kr');
  static const fr = Language('fr', 'Français', 'fr');
  static const de = Language('de', 'Deutsch', 'de');
  static const es = Language('es', 'Español', 'es');
  static const ru = Language('ru', 'Русский', 'ru');

  static const List<Language> common = [zh, en, ja, ko];
  static const List<Language> others = [fr, de, es, ru];
}
