import { Theme } from '../common/Theme';

class VocabItem {
  word: string;
  mean: string;

  constructor(word: string, mean: string) {
    this.word = word;
    this.mean = mean;
  }
}

@Component
export struct VocabPage {
  private words: VocabItem[] = [
    new VocabItem('serendipity', '意外发现美好事物的能力'),
    new VocabItem('ubuntu', '人道精神；我因你而存在'),
    new VocabItem('schadenfreude', '幸灾乐祸'),
    new VocabItem('hinode', '日出（日语：日の出）')
  ];

  build() {
    Column() {
      Column() {
        Text('生词本')
          .fontSize(24)
          .fontWeight(FontWeight.Bold)
          .fontColor(Theme.label)
        Text('长按可删除 · 点击可加入复习')
          .fontSize(12)
          .fontColor(Theme.label3)
          .margin({ top: 4 })
      }
      .alignItems(HorizontalAlign.Start)
      .width('100%')
      .padding({ left: 16, right: 16, top: 16, bottom: 10 })

      List({ space: 12 }) {
        ForEach(this.words, (w: VocabItem) => {
          ListItem() {
            Row() {
              Column() {
                Text(w.word).fontSize(15.5).fontWeight(FontWeight.Medium).fontColor(Theme.label)
                Text(w.mean).fontSize(13).fontColor(Theme.label3).margin({ top: 4 })
              }
              .alignItems(HorizontalAlign.Start)
              .layoutWeight(1)

              Text('★').fontSize(18).fontColor(Theme.accent)
            }
            .width('100%')
            .padding(15)
            .backgroundColor(Theme.surface)
            .borderRadius(Theme.radiusMd)
            .border({ width: 1, color: Theme.sep })
          }
        })
      }
      .layoutWeight(1)
      .width('92%')
      .padding({ top: 4, bottom: 12 })
    }
    .width('100%')
    .height('100%')
    .backgroundColor(Theme.bg)
  }
}
