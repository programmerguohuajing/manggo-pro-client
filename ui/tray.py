"""
系统托盘与图标管理
"""
from PySide6.QtCore import Qt, Signal, QObject
from PySide6.QtWidgets import QSystemTrayIcon, QMenu
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QFont

def create_mango_icon() -> QIcon:
    """动态绘制一个清晰的芒果金黄色托盘图标"""
    pixmap = QPixmap(32, 32)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)

    # 芒果金黄主体
    painter.setBrush(QColor(255, 165, 0))
    painter.setPen(Qt.NoPen)
    painter.drawEllipse(4, 6, 24, 22)

    # 绿叶点缀
    painter.setBrush(QColor(46, 204, 113))
    painter.drawEllipse(16, 2, 8, 6)

    # 字母 M 标识
    painter.setPen(QColor(255, 255, 255))
    painter.setFont(QFont("Arial", 11, QFont.Bold))
    painter.drawText(pixmap.rect(), Qt.AlignCenter, "M")

    painter.end()
    return QIcon(pixmap)

class TrayManager(QObject):
    open_settings_requested = Signal()
    toggle_triple_space_requested = Signal(bool)
    exit_requested = Signal()

    def __init__(self, initial_enabled: bool = True, parent=None):
        super().__init__(parent)
        self.tray_icon = QSystemTrayIcon(create_mango_icon(), parent)
        self.tray_icon.setToolTip("Manggo Pro - 输入框就地转译助手")
        self._build_menu(initial_enabled)
        self.tray_icon.show()

    def _build_menu(self, enabled: bool):
        menu = QMenu()

        self.act_status = menu.addAction("三次空格转译: 运行中" if enabled else "三次空格转译: 已暂停")
        self.act_status.setEnabled(False)
        menu.addSeparator()

        self.act_toggle = menu.addAction("暂停快捷转译" if enabled else "启用快捷转译")
        self.act_toggle.triggered.connect(self._on_toggle)

        act_settings = menu.addAction("转译设置 (API & 参数)...")
        act_settings.triggered.connect(self.open_settings_requested.emit)

        menu.addSeparator()

        act_exit = menu.addAction("退出")
        act_exit.triggered.connect(self.exit_requested.emit)

        self.tray_icon.setContextMenu(menu)
        self.enabled = enabled

    def _on_toggle(self):
        self.enabled = not self.enabled
        self.act_status.setText("三次空格转译: 运行中" if self.enabled else "三次空格转译: 已暂停")
        self.act_toggle.setText("暂停快捷转译" if self.enabled else "启用快捷转译")
        self.toggle_triple_space_requested.emit(self.enabled)

    def show_message(self, title: str, msg: str):
        self.tray_icon.showMessage(title, msg, QSystemTrayIcon.Information, 2000)
