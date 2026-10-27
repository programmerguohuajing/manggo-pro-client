"""
语音输入与实时听写悬浮卡片 (Voice Input / Dictation)
对标原版 Manggo 的 Alt+Space 语音输入特性，支持一键语音转文字并就地输入。
"""
import time
import threading
import ctypes
from PySide6.QtCore import Qt, Signal, QTimer, QPoint
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame
from PySide6.QtGui import QFont, QColor, QPainter, QBrush, QPen
import pyperclip

from ui import theme
from core.platform import IS_WINDOWS

# Windows 模拟按键
VK_LWIN = 0x5B
VK_H = 0x48
KEYEVENTF_KEYUP = 0x0002

def _trigger_windows_dictation():
    """触发 Windows 原生全局听写引擎 (Win + H)"""
    user32 = ctypes.windll.user32
    user32.keybd_event(VK_LWIN, 0, 0, 0)
    time.sleep(0.02)
    user32.keybd_event(VK_H, 0, 0, 0)
    time.sleep(0.02)
    user32.keybd_event(VK_H, 0, KEYEVENTF_KEYUP, 0)
    user32.keybd_event(VK_LWIN, 0, KEYEVENTF_KEYUP, 0)

class VoiceInputWindow(QWidget):
    dictation_finished = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.SubWindow)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(360, 110)

        self.pulse_phase = 0
        self.is_recording = False

        self._init_ui()

        # 呼吸波形定时器
        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self._update_pulse)

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        self.card = QFrame(self)
        self.card.setStyleSheet(f"""
            QFrame {{
                background-color: {theme.DARK_BG};
                border-radius: 16px;
                border: 1.5px solid {theme.ACCENT};
            }}
        """)
        c_layout = QHBoxLayout(self.card)
        c_layout.setContentsMargins(18, 12, 18, 12)
        c_layout.setSpacing(14)

        # 麦克风图标与波形指示
        self.lbl_icon = QLabel("🎙️", self.card)
        self.lbl_icon.setFont(QFont("Segoe UI Emoji", 24))
        c_layout.addWidget(self.lbl_icon)

        # 文字状态
        v_info = QVBoxLayout()
        v_info.setSpacing(4)
        self.lbl_title = QLabel("语音输入就绪 (Alt+Space)", self.card)
        self.lbl_title.setStyleSheet(f"color: {theme.SURFACE}; font-weight: bold; font-size: 13px;")
        v_info.addWidget(self.lbl_title)

        self.lbl_hint = QLabel("正在启动语音引擎，请对准麦克风说话...", self.card)
        self.lbl_hint.setStyleSheet(f"color: {theme.TEXT_FAINT}; font-size: 11px;")
        v_info.addWidget(self.lbl_hint)
        c_layout.addLayout(v_info, 1)

        # 关闭按钮
        btn_close = QPushButton("✕", self.card)
        btn_close.setFixedSize(26, 26)
        btn_close.setStyleSheet(f"""
            QPushButton {{
                background: {theme.DARK_PANEL};
                color: {theme.BORDER_STRONG};
                border: none;
                border-radius: 13px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background: {theme.DANGER};
                color: white;
            }}
        """)
        btn_close.clicked.connect(self.hide)
        c_layout.addWidget(btn_close)

        layout.addWidget(self.card)

    def _update_pulse(self):
        self.pulse_phase = (self.pulse_phase + 1) % 4
        dots = "." * (self.pulse_phase + 1)
        self.lbl_hint.setText(f"正在聆听输入{dots}")

    def start_listening(self):
        """唤出语音输入并唤起 Windows 系统原生高精度听写引擎"""
        if not IS_WINDOWS:
            # macOS / Linux 没有 Win+H 系统听写：只显示提示卡片，不启动听写线程。
            self.lbl_hint.setText("语音听写仅支持 Windows（Win+H）")
            self.show()
            self.raise_()
            self.activateWindow()
            from PySide6.QtCore import QTimer as _QTimer
            _QTimer.singleShot(3000, self.hide)
            return
        # 居中偏下显示
        screen = self.screen().geometry()
        x = screen.x() + (screen.width() - self.width()) // 2
        y = screen.y() + screen.height() - self.height() - 100
        self.move(x, y)

        self.show()
        self.raise_()
        self.activateWindow()

        self.is_recording = True
        self.anim_timer.start(350)

        # 异步调用 Win+H 调出听写
        threading.Thread(target=self._invoke_dictation, daemon=True).start()

        # 5 秒后自动隐藏提示卡片（不影响正在听写的系统输入）
        QTimer.singleShot(4500, self.hide)

    def _invoke_dictation(self):
        time.sleep(0.1)
        _trigger_windows_dictation()
