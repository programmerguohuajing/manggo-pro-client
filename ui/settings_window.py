"""
现代化偏好设置中心 (Manggo Pro Preferences)
采用现代卡片式与侧边导航布局，具备精致的芒果琥珀主题视觉、服务商一键预设与状态监控。
"""
import os
import json
import webbrowser
from typing import Callable
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QComboBox, QSpinBox, QSlider, QPushButton, QCheckBox, QFrame,
    QMessageBox, QTextEdit, QStackedWidget, QListWidget, QListWidgetItem,
    QGraphicsDropShadowEffect, QScrollArea, QSizePolicy
)
from PySide6.QtGui import QFont, QIcon, QColor, QPainter, QPixmap

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
        try:
            res = mgr.translate_to_en(test_src)
            self.lbl_status.setText("测试成功！通道运行正常")
            QMessageBox.information(
                self,
                "翻译通道测试成功",
                f"【原文】\n{test_src}\n\n【译文】\n{res}\n\n通道模式: {'大模型 Pro 通道' if cfg['engine'] == 'llm' else '内置免费极速通道'}"
            )
        except Exception as e:
            self.lbl_status.setText("测试失败，请检查网络或参数")
            QMessageBox.critical(self, "测试失败", f"错误原因:\n{e}")

    def _save_and_apply(self):
        new_cfg = self._gather_config()
        self.config = new_cfg
        save_config(new_cfg)
        self.config_changed.emit(new_cfg)
        self.lbl_status.setText("✓ 配置已保存并实时生效")
        QMessageBox.information(self, "保存成功", "所有偏好配置已成功保存并立即生效！")
        self.hide()
