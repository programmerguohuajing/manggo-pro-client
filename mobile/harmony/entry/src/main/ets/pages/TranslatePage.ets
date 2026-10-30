import router from '@ohos.router';
import { Theme } from '../common/Theme';

@Component
export struct TranslatePage {
  @StorageLink('srcLang') srcLang: string = '中文（简体）';
  @StorageLink('dstLang') dstLang: string = 'English';
  @State inputText: string = '你好，世界';
  private outputText: string = 'Hello, world';

  build() {
    Column() {
      Row() {
        Text('翻译')
          .fontSize(26)
          .fontWeight(FontWeight.Bold)
          .fontColor(Theme.label)
        Blank()
        Text('⋯').fontSize(22).fontColor(Theme.label2)
      }
      .width('100%')
      .padding({ left: 16, right: 16, top: 12, bottom: 8 })

      Row({ space: 8 }) {
        this.langChip(this.srcLang, 'src')
        Button() {
          Text('⇅').fontSize(18).fontColor(Theme.primary)
        }
        .width(42)
        .height(42)
        .borderRadius(21)
        .backgroundColor(Theme.primarySoft)
        .onClick(() => {
          const t: string = this.srcLang;
          this.srcLang = this.dstLang;
          this.dstLang = t;
        })
        this.langChip(this.dstLang, 'dst')
      }
      .width('100%')
      .padding({ left: 16, right: 16 })

      Stack({ alignContent: Alignment.Center }) {
        Column({ space: 18 }) {
          this.card('源语言 · 中文（简体）', '')
          this.card('译文 · English', this.outputText)
        }
        .width('100%')
        .padding({ left: 16, right: 16, top: 16 })

        Button() {
          Text('文A').fontSize(16).fontWeight(FontWeight.Medium).fontColor(Color.White)
        }
        .width(56)
        .height(56)
        .borderRadius(28)
        .backgroundColor(Theme.primary)
        .shadow({ radius: 12, color: '#33000000', offsetX: 0, offsetY: 6 })
      }
      .layoutWeight(1)

      Row({ space: 10 }) {
        this.quick('复制')
        this.quick('语音')
        this.quick('收藏')
        this.quick('分享')
      }
      .width('100%')
      .padding({ left: 16, right: 16, bottom: 12 })
    }
    .width('100%')
    .height('100%')
    .backgroundColor(Theme.bg)
  }

  @Builder
  langChip(label: string, target: string) {
    Row() {
      Text(label)
        .fontSize(15)
        .fontWeight(FontWeight.Medium)
        .fontColor(Theme.label)
      Blank()
      Text('▾').fontSize(13).fontColor(Theme.label3)
    }
    .layoutWeight(1)
    .padding({ left: 14, right: 14, top: 12, bottom: 12 })
    .backgroundColor(Theme.surface)
    .borderRadius(Theme.radiusMd)
    .border({ width: 1, color: Theme.sep })
    .onClick(() => {
      router.pushUrl({ url: 'pages/LanguageSelectPage', params: { target: target } });
    })
  }

  @Builder
  card(header: string, body: string) {
    Column() {
      Text(header).fontSize(11.5).fontColor(Theme.label3)
      if (body.length > 0) {
        Text(body).fontSize(15.5).fontColor(Theme.label).margin({ top: 8 })
      } else {
        TextInput({ text: this.inputText, placeholder: '输入要翻译的内容…' })
          .fontSize(15.5)
          .backgroundColor(Color.Transparent)
          .padding(0)
          .margin({ top: 6 })
          .onChange((value: string) => {
            this.inputText = value;
          })
      }
    }
    .alignItems(HorizontalAlign.Start)
    .width('100%')
    .padding(15)
    .backgroundColor(Theme.surface)
    .borderRadius(Theme.radiusMd)
    .border({ width: 1, color: Theme.sep })
  }

  @Builder
  quick(label: string) {
    Column() {
      Text('·').fontSize(18).fontColor(Theme.label2)
      Text(label).fontSize(11).fontColor(Theme.label2).margin({ top: 2 })
    }
    .layoutWeight(1)
    .padding({ top: 12, bottom: 12 })
    .backgroundColor(Theme.surface)
    .borderRadius(Theme.radiusSm)
    .border({ width: 1, color: Theme.sep })
  }
}
