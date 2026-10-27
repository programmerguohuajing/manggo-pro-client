"""
Manggo Pro Client - 全功能桌面客户端入口 (100% 对标并升级原版 Manggo 全特性)
功能矩阵：
1. 连续 3 次空格输入框就地转译 (Manggo Pro 核心特性)
2. 划词悬浮卡片翻译 (Alt+Q - 严格放行 Alt+D)
3. 截图 OCR 离线文字提取与对照翻译 (Alt+W - 严格放行 Alt+X)
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

from core.platform import IS_WINDOWS

if IS_WINDOWS:
    import win32api
    import win32event
    import winerror

from core.hotkeys import normalize_hotkeys
from core.translator import TranslationManager
from core.replacer import InPlaceReplacer, _send_ctrl_c, _send_key, _safe_copy, _release_modifiers, VK_MENU, VK_CONTROL
from core.hook import GlobalKeyboardHook
from core.logging import error as _log_error, info as _log_info
from core.ocr import ocr_engine
from core.database import db

from ui.toast import FloatToast
from ui.float_window import FloatResultWindow
from ui.snipping import SnippingWidget
from ui.voice_window import VoiceInputWindow
from ui.main_window import MainWindow
from ui.history_window import HistoryWindow
from ui.settings_window import SettingsWindow, load_config
from ui.icons import get_app_icon
from ui.tray import TrayManager
from ui.console_window import ConsoleWindow

user32 = ctypes.windll.user32 if IS_WINDOWS else None
kernel32 = ctypes.windll.kernel32 if IS_WINDOWS else None
if IS_WINDOWS:
    user32.GetClipboardSequenceNumber.restype = ctypes.c_ulong

from core.paths import data_file as _data_file

PID_FILE = _data_file(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".app.pid"))

def force_activate_window(win):
    """确保指定窗口在 Windows 上从后台、最小化或遮挡状态强制置顶并获得焦点"""
    if not win:
        return
    win.show()
    win.setWindowState(win.windowState() & ~Qt.WindowMinimized | Qt.WindowActive)
    win.raise_()
    win.activateWindow()
    if IS_WINDOWS:
        try:
            hwnd = int(win.winId())
            user32.ShowWindow(hwnd, 9)  # SW_RESTORE
            user32.SetForegroundWindow(hwnd)
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
        self.console_win = ConsoleWindow()
        self.tray = TrayManager(
            initial_enabled=self.config.get("triple_space_enabled", True) and IS_WINDOWS,
            engine_label=self._engine_label(),
        )

        # 3. 信号绑定
        self._bind_signals()

        # 4. 就地替换引擎 (三次空格)
        self.replacer = InPlaceReplacer(
            translate_func=self.trans_mgr.translate_to_en,
            notify_callback=self._notify_bridge
        )

        # 5. 全局低级键盘热键监听：4 个组合键可在设置页自定义
        # （默认 Alt+Q/W/M/Space），另加连续 3 次空格就地转译。
        self.hook = GlobalKeyboardHook(
            on_triple_space=self.replacer.trigger_triple_space_replace,
            on_selection_translate=self._on_hotkey_selection,
            on_screenshot_translate=self.open_snipping_signal.emit,
            on_voice_input=self.open_voice_signal.emit,
            on_open_main=self.open_main_signal.emit,
            max_interval=self.config.get("max_interval_ms", 750) / 1000.0,
            hotkeys=normalize_hotkeys(self.config.get("hotkeys")),
        )
        self.hook.start()

        # 欢迎提示
        self.toast.show_message("success", "Manggo Pro 全功能已就绪 (双击托盘打开设置, 3次空格转译)")

    def _engine_label(self) -> str:
        if self.config.get("engine") == "llm":
            model = self.config.get("llm_model", "") or ""
            return f"大模型 ({model})" if model else "大模型通道"
        return "内置极速通道"

    def _bind_signals(self):
        # 基础信号槽连接
        self.notify_signal.connect(self.toast.show_message)
        self.selection_translate_signal.connect(self._do_selection_translate)
        self.ocr_translate_signal.connect(self._do_ocr_translate)
        self.open_main_signal.connect(lambda: force_activate_window(self.main_win))
        self.open_snipping_signal.connect(self._on_snipping_requested)
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
        self.tray.open_console_requested.connect(lambda: force_activate_window(self.console_win))
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

    def _on_snipping_requested(self):
        _release_modifiers()
        self.snipping_widget.start_snipping()

    def _notify_bridge(self, status: str, message: str):
        self.notify_signal.emit(status, message)

    def _on_hotkey_selection(self):
        if not IS_WINDOWS:
            self.notify_signal.emit("failed", "划选翻译仅支持 Windows")
            return
        # 划词翻译：彻底释放物理与逻辑修饰键，防止发送的 Ctrl+C 被识别为 Alt+Ctrl+C
        time.sleep(0.04)
        _release_modifiers()
        time.sleep(0.03)

        old_seq = user32.GetClipboardSequenceNumber()
        _send_ctrl_c()

        # 只认序号变化后的剪贴板：Ctrl+C 没让剪贴板变化，说明这次
        # 根本没复制到选中文字。绝不能兜底读当前剪贴板——那是旧内容
        # （比如之前复制过的 "Test"），会被当成选中文字翻译出来，
        # 正是本次“译的不是选中文字”的根因。抓不到就老实报错，
        # 让失败可诊断，而不是拿旧剪贴板冒充成功。
        captured = ""
        start = time.time()
        while time.time() - start < 0.8:
            if user32.GetClipboardSequenceNumber() != old_seq:
                try:
                    captured = pyperclip.paste().strip()
                except Exception:
                    pass
                break
            time.sleep(0.02)

        if captured:
            _log_info("APP", f"[SELECTION] Captured: {repr(captured[:30])}")
            self.selection_translate_signal.emit(captured)
        else:
            _log_info("APP", "[SELECTION] Failed: clipboard unchanged after Ctrl+C")
            self.notify_signal.emit("failed", "未检测到鼠标选中文本")

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
        try:
            trans_res = self.trans_mgr.translate(ocr_text)
        except Exception:
            # 翻译失败也要把常驻的 translating 提示换掉，否则同样挂着不消失。
            self.notify_signal.emit("failed", "翻译失败，请检查网络或参数")
            return
        self.float_win.display("截图 OCR 翻译", ocr_text, trans_res, source_type="ocr")
        # 结果窗已出，常驻的“正在进行 OCR 文字提取...”必须在这里关闭；
        # 之前成功这路什么都没发，提示就永远挂在右下角。
        self.toast.dismiss()

    @Slot(bool)
    def _on_toggle_hook(self, enabled: bool):
        if not IS_WINDOWS:
            self.tray.set_enabled(False)
            self.toast.show_message("error", "快捷转译仅支持 Windows")
            return
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
        # 组合键改动即时生效：只重建判定表，不用重启钩子线程；
        # 钩子暂停中（托盘暂停）改的键，恢复时按新表工作。
        self.hook.update_hotkeys(new_cfg.get("hotkeys"))
        self.tray.set_engine_label(self._engine_label())

    def quit_app(self):
        self.hook.stop()
        try:
            if os.path.exists(PID_FILE):
                os.remove(PID_FILE)
        except Exception:
            pass
        self.app.quit()

def _is_admin() -> bool:
    if not IS_WINDOWS:
        return False
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def check_admin_elevation():
    """
    检查并提升为管理员权限，确保能穿透注入按键到 Claude 桌面端等管理员应用中 (Windows UIPI 限制)
    """
    if not IS_WINDOWS:
        return
    try:
        if not _is_admin():
            # 打包版直接拉起 exe 本身，不需要传脚本路径：原来传的
            # __file__ 在打包后指向 _internal 里不存在的 .py 路径，
            # 虽然启动器会忽略多余参数，但传一个不存在的路径本身就是错的；
            # 源码运行才需要把 main.py 路径当参数传给 python.exe。
            if getattr(sys, "frozen", False):
                params = None
            else:
                params = f'"{os.path.abspath(__file__)}"'
            res = ctypes.windll.shell32.ShellExecuteW(
                None, "runas", sys.executable, params, None, 1
            )
            # 提权结果必须记日志：之前这一步是黑盒，双击没起来时
            # 根本不知道是 UAC 被拒、runas 失败，还是子进程没起来。
            _log_info("APP", f"elevation: not admin, runas res={res} (>32 means child spawned)")
            if res > 32:
                sys.exit(0)
            _log_info("APP", "elevation: runas did not spawn a child, continuing non-elevated")
        else:
            _log_info("APP", "elevation: already admin, no relaunch")
    except Exception as e:
        _log_info("APP", f"elevation: check failed ({e}), continuing non-elevated")

def main():
    # 异常钩子必须在提权之前就装好：提权、互斥、PID 任何一步崩了，
    # 都要落在 debug_app.log 里，而不是静默死掉让用户猜。
    def _uncaught(exc_type, exc_val, exc_tb):
        import traceback
        err = "".join(traceback.format_exception(exc_type, exc_val, exc_tb))
        _log_error("APP", f"UNCAUGHT EXCEPTION:\n{err}")
    sys.excepthook = _uncaught

    check_admin_elevation()

    # 智能单实例管理：Windows 用互斥体 + 终结旧进程；其他平台用 PID 存活检查。
    if IS_WINDOWS:
        mutex = win32event.CreateMutex(None, False, "ManggoProClient_SingleInstance_Mutex")
        if win32api.GetLastError() == winerror.ERROR_ALREADY_EXISTS:
            if os.path.exists(PID_FILE):
                try:
                    with open(PID_FILE, "r") as f:
                        old_pid = int(f.read().strip())
                    if old_pid != os.getpid():
                        h_proc = kernel32.OpenProcess(0x0001, False, old_pid)
                        if h_proc:
                            kernel32.TerminateProcess(h_proc, 0)
                            kernel32.CloseHandle(h_proc)
                            time.sleep(0.2)
                except Exception:
                    pass
            # 重新创建互斥体
            if mutex:
                win32api.CloseHandle(mutex)
            mutex = win32event.CreateMutex(None, False, "ManggoProClient_SingleInstance_Mutex")
    else:
        mutex = None
        if os.path.exists(PID_FILE):
            try:
                with open(PID_FILE, "r") as f:
                    old_pid = int(f.read().strip())
                if old_pid != os.getpid():
                    os.kill(old_pid, 0)
                    print("已有实例在运行，退出。")
                    return
            except ProcessLookupError:
                pass  # 旧 PID 已不存在，视为残留文件，继续启动并覆盖
            except Exception:
                pass

    # 记录当前进程 PID
    try:
        with open(PID_FILE, "w") as f:
            f.write(str(os.getpid()))
    except Exception:
        pass

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app.setWindowIcon(get_app_icon())

    coordinator = AppCoordinator(app)
    # 启动里程碑：托盘已建、钩子已起。双击没起来时，看日志有没有
    # 这一行就能区分“死在提权/启动早期”还是“起来了但托盘图标没看见”。
    _log_info("APP", f"started: admin={_is_admin()}, tray up, entering event loop")
    exit_code = app.exec()

    try:
        if os.path.exists(PID_FILE):
            os.remove(PID_FILE)
    except Exception:
        pass

    if mutex:
        win32api.CloseHandle(mutex)
    sys.exit(exit_code)

if __name__ == "__main__":
    main()
