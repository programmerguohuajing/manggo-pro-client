import { Theme } from '../common/Theme';

class HistoryItem {
  src: string;
  dst: string;
  time: string;

  constructor(src: string, dst: string, time: string) {
    this.src = src;
    this.dst = dst;
    this.time = time;
  }
}

@Component
export struct HistoryPage {
  private items: HistoryItem[] = [
    new HistoryItem('你好，世界', 'Hello, world', '刚刚'),
    new HistoryItem('今天天气真好', 'The weather is nice today', '10 分钟前'),
    new HistoryItem('请帮我翻译这段', 'Please translate this for me', '昨天'),
    new HistoryItem('谢谢你的帮助', 'Thank you for your help', '昨天'),
    new HistoryItem('我们几点见面', 'What time shall we meet', '周一')
  ];

  build() {
    Column() {
      Column() {
        Text('历史记录')
          .fontSize(24)
          .fontWeight(FontWeight.Bold)
          .fontColor(Theme.label)
        Text('本地存储 · 失败不写入')
          .fontSize(12)
          .fontColor(Theme.label3)
          .margin({ top: 4 })
      }
      .alignItems(HorizontalAlign.Start)
      .width('100%')
      .padding({ left: 16, right: 16, top: 16, bottom: 10 })

      List({ space: 12 }) {
        ForEach(this.items, (it: HistoryItem) => {
          ListItem() {
            Column() {
              Text(it.src).fontSize(15.5).fontWeight(FontWeight.Medium).fontColor(Theme.label)
              Text(it.dst).fontSize(14).fontColor(Theme.label3).margin({ top: 6 })
              Text(it.time).fontSize(11).fontColor(Theme.label3).margin({ top: 8 })
            }
            .alignItems(HorizontalAlign.Start)
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
