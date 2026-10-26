"""
Manggo Pro Client - 全功能桌面客户端入口
包含：主翻译工作台、截图 OCR 翻译 (Alt+W)、划词悬浮翻译 (Alt+Q)、
连续三次空格输入框就地转译、生词本与历史记录、离线 TTS 朗读。
"""
import sys
import os
import time
import threading
from PySide6.QtCore import QObject, Signal, Slot
from PySide6.QtWidgets import QApplication
import pyperclip
import win32api
import win32con

from core.translator import TranslationManager
from core.replacer import InPlaceReplacer, _send_ctrl_c
from core.hook import GlobalKeyboardHook
from core.ocr import ocr_engine
from core.database import db

from ui.toast import FloatToast
from ui.float_window import FloatResultWindow
from ui.snipping import SnippingWidget
from ui.main_window import MainWindow
from ui.history_window import HistoryWindow
from ui.settings_window import SettingsWindow, load_config
from ui.tray import TrayManager

class AppCoordinator(QObject):
    # 跨线程信号
    notify_signal = Signal(str, str)
    selection_translate_signal = Signal(str)
    ocr_translate_signal = Signal(str)
    open_main_signal = Signal()
    open_snipping_signal = Signal()

    def __init__(self, app: QApplication):
        super().__init__()
        self.app = app
        self.config = load_config()

        # 1. 翻译管理器
        self.trans_mgr = TranslationManager(self.config)

        # 2. UI 组件初始化
        self.toast = FloatToast()
        self.float_win = FloatResultWindow()
        self.snipping_widget = SnippingWidget()
        self.main_win = MainWindow(self.trans_mgr)
        self.history_win = HistoryWindow()
        self.settings_win = SettingsWindow()
        self.tray = TrayManager(initial_enabled=self.config.get("triple_space_enabled", True))

        # 3. 信号绑定
        self._bind_signals()

        # 4. 就地替换引擎 (三次空格)
        self.replacer = InPlaceReplacer(
            translate_func=self.trans_mgr.translate_to_en,
            notify_callback=self._notify_bridge
        )

        # 5. 全局低级键盘热键监听 (三次空格, Alt+Q, Alt+W, Alt+D)
        self.hook = GlobalKeyboardHook(
            on_triple_space=self.replacer.trigger_triple_space_replace,
            on_selection_translate=self._on_hotkey_selection,
            on_screenshot_translate=self.open_snipping_signal.emit,
            on_open_main=self.open_main_signal.emit,
            max_interval=self.config.get("max_interval_ms", 550) / 1000.0
        )
        self.hook.start()

        # 欢迎提示
        self.toast.show_message("success", "Manggo Pro 全功能已就绪 (Alt+W 截图, Alt+Q 划词, 3次空格转译)")

    def _bind_signals(self):
        # 信号槽连接
        self.notify_signal.connect(self.toast.show_message)
        self.selection_translate_signal.connect(self._do_selection_translate)
        self.ocr_translate_signal.connect(self._do_ocr_translate)
        self.open_main_signal.connect(self._show_main_win)
        self.open_snipping_signal.connect(self.snipping_widget.start_snipping)

        # 截图完成送入 OCR
        self.snipping_widget.screenshot_captured.connect(self._handle_screenshot)

        # 托盘与窗口联动
        self.tray.open_main_requested.connect(self._show_main_win)
        self.tray.open_snipping_requested.connect(self.snipping_widget.start_snipping)
        self.tray.open_history_requested.connect(self.history_win.show)
        self.tray.open_settings_requested.connect(self.settings_win.show)
        self.tray.toggle_triple_space_requested.connect(self._on_toggle_hook)
        self.tray.exit_requested.connect(self.quit_app)

        # 主窗口内部按钮联动
        self.main_win.request_snipping.connect(self.snipping_widget.start_snipping)
        self.main_win.request_history.connect(self.history_win.show)
        self.main_win.request_settings.connect(self.settings_win.show)

        # 配置变更
        self.settings_win.config_changed.connect(self._on_config_changed)

    def _notify_bridge(self, status: str, message: str):
        self.notify_signal.emit(status, message)

    def _on_hotkey_selection(self):
        # 触发划词翻译：先模拟 Ctrl+C 读取选区
        original_clip = ""
        try:
            original_clip = pyperclip.paste()
        except Exception:
            pass

        sentinel = f"__MANGGO_SEL_{time.time()}__"
        pyperclip.copy(sentinel)
        time.sleep(0.02)
        _send_ctrl_c()
        time.sleep(0.05)

        captured = pyperclip.paste()
        if captured and captured != sentinel:
            self.selection_translate_signal.emit(captured.strip())
        else:
            self.notify_signal.emit("failed", "未检测到已选中文本")

        # 恢复剪贴板
        time.sleep(0.4)
        try:
            pyperclip.copy(original_clip)
        except Exception:
            pass

    @Slot(str)
    def _do_selection_translate(self, text: str):
        if not text:
            return
        trans_res = self.trans_mgr.translate(text)
        self.float_win.display("划词翻译", text, trans_res, source_type="selection")

    def _handle_screenshot(self, pil_img):
        # 异步执行 OCR 与翻译，避免卡顿
        threading.Thread(target=self._ocr_worker, args=(pil_img,), daemon=True).start()

    def _ocr_worker(self, pil_img):
        self.notify_signal.emit("translating", "正在进行 OCR 文字提取...")
        text = ocr_engine.recognize_image(pil_img)
        clean = text.strip()
        if not clean:
            self.notify_signal.emit("failed", "未能在截图区域中识别到有效文字")
            return
        self.ocr_translate_signal.emit(clean)

    @Slot(str)
    def _do_ocr_translate(self, ocr_text: str):
        trans_res = self.trans_mgr.translate(ocr_text)
        self.float_win.display("截图 OCR 翻译", ocr_text, trans_res, source_type="ocr")

    @Slot()
    def _show_main_win(self):
        self.main_win.show()
        self.main_win.raise_()
        self.main_win.activateWindow()

    @Slot(bool)
    def _on_toggle_hook(self, enabled: bool):
        if enabled:
            self.hook.start()
            self.toast.show_message("success", "快捷转译已恢复")
        else:
            self.hook.stop()
            self.toast.show_message("error", "快捷转译已暂停")

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
    app.setQuitOnLastWindowClosed(False)

    coordinator = AppCoordinator(app)
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
