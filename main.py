"""
Manggo Pro Client - 全功能桌面客户端入口 (100% 对标并升级原版 Manggo 全特性)
功能矩阵：
1. 连续 3 次空格输入框就地转译 (Manggo Pro 核心特性)
2. 划词悬浮卡片翻译 (Alt+Q - 严格放行 Alt+D)
3. 截图 OCR 离线文字提取与对照翻译 (Alt+W - 严格放行 Alt+X)
4. 语音听写输入 / 实时语音转文字 (Alt+Space)
5. 沉浸式双栏桌面翻译工作台 (Alt+M)
6. 离线语音合成朗读 (SAPI TTS)
7. 历史记录与生词本 (无缝同步原版数据)
8. 现代化侧栏卡片式偏好设置中心 (双击系统托盘)
"""
import sys
import os
import time
import threading
import ctypes

# 阶段日志：从进程第一毫秒就写，写到 %TEMP%（任何用户都可写，
# 不依赖程序目录/用户目录是否可写）。用途：双击没起来时，现有
# debug_app.log 里经常一行都没有（卡在 import 或提权里，日志模块
# 还没机会写），看这个文件最后一行就知道卡在哪一步。
def _stage(msg: str):
    try:
        path = os.path.join(os.environ.get("TEMP") or os.path.expanduser("~"), "ManggoProClient-startup.log")
        with open(path, "a", encoding="utf-8") as f:
            f.write(f"[{time.strftime('%H:%M:%S')}] pid={os.getpid()} {msg}\n")
    except Exception:
        # 兜底调试日志写失败：它本身就是 fallback，失败时无处可记，只能静默。
        pass

_stage("main-enter")

from PySide6.QtCore import Qt, QObject, Signal, Slot
from PySide6.QtWidgets import QApplication, QMessageBox
_stage("import-pyside6-done")
import pyperclip
_stage("import-pyperclip-done")

from core.platform import IS_WINDOWS, IS_MAC, IS_LINUX

if IS_WINDOWS:
    import win32api
    import win32event
    import winerror
_stage("import-win32-done")

from core.hotkeys import normalize_hotkeys
_stage("import-hotkeys-done")
from core.translator import TranslationManager
_stage("import-translator-done")
from core.replacer import InPlaceReplacer, _send_ctrl_c_input, _release_modifiers, VK_MENU, VK_CONTROL, VK_SHIFT
from core.autostart import is_autostart_enabled, set_autostart_enabled
from core.version import get_channel, get_version
_stage("import-replacer-done")
from core.hook import GlobalKeyboardHook, hook_self_check
from core.hook_macos import MacKeyboardHook, post_cmd_key, is_accessibility_trusted
from core.replacer_macos import MacReplacer
from core.hook_linux import LinuxKeyboardHook, xtest_ctrl_key, open_display
from core.replacer_linux import LinuxReplacer
_stage("import-hook-done")
from core.logging import error as _log_error, info as _log_info
_stage("import-logging-done")
from core.ocr import ocr_engine
_stage("import-ocr-done")
from core.database import db
_stage("import-database-done")

from ui.toast import FloatToast
from ui.float_window import FloatResultWindow
from ui.snipping import SnippingWidget
from ui.voice_window import VoiceInputWindow
_stage("import-ui-early-done")
from ui.main_window import MainWindow
from ui.history_window import HistoryWindow
from ui.settings_window import SettingsWindow, load_config
from ui.icons import get_app_icon
from ui.tray import TrayManager
from ui.console_window import ConsoleWindow
_stage("import-ui-late-done")

_stage("imports-done")

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
        except Exception as e:
            _log_info("APP", f"bring window to front failed: {e}")

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
        # 后台翻译线程持有列表（见 ui/translate_worker.start_translate）。
        self._translate_workers = []

        # 2. UI 组件全矩阵初始化
        self.toast = FloatToast()
        # 配置文件损坏时 load_config 已备份并记下路径，这里提示一次
        # （备份里能找回 Key 与热键，不要静默用默认值把用户蒙过去）。
        from ui import settings_window as _settings_mod

        if getattr(_settings_mod, "CONFIG_CORRUPT_BACKUP", None):
            self.toast.show_message(
                "failed",
                f"配置文件损坏，已用默认值启动，旧文件已备份：{_settings_mod.CONFIG_CORRUPT_BACKUP}",
            )
            _settings_mod.CONFIG_CORRUPT_BACKUP = None
        self.float_win = FloatResultWindow()
        self.snipping_widget = SnippingWidget()
        self.voice_win = VoiceInputWindow()
        self.main_win = MainWindow(self.trans_mgr, hotkeys=self.config.get("hotkeys"))
        self.history_win = HistoryWindow()
        self.settings_win = SettingsWindow()
        self.console_win = ConsoleWindow()
        self.tray = TrayManager(
            initial_enabled=self.config.get("triple_space_enabled", True) and (IS_WINDOWS or IS_MAC or IS_LINUX),
            engine_label=self._engine_label(),
            hotkeys=self.config.get("hotkeys"),
        )

        # 3. 信号绑定
        self._bind_signals()

        # 4. 就地替换引擎 (三次空格)：macOS 用 Cmd 系，Linux 用 Ctrl 系。
        if IS_MAC:
            self.replacer = MacReplacer(
                translate_func=self.trans_mgr.translate_to_en,
                notify_callback=self._notify_bridge
            )
        elif IS_LINUX:
            self.replacer = LinuxReplacer(
                translate_func=self.trans_mgr.translate_to_en,
                notify_callback=self._notify_bridge
            )
        else:
            self.replacer = InPlaceReplacer(
                translate_func=self.trans_mgr.translate_to_en,
                notify_callback=self._notify_bridge
            )

        # 5. 全局键盘热键监听：Windows 用低级钩子（4 个组合键），
        # macOS 用 CGEventTap（首批范围：三次空格 + Alt+Q/W；workbench/
        # voice 不接，对应组合键直接放行不吞键）。
        if IS_MAC:
            self.hook = MacKeyboardHook(
                on_triple_space=self.replacer.trigger_triple_space_replace,
                on_selection_translate=self._on_hotkey_selection,
                on_screenshot_translate=self.open_snipping_signal.emit,
                on_voice_input=None,
                on_open_main=None,
                max_interval=self.config.get("max_interval_ms", 750) / 1000.0,
                hotkeys=normalize_hotkeys(self.config.get("hotkeys")),
            )
        elif IS_LINUX:
            # Linux 首批范围与 macOS 相同：三次空格 + Alt+Q/W。
            self.hook = LinuxKeyboardHook(
                on_triple_space=self.replacer.trigger_triple_space_replace,
                on_selection_translate=self._on_hotkey_selection,
                on_screenshot_translate=self.open_snipping_signal.emit,
                on_voice_input=None,
                on_open_main=None,
                max_interval=self.config.get("max_interval_ms", 750) / 1000.0,
                hotkeys=normalize_hotkeys(self.config.get("hotkeys")),
            )
        else:
            self.hook = GlobalKeyboardHook(
                on_triple_space=self.replacer.trigger_triple_space_replace,
                on_selection_translate=self._on_hotkey_selection,
                on_screenshot_translate=self.open_snipping_signal.emit,
                on_voice_input=self.open_voice_signal.emit,
                on_open_main=self.open_main_signal.emit,
                max_interval=self.config.get("max_interval_ms", 750) / 1000.0,
                hotkeys=normalize_hotkeys(self.config.get("hotkeys")),
            )
        # 1.0.17 自检：装钩子之前先证明钩子不会吞键（1.0.15 的教训）。
        # 自检失败 → 拒绝装钩子（宁可热键不用，也不能让用户打不出字），
        # 原因写进日志并弹提示；通过才 start，并记下安装结果。
        _log_info("APP", f"startup version={get_version()} channel={get_channel()}")
        if IS_MAC:
            # macOS：抽头创建本身就是权限自检（CGEventTapCreate 为 NULL
            # 即缺辅助功能/输入监控权限），失败时不静默，直接报原因。
            if self.hook.start():
                _log_info("HOOK", "mac event tap started")
                self.toast.show_message("success", "Manggo Pro 已就绪 · 全局热键已启用（双击托盘打开设置，3次空格转译）")
            else:
                _log_error("HOOK", f"mac hook NOT started: {self.hook.last_error}")
                self.toast.show_message("failed", f"全局热键未能启用：{self.hook.last_error}")
                self.tray.set_enabled(False)
        elif IS_LINUX:
            # Linux：start() 内已做 Wayland/DISPLAY/Xlib 校验，失败原因
            # 直接报出来（Wayland 会话、缺 X、无 python-xlib 都不静默）。
            if self.hook.start():
                _log_info("HOOK", "linux X11 hook started")
                self.toast.show_message("success", "Manggo Pro 已就绪 · 全局热键已启用（双击托盘打开设置，3次空格转译）")
            else:
                _log_error("HOOK", f"linux hook NOT started: {self.hook.last_error}")
                self.toast.show_message("failed", f"全局热键未能启用：{self.hook.last_error}")
                self.tray.set_enabled(False)
        else:
            _ok, _detail = hook_self_check(self.hook)
            if _ok:
                self.hook.start()
                _log_info(
                    "HOOK",
                    f"self-check OK ({_detail}); start done: running={self.hook._running} "
                    f"hook_id={self.hook.hook_id} "
                    f"thread_alive={self.hook._thread.is_alive() if self.hook._thread else False}",
                )
                self.toast.show_message("success", "Manggo Pro 已就绪 · 钩子自检通过（双击托盘打开设置，3次空格转译）")
            else:
                _log_error("HOOK", f"SELF-CHECK FAILED, hook NOT started: {_detail}")
                self.toast.show_message("failed", f"钩子自检失败，已禁用快捷转译以保护输入：{_detail}")

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
        self.snipping_widget.snipping_failed.connect(lambda msg: self.notify_signal.emit("failed", msg))

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
        # 与划选翻译同理：等用户真正松开修饰键再开始截图，不注入
        # Alt 抬起（会触发目标程序的菜单模式）。
        if not _wait_modifiers_released(timeout=0.6):
            _release_modifiers()
        self.snipping_widget.start_snipping()

    def _notify_bridge(self, status: str, message: str):
        self.notify_signal.emit(status, message)

    def _on_hotkey_selection(self):
        if IS_MAC:
            # macOS：合成事件是 Cmd 系，与 Option 触发键不冲突，无需等修饰键松开；
            # 剪贴板无序号，改用“先清空再等非空”判断复制成功（避免旧剪贴板冒充）。
            # 全程打日志：此前只有成功才记一行，失败时控制台一片空白，
            # 看日志无从分辨是授权、投递还是剪贴板坏了（用户实测反馈）。
            trusted = is_accessibility_trusted()
            _log_info("APP", f"[SELECTION] mac capture start, accessibility_trusted={trusted}")
            captured = ""
            for attempt in (1, 2):
                if attempt == 2:
                    time.sleep(0.1)
                try:
                    pyperclip.copy("")
                except Exception as e:
                    _log_error("APP", f"[SELECTION] clipboard clear failed: {e}")
                time.sleep(0.02)
                try:
                    post_ok = post_cmd_key("C")
                except Exception as e:
                    post_ok = False
                    _log_error("APP", f"[SELECTION] post Cmd+C raised: {e}")
                start = time.time()
                while time.time() - start < 0.8:
                    try:
                        text = pyperclip.paste().strip()
                    except Exception:
                        text = ""
                    if text:
                        captured = text
                        break
                    time.sleep(0.02)
                _log_info("APP", f"[SELECTION] attempt {attempt}: post_ok={post_ok}, clipboard={len(captured)} chars")
                if captured:
                    break
            if captured:
                _log_info("APP", f"[SELECTION] Captured: {len(captured)} chars")
                self.selection_translate_signal.emit(captured)
            else:
                _log_error("APP", f"[SELECTION] mac capture failed, accessibility_trusted={trusted}")
                self.notify_signal.emit("failed", "未检测到鼠标选中文本")
            return
        if IS_LINUX:
            # Linux：XTest 合成 Ctrl+C（与 macOS 同款“先清空再等非空”）；
            # 剪贴板本身坏了（缺 xclip/xsel）时直接明说，不走误导的轮询。
            try:
                pyperclip.copy("")
            except Exception:
                self.notify_signal.emit("failed", "Linux 剪贴板需要 xclip 或 xsel（例如：sudo apt install xclip）")
                return
            dpy = open_display()
            if dpy is None:
                self.notify_signal.emit("failed", "无法连接 X 服务器")
                return
            captured = ""
            try:
                for attempt in (1, 2):
                    if attempt == 2:
                        time.sleep(0.1)
                    time.sleep(0.02)
                    xtest_ctrl_key(dpy, "c")
                    start = time.time()
                    while time.time() - start < 0.8:
                        try:
                            text = pyperclip.paste().strip()
                        except Exception:
                            text = ""
                        if text:
                            captured = text
                            break
                        time.sleep(0.02)
                    if captured:
                        break
            finally:
                try:
                    dpy.close()
                except Exception:
                    pass
            if captured:
                _log_info("APP", f"[SELECTION] Captured: {len(captured)} chars")
                self.selection_translate_signal.emit(captured)
            else:
                _log_error("APP", "[SELECTION] linux capture failed: clipboard still empty")
                self.notify_signal.emit("failed", "未检测到鼠标选中文本")
            return
        if not IS_WINDOWS:
            self.notify_signal.emit("failed", "划选翻译当前平台暂不支持")
            return
        # 2026-10-28：不再注入 Alt 抬起、不再发 Esc。旧做法的问题：
        # 注入的 Alt 抬起本身就是一次“光秃秃的 Alt”，会让 Claude /
        # WinUI 记事本进菜单模式；Esc 退出后，用户手指真正松开 Alt
        # 时又是一次光秃秃的 Alt，菜单重进，Ctrl+C 和重试都被吃掉
        # （1.0.8 热键实测如此）；托盘路径同样失败：合成 Alt 抬起
        # 进菜单后，Esc 在 Claude 里并没能可靠退出。新做法：钩子
        # 匹配时已注入掩码键 0xE8（见 core/hook.py），此后任何 Alt
        # 抬起都不再触发菜单；这里只等用户真正松开修饰键再发
        # Ctrl+C，超时（0.6s）才兜底释放——有掩码键在，兜底也不会进菜单。
        if not _wait_modifiers_released(timeout=0.6):
            _release_modifiers()
            _log_info("APP", "[SELECTION] Modifiers still held after 0.6s, released synthetically (mask-protected)")

        # 只认序号变化后的剪贴板：Ctrl+C 没让剪贴板变化，说明这次
        # 根本没复制到选中文字。绝不能兜底读当前剪贴板——那是旧内容
        # （比如之前复制过的 "Test"），会被当成选中文字翻译出来，
        # 正是本次“译的不是选中文字”的根因。抓不到就老实报错，
        # 让失败可诊断，而不是拿旧剪贴板冒充成功。
        #
        # 2026-10-28：注入改走 SendInput（见 _send_ctrl_c_input），且失败
        # 时再试一次；读取失败不再直接 break，而是继续轮询到时限——
        # 剪贴板被占住时第一次 paste 可能失败，第二次能读到。
        captured = ""
        ever_changed = False
        for attempt in (1, 2):
            if attempt == 2:
                reason = "copied but paste empty/failed" if ever_changed else "changed nothing"
                _log_info("APP", f"[SELECTION] Retry Ctrl+C (attempt 1 {reason})")
                time.sleep(0.1)
            old_seq = user32.GetClipboardSequenceNumber()
            _send_ctrl_c_input()
            start = time.time()
            while time.time() - start < 0.8:
                if user32.GetClipboardSequenceNumber() != old_seq:
                    ever_changed = True
                    try:
                        text = pyperclip.paste().strip()
                    except Exception:
                        text = ""
                    if text:
                        captured = text
                        break
                time.sleep(0.02)
            if captured:
                break

        if captured:
            _log_info("APP", f"[SELECTION] Captured: {len(captured)} chars")
            self.selection_translate_signal.emit(captured)
        elif ever_changed:
            _log_info("APP", "[SELECTION] Failed: clipboard changed but paste empty/failed")
            self.notify_signal.emit("failed", "已复制但未能读取剪贴板内容")
        else:
            _log_info("APP", "[SELECTION] Failed: clipboard unchanged after Ctrl+C (SendInput, 2 attempts)")
            self.notify_signal.emit("failed", "未检测到鼠标选中文本")

    @Slot(str)
    def _do_selection_translate(self, text: str):
        if not text:
            return
        # 翻译放后台线程，界面不再冻住（离线回退最长约 17.5 秒）。
        from ui.translate_worker import start_translate

        start_translate(
            self, self._translate_workers, self.trans_mgr.translate, text,
            self._on_selection_translated,
        )

    @Slot(dict)
    def _on_selection_translated(self, payload):
        if payload.get("ok") and payload.get("result"):
            self.float_win.display(
                "划词翻译", payload["text"], payload["result"], source_type="selection"
            )
        else:
            self.notify_signal.emit(
                "failed", f"翻译失败：{payload.get('error', '未知错误')}"
            )

    def _handle_screenshot(self, pil_img):
        # 异步执行 OCR 与翻译，避免卡顿界面
        threading.Thread(target=self._ocr_worker, args=(pil_img,), daemon=True).start()

    def _ocr_worker(self, pil_img):
        self.notify_signal.emit("translating", "正在进行 OCR 文字提取...")
        try:
            text = ocr_engine.recognize_image(pil_img)
        except Exception as e:
            # OCR 引擎异常以前没接住，“正在识别”常驻提示永远不消失；
            # 现在走 failed 终态，提示正常消失（2026-10-28 review 小问题）。
            _log_error("OCR", f"recognize failed: {e}")
            self.notify_signal.emit("failed", "OCR 识别失败，请重试")
            return
        clean = text.strip()
        if not clean:
            self.notify_signal.emit("failed", "未能在截图区域中识别到有效文字")
            return
        self.ocr_translate_signal.emit(clean)

    @Slot(str)
    def _do_ocr_translate(self, ocr_text: str):
        # 翻译同样放后台线程；OCR 本身已在线程里（见 _handle_screenshot）。
        from ui.translate_worker import start_translate

        start_translate(
            self, self._translate_workers, self.trans_mgr.translate, ocr_text,
            self._on_ocr_translated,
        )

    @Slot(dict)
    def _on_ocr_translated(self, payload):
        if payload.get("ok") and payload.get("result"):
            self.float_win.display(
                "截图 OCR 翻译", payload["text"], payload["result"], source_type="ocr"
            )
            # 结果窗已出，常驻的“正在进行 OCR 文字提取...”必须在这里关闭；
            # 之前成功这路什么都没发，提示就永远挂在右下角。
            self.toast.dismiss()
        else:
            # 翻译失败也要把常驻的 translating 提示换掉，否则同样挂着不消失。
            self.notify_signal.emit(
                "failed", f"翻译失败：{payload.get('error', '请检查网络或参数')}"
            )

    @Slot(bool)
    def _on_toggle_hook(self, enabled: bool):
        if IS_MAC:
            if enabled:
                if self.hook.start():
                    self.toast.show_message("success", "快捷转译已恢复")
                else:
                    self.toast.show_message("failed", f"全局热键未能启用：{self.hook.last_error}")
                    self.tray.set_enabled(False)
            else:
                self.hook.stop()
                self.toast.show_message("error", "快捷转译已暂停")
            return
        if IS_LINUX:
            if enabled:
                if self.hook.start():
                    self.toast.show_message("success", "快捷转译已恢复")
                else:
                    self.toast.show_message("failed", f"全局热键未能启用：{self.hook.last_error}")
                    self.tray.set_enabled(False)
            else:
                self.hook.stop()
                self.toast.show_message("error", "快捷转译已暂停")
            return
        if not IS_WINDOWS:
            self.tray.set_enabled(False)
            self.toast.show_message("error", "全局热键当前平台暂不支持")
            return
        if enabled:
            # 恢复也要先自检：启动时自检没过的钩子，恢复时同样不许装。
            _ok, _detail = hook_self_check(self.hook)
            if not _ok:
                _log_error("HOOK", f"SELF-CHECK FAILED on resume, hook NOT started: {_detail}")
                self.toast.show_message("failed", f"钩子自检失败，快捷转译保持关闭：{_detail}")
                self.tray.set_enabled(False)
                return
            self.hook.start()
            self.toast.show_message("success", "快捷转译已恢复")
        else:
            self.hook.stop()
            self.toast.show_message("error", "快捷转译已暂停")

    @Slot(dict)
    def _on_config_changed(self, new_cfg: dict):
        self.config = new_cfg
        self.trans_mgr.update_config(new_cfg)
        self.hook.max_interval = new_cfg.get("max_interval_ms", 750) / 1000.0
        # 组合键改动即时生效：只重建判定表，不用重启钩子线程；
        # 钩子暂停中（托盘暂停）改的键，恢复时按新表工作。
        self.hook.update_hotkeys(new_cfg.get("hotkeys"))
        # 开机自启（Windows 任务计划）：只在目标状态与实际不一致时
        # 动 schtasks；失败时提示，设置页下次打开仍以实际状态为准。
        # 开机自启只对安装版动任务计划（便携版在 settings 里已禁用勾选，
        # 这里是第二道守卫：旧配置里残留的 True 也不再尝试创建任务）。
        if IS_WINDOWS and get_channel() == "安装版":
            try:
                want_auto = bool(new_cfg.get("auto_start", False))
                if is_autostart_enabled() != want_auto and not set_autostart_enabled(want_auto):
                    self.notify_signal.emit("failed", "开机自启设置失败（需要管理员权限）")
            except Exception as e:
                # is_autostart_enabled 本身抛错时，以前静默，用户的勾选白改了。
                _log_error("AUTOSTART", f"auto_start apply failed: {e}")
                self.notify_signal.emit("failed", "开机自启设置失败（需要管理员权限）")
        self.tray.set_engine_label(self._engine_label())
        self.tray.set_hotkeys(new_cfg.get("hotkeys"))
        self.main_win.set_hotkeys(new_cfg.get("hotkeys"))

    def quit_app(self):
        self.hook.stop()
        try:
            if os.path.exists(PID_FILE):
                os.remove(PID_FILE)
        except Exception as e:
            _log_info("APP", f"pid file cleanup failed: {e}")
        # 退出兜底：3 秒后若进程还在，直接 os._exit(0)。
        # 正常退出时主线程走 sys.exit，跑不到 3 秒；事件循环卡住、
        # QThread 析构阻塞、或之前卡在提权里的残留实例等任何拖住
        # 退出的情况，都由它兜底——托盘退出后绝不在任务管理器里
        # 留残留进程。PID 文件上面已删，互斥体由操作系统在进程
        # 结束时回收，不会因此锁死下一次启动。
        threading.Thread(target=self._exit_watchdog, daemon=True).start()
        try:
            self.tray.tray_icon.hide()
        except Exception as e:
            _log_info("APP", f"tray hide on quit failed: {e}")
        self.app.quit()

    def _exit_watchdog(self):
        time.sleep(3)
        os._exit(0)

def _wait_modifiers_released(timeout: float = 0.6) -> bool:
    """等用户真正松开 Alt/Ctrl/Shift；全松开返回 True，超时返回 False。

    供划选翻译与截图共用：不要没等用户松手就注入修饰键抬起——
    注入的 Alt 抬起会被目标程序当成“光秃秃的 Alt”而进菜单模式。
    非 Windows 直接返回 True（钩子与注入本就是 Windows 专属）。
    """
    if not IS_WINDOWS:
        return True
    deadline = time.time() + timeout
    while time.time() < deadline:
        held = (
            (user32.GetAsyncKeyState(VK_MENU) & 0x8000)
            or (user32.GetAsyncKeyState(VK_CONTROL) & 0x8000)
            or (user32.GetAsyncKeyState(VK_SHIFT) & 0x8000)
        )
        if not held:
            return True
        time.sleep(0.01)
    return False


def _is_admin() -> bool:
    if not IS_WINDOWS:
        return False
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def check_admin_elevation():
    """
    检查并提升为管理员权限，确保能穿透注入按键到 Claude 桌面端等管理员应用中 (Windows UIPI 限制)。

    打包版：spec 里 uac_admin=True，系统在双击时已按 manifest 弹过 UAC，
    与右键管理员启动走同一条路；这里不再做 runas 自重启——已是管理员
    直接过，非管理员则降级运行（避免与 manifest 重复提权）。
    源码运行：保留原来的提示 + runas 自重启。
    """
    if not IS_WINDOWS:
        return
    if getattr(sys, "frozen", False) and not _is_admin():
        # 打包版非管理员：manifest 提权未生效（例如 UAC 被关），不重复 runas。
        _log_info("APP", "elevation: packaged build without admin, continuing non-elevated (manifest path only)")
        return
    try:
        if not _is_admin():
            # 提权前先弹一个可见提示：之前这一步是静默的——ShellExecuteW
            # 会等 UAC 框被点掉才返回，UAC 框若被别的窗口盖住，用户
            # 根本不知道在等自己，进程就悄悄卡在这里、托盘也不出，
            # 看起来就是“双击没反应”。先告诉用户 UAC 框马上来、
            # 点“是”，再去调 runas，框被盖住时用户也知道按 Alt+Tab 找。
            _stage("elevation-runas-call")
            try:
                ctypes.windll.user32.MessageBoxW(
                    None,
                    "Manggo Pro Client 需要管理员权限，才能向管理员应用发送按键。\n\n"
                    "点击“确定”后会弹出系统权限确认窗口，请点“是”。\n"
                    "如果没看到确认窗口，请按 Alt+Tab 找一下。",
                    "Manggo Pro Client",
                    0x40,  # MB_ICONINFORMATION
                )
            except Exception as e:
                _log_error("APP", f"admin notice dialog failed: {e}")
            # 能走到这里的一定是源码运行（打包版非管理员上面已提前
            # 返回），只需把 main.py 路径当参数传给 python.exe。
            params = f'"{os.path.abspath(__file__)}"'
            res = ctypes.windll.shell32.ShellExecuteW(
                None, "runas", sys.executable, params, None, 1
            )
            # 提权结果必须记日志：之前这一步是黑盒，双击没起来时
            # 根本不知道是 UAC 被拒、runas 失败，还是子进程没起来。
            _log_info("APP", f"elevation: not admin, runas res={res} (>32 means child spawned)")
            _stage(f"elevation-runas-res={res}")
            if res > 32:
                sys.exit(0)
            _log_info("APP", "elevation: runas did not spawn a child, continuing non-elevated")
        else:
            _log_info("APP", "elevation: already admin, no relaunch")
            _stage("elevation-already-admin")
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

    # 单实例管理：Windows 用互斥体 + 终结旧进程；其他平台用 PID 存活检查。
    # 接管失败时绝不能静默跑第二个实例——这是 2026-10-27 一串怪象的根源：
    # 旧实例以管理员身份跑着时，非管理员的新实例 OpenProcess 会因
    # 权限不足打不开它，旧代码直接跳过、照常启动，于是托盘里出现两个
    # 一模一样的图标、钩子打架；用户在其中一个上点“退出应用”，
    # 另一个还活着，看起来就是“退出杀不死进程”，安装器也永远关不掉它。
    if IS_WINDOWS:
        mutex = win32event.CreateMutex(None, False, "ManggoProClient_SingleInstance_Mutex")
        if win32api.GetLastError() == winerror.ERROR_ALREADY_EXISTS:
            old_pid = None
            if os.path.exists(PID_FILE):
                try:
                    with open(PID_FILE, "r") as f:
                        old_pid = int(f.read().strip())
                except Exception as e:
                    # PID 文件读不出：无法确认旧进程，接管逻辑会按“旧实例活着”拒绝重复。
                    _log_info("APP", f"takeover: pid file unreadable ({e}), refusing duplicate")
            took_over = False
            if old_pid is not None and old_pid != os.getpid():
                try:
                    # SYNCHRONIZE | PROCESS_TERMINATE：既能杀，也能等它真死。
                    h_proc = kernel32.OpenProcess(0x00100000 | 0x0001, False, old_pid)
                    if h_proc:
                        if kernel32.TerminateProcess(h_proc, 0):
                            took_over = (kernel32.WaitForSingleObject(h_proc, 2000) == 0)
                        kernel32.CloseHandle(h_proc)
                    else:
                        _log_info("APP", f"takeover: cannot open old pid {old_pid} (likely admin instance)")
                except Exception as e:
                    _log_info("APP", f"takeover: failed for old pid {old_pid} ({e})")
            if not took_over:
                # 旧实例还活着且接管不了：直接退出并明说，不跑重复实例。
                # 这里还没有 QApplication，用原生消息框，不依赖 Qt。
                _log_info("APP", f"takeover: old instance still alive (pid={old_pid}), refusing duplicate")
                try:
                    ctypes.windll.user32.MessageBoxW(
                        None,
                        "Manggo Pro Client 已在运行（可能以管理员身份运行）。\n\n"
                        "当前启动无法接管旧实例，已退出，不会再起第二个。\n"
                        "请先右键托盘图标 → 退出应用，或在任务管理器中结束旧进程；\n"
                        "也可以右键以管理员身份运行来接管它。",
                        "Manggo Pro Client",
                        0x30,  # MB_ICONWARNING
                    )
                except Exception as e:
                    _log_info("APP", f"takeover: duplicate warning dialog failed: {e}")
                if mutex:
                    win32api.CloseHandle(mutex)
                return
            # 接管成功：重新创建互斥体
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
            except PermissionError:
                # 旧实例活着但当前用户无权发信号：按 Windows 分支的策略拒绝重复实例，
                # 否则两个图标、钩子打架（以前这里落进通用 except，直接覆盖 PID 启动了重复实例）。
                print("已有实例在运行（无权接管），退出。")
                return
            except Exception as e:
                # 损坏的 PID 文件（int 解析失败等）也落在这里：视为残留文件覆盖，日志留痕。
                _log_info("APP", f"pid file check failed ({e}), treating as stale")

    # 记录当前进程 PID
    try:
        with open(PID_FILE, "w") as f:
            f.write(str(os.getpid()))
    except Exception as e:
        _log_info("APP", f"pid file write failed: {e}")
    _stage("mutex-done")

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app.setWindowIcon(get_app_icon())
    _stage("app-created")

    coordinator = AppCoordinator(app)
    # 启动里程碑：托盘已建、钩子已起。双击没起来时，看日志有没有
    # 这一行就能区分“死在提权/启动早期”还是“起来了但托盘图标没看见”。
    _log_info("APP", f"started: admin={_is_admin()}, tray up, entering event loop")
    _stage("event-loop-enter")
    exit_code = app.exec()

    try:
        if os.path.exists(PID_FILE):
            os.remove(PID_FILE)
    except Exception as e:
        _log_info("APP", f"pid file cleanup failed: {e}")

    if mutex:
        win32api.CloseHandle(mutex)
    sys.exit(exit_code)

if __name__ == "__main__":
    main()
