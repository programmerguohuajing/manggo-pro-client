"""
应用图标：原 ui/tray.py 里的 create_mango_icon / get_app_icon 原样迁移。

托盘与主窗口共用同一份图标来源，不再由托盘模块兼管图标绘制。
"""
import os
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QFont

ICON_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "app.ico")


def create_mango_icon() -> QIcon:
    if os.path.exists(ICON_PATH):
        return QIcon(ICON_PATH)

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


def get_app_icon() -> QIcon:
    return create_mango_icon()
