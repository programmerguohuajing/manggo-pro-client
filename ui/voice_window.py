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

        # 自动隐藏定时器（单例、可重入）：重复唤出时重新计时，不会被
        # 上一次的 singleShot 提前隐藏。
        self._auto_hide_timer = QTimer(self)
        self._auto_hide_timer.setSingleShot(True)
        self._auto_hide_timer.timeout.connect(self.hide)

    def hideEvent(self, event):
        # 卡片一隐藏就停掉呼吸动画：以前 hide 后计时器还在跑，
        # “正在聆听”名义上永远不结束（2026-10-28 review 小问题）。
        self.anim_timer.stop()
        self.is_recording = False
        super().hideEvent(event)

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        self.card = QFrame(self)
        self.card.setStyleSheet(f"""
            QFrame {{
                background-color: {theme.SURFACE};
                border-radius: 12px;
                border: 1px solid {theme.BORDER};
            }}
        """)
        c_layout = QHBoxLayout(self.card)
        c_layout.setContentsMargins(18, 12, 18, 12)
        c_layout.setSpacing(14)

        # 波形指示（方案 A：主题橙波形条，不用 emoji）
        self.lbl_icon = QLabel("▃▅▇▅▃", self.card)
        self.lbl_icon.setFont(QFont("Segoe UI", 18, QFont.Bold))
        self.lbl_icon.setStyleSheet(f"color: {theme.ACCENT};")
        c_layout.addWidget(self.lbl_icon)

        # 文字状态
        v_info = QVBoxLayout()
        v_info.setSpacing(4)
        self.lbl_title = QLabel("语音输入就绪 (Alt+Space)", self.card)
        self.lbl_title.setStyleSheet(f"color: {theme.INK}; font-weight: bold; font-size: 13px;")
        v_info.addWidget(self.lbl_title)

        self.lbl_hint = QLabel("正在启动语音引擎，请对准麦克风说话...", self.card)
        self.lbl_hint.setStyleSheet(f"color: {theme.SECONDARY}; font-size: 11px;")
        v_info.addWidget(self.lbl_hint)
        c_layout.addLayout(v_info, 1)

        # 关闭按钮（安静样式，悬停只加浅底）
        btn_close = QPushButton("✕", self.card)
        btn_close.setFixedSize(26, 26)
        btn_close.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {theme.SECONDARY};
                border: none;
                border-radius: 13px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background: {theme.SURFACE_MUTED};
                color: {theme.INK};
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
            # 不 activate：Win+H 是往当前焦点应用里听写，抢了焦点就
            # 听写到自己卡片里去了（2026-10-28 review 小问题）。
            self._auto_hide_timer.start(3000)
            return
        # 居中偏下显示
        screen = self.screen().geometry()
        x = screen.x() + (screen.width() - self.width()) // 2
        y = screen.y() + screen.height() - self.height() - 100
        self.move(x, y)

        self.show()
        self.raise_()
        # 不 activate：同上，焦点必须留在用户原来的应用里。

        self.is_recording = True
        self.anim_timer.start(350)

        # 异步调用 Win+H 调出听写
        threading.Thread(target=self._invoke_dictation, daemon=True).start()

        # 4.5 秒后自动隐藏提示卡片（不影响正在听写的系统输入）
        self._auto_hide_timer.start(4500)

    def _invoke_dictation(self):
        time.sleep(0.1)
        _trigger_windows_dictation()
