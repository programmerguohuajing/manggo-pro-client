"""
现代化划词/截图翻译悬浮结果卡片
"""
from PySide6.QtCore import Qt, QPoint
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit,
    QPushButton, QFrame, QGraphicsDropShadowEffect
)
from PySide6.QtGui import QFont, QColor, QCursor, QGuiApplication
import pyperclip

from core.tts import tts_player
from core.database import db

class FloatResultWindow(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.resize(380, 280)

        self.current_source_text = ""
        self.current_target_text = ""
        self.current_record_id = -1
        self.is_starred = False

        self._init_ui()

    def _init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(10, 10, 10, 10)

        self.card = QFrame(self)
        self.card.setStyleSheet("""
            QFrame {
                background-color: #ffffff;
                border-radius: 12px;
                border: 1px solid #e1e8ed;
            }
        """)
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 45))
        shadow.setOffset(0, 4)
        self.card.setGraphicsEffect(shadow)

        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(14, 12, 14, 12)
        card_layout.setSpacing(8)

        # 1. 顶栏
        top_bar = QHBoxLayout()
        self.lbl_title = QLabel("Manggo 快捷翻译", self.card)
        self.lbl_title.setFont(QFont("Microsoft YaHei", 9, QFont.Bold))
        self.lbl_title.setStyleSheet("color: #e67e22; border: none;")
        top_bar.addWidget(self.lbl_title)

        top_bar.addStretch()

        self.btn_star = QPushButton("☆", self.card)
        self.btn_star.setToolTip("收藏到生词本")
        self.btn_star.setFixedSize(24, 24)
        self.btn_star.setStyleSheet("border: none; font-size: 15px; color: #f39c12; cursor: pointer;")
        self.btn_star.clicked.connect(self._toggle_star)
        top_bar.addWidget(self.btn_star)

        btn_close = QPushButton("✕", self.card)
        btn_close.setToolTip("关闭")
        btn_close.setFixedSize(24, 24)
        btn_close.setStyleSheet("border: none; font-size: 13px; color: #95a5a6; cursor: pointer;")
        btn_close.clicked.connect(self.hide)
        top_bar.addWidget(btn_close)
        card_layout.addLayout(top_bar)

        # 2. 原文展示与操作
        h_src_bar = QHBoxLayout()
        h_src_bar.addWidget(QLabel("原文:", self.card))
        h_src_bar.addStretch()
        btn_speak_src = QPushButton("🔊 朗读", self.card)
        btn_speak_src.setFixedSize(60, 20)
        btn_speak_src.setStyleSheet("font-size: 11px; border: 1px solid #dcdde1; border-radius: 4px; color: #576574;")
        btn_speak_src.clicked.connect(lambda: tts_player.speak(self.current_source_text))
        h_src_bar.addWidget(btn_speak_src)

        btn_copy_src = QPushButton("📋 复制", self.card)
        btn_copy_src.setFixedSize(60, 20)
        btn_copy_src.setStyleSheet("font-size: 11px; border: 1px solid #dcdde1; border-radius: 4px; color: #576574;")
        btn_copy_src.clicked.connect(lambda: pyperclip.copy(self.current_source_text))
        h_src_bar.addWidget(btn_copy_src)
        card_layout.addLayout(h_src_bar)

        self.txt_source = QTextEdit(self.card)
        self.txt_source.setReadOnly(True)
        self.txt_source.setFixedHeight(60)
        self.txt_source.setStyleSheet("border: 1px solid #edf2f7; border-radius: 6px; background: #f8fafc; font-size: 12px; padding: 4px;")
        card_layout.addWidget(self.txt_source)

        # 3. 译文展示与操作
        h_tgt_bar = QHBoxLayout()
        lbl_trans_tag = QLabel("译文:", self.card)
        lbl_trans_tag.setStyleSheet("font-weight: bold; color: #2ecc71;")
        h_tgt_bar.addWidget(lbl_trans_tag)
        h_tgt_bar.addStretch()

        btn_speak_tgt = QPushButton("🔊 朗读", self.card)
        btn_speak_tgt.setFixedSize(60, 20)
        btn_speak_tgt.setStyleSheet("font-size: 11px; border: 1px solid #dcdde1; border-radius: 4px; color: #576574;")
        btn_speak_tgt.clicked.connect(lambda: tts_player.speak(self.current_target_text))
        h_tgt_bar.addWidget(btn_speak_tgt)

        btn_copy_tgt = QPushButton("📋 复制", self.card)
        btn_copy_tgt.setFixedSize(60, 20)
        btn_copy_tgt.setStyleSheet("font-size: 11px; border: 1px solid #dcdde1; border-radius: 4px; color: #576574;")
        btn_copy_tgt.clicked.connect(lambda: pyperclip.copy(self.current_target_text))
        h_tgt_bar.addWidget(btn_copy_tgt)
        card_layout.addLayout(h_tgt_bar)

        self.txt_target = QTextEdit(self.card)
        self.txt_target.setReadOnly(True)
        self.txt_target.setStyleSheet("border: 1px solid #c8d6e5; border-radius: 6px; background: #ffffff; font-size: 13px; font-weight: 500; color: #222f3e; padding: 4px;")
        card_layout.addWidget(self.txt_target)

        root_layout.addWidget(self.card)

    def display(self, title: str, source_text: str, target_text: str, source_type: str = "selection"):
        self.lbl_title.setText(f"Manggo {title}")
        self.current_source_text = source_text
        self.current_target_text = target_text
        self.is_starred = False
        self.btn_star.setText("☆")

        self.txt_source.setPlainText(source_text)
        self.txt_target.setPlainText(target_text)

        # 记录到 SQLite 数据库
        self.current_record_id = db.add_record(source_text, target_text, source_type=source_type)

        # 智能跟随鼠标光标位置弹出
        cursor_pos = QCursor.pos()
        screen = QGuiApplication.screenAt(cursor_pos) or QGuiApplication.primaryScreen()
        screen_rect = screen.geometry()

        x = cursor_pos.x() + 15
        y = cursor_pos.y() + 15

        # 避免超出屏幕边界
        if x + self.width() > screen_rect.right():
            x = cursor_pos.x() - self.width() - 10
        if y + self.height() > screen_rect.bottom():
            y = cursor_pos.y() - self.height() - 10

        self.move(x, y)
        self.show()
        self.raise_()
        self.activateWindow()
        try:
            import ctypes
            hwnd = int(self.winId())
            ctypes.windll.user32.SetWindowPos(hwnd, -1, 0, 0, 0, 0, 0x0001 | 0x0002 | 0x0040)
            ctypes.windll.user32.SetForegroundWindow(hwnd)
        except Exception:
            pass

    def _toggle_star(self):
        if self.current_record_id > 0:
            self.is_starred = db.toggle_star(self.current_record_id)
            self.btn_star.setText("★" if self.is_starred else "☆")
