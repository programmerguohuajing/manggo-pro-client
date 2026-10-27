"""
系统托盘展示层：只负责图标、菜单、提示与信号转发，不碰翻译与钩子逻辑。

重构点（行为保持不变，新增一项）：
- 图标绘制迁移到 ui/icons.py，这里只引用；
- 菜单套用 ui/theme.py 的托盘样式，不再是原生裸菜单；
- 状态行与工具提示改为实时刷新：运行 / 暂停 + 当前翻译通道；
- 新增“诊断控制台”入口（open_console_requested），其余 8 个信号原样保留；
- 启动气泡文案缩短，不再堆三行说明。
"""
from PySide6.QtCore import Signal, QObject
from PySide6.QtWidgets import QSystemTrayIcon, QMenu

from ui import theme
from ui.icons import get_app_icon

# 兼容旧导入：main.py 之前从这里取图标，现图标住在 ui/icons.py。
__all__ = ["TrayManager", "get_app_icon"]


class TrayManager(QObject):
    open_main_requested = Signal()
    open_selection_requested = Signal()
    open_snipping_requested = Signal()
    open_voice_requested = Signal()
    open_history_requested = Signal()
    open_settings_requested = Signal()
    open_console_requested = Signal()
    toggle_triple_space_requested = Signal(bool)
    exit_requested = Signal()

    def __init__(self, initial_enabled: bool = True, engine_label: str = "内置极速通道", parent=None):
        super().__init__(parent)
        self.icon = get_app_icon()
        self.tray_icon = QSystemTrayIcon(self.icon, self)
        self.enabled = initial_enabled
        self.engine_label = engine_label
        self._build_menu()
        self._refresh_status()
        self.tray_icon.activated.connect(self._on_tray_activated)
        self.tray_icon.show()
        self.tray_icon.showMessage(
            "Manggo Pro 助手已就绪",
            "服务已在系统托盘运行中，双击图标打开设置。",
            QSystemTrayIcon.Information,
            3500,
        )

    def _build_menu(self):
        menu = QMenu()
        menu.setStyleSheet(theme.TRAY_MENU_STYLESHEET)

        act_main = menu.addAction("🖥️ 桌面翻译工作台 (Alt+M)")
        act_main.triggered.connect(self.open_main_requested.emit)

        act_sel = menu.addAction("📝 划选文本翻译 (Alt+Q)")
        act_sel.triggered.connect(self.open_selection_requested.emit)

        act_snip = menu.addAction("📷 截图 OCR 识别 (Alt+W)")
        act_snip.triggered.connect(self.open_snipping_requested.emit)

        act_voice = menu.addAction("🎤 语音输入与听写 (Alt+Space)")
        act_voice.triggered.connect(self.open_voice_requested.emit)

        act_history = menu.addAction("📖 历史记录 & 生词本")
        act_history.triggered.connect(self.open_history_requested.emit)

        menu.addSeparator()

        self.act_status = menu.addAction("")
        self.act_status.setEnabled(False)

        self.act_toggle = menu.addAction("")
        self.act_toggle.triggered.connect(self._on_toggle)

        act_settings = menu.addAction("⚙️ 软件偏好设置 (API & 参数)...")
        act_settings.triggered.connect(self.open_settings_requested.emit)

        act_console = menu.addAction("🪵 诊断控制台 (运行日志)...")
        act_console.triggered.connect(self.open_console_requested.emit)

        menu.addSeparator()

        act_exit = menu.addAction("退出应用")
        act_exit.triggered.connect(self.exit_requested.emit)

        self.tray_icon.setContextMenu(menu)

    def _refresh_status(self):
        state = "运行中" if self.enabled else "已暂停"
        self.act_status.setText(f"⚡ 快捷转译：{state} · {self.engine_label}")
        self.act_toggle.setText("暂停三次空格转译" if self.enabled else "启用三次空格转译")
        self.tray_icon.setToolTip(
            f"Manggo Pro Client\n快捷转译：{state}\n翻译通道：{self.engine_label}\n双击打开设置"
        )

    def set_enabled(self, enabled: bool):
        """仅刷新展示状态，不发 toggle 信号（供非 Windows 平台回拨用）。"""
        self.enabled = enabled
        self._refresh_status()

    def set_engine_label(self, engine_label: str):
        """配置变更时由 AppCoordinator 调用，只刷新展示，不改任何逻辑。"""
        self.engine_label = engine_label
        self._refresh_status()

    def _on_toggle(self):
        self.enabled = not self.enabled
        self._refresh_status()
        self.toggle_triple_space_requested.emit(self.enabled)

    def _on_tray_activated(self, reason):
        # 双击托盘图标，默认打开设置页面
        if reason == QSystemTrayIcon.DoubleClick:
            self.open_settings_requested.emit()
