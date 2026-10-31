import { InputClient } from '@kit.IMEKit';
import { ImeBridge } from '../inputmethod/ImeBridge';
import { KeyboardTranslator, KeyboardTranslation } from '../inputmethod/KeyboardTranslator';

/**
 * 软键盘面板（HarmonyOS NEXT）。
 *
 * 交互与 Android 的 ManggoImeService、iOS 的 KeyboardViewController 一致：
 * 连按三次空格，把光标所在这一行翻译并原地替换。前两次空格照常输入。
 */
@Entry
@Component
struct KeyboardPanel {
  @State status: string = '空格 ×3 翻译这一段';
  @State shiftOn: boolean = false;
  @State translating: boolean = false;

  private spaceTaps: number = 0;
  private token: number = 0;
  private resetTimer: number = -1;

  private readonly idleStatus: string = '空格 ×3 翻译这一段';
  private readonly spaceWindow: number = 1500;
  /** OHOS KeyCode.KEYCODE_ENTER */
  private readonly keyCodeEnter: number = 2054;

  private readonly row1: string[] = ['q', 'w', 'e', 'r', 't', 'y', 'u', 'i', 'o', 'p'];
  private readonly row2: string[] = ['a', 's', 'd', 'f', 'g', 'h', 'j', 'k', 'l'];
  private readonly row3: string[] = ['z', 'x', 'c', 'v', 'b', 'n', 'm'];

  aboutToAppear(): void {
    ImeBridge.getInstance().setListener((text: string) => {
      this.status = text;
    });
  }

  aboutToDisappear(): void {
    ImeBridge.getInstance().clearListener();
    if (this.resetTimer >= 0) {
      clearTimeout(this.resetTimer);
      this.resetTimer = -1;
    }
  }

  build() {
    Column({ space: 6 }) {
      this.letterRow(this.row1, 0)
      this.letterRow(this.row2, 10)

      // 第三行：⇧ + zxcvbnm + ⌫
      Row({ space: 6 }) {
        this.keyView('⇧', true, 18, () => {
          this.shiftOn = !this.shiftOn;
        })
        ForEach(this.row3, (letter: string) => {
          this.keyView(this.display(letter), false, 20, () => {
            this.onLetter(letter);
          })
        }, (letter: string) => letter)
        this.keyView('⌫', true, 18, () => {
          this.onDelete();
        })
      }
      .width('100%')
      .padding({ left: 4, right: 4 })

      // 第四行：空格（显示状态）+ 回车
      Row({ space: 6 }) {
        Text(this.status)
          .fontSize(13)
          .fontColor('#1F2328')
          .textAlign(TextAlign.Center)
          .height(46)
          .borderRadius(8)
          .backgroundColor('#FFFFFF')
          .layoutWeight(1)
          .onClick(() => {
            this.onSpace();
          })
        this.keyView('↵', true, 18, () => {
          this.onEnter();
        })
      }
      .width('100%')
      .padding({ left: 4, right: 4 })
    }
    .width('100%')
    .padding({ left: 4, right: 4, top: 6, bottom: 6 })
    .backgroundColor('#EEF0F3')
  }

  // ---------------- UI 片段 ----------------

  @Builder
  keyView(label: string, accent: boolean, fontSize: number, onTap: () => void) {
    Text(label)
      .fontSize(fontSize)
      .fontColor(accent ? '#0F7B4F' : '#1F2328')
      .textAlign(TextAlign.Center)
      .height(46)
      .borderRadius(8)
      .backgroundColor(accent ? '#E3F6EC' : '#FFFFFF')
      .layoutWeight(1)
      .onClick(onTap)
  }

  @Builder
  letterRow(keys: string[], indent: number) {
    Row({ space: 6 }) {
      if (indent > 0) {
        Text('').height(46).layoutWeight(indent)
      }
      ForEach(keys, (letter: string) => {
        this.keyView(this.display(letter), false, 20, () => {
          this.onLetter(letter);
        })
      }, (letter: string) => letter)
      if (indent > 0) {
        Text('').height(46).layoutWeight(indent)
      }
    }
    .width('100%')
    .padding({ left: 4, right: 4 })
  }

  // ---------------- 输入行为 ----------------

  private display(letter: string): string {
    return this.shiftOn ? letter.toUpperCase() : letter;
  }

  private inputClient(): InputClient | undefined {
    return ImeBridge.getInstance().getClient();
  }

  private async insertText(text: string): Promise<void> {
    const client: InputClient | undefined = this.inputClient();
    if (client === undefined) {
      return;
    }
    try {
      await client.insertText(text);
    } catch (err) {
      // 输入框已失焦等情况，忽略即可
    }
  }

  private async onLetter(letter: string): Promise<void> {
    await this.insertText(this.shiftOn ? letter.toUpperCase() : letter);
    this.spaceTaps = 0;
    this.resetStatusIfIdle();
    if (this.shiftOn) {
      this.shiftOn = false;
    }
  }

  private async onDelete(): Promise<void> {
    const client: InputClient | undefined = this.inputClient();
    if (client !== undefined) {
      try {
        await client.deleteForward(1);
      } catch (err) {
      }
    }
    this.spaceTaps = 0;
    this.resetStatusIfIdle();
  }

  private async onEnter(): Promise<void> {
    const client: InputClient | undefined = this.inputClient();
    if (client !== undefined) {
      try {
        await client.sendKeyFunction({ keyCode: this.keyCodeEnter });
      } catch (err) {
      }
    }
    this.spaceTaps = 0;
  }

  /** 译完后继续打字时把「已翻译 ✓」换回提示；请求进行中不改，免得冲掉「翻译中…」 */
  private resetStatusIfIdle(): void {
    if (!this.translating && this.status !== this.idleStatus) {
      this.setStatus(this.idleStatus);
    }
  }

  private setStatus(text: string): void {
    this.status = text;
  }

  // ---------------- 三连空格 ----------------

  private onSpace(): void {
    if (this.translating) {
      return;
    }
    this.spaceTaps += 1;

    if (this.spaceTaps >= 3) {
      this.spaceTaps = 0;
      if (this.resetTimer >= 0) {
        clearTimeout(this.resetTimer);
        this.resetTimer = -1;
      }
      this.translateCurrentLine();
      return;
    }

    this.insertText(' ');
    if (this.resetTimer >= 0) {
      clearTimeout(this.resetTimer);
    }
    this.resetTimer = setTimeout(() => {
      this.spaceTaps = 0;
      this.resetTimer = -1;
    }, this.spaceWindow);
  }

  private async translateCurrentLine(): Promise<void> {
    if (this.translating) {
      return;
    }
    const client: InputClient | undefined = this.inputClient();
    if (client === undefined) {
      this.setStatus('输入框未就绪');
      return;
    }

    // getForward 取的是光标前文本，与 Android 的 getTextBeforeCursor 等价
    let before: string = '';
    try {
      before = await client.getForward(1000);
    } catch (err) {
      before = '';
    }
    if (before.length === 0) {
      this.setStatus('此输入框不支持读取');
      return;
    }

    const line: string = before.lastIndexOf('\n') >= 0
      ? before.substring(before.lastIndexOf('\n') + 1)
      : before;
    const content: string = line.trim();
    if (content.length === 0) {
      this.setStatus('先输入内容');
      return;
    }

    this.translating = true;
    this.token += 1;
    const currentToken: number = this.token;
    this.setStatus('翻译中…');

    const result: KeyboardTranslation | null = await KeyboardTranslator.translate(content);
    if (currentToken !== this.token) {
      this.translating = false;
      return;
    }
    if (result === null) {
      this.translating = false;
      this.setStatus('翻译失败，请检查网络');
      return;
    }

    // 请求期间用户可能继续打字，确认光标前仍是原文再删
    let now: string = '';
    try {
      now = await client.getForward(1000);
    } catch (err) {
      now = '';
    }
    if (!now.endsWith(line)) {
      this.translating = false;
      this.setStatus('内容已变化，已取消');
      return;
    }

    try {
      if (line.length > 0) {
        await client.deleteForward(line.length);
      }
      await client.insertText(result.text);
      this.setStatus(result.online ? '已翻译 ✓' : '已翻译 ✓（离线词表）');
    } catch (err) {
      this.setStatus('替换失败');
    } finally {
      this.translating = false;
    }
  }
}
