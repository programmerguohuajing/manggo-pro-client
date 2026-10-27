"""
Manggo Pro Client - 全功能桌面客户端入口 (100% 对标并升级原版 Manggo 全特性)
功能矩阵：
1. 连续 3 次空格输入框就地转译 (Manggo Pro 核心特性)
2. 划词悬浮卡片翻译 (Alt+D / Alt+Q)
3. 截图 OCR 离线文字提取与对照翻译 (Alt+X / Alt+W)
4. 语音听写输入 / 实时语音转文字 (Alt+Space)
5. 沉浸式双栏桌面翻译工作台 (Alt+Shift+D)
6. 离线语音合成朗读 (SAPI TTS)
7. 历史记录与生词本 (无缝同步原版数据)
8. 现代化侧栏卡片式偏好设置中心 (双击系统托盘)
"""
import sys
import os
import time
import threading
import ctypes
from PySide6.QtCore import Qt, QObject, Signal, Slot
from PySide6.QtWidgets import QApplication, QMessageBox
import pyperclip
import win32event
import win32api
import winerror

from core.translator import TranslationManager
from core.replacer import InPlaceReplacer, _send_ctrl_c, _send_key, _safe_copy, _safe_paste, VK_MENU
from core.hook import GlobalKeyboardHook
from core.ocr import ocr_engine
from core.database import db

from ui.toast import FloatToast
from ui.float_window import FloatResultWindow
from ui.snipping import SnippingWidget
from ui.voice_window import VoiceInputWindow
from ui.main_window import MainWindow
from ui.history_window import HistoryWindow
from ui.settings_window import SettingsWindow, load_config
from ui.tray import TrayManager

def force_activate_window(win):
    """确保指定窗口在 Windows 上从后台、最小化或遮挡状态强制置顶并获得焦点"""
    if not win:
        return
    win.show()
    win.setWindowState(win.windowState() & ~Qt.WindowMinimized | Qt.WindowActive)
    win.raise_()
    win.activateWindow()
    try:
        hwnd = int(win.winId())
        ctypes.windll.user32.ShowWindow(hwnd, 9)  # SW_RESTORE
        ctypes.windll.user32.SetForegroundWindow(hwnd)
    except Exception:
        pass

class AppCoordinator(QObject):
    # 跨线程信号
    notify_signal = Signal(str, str)
    selection_translate_signal = Signal(str)
    ocr_translate_signal = Signal(str)
    open_main_signal = Signal()
    open_snipping_signal = Signal()
    open_voice_signal = Signal()

    def __init__(self, app: QApplication):
        super().__init__()
        self.app = app
        self.config = load_config()

        # 1. 翻译管理器
        self.trans_mgr = TranslationManager(self.config)

        # 2. UI 组件全矩阵初始化
        self.toast = FloatToast()
        self.float_win = FloatResultWindow()
        self.snipping_widget = SnippingWidget()
        self.voice_win = VoiceInputWindow()
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

        # 5. 全局低级键盘热键监听 (全面支持原版 Manggo 键位: Alt+D, Alt+X, Alt+Space, Alt+Shift+D, 3次空格)
        self.hook = GlobalKeyboardHook(
            on_triple_space=self.replacer.trigger_triple_space_replace,
            on_selection_translate=self._on_hotkey_selection,
            on_screenshot_translate=self.open_snipping_signal.emit,
            on_voice_input=self.open_voice_signal.emit,
            on_open_main=self.open_main_signal.emit,
            max_interval=self.config.get("max_interval_ms", 750) / 1000.0
        )
        self.hook.start()

        # 欢迎提示
        self.toast.show_message("success", "Manggo Pro 全功能已就绪 (双击托盘打开设置, 3次空格转译)")

    def _bind_signals(self):
        # 基础信号槽连接
        self.notify_signal.connect(self.toast.show_message)
        self.selection_translate_signal.connect(self._do_selection_translate)
        self.ocr_translate_signal.connect(self._do_ocr_translate)
        self.open_main_signal.connect(lambda: force_activate_window(self.main_win))
        self.open_snipping_signal.connect(self.snipping_widget.start_snipping)
        self.open_voice_signal.connect(self.voice_win.start_listening)

        # 截图完成送入 OCR
        self.snipping_widget.screenshot_captured.connect(self._handle_screenshot)

        # 托盘与窗口联动 (100% 对齐原版功能)
        self.tray.open_main_requested.connect(lambda: force_activate_window(self.main_win))
        self.tray.open_selection_requested.connect(self._on_hotkey_selection)
        self.tray.open_snipping_requested.connect(self.snipping_widget.start_snipping)
        self.tray.open_voice_requested.connect(self.voice_win.start_listening)
        self.tray.open_history_requested.connect(lambda: force_activate_window(self.history_win))
        self.tray.open_settings_requested.connect(lambda: force_activate_window(self.settings_win))
        self.tray.toggle_triple_space_requested.connect(self._on_toggle_hook)
        self.tray.exit_requested.connect(self.quit_app)

        # 主窗口内部按钮联动
        self.main_win.request_snipping.connect(self.snipping_widget.start_snipping)
        self.main_win.request_history.connect(lambda: force_activate_window(self.history_win))
        self.main_win.request_settings.connect(lambda: force_activate_window(self.settings_win))

        # 设置窗口跳转联动
        self.settings_win.open_main_requested.connect(lambda: force_activate_window(self.main_win))

        # 配置变更
        self.settings_win.config_changed.connect(self._on_config_changed)

    def _notify_bridge(self, status: str, message: str):
        self.notify_signal.emit(status, message)

    def _on_hotkey_selection(self):
        # 划词翻译：首先强制将 Alt/Ctrl 物理修饰键置为抬起状态，防止发送的 Ctrl+C 被操作系统或 Claude 识别为 Alt+Ctrl+C
        _send_key(VK_MENU, is_up=True)
        time.sleep(0.06)

        original_clip = ""
        try:
            original_clip = pyperclip.paste()
        except Exception:
            pass

        sentinel = f"__MANGGO_SEL_{time.time()}__"
        _safe_copy(sentinel)
        time.sleep(0.02)
        _send_ctrl_c()
        time.sleep(0.08)

        captured = _safe_paste(timeout=0.45, ignore_val=sentinel)
        if captured and captured != sentinel:
            self.selection_translate_signal.emit(captured.strip())
        else:
            self.notify_signal.emit("failed", "未检测到鼠标选中文本")

        # 延迟恢复剪贴板
        time.sleep(0.5)
        _safe_copy(original_clip)

    @Slot(str)
    def _do_selection_translate(self, text: str):
        if not text:
            return
        trans_res = self.trans_mgr.translate(text)
        self.float_win.display("划词翻译", text, trans_res, source_type="selection")

    def _handle_screenshot(self, pil_img):
        # 异步执行 OCR 与翻译，避免卡顿界面
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
    def _uncaught(exc_type, exc_val, exc_tb):
        import traceback
        err = "".join(traceback.format_exception(exc_type, exc_val, exc_tb))
        try:
            with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "debug_app.log"), "a", encoding="utf-8") as f:
                f.write(f"[{time.strftime('%H:%M:%S')}] UNCAUGHT EXCEPTION:\n{err}\n")
        except Exception:
            pass
    sys.excepthook = _uncaught

    # 会话级互斥体，防止重复启动冲突
    mutex = win32event.CreateMutex(None, False, "ManggoProClient_SingleInstance_Mutex")
    if win32api.GetLastError() == winerror.ERROR_ALREADY_EXISTS:
        sys.exit(0)

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    coordinator = AppCoordinator(app)
    exit_code = app.exec()

    if mutex:
        win32api.CloseHandle(mutex)
    sys.exit(exit_code)

if __name__ == "__main__":
    main()
