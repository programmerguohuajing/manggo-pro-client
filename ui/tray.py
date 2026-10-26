"""
系统托盘与图标管理 (100% 对齐原版 Manggo 功能矩阵)
"""
from PySide6.QtCore import Qt, Signal, QObject
from PySide6.QtWidgets import QSystemTrayIcon, QMenu
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QFont

def create_mango_icon() -> QIcon:
    pixmap = QPixmap(32, 32)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)

    # 芒果金黄主体
    painter.setBrush(QColor(255, 165, 0))
    painter.setPen(Qt.NoPen)
    painter.drawEllipse(4, 6, 24, 22)

    # 嫩绿叶片
    painter.setBrush(QColor(46, 204, 113))
    painter.drawEllipse(16, 2, 8, 6)

    # 标识字符 M
    painter.setPen(QColor(255, 255, 255))
    painter.setFont(QFont("Arial", 11, QFont.Bold))
    painter.drawText(pixmap.rect(), Qt.AlignCenter, "M")

    painter.end()
    return QIcon(pixmap)

class TrayManager(QObject):
    open_main_requested = Signal()
    open_selection_requested = Signal()
    open_snipping_requested = Signal()
    open_voice_requested = Signal()
    open_history_requested = Signal()
    open_settings_requested = Signal()
    toggle_triple_space_requested = Signal(bool)
    exit_requested = Signal()

    def __init__(self, initial_enabled: bool = True, parent=None):
        super().__init__(parent)
        self.tray_icon = QSystemTrayIcon(create_mango_icon(), parent)
        self.tray_icon.setToolTip("Manggo Pro Client (双击打开设置)")
        self._build_menu(initial_enabled)
        self.tray_icon.activated.connect(self._on_tray_activated)
        self.tray_icon.show()

    def _build_menu(self, enabled: bool):
        menu = QMenu()

        act_main = menu.addAction("🖥️ 桌面翻译工作台 (Alt+Shift+D)")
        act_main.triggered.connect(self.open_main_requested.emit)

        act_sel = menu.addAction("📝 划选文本翻译 (Alt+D / Alt+Q)")
        act_sel.triggered.connect(self.open_selection_requested.emit)

        act_snip = menu.addAction("📷 截图 OCR 识别 (Alt+X / Alt+W)")
        act_snip.triggered.connect(self.open_snipping_requested.emit)

        act_voice = menu.addAction("🎤 语音输入与听写 (Alt+Space)")
        act_voice.triggered.connect(self.open_voice_requested.emit)

        act_history = menu.addAction("📖 历史记录 & 生词本")
        act_history.triggered.connect(self.open_history_requested.emit)

        menu.addSeparator()

        self.act_status = menu.addAction("⚡ 快捷转译: 运行中" if enabled else "⚡ 快捷转译: 已暂停")
        self.act_status.setEnabled(False)

        self.act_toggle = menu.addAction("暂停三次空格转译" if enabled else "启用三次空格转译")
        self.act_toggle.triggered.connect(self._on_toggle)

        act_settings = menu.addAction("⚙️ 软件偏好设置 (API & 参数)...")
        act_settings.triggered.connect(self.open_settings_requested.emit)

        menu.addSeparator()

        act_exit = menu.addAction("退出应用")
        act_exit.triggered.connect(self.exit_requested.emit)

        self.tray_icon.setContextMenu(menu)
        self.enabled = enabled

    def _on_toggle(self):
        self.enabled = not self.enabled
        self.act_status.setText("⚡ 快捷转译: 运行中" if self.enabled else "⚡ 快捷转译: 已暂停")
        self.act_toggle.setText("暂停三次空格转译" if self.enabled else "启用三次空格转译")
        self.toggle_triple_space_requested.emit(self.enabled)

    def _on_tray_activated(self, reason):
        # 双击托盘图标，默认打开设置页面
        if reason == QSystemTrayIcon.DoubleClick:
            self.open_settings_requested.emit()
