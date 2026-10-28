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

from ui import theme

from core.tts import tts_player
from core.database import db

class MainWindow(QWidget):
    request_snipping = Signal()
    request_history = Signal()
    request_settings = Signal()

    def __init__(self, translator_mgr, hotkeys=None, parent=None):
        super().__init__(parent)
        self.translator_mgr = translator_mgr
        self._translate_workers = []
        self.setWindowTitle("Manggo Pro - 桌面翻译工作台")
        self.resize(780, 520)
        self.setStyleSheet(theme.WINDOW_STYLESHEET)

        # 热键先在 __init__ 里归一化好存在 self._hotkeys，_init_ui 只读它：
        # _init_ui 没有 hotkeys 参数，直接引用会 NameError。
        from core.hotkeys import normalize_hotkeys as _normalize_hotkeys
        self._hotkeys = _normalize_hotkeys(hotkeys)

        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        # 1. 顶部工具栏
        top_bar = QHBoxLayout()
        lbl_app_logo = QLabel("Manggo Pro", self)
        lbl_app_logo.setFont(QFont("Microsoft YaHei", 12, QFont.Bold))
        lbl_app_logo.setStyleSheet(f"color: {theme.INK};")
        top_bar.addWidget(lbl_app_logo)

        top_bar.addStretch()

        # 截图按钮的热键文案以前写死 Alt+W，改了热键后会误导；
        # 现在跟配置走（2026-10-28 review 小问题）。
        self.btn_snip = QPushButton(f"截图翻译 · {self._hotkeys['screenshot']}", self)
        self.btn_snip.setProperty("class", "SecondaryBtn")
        self.btn_snip.clicked.connect(self.request_snipping.emit)
        top_bar.addWidget(self.btn_snip)

        self.btn_history = QPushButton("历史 & 生词本", self)
        self.btn_history.setProperty("class", "SecondaryBtn")
        self.btn_history.clicked.connect(self.request_history.emit)
        top_bar.addWidget(self.btn_history)

        self.btn_cfg = QPushButton("设置", self)
        self.btn_cfg.setProperty("class", "SecondaryBtn")
        self.btn_cfg.clicked.connect(self.request_settings.emit)
        top_bar.addWidget(self.btn_cfg)

        main_layout.addLayout(top_bar)

        # 2. 语言选择条
        lang_bar = QHBoxLayout()
        self.cmb_src = QComboBox(self)
        self.cmb_src.addItems(["自动检测", "中文 (简体)", "英语 (English)"])
        lang_bar.addWidget(self.cmb_src)

        btn_swap = QPushButton("⇄", self)
        btn_swap.setProperty("class", "SecondaryBtn")
        btn_swap.setFixedSize(32, 26)
        btn_swap.clicked.connect(self._swap_lang)
        lang_bar.addWidget(btn_swap)

        self.cmb_tgt = QComboBox(self)
        self.cmb_tgt.addItems(["自动检测 (目标)", "英语 (English)", "中文 (简体)"])
        lang_bar.addWidget(self.cmb_tgt)

        lang_bar.addStretch()

        self.btn_translate = QPushButton("立即翻译 (Ctrl+Enter)", self)
        self.btn_translate.setProperty("class", "PrimaryBtn")
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
        lbl_src_tag = QLabel("输入原文:")
        lbl_src_tag.setStyleSheet(f"color: {theme.INK};")
        h_left_tools.addWidget(lbl_src_tag)
        h_left_tools.addStretch()
        btn_speak_src = QPushButton("朗读")
        btn_speak_src.clicked.connect(lambda: tts_player.speak(self.txt_source.toPlainText()))
        h_left_tools.addWidget(btn_speak_src)
        btn_clear = QPushButton("清空")
        btn_clear.clicked.connect(lambda: self.txt_source.clear())
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
        lbl_target_tag.setStyleSheet(f"color: {theme.INK}; font-weight: bold;")
        h_right_tools.addWidget(lbl_target_tag)
        h_right_tools.addStretch()
        btn_speak_tgt = QPushButton("朗读")
        btn_speak_tgt.clicked.connect(lambda: tts_player.speak(self.txt_target.toPlainText()))
        h_right_tools.addWidget(btn_speak_tgt)
        btn_copy_tgt = QPushButton("复制")
        btn_copy_tgt.clicked.connect(lambda: pyperclip.copy(self.txt_target.toPlainText()))
        h_right_tools.addWidget(btn_copy_tgt)
        r_layout.addLayout(h_right_tools)

        self.txt_target = QTextEdit(self)
        self.txt_target.setFont(QFont("Microsoft YaHei", 11))
        self.txt_target.setReadOnly(True)
        self.txt_target.setStyleSheet(f"background: {theme.SURFACE_MUTED};")
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

    # 下拉框索引 -> 翻译器语言码（2026-10-28 review：以前 do_translate
    # 根本不读这两个框，选了等于没选）。
    _SRC_MAP = {0: "auto", 1: "zh-CN", 2: "en"}
    _TGT_MAP = {0: "auto", 1: "en", 2: "zh-CN"}

    def set_hotkeys(self, hotkeys):
        """配置里的热键变了，刷新截图按钮文案。"""
        from core.hotkeys import normalize_hotkeys as _normalize_hotkeys
        self._hotkeys = _normalize_hotkeys(hotkeys)
        self.btn_snip.setText(f"截图翻译 · {self._hotkeys['screenshot']}")

    def do_translate(self):
        src_text = self.txt_source.toPlainText().strip()
        if not src_text:
            return

        src_lang = self._SRC_MAP.get(self.cmb_src.currentIndex(), "auto")
        tgt_lang = self._TGT_MAP.get(self.cmb_tgt.currentIndex(), "auto")
        if src_lang != "auto" and src_lang == tgt_lang:
            self.txt_target.setPlainText("源语言与目标语言相同，无需翻译。")
            return

        # 翻译放后台线程：离线回退时主窗口不再冻住。
        from ui.translate_worker import start_translate

        self.btn_translate.setEnabled(False)
        self.txt_target.setPlainText("翻译中…")
        self._pending_langs = (src_lang, tgt_lang)
        start_translate(
            self, self._translate_workers,
            lambda t: self.translator_mgr.translate(t, src_lang, tgt_lang),
            src_text, self._on_translate_done,
        )

    def _on_translate_done(self, payload):
        self.btn_translate.setEnabled(True)
        if not payload.get("ok") or not payload.get("result"):
            # 失败不进历史、不冒充成功，直接把原因显示出来。
            self.txt_target.setPlainText(
                f"翻译失败：{payload.get('error', '未知错误')}"
            )
            return
        src_text = payload["text"]
        tgt_text = payload["result"]
        self.txt_target.setPlainText(tgt_text)

        # 保存到数据库（带上用户选的语言方向，不再一律写 auto/en）。
        src_lang, tgt_lang = getattr(self, "_pending_langs", ("auto", "auto"))
        db.add_record(
            src_text, tgt_text, source_type="main_win",
            source_lang=src_lang, target_lang=tgt_lang,
        )

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter) and (event.modifiers() & Qt.ControlModifier):
            self.do_translate()
        else:
            super().keyPressEvent(event)
