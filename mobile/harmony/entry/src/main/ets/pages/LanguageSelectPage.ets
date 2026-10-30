import router from '@ohos.router';
import { Theme } from '../common/Theme';
import { Language } from '../common/Language';

@Entry
@Component
struct LanguageSelectPage {
  private target: string = 'src';

  aboutToAppear(): void {
    const p = router.getParams();
    if (p !== undefined && p !== null) {
      const obj = p as Record<string, string>;
      const t = obj.target;
      if (t !== undefined) {
        this.target = t;
      }
    }
  }

  private pick(lang: Language): void {
    if (this.target === 'src') {
      AppStorage.setOrCreate('srcLang', lang.name);
    } else {
      AppStorage.setOrCreate('dstLang', lang.name);
    }
    router.back();
  }

  build() {
    Column() {
      Row() {
        Text('‹')
          .fontSize(26)
          .fontColor(Theme.label)
          .padding({ left: 6, right: 6 })
          .onClick(() => router.back())
        Text('选择语言')
          .fontSize(18)
          .fontWeight(FontWeight.Bold)
          .fontColor(Theme.label)
          .margin({ left: 8 })
        Blank()
      }
      .width('100%')
      .padding({ left: 12, right: 16, top: 12, bottom: 12 })

      Row() {
        Text('⌕').fontSize(16).fontColor(Theme.label3)
        Text('搜索语言').fontSize(14).fontColor(Theme.label3).margin({ left: 8 })
      }
      .width('92%')
      .padding(12)
      .backgroundColor(Theme.surface2)
      .borderRadius(13)

      List() {
        ListItem() {
          Text('常用')
            .fontSize(13)
            .fontColor(Theme.label3)
            .padding({ left: 16, top: 14, bottom: 6 })
        }

        ForEach(Language.common(), (lang: Language) => {
          ListItem() {
            this.row(lang)
          }
        })

        ListItem() {
          Text('其他')
            .fontSize(13)
            .fontColor(Theme.label3)
            .padding({ left: 16, top: 14, bottom: 6 })
        }

        ForEach(Language.others(), (lang: Language) => {
          ListItem() {
            this.row(lang)
          }
        })
      }
      .layoutWeight(1)
      .width('100%')
      .margin({ top: 12 })
    }
    .width('100%')
    .height('100%')
    .backgroundColor(Theme.bg)
  }

  @Builder
  row(lang: Language) {
    Row() {
      Text(lang.badge)
        .fontSize(10)
        .fontColor(Theme.label2)
        .width(28)
        .height(19)
        .textAlign(TextAlign.Center)
        .backgroundColor(Theme.surface2)
        .borderRadius(3)
      Text(lang.name)
        .fontSize(15.5)
        .fontColor(Theme.label)
        .margin({ left: 12 })
      Blank()
      Text('✓').fontSize(16).fontColor(Theme.primary)
    }
    .width('100%')
    .padding({ left: 16, right: 16, top: 14, bottom: 14 })
    .onClick(() => this.pick(lang))
  }
}
