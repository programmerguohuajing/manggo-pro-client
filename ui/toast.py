"""
极简悬浮状态通知 (Toast)
"""
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QPoint
from PySide6.QtWidgets import QWidget, QLabel, QHBoxLayout, QGraphicsOpacityEffect
from PySide6.QtGui import QFont, QColor, QScreen, QGuiApplication

class FloatToast(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool |
            Qt.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 8, 16, 8)

        self.label = QLabel("正在转译...", self)
        self.label.setFont(QFont("Microsoft YaHei", 9, QFont.Bold))
        layout.addWidget(self.label)

        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)

        self.hide_timer = QTimer(self)
        self.hide_timer.setSingleShot(True)
        self.hide_timer.timeout.connect(self.fade_out)

    def show_message(self, status: str, message: str, duration_ms: int = 1500):
        # 区分状态颜色
        if status == "translating":
            bg_color = "rgba(40, 44, 52, 0.9)"
            text_color = "#61afef"
            icon = "⚡"
        elif status == "success":
            bg_color = "rgba(40, 52, 45, 0.9)"
            text_color = "#98c379"
            icon = "✓"
        else:
            bg_color = "rgba(52, 40, 40, 0.9)"
            text_color = "#e06c75"
            icon = "✕"

        self.setStyleSheet(f"""
            QWidget {{
                background-color: {bg_color};
                border-radius: 8px;
                border: 1px solid rgba(255, 255, 255, 0.15);
            }}
            QLabel {{
                color: {text_color};
                background: transparent;
                border: none;
            }}
        """)
        self.label.setText(f"{icon} {message}")
        self.adjustSize()

        # 移动到主屏幕右下角任务栏上方
        screen = QGuiApplication.primaryScreen().geometry()
        margin_right = 24
        margin_bottom = 60
        x = screen.width() - self.width() - margin_right
        y = screen.height() - self.height() - margin_bottom
        self.move(x, y)

        self.opacity_effect.setOpacity(1.0)
        self.show()
        try:
            import ctypes
            hwnd = int(self.winId())
            # SWP_NOSIZE (0x0001) | SWP_NOMOVE (0x0002) | SWP_SHOWWINDOW (0x0040) | SWP_NOACTIVATE (0x0010) = 0x0053
            ctypes.windll.user32.SetWindowPos(hwnd, -1, 0, 0, 0, 0, 0x0053)
        except Exception:
            pass

        if status != "translating":
            self.hide_timer.start(duration_ms)

    def fade_out(self):
        self.anim = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.anim.setDuration(250)
        self.anim.setStartValue(1.0)
        self.anim.setEndValue(0.0)
        self.anim.finished.connect(self.hide)
        self.anim.start()
