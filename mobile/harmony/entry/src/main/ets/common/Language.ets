export class Language {
  code: string;
  name: string;
  badge: string;

  constructor(code: string, name: string, badge: string) {
    this.code = code;
    this.name = name;
    this.badge = badge;
  }

  static common(): Language[] {
    return [
      new Language('zh', '中文（简体）', 'CN'),
      new Language('en', 'English', 'GB'),
      new Language('ja', '日本語', 'JP'),
      new Language('ko', '한국어', 'KR')
    ];
  }

  static others(): Language[] {
    return [
      new Language('fr', 'Français', 'FR'),
      new Language('de', 'Deutsch', 'DE'),
      new Language('es', 'Español', 'ES'),
      new Language('ru', 'Русский', 'RU')
    ];
  }
}
