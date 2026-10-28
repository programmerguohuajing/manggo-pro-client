"""
极简悬浮状态通知 (Toast)
"""
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QPoint
from PySide6.QtWidgets import QWidget, QLabel, QHBoxLayout, QGraphicsOpacityEffect
from PySide6.QtGui import QFont, QColor, QScreen, QGuiApplication

from ui import theme
from core.logging import debug as _log_debug

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
        # 消息序号：每条新消息 +1。旧消息的淡出动画/定时器回调只能
        # 在序号仍是自己时才 hide，否则会把刚来的新消息提前隐藏
        # （2026-10-28 review 小问题）。
        self._msg_serial = 0

    def show_message(self, status: str, message: str, duration_ms: int = 1500):
        self._msg_serial += 1
        # 先停掉上一条消息可能还在跑的淡出动画：它会继续把 opacity
        # 拉向 0 并在结束时 hide，正好把这条新消息提前藏起来。
        try:
            if getattr(self, "anim", None) is not None:
                self.anim.stop()
        except Exception as e:
            _log_debug("TOAST", f"stop old fade animation failed: {e}")
        self.hide_timer.stop()

        # 区分状态颜色与图标，配色见 ui/theme.py 的 toast_stylesheet
        icon = {"translating": "●", "success": "✓"}.get(status, "✕")
        self.setStyleSheet(theme.toast_stylesheet(status))
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
        except Exception as e:
            _log_debug("TOAST", f"SetWindowPos failed: {e}")

        if status != "translating":
            self.hide_timer.start(duration_ms)

    def dismiss(self):
        """主动关闭常驻提示。translating 是有意常驻的进度提示（等终态
        消息来替换），所以任务完成时必须由调用方显式关闭，否则像 OCR
        成功那路一样永远挂在右下角。"""
        self.hide_timer.stop()
        self.fade_out()

    def fade_out(self):
        serial = self._msg_serial
        self.anim = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.anim.setDuration(250)
        self.anim.setStartValue(1.0)
        self.anim.setEndValue(0.0)
        # 动画跑完时如果已经来了新消息，就不 hide（双重保险，
        # 配合 show_message 里先停动画）。
        self.anim.finished.connect(lambda: self.hide() if serial == self._msg_serial else None)
        self.anim.start()
