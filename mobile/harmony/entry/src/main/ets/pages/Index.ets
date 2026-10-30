import { Theme } from '../common/Theme';
import { TranslatePage } from './TranslatePage';
import { HistoryPage } from './HistoryPage';
import { VocabPage } from './VocabPage';
import { SettingsPage } from './SettingsPage';
import { OcrPage } from './OcrPage';

class TabItem {
  label: string;
  glyph: string;

  constructor(label: string, glyph: string) {
    this.label = label;
    this.glyph = glyph;
  }
}

@Entry
@Component
struct Index {
  @State currentIndex: number = 0;
  private tabs: TabItem[] = [
    new TabItem('翻译', '译'),
    new TabItem('历史', '史'),
    new TabItem('生词本', '词'),
    new TabItem('设置', '设'),
    new TabItem('拍照', '拍')
  ];

  @Builder
  tabBar(index: number) {
    Column() {
      Text(this.tabs[index].glyph)
        .fontSize(19)
        .fontWeight(this.currentIndex === index ? FontWeight.Bold : FontWeight.Normal)
        .fontColor(this.currentIndex === index ? Theme.primary : Theme.label3)
      Text(this.tabs[index].label)
        .fontSize(11)
        .fontColor(this.currentIndex === index ? Theme.primary : Theme.label3)
        .margin({ top: 2 })
    }
    .width('100%')
    .height(56)
    .justifyContent(FlexAlign.Center)
  }

  build() {
    Tabs({ barPosition: BarPosition.End, index: this.currentIndex }) {
      TabContent() {
        TranslatePage()
      }.tabBar(this.tabBar(0))

      TabContent() {
        HistoryPage()
      }.tabBar(this.tabBar(1))

      TabContent() {
        VocabPage()
      }.tabBar(this.tabBar(2))

      TabContent() {
        SettingsPage()
      }.tabBar(this.tabBar(3))

      TabContent() {
        OcrPage()
      }.tabBar(this.tabBar(4))
    }
    .barHeight(56)
    .barBackgroundColor(Theme.bg)
    .backgroundColor(Theme.bg)
    .onChange((index: number) => {
      this.currentIndex = index;
    })
  }
}
