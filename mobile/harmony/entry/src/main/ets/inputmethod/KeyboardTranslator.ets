import { http } from '@kit.NetworkKit';

/**
 * 一次翻译的结果。online === false 表示命中本地词表兜底。
 */
export class KeyboardTranslation {
  text: string;
  online: boolean;

  constructor(text: string, online: boolean) {
    this.text = text;
    this.online = online;
  }
}

/**
 * 输入法侧的翻译客户端，与 Android 的 RemoteTranslator / iOS 的 KeyboardTranslator
 * 使用同一个接口、同一套语言判定、同样的「先网络后词表」顺序。
 */
export class KeyboardTranslator {
  private static readonly ENDPOINT: string = 'https://translate.googleapis.com/translate_a/single';
  private static readonly TIMEOUT: number = 12000;

  static async translate(text: string): Promise<KeyboardTranslation | null> {
    const input: string = text.trim();
    if (input.length === 0) {
      return null;
    }
    const cjk: boolean = KeyboardTranslator.hasCjk(input);
    const source: string = cjk ? 'zh-CN' : 'en';
    const target: string = cjk ? 'en' : 'zh-CN';

    const online: string | null = await KeyboardTranslator.requestOnce(input, source, target);
    if (online !== null) {
      return new KeyboardTranslation(online, true);
    }
    // 网络失败才查词表，避免把「没网」误报成「没收录」
    const offline: string | null = KeyboardTranslator.offlineLookup(input);
    if (offline !== null) {
      return new KeyboardTranslation(offline, false);
    }
    return null;
  }

  private static async requestOnce(text: string, source: string, target: string): Promise<string | null> {
    const body: string = 'client=gtx&sl=' + encodeURIComponent(source) +
      '&tl=' + encodeURIComponent(target) +
      '&dt=t&q=' + encodeURIComponent(text);
    const headers: Record<string, string> = {
      'Content-Type': 'application/x-www-form-urlencoded; charset=utf-8'
    };

    const request = http.createHttp();
    try {
      const response = await request.request(KeyboardTranslator.ENDPOINT, {
        method: http.RequestMethod.POST,
        header: headers,
        extraData: body,
        connectTimeout: KeyboardTranslator.TIMEOUT,
        readTimeout: KeyboardTranslator.TIMEOUT,
        expectDataType: http.HttpDataType.STRING
      });
      if (response.responseCode !== 200) {
        return null;
      }
      const raw: string = response.result as string;
      return KeyboardTranslator.parse(raw);
    } catch (err) {
      return null;
    } finally {
      request.destroy();
    }
  }

  /** 响应形如 [[["译文","原文",null,...]],null,"en",...]，长句分多段需拼接 */
  private static parse(raw: string): string | null {
    try {
      const root: Object = JSON.parse(raw) as Object;
      const top: Object[] = root as Object[];
      if (top.length === 0) {
        return null;
      }
      const segments: Object[] = top[0] as Object[];
      let out: string = '';
      for (let i = 0; i < segments.length; i++) {
        const segment: Object[] = segments[i] as Object[];
        if (segment.length === 0) {
          continue;
        }
        const piece: string = segment[0] as string;
        if (piece.length > 0) {
          out += piece;
        }
      }
      const trimmed: string = out.trim();
      return trimmed.length > 0 ? trimmed : null;
    } catch (err) {
      return null;
    }
  }

  private static hasCjk(text: string): boolean {
    for (let i = 0; i < text.length; i++) {
      const code: number = text.charCodeAt(i);
      if ((code >= 0x4E00 && code <= 0x9FFF) || (code >= 0x3400 && code <= 0x4DBF)) {
        return true;
      }
    }
    return false;
  }

  // ---------------- 离线词表（与 DemoTranslator.kt 一致） ----------------

  private static readonly ZH_TO_EN: Map<string, string> = new Map<string, string>([
    ['你好', 'Hello'],
    ['你好，世界', 'Hello, world'],
    ['你好世界', 'Hello world'],
    ['早上好', 'Good morning'],
    ['晚安', 'Good night'],
    ['谢谢', 'Thank you'],
    ['谢谢你的帮助', 'Thank you for your help'],
    ['今天天气真好', 'The weather is nice today'],
    ['请帮我翻译这段', 'Please translate this for me'],
    ['我们几点见面', 'What time shall we meet'],
    ['多少钱', 'How much is it?'],
    ['我不明白', 'I don\'t understand'],
    ['再见', 'Goodbye'],
    ['好久不见', 'Long time no see']
  ]);

  private static normalize(input: string): string {
    let text: string = input.trim().toLowerCase();
    while (text.length > 0 && '.,!?'.indexOf(text.charAt(text.length - 1)) >= 0) {
      text = text.substring(0, text.length - 1);
    }
    return text;
  }

  private static readonly EN_TO_ZH: Map<string, string> = new Map<string, string>();

  private static reverseMap(): Map<string, string> {
    if (KeyboardTranslator.EN_TO_ZH.size === 0) {
      KeyboardTranslator.ZH_TO_EN.forEach((en: string, zh: string) => {
        KeyboardTranslator.EN_TO_ZH.set(KeyboardTranslator.normalize(en), zh);
      });
    }
    return KeyboardTranslator.EN_TO_ZH;
  }

  private static offlineLookup(text: string): string | null {
    if (KeyboardTranslator.hasCjk(text)) {
      const hit: string | undefined = KeyboardTranslator.ZH_TO_EN.get(text);
      if (hit !== undefined) {
        return hit;
      }
      const replaced: string | undefined = KeyboardTranslator.ZH_TO_EN.get(text.replace('，', ','));
      return replaced !== undefined ? replaced : null;
    }

    const found: string | undefined =
      KeyboardTranslator.reverseMap().get(KeyboardTranslator.normalize(text));
    return found !== undefined ? found : null;
  }
}
