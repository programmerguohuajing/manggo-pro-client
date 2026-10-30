import { Theme } from '../common/Theme';

@Component
export struct SettingsPage {
  @State darkMode: boolean = false;

  build() {
    Column() {
      Text('设置')
        .fontSize(24)
        .fontWeight(FontWeight.Bold)
        .fontColor(Theme.label)
        .width('100%')
        .padding({ left: 16, top: 16, bottom: 10 })
        .textAlign(TextAlign.Start)

      Column() {
        this.row('深色外观', '跟随系统或手动开启', true)
        Divider().color(Theme.sep)
        this.row('语音播报', '', false)
        Divider().color(Theme.sep)
        this.row('默认翻译语言', '中文 → 英语', false)
        Divider().color(Theme.sep)
        this.row('关于 Manggo Pro', '', false)
      }
      .width('92%')
      .backgroundColor(Theme.surface)
      .borderRadius(Theme.radiusMd)
      .border({ width: 1, color: Theme.sep })

      Blank()
    }
    .width('100%')
    .height('100%')
    .backgroundColor(Theme.bg)
  }

  @Builder
  row(title: string, subtitle: string, isSwitch: boolean) {
    Row() {
      Column() {
        Text(title).fontSize(15.5).fontColor(Theme.label)
        if (subtitle.length > 0) {
          Text(subtitle).fontSize(12).fontColor(Theme.label3).margin({ top: 3 })
        }
      }
      .alignItems(HorizontalAlign.Start)
      .layoutWeight(1)

      if (isSwitch) {
        Toggle({ type: ToggleType.Switch, isOn: this.darkMode })
          .selectedColor(Theme.primary)
          .onChange((isOn: boolean) => {
            this.darkMode = isOn;
          })
      } else {
        Text('›').fontSize(18).fontColor(Theme.label3)
      }
    }
    .width('100%')
    .padding({ left: 16, right: 16, top: 14, bottom: 14 })
  }
}
