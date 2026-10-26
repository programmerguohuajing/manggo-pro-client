"""
Manggo Pro 独立桌面主翻译窗口 (对标原版核心工作台)
"""
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit,
    QPushButton, QComboBox, QFrame, QSplitter
)
from PySide6.QtGui import QFont, QIcon
import pyperclip

from core.tts import tts_player
from core.database import db

class MainWindow(QWidget):
    request_snipping = Signal()
    request_history = Signal()
    request_settings = Signal()

    def __init__(self, translator_mgr, parent=None):
        super().__init__(parent)
        self.translator_mgr = translator_mgr
        self.setWindowTitle("Manggo Pro - 桌面翻译工作台")
        self.resize(780, 520)

        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        # 1. 顶部工具栏
        top_bar = QHBoxLayout()
        lbl_app_logo = QLabel("🥭 Manggo Pro", self)
        lbl_app_logo.setFont(QFont("Microsoft YaHei", 12, QFont.Bold))
        lbl_app_logo.setStyleSheet("color: #e67e22;")
        top_bar.addWidget(lbl_app_logo)

        top_bar.addStretch()

        self.btn_snip = QPushButton("📷 截图翻译 (Alt+W)", self)
        self.btn_snip.setStyleSheet("padding: 5px 12px; border-radius: 4px; background: #f1f2f6;")
        self.btn_snip.clicked.connect(self.request_snipping.emit)
        top_bar.addWidget(self.btn_snip)

        self.btn_history = QPushButton("📖 历史 & 生词本", self)
        self.btn_history.setStyleSheet("padding: 5px 12px; border-radius: 4px; background: #f1f2f6;")
        self.btn_history.clicked.connect(self.request_history.emit)
        top_bar.addWidget(self.btn_history)

        self.btn_cfg = QPushButton("⚙️ 设置", self)
        self.btn_cfg.setStyleSheet("padding: 5px 12px; border-radius: 4px; background: #f1f2f6;")
        self.btn_cfg.clicked.connect(self.request_settings.emit)
        top_bar.addWidget(self.btn_cfg)

        main_layout.addLayout(top_bar)

        # 2. 语言选择条
        lang_bar = QHBoxLayout()
        self.cmb_src = QComboBox(self)
        self.cmb_src.addItems(["自动检测", "中文 (简体)", "英语 (English)"])
        lang_bar.addWidget(self.cmb_src)

        btn_swap = QPushButton("⇄", self)
        btn_swap.setFixedSize(32, 26)
        btn_swap.clicked.connect(self._swap_lang)
        lang_bar.addWidget(btn_swap)

        self.cmb_tgt = QComboBox(self)
        self.cmb_tgt.addItems(["自动检测 (目标)", "英语 (English)", "中文 (简体)"])
        lang_bar.addWidget(self.cmb_tgt)

        lang_bar.addStretch()

        self.btn_translate = QPushButton("立即翻译 (Ctrl+Enter)", self)
        self.btn_translate.setStyleSheet("background: #27ae60; color: white; font-weight: bold; padding: 6px 18px; border-radius: 4px;")
        self.btn_translate.clicked.connect(self.do_translate)
        lang_bar.addWidget(self.btn_translate)

        main_layout.addLayout(lang_bar)

        # 3. 双栏翻译编辑区
        splitter = QSplitter(Qt.Horizontal)

        # 左侧原文面板
        left_panel = QFrame(self)
        l_layout = QVBoxLayout(left_panel)
        l_layout.setContentsMargins(0, 0, 0, 0)

        h_left_tools = QHBoxLayout()
        h_left_tools.addWidget(QLabel("输入原文:"))
        h_left_tools.addStretch()
        btn_speak_src = QPushButton("🔊 朗读")
        btn_speak_src.clicked.connect(lambda: tts_player.speak(self.txt_source.toPlainText()))
        h_left_tools.addWidget(btn_speak_src)
        btn_clear = QPushButton("清空")
        btn_clear.clicked.connect(self.txt_source.clear)
        h_left_tools.addWidget(btn_clear)
        l_layout.addLayout(h_left_tools)

        self.txt_source = QTextEdit(self)
        self.txt_source.setFont(QFont("Microsoft YaHei", 11))
        self.txt_source.setPlaceholderText("在此键入要翻译的文字...")
        l_layout.addWidget(self.txt_source)
        splitter.addWidget(left_panel)

        # 右侧译文面板
        right_panel = QFrame(self)
        r_layout = QVBoxLayout(right_panel)
        r_layout.setContentsMargins(0, 0, 0, 0)

        h_right_tools = QHBoxLayout()
        lbl_target_tag = QLabel("译文结果:")
        lbl_target_tag.setStyleSheet("color: #27ae60; font-weight: bold;")
        h_right_tools.addWidget(lbl_target_tag)
        h_right_tools.addStretch()
        btn_speak_tgt = QPushButton("🔊 朗读")
        btn_speak_tgt.clicked.connect(lambda: tts_player.speak(self.txt_target.toPlainText()))
        h_right_tools.addWidget(btn_speak_tgt)
        btn_copy_tgt = QPushButton("📋 复制")
        btn_copy_tgt.clicked.connect(lambda: pyperclip.copy(self.txt_target.toPlainText()))
        h_right_tools.addWidget(btn_copy_tgt)
        r_layout.addLayout(h_right_tools)

        self.txt_target = QTextEdit(self)
        self.txt_target.setFont(QFont("Microsoft YaHei", 11))
        self.txt_target.setReadOnly(True)
        self.txt_target.setStyleSheet("background: #fbfbfb;")
        r_layout.addWidget(self.txt_target)
        splitter.addWidget(right_panel)

        main_layout.addWidget(splitter, 1)

    def _swap_lang(self):
        curr_src = self.cmb_src.currentIndex()
        curr_tgt = self.cmb_tgt.currentIndex()
        if curr_src == 1 and curr_tgt == 1:
            self.cmb_src.setCurrentIndex(2)
            self.cmb_tgt.setCurrentIndex(2)
        elif curr_src == 2 and curr_tgt == 2:
            self.cmb_src.setCurrentIndex(1)
            self.cmb_tgt.setCurrentIndex(1)

    def do_translate(self):
        src_text = self.txt_source.toPlainText().strip()
        if not src_text:
            return

        tgt_text = self.translator_mgr.translate(src_text)
        self.txt_target.setPlainText(tgt_text)

        # 保存到数据库
        db.add_record(src_text, tgt_text, source_type="main_win")

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter) and (event.modifiers() & Qt.ControlModifier):
            self.do_translate()
        else:
            super().keyPressEvent(event)
