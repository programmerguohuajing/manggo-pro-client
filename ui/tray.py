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
from core.hotkeys import normalize_hotkeys
from core.platform import IS_WINDOWS, IS_MAC

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

    def __init__(self, initial_enabled: bool = True, engine_label: str = "内置极速通道", hotkeys=None, parent=None):
        super().__init__(parent)
        self.icon = get_app_icon()
        self.tray_icon = QSystemTrayIcon(self.icon, self)
        self.enabled = initial_enabled
        self.engine_label = engine_label
        # 菜单里的热键文案以前写死（Alt+M/Q/W/Space），用户改了热键后
        # 菜单还显示旧的；现在跟配置走，配置变了就刷新（2026-10-28 review 小问题）。
        self._hotkeys = normalize_hotkeys(hotkeys)
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

        self.act_main = menu.addAction("")
        self.act_main.triggered.connect(self.open_main_requested.emit)

        self.act_sel = menu.addAction("")
        self.act_sel.triggered.connect(self.open_selection_requested.emit)

        self.act_snip = menu.addAction("")
        self.act_snip.triggered.connect(self.open_snipping_requested.emit)

        self.act_voice = menu.addAction("")
        self.act_voice.triggered.connect(self.open_voice_requested.emit)
        self._apply_hotkey_texts()

        act_history = menu.addAction("历史记录 & 生词本")
        act_history.triggered.connect(self.open_history_requested.emit)

        menu.addSeparator()

        self.act_status = menu.addAction("")
        self.act_status.setEnabled(False)

        self.act_toggle = menu.addAction("")
        self.act_toggle.triggered.connect(self._on_toggle)

        act_settings = menu.addAction("软件偏好设置 (API & 参数)...")
        act_settings.triggered.connect(self.open_settings_requested.emit)

        act_console = menu.addAction("诊断控制台 (运行日志)...")
        act_console.triggered.connect(self.open_console_requested.emit)

        menu.addSeparator()

        act_exit = menu.addAction("退出应用")
        act_exit.triggered.connect(self.exit_requested.emit)

        self.tray_icon.setContextMenu(menu)

    def set_hotkeys(self, hotkeys):
        """配置里的热键变了，刷新菜单文案（不重建菜单）。"""
        self._hotkeys = normalize_hotkeys(hotkeys)
        self._apply_hotkey_texts()

    def _apply_hotkey_texts(self):
        hk = self._hotkeys
        self.act_main.setText(f"桌面翻译工作台\t{hk['workbench']}")
        self.act_sel.setText(f"划选文本翻译\t{hk['selection']}")
        self.act_snip.setText(f"截图 OCR 识别\t{hk['screenshot']}")
        self.act_voice.setText(f"语音输入与听写\t{hk['voice']}")

    def _refresh_status(self):
        if not IS_WINDOWS and not IS_MAC:
            # 非 Windows：钩子根本不存在，“已暂停”会误导（用户没暂停过，
            # 只是平台还没实现）；托盘只陈述平台状态，不给死开关。
            # 设置页的勾选是偏好，热键上线后即按此生效（见设置页附注）。
            self.act_status.setText("Manggo Pro · 热键暂不可用")
            self.act_toggle.setText("全局热键（Mac/Linux 开发中）")
            self.act_toggle.setEnabled(False)
            self.tray_icon.setToolTip(
                f"Manggo Pro Client\n快捷转译：当前平台暂不支持\n翻译通道：{self.engine_label}\n双击打开设置"
            )
            return
        state = "运行中" if self.enabled else "已暂停"
        self.act_status.setText(f"Manggo Pro · {state}")
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
