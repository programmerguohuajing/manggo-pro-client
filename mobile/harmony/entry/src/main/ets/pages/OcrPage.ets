import { Theme } from '../common/Theme';

@Component
export struct OcrPage {
  build() {
    Stack() {
      Column()
        .width('100%')
        .height('100%')
        .backgroundColor('#0E140D')

      Text('拍照取词 / 从相册选图')
        .fontSize(14)
        .fontColor('#B3FFFFFF')
        .align(Alignment.Top)
        .margin({ top: 28 })

      Stack() {
        Text('将文本放入框内')
          .fontSize(14)
          .fontColor('#B3FFFFFF')
      }
      .width(260)
      .height(260)
      .borderRadius(16)
      .border({ width: 2, color: '#8CFFFFFF' })

      Button()
        .width(64)
        .height(64)
        .borderRadius(32)
        .backgroundColor(Color.White)
        .border({ width: 4, color: Theme.accent })
        .align(Alignment.Bottom)
        .margin({ bottom: 40 })
    }
    .width('100%')
    .height('100%')
    .backgroundColor('#0E140D')
  }
}
