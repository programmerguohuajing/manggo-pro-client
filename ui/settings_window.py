"""
现代化偏好设置中心 (Manggo Pro Preferences)
采用现代卡片式与侧边导航布局，具备精致的芒果琥珀主题视觉、服务商一键预设与状态监控。
"""
import os
import json
import time
import webbrowser
from typing import Callable
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtWidgets import (
    QWidget, QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QComboBox, QSpinBox, QSlider, QPushButton, QCheckBox, QFrame,
    QMessageBox, QTextEdit, QStackedWidget, QListWidget, QListWidgetItem,
    QGraphicsDropShadowEffect, QScrollArea, QSizePolicy
)
from PySide6.QtGui import QFont, QIcon, QColor, QPainter, QPixmap
import pyperclip
from core.tts import tts_player

CONFIG_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.json")

DEFAULT_CONFIG = {
    "engine": "free",  # "free" 或 "llm"
    "triple_space_enabled": True,
    "max_interval_ms": 550,
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
        print(f"[Config] Error saving config: {e}")

SETTINGS_STYLESHEET = """
QWidget#SettingsWindow {
    background-color: #F8F9FB;
    font-family: -apple-system, "Segoe UI", "Microsoft YaHei", sans-serif;
}

/* 侧边导航栏 */
QListWidget#NavList {
    background-color: #FFFFFF;
    border: none;
    border-right: 1px solid #E5E7EB;
    outline: none;
    padding-top: 14px;
}
QListWidget#NavList::item {
    height: 44px;
    margin: 4px 10px;
    padding-left: 14px;
    border-radius: 8px;
    color: #4B5563;
    font-size: 13px;
    font-weight: 500;
}
QListWidget#NavList::item:hover {
    background-color: #FFF7ED;
    color: #EA580C;
}
QListWidget#NavList::item:selected {
    background-color: #FFEDD5;
    color: #C2410C;
    font-weight: bold;
}

/* 卡片容器 */
QFrame.CardFrame {
    background-color: #FFFFFF;
    border: 1px solid #E5E7EB;
    border-radius: 12px;
    padding: 16px 18px;
}
QFrame.CardFrame:hover {
    border-color: #FDBA74;
}

/* 标题规范 */
QLabel.SectionTitle {
    font-size: 14px;
    font-weight: bold;
    color: #1F2937;
}
QLabel.SectionDesc {
    font-size: 12px;
    color: #6B7280;
    line-height: 1.4;
}
QLabel.FieldLabel {
    font-size: 12px;
    font-weight: 600;
    color: #374151;
}

/* 输入框与下拉框 */
QLineEdit, QComboBox, QSpinBox, QTextEdit {
    background-color: #FFFFFF;
    border: 1px solid #D1D5DB;
    border-radius: 6px;
    padding: 7px 10px;
    font-size: 12px;
    color: #111827;
    selection-background-color: #F97316;
}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QTextEdit:focus {
    border: 1.5px solid #EA580C;
    background-color: #FFFAF5;
}
QComboBox::drop-down {
    border: none;
    width: 24px;
}

/* 按钮规范 */
QPushButton.PrimaryBtn {
    background-color: #EA580C;
    color: #FFFFFF;
    font-size: 13px;
    font-weight: 600;
    border: none;
    border-radius: 7px;
    padding: 8px 20px;
}
QPushButton.PrimaryBtn:hover {
    background-color: #C2410C;
}
QPushButton.PrimaryBtn:pressed {
    background-color: #9A3412;
}

QPushButton.SecondaryBtn {
    background-color: #FFFFFF;
    color: #374151;
    font-size: 12px;
    font-weight: 500;
    border: 1px solid #D1D5DB;
    border-radius: 6px;
    padding: 6px 14px;
}
QPushButton.SecondaryBtn:hover {
    background-color: #F3F4F6;
    border-color: #9CA3AF;
}

QPushButton.TextBtn {
    background: transparent;
    color: #EA580C;
    font-size: 12px;
    font-weight: 500;
    border: none;
    padding: 4px 8px;
}
QPushButton.TextBtn:hover {
    text-decoration: underline;
}

/* 复选框样式 */
QCheckBox {
    font-size: 13px;
    color: #1F2937;
    spacing: 8px;
}
QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border-radius: 4px;
    border: 1px solid #D1D5DB;
    background: #FFFFFF;
}
QCheckBox::indicator:hover {
    border-color: #EA580C;
}
QCheckBox::indicator:checked {
    background-color: #EA580C;
    border-color: #EA580C;
    image: none;
}

/* 滑块样式 */
QSlider::groove:horizontal {
    height: 6px;
    background: #E5E7EB;
    border-radius: 3px;
}
QSlider::sub-page:horizontal {
    background: #EA580C;
    border-radius: 3px;
}
QSlider::handle:horizontal {
    background: #FFFFFF;
    border: 2px solid #EA580C;
    width: 16px;
    height: 16px;
    margin: -5px 0;
    border-radius: 8px;
}
QSlider::handle:horizontal:hover {
    background: #FFEDD5;
}
"""

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
        lbl_title.setStyleSheet("color: #EA580C;")
        header.addWidget(lbl_title)

        header.addStretch()

        # 状态小胶囊
        lbl_badge = QLabel(f"● 连通正常 ({elapsed_ms}ms)" if is_success else "● 连接异常", self)
        if is_success:
            lbl_badge.setStyleSheet("background: #DCFCE7; color: #15803D; font-weight: bold; padding: 4px 10px; border-radius: 12px; font-size: 11px;")
        else:
            lbl_badge.setStyleSheet("background: #FEE2E2; color: #B91C1C; font-weight: bold; padding: 4px 10px; border-radius: 12px; font-size: 11px;")
        header.addWidget(lbl_badge)
        root.addLayout(header)

        # 通道模式与指标条
        metrics_bar = QFrame(self)
        metrics_bar.setStyleSheet("background: #F3F4F6; border-radius: 8px; padding: 4px 12px;")
        m_layout = QHBoxLayout(metrics_bar)
        m_layout.setContentsMargins(8, 6, 8, 6)

        lbl_mode = QLabel(f"🌐 激活通道: {mode_name}", metrics_bar)
        lbl_mode.setStyleSheet("color: #374151; font-size: 12px; font-weight: 500;")
        m_layout.addWidget(lbl_mode)

        m_layout.addStretch()

        lbl_speed = QLabel(f"⏱️ 耗时: {elapsed_ms} ms" if is_success else "❌ 请求失败", metrics_bar)
        lbl_speed.setStyleSheet("color: #6B7280; font-size: 11px;")
        m_layout.addWidget(lbl_speed)
        root.addWidget(metrics_bar)

        if is_success:
            # 2. 原文卡片
            card_src = QFrame(self)
            card_src.setStyleSheet("background: #FFFFFF; border: 1px solid #E5E7EB; border-radius: 10px; padding: 10px;")
            cs_layout = QVBoxLayout(card_src)
            cs_layout.setSpacing(6)

            h_src_top = QHBoxLayout()
            lbl_src_tag = QLabel("🇨🇳 原文 (中文)", card_src)
            lbl_src_tag.setStyleSheet("color: #4B5563; font-size: 11px; font-weight: bold;")
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
            txt_src.setStyleSheet("background: #F9FAFB; border: 1px solid #E5E7EB; border-radius: 6px; padding: 6px; font-size: 12px; color: #1F2937;")
            cs_layout.addWidget(txt_src)
            root.addWidget(card_src)

            # 3. 译文卡片
            card_tgt = QFrame(self)
            card_tgt.setStyleSheet("background: #FFFFFF; border: 1px solid #FDBA74; border-radius: 10px; padding: 10px;")
            ct_layout = QVBoxLayout(card_tgt)
            ct_layout.setSpacing(6)

            h_tgt_top = QHBoxLayout()
            lbl_tgt_tag = QLabel("🇬🇧 译文 (English)", card_tgt)
            lbl_tgt_tag.setStyleSheet("color: #EA580C; font-size: 11px; font-weight: bold;")
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
            txt_tgt.setStyleSheet("background: #FFFAF5; border: 1.5px solid #EA580C; border-radius: 6px; padding: 6px; font-size: 13px; font-weight: 500; color: #111827;")
            ct_layout.addWidget(txt_tgt)
            root.addWidget(card_tgt)
        else:
            # 异常详情卡片
            card_err = QFrame(self)
            card_err.setStyleSheet("background: #FFF5F5; border: 1.5px solid #FEB2B2; border-radius: 10px; padding: 12px;")
            ce_layout = QVBoxLayout(card_err)
            ce_layout.setSpacing(8)

            lbl_err_title = QLabel("⚠️ 通道异常报错信息", card_err)
            lbl_err_title.setStyleSheet("color: #C53030; font-weight: bold; font-size: 13px;")
            ce_layout.addWidget(lbl_err_title)

            txt_err = QTextEdit(card_err)
            txt_err.setPlainText(error_msg)
            txt_err.setReadOnly(True)
            txt_err.setFixedHeight(90)
            txt_err.setStyleSheet("background: #FFFFFF; border: 1px solid #FEB2B2; border-radius: 6px; padding: 6px; font-size: 11px; color: #742A2A;")
            ce_layout.addWidget(txt_err)

            lbl_err_hint = QLabel("💡 排查建议：\n1. 若为大模型 Pro 通道，请确认 API Key 是否有效且账户有余额；\n2. 检查 Base URL 是否正确（官方 OpenAI/DeepSeek 需包含 /v1）；\n3. 确认网络连接或代理设置正常。", card_err)
            lbl_err_hint.setStyleSheet("color: #9B2C2C; font-size: 11px; line-height: 1.4;")
            ce_layout.addWidget(lbl_err_hint)
            root.addWidget(card_err)

        # 4. 底部操作栏
        footer = QHBoxLayout()
        lbl_foot_info = QLabel("通道就绪后，可在任意界面随时使用 3 次空格就地转译或 Alt+D 划词翻译。" if is_success else "请修改参数后再次测试。", self)
        lbl_foot_info.setStyleSheet("color: #6B7280; font-size: 11px;")
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

class SettingsWindow(QWidget):
    config_changed = Signal(dict)
    open_main_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("SettingsWindow")
        self.setWindowTitle("Manggo Pro - 偏好设置")
        self.resize(720, 600)
        self.setMinimumSize(680, 560)
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
        header.setStyleSheet("background-color: #FFFFFF; border-bottom: 1px solid #E5E7EB;")
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(20, 0, 20, 0)

        lbl_logo = QLabel("🥭 Manggo Pro", header)
        lbl_logo.setFont(QFont("Microsoft YaHei", 14, QFont.Bold))
        lbl_logo.setStyleSheet("color: #EA580C;")
        h_layout.addWidget(lbl_logo)

        lbl_sub = QLabel("偏好设置与通道配置", header)
        lbl_sub.setStyleSheet("color: #6B7280; font-size: 13px; margin-left: 8px;")
        h_layout.addWidget(lbl_sub)

        h_layout.addStretch()

        btn_go_main = QPushButton("🖥️ 打开主工作台 (Alt+D)", header)
        btn_go_main.setProperty("class", "SecondaryBtn")
        btn_go_main.clicked.connect(self.open_main_requested.emit)
        h_layout.addWidget(btn_go_main)

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
        footer.setStyleSheet("background-color: #FFFFFF; border-top: 1px solid #E5E7EB;")
        f_layout = QHBoxLayout(footer)
        f_layout.setContentsMargins(20, 0, 20, 0)

        self.lbl_status = QLabel("", footer)
        self.lbl_status.setStyleSheet("color: #059669; font-size: 12px; font-weight: 500;")
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
        line.setStyleSheet("color: #F3F4F6;")
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
        lbl_tip.setStyleSheet("font-size: 11px; color: #9CA3AF;")
        c_layout.addWidget(lbl_tip)

        l.addWidget(card)

        # 机制提示卡片
        tip_card = QFrame()
        tip_card.setProperty("class", "CardFrame")
        tip_card.setStyleSheet("background-color: #FFFBEB; border-color: #FDE68A;")
        t_l = QVBoxLayout(tip_card)
        lbl_tip_title = QLabel("💡 贴心使用提示")
        lbl_tip_title.setStyleSheet("font-weight: bold; color: #92400E; font-size: 13px;")
        t_l.addWidget(lbl_tip_title)

        lbl_tip_content = QLabel("1. 支持两种触发模式：已手动划选文本时，连按 3 次空格直接转译选中文本；光标在行尾时，自动捕捉并替换光标前的中文片段。\n2. 转译过程中右下角伴有呼吸气泡通知，不抢占当前焦点，不打断您的打字心流。")
        lbl_tip_content.setStyleSheet("color: #B45309; font-size: 12px; line-height: 1.5;")
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
        container = QWidget()
        l = QVBoxLayout(container)
        l.setContentsMargins(24, 20, 24, 20)
        l.setSpacing(14)

        card = QFrame()
        card.setProperty("class", "CardFrame")
        c_layout = QVBoxLayout(card)
        c_layout.setSpacing(12)

        lbl_t = QLabel("全局热键速查表")
        lbl_t.setProperty("class", "SectionTitle")
        c_layout.addWidget(lbl_t)

        hotkeys = [
            ("连续 3 次空格 (Space)", "输入框就地转译", "在任意光标输入框输入中文后连击 3 次空格即可就地替换为英文"),
            ("Alt + Q", "划词悬浮翻译", "鼠标高亮划选任意屏幕文本后按下，呼出多功能悬浮翻译卡片"),
            ("Alt + W", "截图 OCR 翻译", "全屏十字光标拖拽框选，毫秒级提取图像中文字并翻译对照"),
            ("Alt + D", "呼出翻译工作台", "双栏沉浸式翻译面板，中英互译、生词本与长文本翻译"),
            ("Ctrl + Enter", "工作台立即翻译", "在主翻译面板编辑框内一键提交翻译请求")
        ]

        for key, name, desc in hotkeys:
            row = QFrame()
            row.setStyleSheet("background-color: #F9FAFB; border-radius: 8px; padding: 6px 10px;")
            r_l = QHBoxLayout(row)
            r_l.setContentsMargins(8, 4, 8, 4)

            lbl_badge = QLabel(key)
            lbl_badge.setStyleSheet("background: #EA580C; color: white; font-weight: bold; padding: 3px 8px; border-radius: 4px; font-size: 11px;")
            r_l.addWidget(lbl_badge)

            lbl_name = QLabel(name)
            lbl_name.setStyleSheet("font-weight: bold; color: #1F2937; font-size: 12px; margin-left: 6px;")
            r_l.addWidget(lbl_name)

            r_l.addStretch()

            lbl_d = QLabel(desc)
            lbl_d.setStyleSheet("color: #6B7280; font-size: 11px;")
            r_l.addWidget(lbl_d)

            c_layout.addWidget(row)

        l.addWidget(card)
        l.addStretch()
        return container

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
        lbl_app_name.setStyleSheet("color: #EA580C;")
        c_l.addWidget(lbl_app_name)

        lbl_ver = QLabel("版本号: v2.0 Pro Edition | 纯本地运行 | 免外部侵入")
        lbl_ver.setStyleSheet("color: #4B5563; font-size: 12px;")
        c_l.addWidget(lbl_ver)

        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("color: #E5E7EB;")
        c_l.addWidget(line)

        # 状态指示
        status_items = [
            ("⚡ 键盘底层钩子 (WH_KEYBOARD_LL):", "🟢 正常监听中 (无需管理员权限)"),
            ("📖 本地历史记录数据库 (SQLite):", "🟢 已挂载 (history.sqlite3)"),
            ("📷 离线文字识别引擎 (RapidOCR):", "🟢 就绪 (支持中英混排离线识别)"),
            ("🔊 离线语音合成朗读 (SAPI TTS):", "🟢 就绪 (Windows 原生秒发音)")
        ]
        for title, val in status_items:
            h = QHBoxLayout()
            h.addWidget(QLabel(title, styleSheet="color: #374151; font-weight: 500; font-size: 12px;"))
            h.addStretch()
            h.addWidget(QLabel(val, styleSheet="color: #059669; font-weight: bold; font-size: 12px;"))
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
        self.chk_triple_space.setChecked(self.config.get("triple_space_enabled", True))
        inv = self.config.get("max_interval_ms", 550)
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
        new_cfg = self._gather_config()
        self.config = new_cfg
        save_config(new_cfg)
        self.config_changed.emit(new_cfg)
        self.lbl_status.setText("✓ 配置已保存并实时生效")
        QMessageBox.information(self, "保存成功", "所有偏好配置已成功保存并立即生效！")
        self.hide()
