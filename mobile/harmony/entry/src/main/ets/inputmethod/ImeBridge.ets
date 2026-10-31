import { InputClient } from '@kit.IMEKit';

export type StatusListener = (text: string) => void;

/**
 * 输入法 Ability 与键盘面板（ArkUI 页面）之间的桥。
 *
 * 两者跑在同一个进程里，但没有直接的引用关系：Ability 在 onCreate 里拿到
 * InputClient，面板页面通过这个单例把它取走，状态文案反向回传给面板。
 */
export class ImeBridge {
  private static readonly INSTANCE: ImeBridge = new ImeBridge();

  private client: InputClient | undefined = undefined;
  private listener: StatusListener | undefined = undefined;

  static getInstance(): ImeBridge {
    return ImeBridge.INSTANCE;
  }

  attach(client: InputClient): void {
    this.client = client;
  }

  detach(): void {
    this.client = undefined;
  }

  getClient(): InputClient | undefined {
    return this.client;
  }

  setListener(listener: StatusListener): void {
    this.listener = listener;
  }

  clearListener(): void {
    this.listener = undefined;
  }

  /** 只在面板已经挂载时生效，避免 Ability 先于页面回调时报错 */
  status(text: string): void {
    if (this.listener !== undefined) {
      this.listener(text);
    }
  }
}
