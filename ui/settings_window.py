"""
现代化偏好设置中心 (Manggo Pro Preferences)
采用现代卡片式与侧边导航布局，具备精致的芒果琥珀主题视觉、服务商一键预设与状态监控。
"""
import os
import json
import time
import webbrowser
from typing import Callable
from PySide6.QtCore import Qt, Signal, QSize, QEvent
from PySide6.QtWidgets import (
    QApplication, QWidget, QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QComboBox, QSpinBox, QSlider, QPushButton, QCheckBox, QFrame,
    QMessageBox, QTextEdit, QStackedWidget, QListWidget, QListWidgetItem,
    QGraphicsDropShadowEffect, QScrollArea, QSizePolicy, QListView
)
from PySide6.QtGui import QFont, QIcon, QColor, QPainter, QPixmap
import pyperclip
from core.tts import tts_player
from core.hotkeys import (
    ACTION_NAMES,
    DEFAULT_HOTKEYS,
    normalize_hotkeys,
    parse_hotkey,
    validate_hotkeys,
)
from core.platform import IS_WINDOWS
from ui import theme
from ui.theme import SETTINGS_STYLESHEET
from core.logging import error as _log_error

CONFIG_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.json")

DEFAULT_CONFIG = {
    "engine": "free",  # "free" 或 "llm"
    "hotkeys": dict(DEFAULT_HOTKEYS),
    "triple_space_enabled": True,
    "max_interval_ms": 750,
    "llm_api_url": "https://api.deepseek.com/v1",
    "llm_api_key": "",
    "llm_model": "deepseek-chat",
    "llm_prompt": "You are a professional translator. Translate the given Chinese text directly into idiomatic, natural English. Output ONLY the English translation without quotes or explanations."
}

# 常见 LLM 服务商快速预设
PRESETS = {
    "DeepSeek (官方)": {
        "url": "https://api.deepseek.com/v1",
        "model": "deepseek-chat",
        "prompt": "You are a professional translator. Translate the given Chinese text directly into idiomatic, natural English. Output ONLY the English translation without quotes or explanations."
    },
    "DeepSeek-R1 (推理版)": {
        "url": "https://api.deepseek.com/v1",
        "model": "deepseek-reasoner",
        "prompt": "You are a professional translator. Translate the given Chinese text directly into idiomatic, natural English. Output ONLY the English translation without quotes or explanations."
    },
    "通义千问 (DashScope)": {
        "url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "model": "qwen-plus",
        "prompt": "You are a professional translator. Translate the given Chinese text directly into idiomatic, natural English. Output ONLY the English translation without quotes or explanations."
    },
    "OpenAI (GPT-4o-mini)": {
        "url": "https://api.openai.com/v1",
        "model": "gpt-4o-mini",
        "prompt": "You are a professional translator. Translate the given Chinese text directly into idiomatic, natural English. Output ONLY the English translation without quotes or explanations."
    },
    "本地 Ollama (Qwen2.5)": {
        "url": "http://localhost:11434/v1",
        "model": "qwen2.5:7b",
        "prompt": "You are a professional translator. Translate the given Chinese text directly into idiomatic, natural English. Output ONLY the English translation without quotes or explanations."
    }
}

PROMPT_TEMPLATES = {
    "💼 职场商务 & 外企口语": "You are an expert bilingual business communicator. Translate the given Chinese text into natural, polite, and professional workplace English. Output ONLY the translated text.",
    "🎓 学术论文 & 正式严谨": "You are an academic translation assistant. Translate the text into formal, precise academic English with rigorous terminology. Output ONLY the translation.",
    "💬 社交日常 & 俚语口语": "You are a native English speaker. Translate the text into casual, authentic, and modern spoken English. Output ONLY the translation.",
    "💻 极简代码注释 & 变量": "You are a software engineer. Translate the text into concise, professional English code comment or commit message format. Output ONLY the translated text."
}

def load_config() -> dict:
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                cfg = DEFAULT_CONFIG.copy()
                cfg.update(data)
                return cfg
        except Exception:
            pass
    return DEFAULT_CONFIG.copy()

def save_config(cfg: dict):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
    except Exception as e:
        _log_error("CONFIG", f"Error saving config: {e}")

class TranslationTestDialog(QDialog):
    """
    对标原版 Manggo 软件视觉规范的翻译通道测试与诊断面板
    """
    def __init__(self, parent=None, is_success=True, source_text="", target_text="", mode_name="", elapsed_ms=0, error_msg=""):
        super().__init__(parent)
        self.setWindowTitle("Manggo 翻译通道测试与诊断")
        self.resize(540, 500)
        self.setMinimumSize(480, 440)
        self.source_text = source_text
        self.target_text = target_text

        self._init_ui(is_success, mode_name, elapsed_ms, error_msg)

    def _init_ui(self, is_success: bool, mode_name: str, elapsed_ms: int, error_msg: str):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(14)

        # 1. 顶部 Header
        header = QHBoxLayout()
        lbl_title = QLabel("🥭 Manggo 通道测试诊断", self)
        lbl_title.setFont(QFont("Microsoft YaHei", 12, QFont.Bold))
        lbl_title.setStyleSheet(f"color: {theme.ACCENT};")
        header.addWidget(lbl_title)

        header.addStretch()

        # 状态小胶囊
        lbl_badge = QLabel(f"● 连通正常 ({elapsed_ms}ms)" if is_success else "● 连接异常", self)
        if is_success:
            lbl_badge.setStyleSheet(theme.badge_stylesheet(True))
        else:
            lbl_badge.setStyleSheet(theme.badge_stylesheet(False))
        header.addWidget(lbl_badge)
        root.addLayout(header)

        # 通道模式与指标条
        metrics_bar = QFrame(self)
        metrics_bar.setStyleSheet(f"background: {theme.SURFACE_GRAY}; border-radius: 8px; padding: 4px 12px;")
        m_layout = QHBoxLayout(metrics_bar)
        m_layout.setContentsMargins(8, 6, 8, 6)

        lbl_mode = QLabel(f"🌐 激活通道: {mode_name}", metrics_bar)
        lbl_mode.setStyleSheet(f"color: {theme.TEXT_SECONDARY}; font-size: 12px; font-weight: 500;")
        m_layout.addWidget(lbl_mode)

        m_layout.addStretch()

        lbl_speed = QLabel(f"⏱️ 耗时: {elapsed_ms} ms" if is_success else "❌ 请求失败", metrics_bar)
        lbl_speed.setStyleSheet(f"color: {theme.TEXT_MUTED}; font-size: 11px;")
        m_layout.addWidget(lbl_speed)
        root.addWidget(metrics_bar)

        if is_success:
            # 2. 原文卡片
            card_src = QFrame(self)
            card_src.setStyleSheet(f"background: {theme.SURFACE}; border: 1px solid {theme.BORDER}; border-radius: 10px; padding: 10px;")
            cs_layout = QVBoxLayout(card_src)
            cs_layout.setSpacing(6)

            h_src_top = QHBoxLayout()
            lbl_src_tag = QLabel("🇨🇳 原文 (中文)", card_src)
            lbl_src_tag.setStyleSheet(f"color: {theme.TEXT_GRAY600}; font-size: 11px; font-weight: bold;")
            h_src_top.addWidget(lbl_src_tag)
            h_src_top.addStretch()

            btn_src_tts = QPushButton("🔊 朗读", card_src)
            btn_src_tts.setProperty("class", "SecondaryBtn")
            btn_src_tts.clicked.connect(lambda: tts_player.speak(self.source_text))
            h_src_top.addWidget(btn_src_tts)

            btn_src_copy = QPushButton("📋 复制", card_src)
            btn_src_copy.setProperty("class", "SecondaryBtn")
            btn_src_copy.clicked.connect(lambda: pyperclip.copy(self.source_text))
            h_src_top.addWidget(btn_src_copy)
            cs_layout.addLayout(h_src_top)

            txt_src = QTextEdit(card_src)
            txt_src.setPlainText(self.source_text)
            txt_src.setReadOnly(True)
            txt_src.setFixedHeight(65)
            txt_src.setStyleSheet(f"background: {theme.SURFACE_MUTED}; border: 1px solid {theme.BORDER}; border-radius: 6px; padding: 6px; font-size: 12px; color: {theme.TEXT_PRIMARY};")
            cs_layout.addWidget(txt_src)
            root.addWidget(card_src)

            # 3. 译文卡片
            card_tgt = QFrame(self)
            card_tgt.setStyleSheet(f"background: {theme.SURFACE}; border: 1px solid {theme.ACCENT_SOFT_BORDER}; border-radius: 10px; padding: 10px;")
            ct_layout = QVBoxLayout(card_tgt)
            ct_layout.setSpacing(6)

            h_tgt_top = QHBoxLayout()
            lbl_tgt_tag = QLabel("🇬🇧 译文 (English)", card_tgt)
            lbl_tgt_tag.setStyleSheet(f"color: {theme.ACCENT}; font-size: 11px; font-weight: bold;")
            h_tgt_top.addWidget(lbl_tgt_tag)
            h_tgt_top.addStretch()

            btn_tgt_tts = QPushButton("🔊 朗读", card_tgt)
            btn_tgt_tts.setProperty("class", "SecondaryBtn")
            btn_tgt_tts.clicked.connect(lambda: tts_player.speak(self.target_text))
            h_tgt_top.addWidget(btn_tgt_tts)

            btn_tgt_copy = QPushButton("📋 复制译文", card_tgt)
            btn_tgt_copy.setProperty("class", "SecondaryBtn")
            btn_tgt_copy.clicked.connect(lambda: pyperclip.copy(self.target_text))
            h_tgt_top.addWidget(btn_tgt_copy)
            ct_layout.addLayout(h_tgt_top)

            txt_tgt = QTextEdit(card_tgt)
            txt_tgt.setPlainText(self.target_text)
            txt_tgt.setReadOnly(True)
            txt_tgt.setFixedHeight(75)
            txt_tgt.setStyleSheet(f"background: {theme.ACCENT_BG}; border: 1.5px solid {theme.ACCENT}; border-radius: 6px; padding: 6px; font-size: 13px; font-weight: 500; color: {theme.TEXT};")
            ct_layout.addWidget(txt_tgt)
            root.addWidget(card_tgt)
        else:
            # 异常详情卡片
            card_err = QFrame(self)
            card_err.setStyleSheet(f"background: {theme.ERROR_BG_LIGHT}; border: 1.5px solid {theme.ERROR_BORDER}; border-radius: 10px; padding: 12px;")
            ce_layout = QVBoxLayout(card_err)
            ce_layout.setSpacing(8)

            lbl_err_title = QLabel("⚠️ 通道异常报错信息", card_err)
            lbl_err_title.setStyleSheet(f"color: {theme.ERROR_DARK}; font-weight: bold; font-size: 13px;")
            ce_layout.addWidget(lbl_err_title)

            txt_err = QTextEdit(card_err)
            txt_err.setPlainText(error_msg)
            txt_err.setReadOnly(True)
            txt_err.setFixedHeight(90)
            txt_err.setStyleSheet(f"background: {theme.SURFACE}; border: 1px solid {theme.ERROR_BORDER}; border-radius: 6px; padding: 6px; font-size: 11px; color: {theme.ERROR_TEXT_DARK};")
            ce_layout.addWidget(txt_err)

            lbl_err_hint = QLabel("💡 排查建议：\n1. 若为大模型 Pro 通道，请确认 API Key 是否有效且账户有余额；\n2. 检查 Base URL 是否正确（官方 OpenAI/DeepSeek 需包含 /v1）；\n3. 确认网络连接或代理设置正常。", card_err)
            lbl_err_hint.setStyleSheet(f"color: {theme.ERROR_HINT_DARK}; font-size: 11px; line-height: 1.4;")
            ce_layout.addWidget(lbl_err_hint)
            root.addWidget(card_err)

        # 4. 底部操作栏
        footer = QHBoxLayout()
        lbl_foot_info = QLabel("通道就绪后，可在任意界面随时使用 3 次空格就地转译或 Alt+D 划词翻译。" if is_success else "请修改参数后再次测试。", self)
        lbl_foot_info.setStyleSheet(f"color: {theme.TEXT_MUTED}; font-size: 11px;")
        footer.addWidget(lbl_foot_info)

        footer.addStretch()

        if is_success:
            btn_copy_all = QPushButton("📋 复制结果", self)
            btn_copy_all.setProperty("class", "SecondaryBtn")
            btn_copy_all.clicked.connect(lambda: pyperclip.copy(self.target_text))
            footer.addWidget(btn_copy_all)

        btn_confirm = QPushButton("确定", self)
        btn_confirm.setProperty("class", "PrimaryBtn")
        btn_confirm.setFixedWidth(80)
        btn_confirm.clicked.connect(self.accept)
        footer.addWidget(btn_confirm)
        root.addLayout(footer)

def _create_label(text: str, css_class: str = "", parent=None) -> QLabel:
    lbl = QLabel(text, parent)
    if css_class:
        lbl.setProperty("class", css_class)
    return lbl

def setup_modern_combobox(combo: QComboBox):
    """消除 QComboBox 在 Windows 上的黑色边框与暗黑容器背景，呈现柔和纯白现代弹层"""
    lv = QListView(combo)
    lv.setFrameShape(QFrame.NoFrame)
    lv.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    combo.setView(lv)
    popup = combo.view().window()
    if popup:
        popup.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint | Qt.NoDropShadowWindowHint)
        popup.setAttribute(Qt.WA_TranslucentBackground)

class SettingsWindow(QWidget):
    config_changed = Signal(dict)
    open_main_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("SettingsWindow")
        self.setWindowTitle("Manggo Pro - 偏好设置")
        self.resize(780, 620)
        self.setMinimumSize(700, 560)
        self.setStyleSheet(SETTINGS_STYLESHEET)

        self.config = load_config()

        self._init_ui()
        self._load_values()

    def _init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # 1. 顶部 Header 栏
        header = QFrame(self)
        header.setFixedHeight(64)
        header.setStyleSheet(f"background-color: {theme.SURFACE}; border-bottom: 1px solid {theme.BORDER};")
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(20, 0, 20, 0)

        lbl_logo = QLabel("🥭 Manggo Pro", header)
        lbl_logo.setFont(QFont("Microsoft YaHei", 14, QFont.Bold))
        lbl_logo.setStyleSheet(f"color: {theme.ACCENT};")
        h_layout.addWidget(lbl_logo)

        lbl_sub = QLabel("偏好设置与通道配置", header)
        lbl_sub.setStyleSheet(f"color: {theme.TEXT_MUTED}; font-size: 13px; margin-left: 8px;")
        h_layout.addWidget(lbl_sub)

        h_layout.addStretch()

        self.btn_go_main = QPushButton("🖥️ 打开主工作台 (Alt+M)", header)
        self.btn_go_main.setProperty("class", "SecondaryBtn")
        self.btn_go_main.clicked.connect(self.open_main_requested.emit)
        h_layout.addWidget(self.btn_go_main)

        root_layout.addWidget(header)

        # 2. 中间主体区 (左侧导航 + 右侧卡片页面)
        body = QWidget(self)
        b_layout = QHBoxLayout(body)
        b_layout.setContentsMargins(0, 0, 0, 0)
        b_layout.setSpacing(0)

        # 侧边栏
        self.nav_list = QListWidget(body)
        self.nav_list.setObjectName("NavList")
        self.nav_list.setFixedWidth(160)
        self.nav_list.addItem(QListWidgetItem("⚡ 快捷转译"))
        self.nav_list.addItem(QListWidgetItem("🧠 翻译引擎"))
        self.nav_list.addItem(QListWidgetItem("⌨️ 全局热键"))
        self.nav_list.addItem(QListWidgetItem("ℹ️ 关于与状态"))
        self.nav_list.setCurrentRow(0)
        self.nav_list.currentRowChanged.connect(self._on_tab_changed)
        b_layout.addWidget(self.nav_list)

        # 堆叠卡片区
        self.stack = QStackedWidget(body)
        self.stack.setStyleSheet("background-color: transparent;")

        self.tab_trigger = self._build_trigger_tab()
        self.tab_engine = self._build_engine_tab()
        self.tab_hotkeys = self._build_hotkeys_tab()
        self.tab_about = self._build_about_tab()

        self.stack.addWidget(self.tab_trigger)
        self.stack.addWidget(self.tab_engine)
        self.stack.addWidget(self.tab_hotkeys)
        self.stack.addWidget(self.tab_about)

        b_layout.addWidget(self.stack, 1)
        root_layout.addWidget(body, 1)

        # 3. 底部操作栏
        footer = QFrame(self)
        footer.setFixedHeight(62)
        footer.setStyleSheet(f"background-color: {theme.SURFACE}; border-top: 1px solid {theme.BORDER};")
        f_layout = QHBoxLayout(footer)
        f_layout.setContentsMargins(20, 0, 20, 0)

        self.lbl_status = QLabel("", footer)
        self.lbl_status.setStyleSheet(f"color: {theme.SUCCESS_DARK}; font-size: 12px; font-weight: 500;")
        f_layout.addWidget(self.lbl_status)

        f_layout.addStretch()

        self.btn_test = QPushButton("⚡ 测试当前翻译", footer)
        self.btn_test.setProperty("class", "SecondaryBtn")
        self.btn_test.clicked.connect(self._test_translation)
        f_layout.addWidget(self.btn_test)

        self.btn_save = QPushButton("保存并应用", footer)
        self.btn_save.setProperty("class", "PrimaryBtn")
        self.btn_save.clicked.connect(self._save_and_apply)
        f_layout.addWidget(self.btn_save)

        root_layout.addWidget(footer)

    def _on_tab_changed(self, idx: int):
        self.stack.setCurrentIndex(idx)

    # ---------------- 选项卡 1: 快捷转译 ----------------
    def _build_trigger_tab(self) -> QWidget:
        container = QWidget()
        l = QVBoxLayout(container)
        l.setContentsMargins(24, 20, 24, 20)
        l.setSpacing(16)

        # 主卡片: 三击空格就地转译
        card = QFrame()
        card.setProperty("class", "CardFrame")
        c_layout = QVBoxLayout(card)
        c_layout.setSpacing(12)

        self.chk_triple_space = QCheckBox("启用【连续三次空格】输入框就地转译")
        self.chk_triple_space.setFont(QFont("Microsoft YaHei", 10, QFont.Bold))
        c_layout.addWidget(self.chk_triple_space)

        lbl_desc = QLabel("在任意软件（微信、Word、浏览器、终端等）中打完中文后，只需连击 3 次空格，即可自动消除空格并将光标前中文直接替换为英文。")
        lbl_desc.setProperty("class", "SectionDesc")
        lbl_desc.setWordWrap(True)
        c_layout.addWidget(lbl_desc)

        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet(f"color: {theme.SURFACE_GRAY};")
        c_layout.addWidget(line)

        # 灵敏度时间调节
        lbl_interval_title = QLabel("连击灵敏度（相邻空格击键容忍间隔）:")
        lbl_interval_title.setProperty("class", "FieldLabel")
        c_layout.addWidget(lbl_interval_title)

        h_slider = QHBoxLayout()
        self.slider_interval = QSlider(Qt.Horizontal)
        self.slider_interval.setRange(300, 900)
        self.slider_interval.setSingleStep(20)

        self.spn_interval = QSpinBox()
        self.spn_interval.setRange(300, 900)
        self.spn_interval.setSingleStep(20)
        self.spn_interval.setSuffix(" ms")
        self.spn_interval.setFixedWidth(85)

        # 联动
        self.slider_interval.valueChanged.connect(self.spn_interval.setValue)
        self.spn_interval.valueChanged.connect(self.slider_interval.setValue)

        h_slider.addWidget(self.slider_interval, 1)
        h_slider.addWidget(self.spn_interval)
        c_layout.addLayout(h_slider)

        lbl_tip = QLabel("推荐值：500 ~ 650 ms。如打字节奏较慢可适当调大，如常误触可适当调小。")
        lbl_tip.setStyleSheet(f"font-size: 11px; color: {theme.TEXT_FAINT};")
        c_layout.addWidget(lbl_tip)

        l.addWidget(card)

        # 机制提示卡片
        tip_card = QFrame()
        tip_card.setProperty("class", "CardFrame")
        tip_card.setStyleSheet(f"background-color: {theme.WARNING_BG}; border-color: {theme.WARNING_BORDER};")
        t_l = QVBoxLayout(tip_card)
        lbl_tip_title = QLabel("💡 贴心使用提示")
        lbl_tip_title.setStyleSheet(f"font-weight: bold; color: {theme.WARNING_TITLE}; font-size: 13px;")
        t_l.addWidget(lbl_tip_title)

        lbl_tip_content = QLabel("1. 支持两种触发模式：已手动划选文本时，连按 3 次空格直接转译选中文本；光标在行尾时，自动捕捉并替换光标前的中文片段。\n2. 转译过程中右下角伴有呼吸气泡通知，不抢占当前焦点，不打断您的打字心流。")
        lbl_tip_content.setStyleSheet(f"color: {theme.WARNING_TEXT}; font-size: 12px; line-height: 1.5;")
        lbl_tip_content.setWordWrap(True)
        t_l.addWidget(lbl_tip_content)

        l.addWidget(tip_card)
        l.addStretch()
        return container

    # ---------------- 选项卡 2: 翻译引擎 ----------------
    def _build_engine_tab(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background: transparent;")

        container = QWidget()
        l = QVBoxLayout(container)
        l.setContentsMargins(24, 20, 24, 20)
        l.setSpacing(14)

        # 引擎选择卡片
        card_sel = QFrame()
        card_sel.setProperty("class", "CardFrame")
        cs_l = QVBoxLayout(card_sel)
        cs_l.setSpacing(10)

        lbl_eng_title = QLabel("选择转译通道模式")
        lbl_eng_title.setProperty("class", "SectionTitle")
        cs_l.addWidget(lbl_eng_title)

        self.cmb_engine = QComboBox()
        setup_modern_combobox(self.cmb_engine)
        self.cmb_engine.addItems([
            "⚡ 内置极速通道 (免 API Key，国内毫秒级响应，开箱即用)",
            "🧠 自定义大模型 Pro 通道 (DeepSeek / 通义千问 / OpenAI / 本地 Ollama)"
        ])
        self.cmb_engine.currentIndexChanged.connect(self._on_engine_mode_changed)
        cs_l.addWidget(self.cmb_engine)
        l.addWidget(card_sel)

        # LLM 配置卡片
        self.card_llm = QFrame()
        self.card_llm.setProperty("class", "CardFrame")
        cl_layout = QVBoxLayout(self.card_llm)
        cl_layout.setSpacing(12)

        # 服务商快捷预设
        h_preset = QHBoxLayout()
        lbl_preset = QLabel("常用服务商快速填入:")
        lbl_preset.setProperty("class", "FieldLabel")
        h_preset.addWidget(lbl_preset)

        self.cmb_preset = QComboBox()
        setup_modern_combobox(self.cmb_preset)
        self.cmb_preset.addItem("—— 请选择预设模板 ——")
        for name in PRESETS.keys():
            self.cmb_preset.addItem(name)
        self.cmb_preset.currentIndexChanged.connect(self._apply_preset)
        h_preset.addWidget(self.cmb_preset, 1)
        cl_layout.addLayout(h_preset)

        # API Base URL
        cl_layout.addWidget(_create_label("API Base URL:", "FieldLabel"))
        self.txt_url = QLineEdit()
        self.txt_url.setPlaceholderText("https://api.deepseek.com/v1")
        cl_layout.addWidget(self.txt_url)

        # API Key
        h_key_title = QHBoxLayout()
        h_key_title.addWidget(_create_label("API Key (密钥安全加密存储):", "FieldLabel"))
        h_key_title.addStretch()

        self.btn_toggle_key = QPushButton("👁️ 显示密钥")
        self.btn_toggle_key.setProperty("class", "TextBtn")
        self.btn_toggle_key.clicked.connect(self._toggle_key_visibility)
        h_key_title.addWidget(self.btn_toggle_key)
        cl_layout.addLayout(h_key_title)

        self.txt_key = QLineEdit()
        self.txt_key.setEchoMode(QLineEdit.Password)
        self.txt_key.setPlaceholderText("sk-...")
        cl_layout.addWidget(self.txt_key)

        # 模型名称
        cl_layout.addWidget(_create_label("Model 名称:", "FieldLabel"))
        self.txt_model = QLineEdit()
        self.txt_model.setPlaceholderText("deepseek-chat")
        cl_layout.addWidget(self.txt_model)

        # Prompt 提示词与风格选择
        h_prompt_hdr = QHBoxLayout()
        h_prompt_hdr.addWidget(_create_label("翻译 Prompt (风格定制):", "FieldLabel"))
        h_prompt_hdr.addStretch()

        self.cmb_prompt_tpl = QComboBox()
        setup_modern_combobox(self.cmb_prompt_tpl)
        self.cmb_prompt_tpl.addItem("—— 选用表达风格模板 ——")
        for tpl_name in PROMPT_TEMPLATES.keys():
            self.cmb_prompt_tpl.addItem(tpl_name)
        self.cmb_prompt_tpl.currentIndexChanged.connect(self._apply_prompt_template)
        h_prompt_hdr.addWidget(self.cmb_prompt_tpl)
        cl_layout.addLayout(h_prompt_hdr)

        self.txt_prompt = QTextEdit()
        self.txt_prompt.setFixedHeight(65)
        cl_layout.addWidget(self.txt_prompt)

        l.addWidget(self.card_llm)
        l.addStretch()

        scroll.setWidget(container)
        return scroll

    # ---------------- 选项卡 3: 全局热键 ----------------
    def _build_hotkeys_tab(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background: transparent;")

        container = QWidget()
        l = QVBoxLayout(container)
        l.setContentsMargins(24, 20, 24, 20)
        l.setSpacing(14)

        card = QFrame()
        card.setProperty("class", "CardFrame")
        c_layout = QVBoxLayout(card)
        c_layout.setSpacing(12)

        lbl_t = QLabel("全局热键（点【点击录制】可修改组合键，保存后立即生效）")
        lbl_t.setProperty("class", "SectionTitle")
        c_layout.addWidget(lbl_t)

        # 待保存的组合键：录制时先改这里，点底部保存才写 config.json。
        # 非 Windows 上全局钩子不存在，录制按钮置灰，只作展示。
        self._hotkey_values = normalize_hotkeys(self.config.get("hotkeys"))
        self._hotkey_badges = {}
        self._hotkey_record_btns = {}
        self._recording_action = None
        self._filter_installed = False

        # (动作 key 或 None, 徽章文字, 功能名, 说明)；动作为 None 的是固定项，不可改。
        rows = [
            ("selection", None, ACTION_NAMES["selection"], "鼠标高亮划选任意屏幕文本后按下，呼出多功能悬浮翻译卡片，支持朗读、复制、存入生词本。"),
            ("screenshot", None, ACTION_NAMES["screenshot"], "全屏十字光标框选任意区域，提取图像中的中英文文字并自动进行翻译对照。"),
            ("workbench", None, ACTION_NAMES["workbench"], "沉浸式双栏对照翻译工作台，支持中英双向互译、生词本检索与长文本排版翻译。"),
            ("voice", None, ACTION_NAMES["voice"], "唤起麦克风拾音指示气泡，语音转文字直接打字上屏。"),
            (None, "连续 3 次空格 (Space)", "输入框就地转译", "在任意应用输入中文后连击 3 次空格，自动消除空格并将文字就地替换为英文。开关与灵敏度在【快捷转译】页设置。"),
            (None, "双击系统托盘图标", "打开偏好设置中心", "随时快速呼出本设置面板，调节连击灵敏度与切换翻译通道。"),
            (None, "Ctrl + Enter", "工作台立即翻译", "在主翻译工作台原文编辑框内一键提交翻译请求。"),
        ]

        for action, key_text, name, desc in rows:
            row = QFrame()
            row.setStyleSheet(f"background-color: {theme.SURFACE_MUTED}; border: 1px solid {theme.SURFACE_GRAY}; border-radius: 8px; padding: 10px 12px;")
            r_l = QVBoxLayout(row)
            r_l.setContentsMargins(10, 8, 10, 8)
            r_l.setSpacing(6)

            # 顶部行：功能名称 + 快捷键徽章
            h_top = QHBoxLayout()
            lbl_name = QLabel(name)
            lbl_name.setStyleSheet(f"font-weight: bold; color: {theme.TEXT_PRIMARY}; font-size: 13px;")
            h_top.addWidget(lbl_name)

            h_top.addStretch()

            if action is not None:
                btn_record = QPushButton("点击录制")
                btn_record.setProperty("class", "SecondaryBtn")
                btn_record.setEnabled(IS_WINDOWS)
                btn_record.clicked.connect(lambda _=False, a=action: self._start_recording(a))
                self._hotkey_record_btns[action] = btn_record
                h_top.addWidget(btn_record)

            badge_text = self._hotkey_values[action] if action is not None else key_text
            lbl_badge = QLabel(badge_text)
            lbl_badge.setStyleSheet(f"background: {theme.ACCENT_SOFT_BG}; color: {theme.ACCENT}; border: 1px solid {theme.ACCENT_SOFT_BORDER}; font-weight: bold; padding: 3px 10px; border-radius: 6px; font-size: 11px; font-family: {theme.FONT_MONO};")
            if action is not None:
                self._hotkey_badges[action] = lbl_badge
            h_top.addWidget(lbl_badge)
            r_l.addLayout(h_top)

            # 次行：完整说明文本（开启自适应折行，彻底杜绝文字截断）
            lbl_d = QLabel(desc)
            lbl_d.setStyleSheet(f"color: {theme.TEXT_MUTED}; font-size: 12px; line-height: 1.4;")
            lbl_d.setWordWrap(True)
            r_l.addWidget(lbl_d)

            c_layout.addWidget(row)

        # 录制说明 + 恢复默认：放在卡片底部，不随行循环重复。
        self.lbl_hotkey_status = QLabel(
            "录制方法：点【点击录制】后直接按下组合键（需带 Alt / Ctrl / Shift，Win 键不支持）；按 Esc 取消。"
            if IS_WINDOWS else
            "全局热键仅支持 Windows，当前平台下录制不可用；这里只展示默认组合键。"
        )
        self.lbl_hotkey_status.setStyleSheet(f"color: {theme.TEXT_MUTED}; font-size: 12px;")
        self.lbl_hotkey_status.setWordWrap(True)
        c_layout.addWidget(self.lbl_hotkey_status)

        h_restore = QHBoxLayout()
        h_restore.addStretch()
        btn_restore = QPushButton("恢复默认")
        btn_restore.setProperty("class", "SecondaryBtn")
        btn_restore.setEnabled(IS_WINDOWS)
        btn_restore.clicked.connect(self._restore_default_hotkeys)
        h_restore.addWidget(btn_restore)
        c_layout.addLayout(h_restore)

        l.addWidget(card)
        l.addStretch()

        scroll.setWidget(container)
        return scroll

    # ---------------- 热键录制 ----------------
    @staticmethod
    def _qt_key_name(key: int):
        """把 Qt 按键码转成热键主键名；不支持的键返回 None。"""
        if 0x41 <= key <= 0x5A or 0x30 <= key <= 0x39:
            return chr(key)
        if key == 0x20:
            return "Space"
        if 0x01000030 <= key <= 0x0100003B:  # F1-F12
            return f"F{key - 0x01000030 + 1}"
        return None

    def _start_recording(self, action: str):
        if self._recording_action is not None:
            self._cancel_recording()
        self._recording_action = action
        btn = self._hotkey_record_btns[action]
        btn.setText("请按下组合键…（Esc 取消）")
        app = QApplication.instance()
        if app is not None and not self._filter_installed:
            app.installEventFilter(self)
            self._filter_installed = True
        self.lbl_hotkey_status.setText(f"正在录制【{ACTION_NAMES[action]}】，请按下组合键…")

    def _finish_recording(self):
        if self._recording_action is not None:
            self._hotkey_record_btns[self._recording_action].setText("点击录制")
        self._recording_action = None
        app = QApplication.instance()
        if app is not None and self._filter_installed:
            app.removeEventFilter(self)
            self._filter_installed = False

    def _cancel_recording(self):
        self._finish_recording()
        self.lbl_hotkey_status.setText("已取消录制，组合键未改动。")

    def _restore_default_hotkeys(self):
        if self._recording_action is not None:
            self._cancel_recording()
        self._hotkey_values = dict(DEFAULT_HOTKEYS)
        self._refresh_hotkey_rows()
        self.lbl_hotkey_status.setText("已恢复默认组合键，点底部【保存并应用】后生效。")

    def _refresh_hotkey_rows(self):
        for action, badge in self._hotkey_badges.items():
            badge.setText(self._hotkey_values[action])

    def eventFilter(self, obj, event):
        # 只在录制期间拦截按键；其他时候原样放行，避免影响正常输入。
        if self._recording_action is not None and event.type() == QEvent.Type.KeyPress:
            return self._on_record_key(event)
        return super().eventFilter(obj, event)

    def _on_record_key(self, event) -> bool:
        key = event.key()
        if key == Qt.Key.Key_Escape:
            self._cancel_recording()
            return True
        # 纯修饰键：等主键，不吞之外的行为也无妨，吞掉可避免按钮误触发。
        if key in (Qt.Key.Key_Alt, Qt.Key.Key_Control, Qt.Key.Key_Shift,
                   Qt.Key.Key_Meta, Qt.Key.Key_AltGr, Qt.Key.Key_CapsLock):
            return True
        mods = []
        m = event.modifiers()
        if m & Qt.KeyboardModifier.AltModifier:
            mods.append("Alt")
        if m & Qt.KeyboardModifier.ControlModifier:
            mods.append("Ctrl")
        if m & Qt.KeyboardModifier.ShiftModifier:
            mods.append("Shift")
        main = self._qt_key_name(key)
        action = self._recording_action
        if main is None:
            self.lbl_hotkey_status.setText("该按键不支持作为热键主键，请用字母、数字、F1-F12 或 Space。")
            return True
        if not mods:
            self.lbl_hotkey_status.setText("请带上 Alt / Ctrl / Shift 再按一次（单独按键不能做全局热键）。")
            return True
        combo = "+".join(mods + [main])
        parsed = parse_hotkey(combo)
        if parsed is None:
            self.lbl_hotkey_status.setText(f"组合键“{combo}”无效，请换一个。")
            return True
        combo = parsed[2]
        for other, value in self._hotkey_values.items():
            if other != action and value == combo:
                QMessageBox.warning(self, "组合键重复", f"“{combo}”已用于【{ACTION_NAMES[other]}】，请换一个。")
                return True
        self._hotkey_values[action] = combo
        self._hotkey_badges[action].setText(combo)
        self._finish_recording()
        self.lbl_hotkey_status.setText(f"已录制【{ACTION_NAMES[action]}】：{combo}，点底部【保存并应用】后生效。")
        return True

    # ---------------- 选项卡 4: 关于与状态 ----------------
    def _build_about_tab(self) -> QWidget:
        container = QWidget()
        l = QVBoxLayout(container)
        l.setContentsMargins(24, 20, 24, 20)
        l.setSpacing(14)

        card = QFrame()
        card.setProperty("class", "CardFrame")
        c_l = QVBoxLayout(card)
        c_l.setSpacing(12)

        lbl_app_name = QLabel("🥭 Manggo Pro Client 桌面客户端")
        lbl_app_name.setFont(QFont("Microsoft YaHei", 12, QFont.Bold))
        lbl_app_name.setStyleSheet(f"color: {theme.ACCENT};")
        c_l.addWidget(lbl_app_name)

        lbl_ver = QLabel("版本号: v2.0 Pro Edition | 纯本地运行 | 免外部侵入")
        lbl_ver.setStyleSheet(f"color: {theme.TEXT_GRAY600}; font-size: 12px;")
        c_l.addWidget(lbl_ver)

        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet(f"color: {theme.BORDER};")
        c_l.addWidget(line)

        # 状态指示：Windows 专属项在其他平台上如实标注，不谎报就绪。
        from core.platform import IS_MAC, IS_WINDOWS
        if IS_WINDOWS:
            hook_status = "🟢 正常监听中 (无需管理员权限)"
            tts_status = "🟢 就绪 (Windows 原生秒发音)"
        elif IS_MAC:
            hook_status = "⚪ 当前平台暂不支持 (仅 Windows)"
            tts_status = "🟢 就绪 (macOS 系统 say)"
        else:
            hook_status = "⚪ 当前平台暂不支持 (仅 Windows)"
            tts_status = "🟡 需安装 espeak-ng 后可用"
        status_items = [
            ("⚡ 键盘底层钩子 (WH_KEYBOARD_LL):", hook_status),
            ("📖 本地历史记录数据库 (SQLite):", "🟢 已挂载 (history.sqlite3)"),
            ("📷 离线文字识别引擎 (RapidOCR):", "🟢 就绪 (支持中英混排离线识别)"),
            ("🔊 语音合成朗读 (TTS):", tts_status)
        ]
        for title, val in status_items:
            h = QHBoxLayout()
            h.addWidget(QLabel(title, styleSheet=f"color: {theme.TEXT_SECONDARY}; font-weight: 500; font-size: 12px;"))
            h.addStretch()
            h.addWidget(QLabel(val, styleSheet=f"color: {theme.SUCCESS_DARK}; font-weight: bold; font-size: 12px;"))
            c_l.addLayout(h)

        l.addWidget(card)
        l.addStretch()
        return container

    # ---------------- 逻辑与事件绑定 ----------------
    def _on_engine_mode_changed(self, idx: int):
        self.card_llm.setVisible(idx == 1)

    def _toggle_key_visibility(self):
        if self.txt_key.echoMode() == QLineEdit.Password:
            self.txt_key.setEchoMode(QLineEdit.Normal)
            self.btn_toggle_key.setText("🙈 隐藏密钥")
        else:
            self.txt_key.setEchoMode(QLineEdit.Password)
            self.btn_toggle_key.setText("👁️ 显示密钥")

    def _apply_preset(self, idx: int):
        if idx == 0:
            return
        name = self.cmb_preset.currentText()
        cfg = PRESETS.get(name)
        if cfg:
            self.txt_url.setText(cfg["url"])
            self.txt_model.setText(cfg["model"])
            if cfg.get("prompt"):
                self.txt_prompt.setPlainText(cfg["prompt"])
            self.lbl_status.setText(f"已填入 {name} 预设模板，请输入您的 API Key 后保存")

    def _apply_prompt_template(self, idx: int):
        if idx == 0:
            return
        tpl_name = self.cmb_prompt_tpl.currentText()
        content = PROMPT_TEMPLATES.get(tpl_name)
        if content:
            self.txt_prompt.setPlainText(content)

    def _load_values(self):
        # 热键行：配置里的非法/重复项在 normalize 里已回退，这里如实显示回退结果。
        self._hotkey_values = normalize_hotkeys(self.config.get("hotkeys"))
        if hasattr(self, "_hotkey_badges"):
            self._refresh_hotkey_rows()
        if hasattr(self, "btn_go_main"):
            self.btn_go_main.setText(f"🖥️ 打开主工作台 ({self._hotkey_values['workbench']})")
        self.chk_triple_space.setChecked(self.config.get("triple_space_enabled", True))
        inv = self.config.get("max_interval_ms", 750)
        self.spn_interval.setValue(inv)
        self.slider_interval.setValue(inv)

        is_llm = self.config.get("engine", "free") == "llm"
        self.cmb_engine.setCurrentIndex(1 if is_llm else 0)
        self.card_llm.setVisible(is_llm)

        self.txt_url.setText(self.config.get("llm_api_url", "https://api.deepseek.com/v1"))
        self.txt_key.setText(self.config.get("llm_api_key", ""))
        self.txt_model.setText(self.config.get("llm_model", "deepseek-chat"))
        self.txt_prompt.setPlainText(self.config.get("llm_prompt", DEFAULT_CONFIG["llm_prompt"]))

    def _gather_config(self) -> dict:
        return {
            "engine": "llm" if self.cmb_engine.currentIndex() == 1 else "free",
            "hotkeys": dict(getattr(self, "_hotkey_values", normalize_hotkeys(self.config.get("hotkeys")))),
            "triple_space_enabled": self.chk_triple_space.isChecked(),
            "max_interval_ms": self.spn_interval.value(),
            "llm_api_url": self.txt_url.text().strip(),
            "llm_api_key": self.txt_key.text().strip(),
            "llm_model": self.txt_model.text().strip(),
            "llm_prompt": self.txt_prompt.toPlainText().strip()
        }

    def _test_translation(self):
        self.lbl_status.setText("正在测试连接翻译中...")
        from core.translator import TranslationManager
        cfg = self._gather_config()
        mgr = TranslationManager(cfg)
        test_src = "今天天气真好，一起去公园散步吧。"

        is_llm = cfg.get("engine") == "llm"
        model_name = cfg.get("llm_model", "deepseek-chat")
        mode_desc = f"大模型 Pro 通道 ({model_name})" if is_llm else "内置免费极速通道 (免Key)"

        start_time = time.time()
        try:
            res = mgr.translate_to_en(test_src)
            elapsed_ms = int((time.time() - start_time) * 1000)
            self.lbl_status.setText(f"✓ 测试成功！通道响应正常 ({elapsed_ms}ms)")
            
            dlg = TranslationTestDialog(
                parent=self,
                is_success=True,
                source_text=test_src,
                target_text=res,
                mode_name=mode_desc,
                elapsed_ms=elapsed_ms
            )
            dlg.exec()
        except Exception as e:
            elapsed_ms = int((time.time() - start_time) * 1000)
            self.lbl_status.setText("❌ 测试失败，请检查网络或参数")
            
            dlg = TranslationTestDialog(
                parent=self,
                is_success=False,
                source_text=test_src,
                mode_name=mode_desc,
                elapsed_ms=elapsed_ms,
                error_msg=str(e)
            )
            dlg.exec()

    def _save_and_apply(self):
        if self._recording_action is not None:
            self._cancel_recording()
        new_cfg = self._gather_config()
        err = validate_hotkeys(new_cfg.get("hotkeys"))
        if err:
            QMessageBox.warning(self, "热键无效", err + "，请重新录制后再保存。")
            return
        self.config = new_cfg
        save_config(new_cfg)
        self.config_changed.emit(new_cfg)
        if hasattr(self, "btn_go_main"):
            self.btn_go_main.setText(f"🖥️ 打开主工作台 ({new_cfg['hotkeys']['workbench']})")
        self.lbl_status.setText("✓ 配置已保存并实时生效")
        QMessageBox.information(self, "保存成功", "所有偏好配置已成功保存并立即生效！")
        self.hide()
