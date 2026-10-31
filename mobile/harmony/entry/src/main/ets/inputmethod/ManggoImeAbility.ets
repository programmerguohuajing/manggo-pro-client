import { InputMethodExtensionAbility, InputClient, inputMethodEngine, panel } from '@kit.IMEKit';
import { Want } from '@kit.AbilityKit';
import { ImeBridge } from './ImeBridge';

/**
 * Manggo 翻译输入法（HarmonyOS NEXT）。
 *
 * 与 Android 的 ManggoImeService、iOS 的 KeyboardViewController 对应：
 * 软键盘界面由 pages/KeyboardPanel 绘制，本 Ability 只负责
 * 1) 接住系统给的 InputClient（读写输入框内容的唯一通道）
 * 2) 创建软键盘面板并挂上 ArkUI 页面
 *
 * 启用路径：设置 → 系统 → 输入法 → 更多输入法 → 启用「Manggo 翻译键盘」，
 * 再切到它。
 */
export default class ManggoImeAbility extends InputMethodExtensionAbility {
  private keyboardPanel: panel.Panel | undefined = undefined;
  // 类型由 getInputMethodAbility() 推断，避免不同 SDK 版本里类型名不一致
  private inputMethodAbility = inputMethodEngine.getInputMethodAbility();

  onCreate(want: Want): void {
    // 输入框获得焦点时系统下发 InputClient；失去焦点时回收
    this.inputMethodAbility.on('inputStart', (client: InputClient) => {
      ImeBridge.getInstance().attach(client);
      ImeBridge.getInstance().status('空格 ×3 翻译这一段');
    });
    this.inputMethodAbility.on('inputStop', (client: InputClient) => {
      ImeBridge.getInstance().detach();
    });

    const panelInfo: panel.PanelInfo = {
      type: panel.PanelType.SOFT_KEYBOARD
    };
    this.keyboardPanel = panel.createPanel(this.context, panelInfo);
    this.keyboardPanel.setUiContent('pages/KeyboardPanel');
  }

  onDestroy(): void {
    if (this.keyboardPanel !== undefined) {
      this.keyboardPanel.destroy();
      this.keyboardPanel = undefined;
    }
    ImeBridge.getInstance().detach();
  }
}
