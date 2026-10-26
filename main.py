"""
Manggo Pro Client - 主程序入口
支持连续三次空格在任意输入框中将中文就地转译为英文
"""
import sys
import os
from PySide6.QtCore import QObject, Signal, Slot
from PySide6.QtWidgets import QApplication

from core.translator import TranslationManager
from core.replacer import InPlaceReplacer
from core.hook import GlobalKeyboardHook
from ui.toast import FloatToast
from ui.settings_window import SettingsWindow, load_config
from ui.tray import TrayManager

class AppCoordinator(QObject):
    notify_signal = Signal(str, str)

    def __init__(self, app: QApplication):
        super().__init__()
        self.app = app
        self.config = load_config()

        # 1. 翻译管理器
        self.trans_mgr = TranslationManager(self.config)

        # 2. 悬浮状态通知 (Toast)
        self.toast = FloatToast()
        self.notify_signal.connect(self._on_notify)

        # 3. 就地转译核心处理器
        self.replacer = InPlaceReplacer(
            translate_func=self.trans_mgr.translate_to_en,
            notify_callback=self._notify_bridge
        )

        # 4. 全局键盘钩子 (监听连续 3 次空格)
        self.hook = GlobalKeyboardHook(
            on_triple_space=self._on_triple_space,
            max_interval=self.config.get("max_interval_ms", 550) / 1000.0
        )
        if self.config.get("triple_space_enabled", True):
            self.hook.start()

        # 5. 设置窗口
        self.settings_win = SettingsWindow()
        self.settings_win.config_changed.connect(self._on_config_changed)

        # 6. 系统托盘
        self.tray = TrayManager(initial_enabled=self.config.get("triple_space_enabled", True))
        self.tray.open_settings_requested.connect(self.settings_win.show)
        self.tray.toggle_triple_space_requested.connect(self._on_toggle_hook)
        self.tray.exit_requested.connect(self.quit_app)

        # 启动提示
        self.toast.show_message("success", "Manggo Pro 转译助手已就绪 (连按 3 次空格触发)")

    def _notify_bridge(self, status: str, message: str):
        # 跨线程投递到 Qt 主线程
        self.notify_signal.emit(status, message)

    @Slot(str, str)
    def _on_notify(self, status: str, message: str):
        self.toast.show_message(status, message)

    def _on_triple_space(self):
        # 触发就地转译替换
        self.replacer.trigger_triple_space_replace()

    @Slot(bool)
    def _on_toggle_hook(self, enabled: bool):
        if enabled:
            self.hook.start()
            self.toast.show_message("success", "已开启三次空格转译")
        else:
            self.hook.stop()
            self.toast.show_message("error", "已暂停快捷转译")

    @Slot(dict)
    def _on_config_changed(self, new_cfg: dict):
        self.config = new_cfg
        self.trans_mgr.update_config(new_cfg)
        self.hook.max_interval = new_cfg.get("max_interval_ms", 550) / 1000.0

    def quit_app(self):
        self.hook.stop()
        self.app.quit()

def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)  # 保持托盘常驻

    coordinator = AppCoordinator(app)
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
