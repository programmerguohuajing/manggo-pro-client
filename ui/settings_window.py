"""
现代化偏好设置中心 (Manggo Pro Preferences)
采用现代卡片式与侧边导航布局，具备精致的芒果琥珀主题视觉、服务商一键预设与状态监控。
"""
import os
import sys
import json
import subprocess
import tempfile
import time
import webbrowser
from typing import Callable
from PySide6.QtCore import Qt, Signal, QSize, QEvent, QThread
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
from core.version import get_version, get_channel
from core import updater
from core.settings_search import section_matches


class _UpdateWorker(QThread):
    """在线更新的后台线程：网络请求不在 UI 线程做，避免界面卡死。

    mode="check" 时拉最新 Release；mode="download" 时下载指定安装包。
    done 统一发 dict：{"ok": True, ...} 或 {"ok": False, "error": ...}。
    """

    progress = Signal(int)
    done = Signal(dict)

    def __init__(self, mode, asset=None, parent=None):
        super().__init__(parent)
        self.mode = mode
        self.asset = asset

    def run(self):
        try:
            if self.mode == "check":
                release = updater.fetch_latest()
                self.done.emit({"ok": True, "release": release})
                return
            asset = self.asset or {}
            name = asset.get("name", "ManggoProClient-update")
            if get_channel() == "安装版" and name.endswith(".exe"):
                dest = os.path.join(tempfile.gettempdir(), name)
            else:
                dest = os.path.join(updater.download_dir(), name)
            updater.download(
                asset.get("url", ""), dest, progress_cb=self.progress.emit
            )
            self.done.emit({"ok": True, "path": dest})
        except Exception as e:
            self.done.emit({"ok": False, "error": str(e)})

from core.paths import data_file as _data_file

CONFIG_FILE = _data_file(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.json"))

DEFAULT_CONFIG = {
    "engine": "free",  # "free" 或 "llm"
    "hotkeys": dict(DEFAULT_HOTKEYS),
    "triple_space_enabled": True,
    "auto_start": False,
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
        lbl_title = QLabel("Manggo 通道测试诊断", self)
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

            btn_src_tts = QPushButton("朗读", card_src)
            btn_src_tts.setProperty("class", "SecondaryBtn")
            btn_src_tts.clicked.connect(lambda: tts_player.speak(self.source_text))
            h_src_top.addWidget(btn_src_tts)

            btn_src_copy = QPushButton("复制", card_src)
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

            btn_tgt_tts = QPushButton("朗读", card_tgt)
            btn_tgt_tts.setProperty("class", "SecondaryBtn")
            btn_tgt_tts.clicked.connect(lambda: tts_player.speak(self.target_text))
            h_tgt_top.addWidget(btn_tgt_tts)

            btn_tgt_copy = QPushButton("复制译文", card_tgt)
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

            lbl_err_hint = QLabel("排查建议：\n1. 若为大模型 Pro 通道，请确认 API Key 是否有效且账户有余额；\n2. 检查 Base URL 是否正确（官方 OpenAI/DeepSeek 需包含 /v1）；\n3. 确认网络连接或代理设置正常。", card_err)
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
            btn_copy_all = QPushButton("复制结果", self)
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

def _qt_key_name(key: int):
    """把 Qt 按键码转成热键主键名；不支持的键返回 None。"""
    if 0x41 <= key <= 0x5A or 0x30 <= key <= 0x39:
        return chr(key)
    if key == 0x20:
        return "Space"
    if 0x01000030 <= key <= 0x0100003B:  # F1-F12
        return f"F{key - 0x01000030 + 1}"
    return None


class ClickableLabel(QLabel):
    """可点的徽章：点按即进入热键编辑（仅 Windows 下创建）。"""
    clicked = Signal()

    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class HotkeyEdit(QLineEdit):
    """热键编辑框：按键实时反填组合键，Enter 确认，Esc 取消，失焦取消。

    这里不调用父类 keyPressEvent，所以按键不会落成文本；
    修饰键单独按下时忽略，等主键；自动重复忽略。
    """
    confirmed = Signal()
    cancelled = Signal()
    invalid = Signal(str)

    def keyPressEvent(self, event):
        key = event.key()
        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.confirmed.emit()
            return
        if key == Qt.Key.Key_Escape:
            self.cancelled.emit()
            return
        if event.isAutoRepeat():
            return
        if key in (Qt.Key.Key_Alt, Qt.Key.Key_Control, Qt.Key.Key_Shift,
                   Qt.Key.Key_Meta, Qt.Key.Key_AltGr, Qt.Key.Key_CapsLock):
            return
        mods = []
        m = event.modifiers()
        if m & Qt.KeyboardModifier.AltModifier:
            mods.append("Alt")
        if m & Qt.KeyboardModifier.ControlModifier:
            mods.append("Ctrl")
        if m & Qt.KeyboardModifier.ShiftModifier:
            mods.append("Shift")
        main = _qt_key_name(key)
        if main is None:
            self.invalid.emit("该按键不支持作为热键主键，请用字母、数字、F1-F12 或 Space。")
            return
        if not mods:
            self.invalid.emit("请带上 Alt / Ctrl / Shift 再按一次（单独按键不能做全局热键）。")
            return
        combo = "+".join(mods + [main])
        parsed = parse_hotkey(combo)
        if parsed is None:
            self.invalid.emit(f"组合键“{combo}”无效，请换一个。")
            return
        self.setText(parsed[2])

    def focusOutEvent(self, event):
        # 失焦 = 放弃本次修改；Enter 确认后收起编辑态也会触发一次，
        # 但那时 _editing_action 已清零，父类的取消处理直接返回。
        self.cancelled.emit()
        super().focusOutEvent(event)


def _checked_indicator_stylesheet() -> str:
    """选中态 √ 图片规则：白 √（assets/check_white.png）画在橙底上。

    打包版走 _MEIPASS/assets，源码运行走仓库根目录 assets；spec 已把整个
    assets 目录打进包，无需额外 datas。注意：指示器一旦被样式接管就不再画
    原生 √，这张图必须能加载，否则选中态仍是纯橙方块。
    """
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        base = sys._MEIPASS
    else:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    # Qt 样式表的 image: url() 不解析 file://，必须用裸路径；加引号防空格
    #（如 Program Files），反斜杠统一成正斜杠。
    path = os.path.join(base, "assets", "check_white.png").replace("\\", "/")
    return f"""
QCheckBox::indicator:checked {{
    image: url("{path}");
}}
"""


def _combo_arrow_stylesheet() -> str:
    """下拉箭头图片规则：QComboBox 一旦被样式表接管（::drop-down 写了
    规则），Qt 就不再画默认 ▼，必须显式给 ::down-arrow 配图，否则
    字段右侧只有一块空白（离屏复现已证实）。路径解析与 √ 规则同款：
    打包版 _MEIPASS/assets，源码版仓库根 assets；spec 已打包整个 assets。"""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        base = sys._MEIPASS
    else:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = os.path.join(base, "assets", "chevron_down.png").replace("\\", "/")
    return f"""
QComboBox::down-arrow {{
    image: url("{path}");
    width: 14px;
    height: 14px;
}}
"""


class SettingsWindow(QWidget):
    config_changed = Signal(dict)
    open_main_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("SettingsWindow")
        self.setWindowTitle("Manggo Pro - 偏好设置")
        self.resize(860, 640)
        self.setMinimumSize(760, 600)
        self.setStyleSheet(SETTINGS_STYLESHEET + _checked_indicator_stylesheet() + _combo_arrow_stylesheet())

        self.config = load_config()
        # _load_values 期间的控件赋值不算“未保存更改”。
        self._loading = True

        self._init_ui()
        self._load_values()
        self._loading = False

    def _init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # 1. 顶部 Header 栏（V2：标题 + 搜索 + 打开主工作台；运行中状态
        # 不放这里——暂停状态在托盘手里，设置页拿不到，接它要改主程序
        # 状态管线，不属于纯布局范围；通道信息在引擎分区第一行可见。）
        header = QFrame(self)
        header.setFixedHeight(64)
        header.setObjectName("SettingsHeader")
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(28, 0, 28, 0)

        lbl_title = QLabel("偏好设置", header)
        lbl_title.setFont(QFont("Microsoft YaHei", 16, QFont.Bold))
        lbl_title.setStyleSheet(f"color: {theme.INK};")
        h_layout.addWidget(lbl_title)

        lbl_wordmark = QLabel("Manggo Pro", header)
        lbl_wordmark.setStyleSheet(f"color: {theme.WARM_GRAY}; font-size: 13px; margin-left: 6px;")
        h_layout.addWidget(lbl_wordmark)

        h_layout.addStretch()

        self._search = QLineEdit(header)
        self._search.setProperty("class", "SearchBox")
        self._search.setPlaceholderText("搜索设置")
        self._search.setFixedWidth(200)
        self._search.textChanged.connect(self._apply_search)
        h_layout.addWidget(self._search)

        self.btn_go_main = QPushButton("打开主工作台 (Alt+M)", header)
        self.btn_go_main.setProperty("class", "SecondaryBtn")
        self.btn_go_main.clicked.connect(self.open_main_requested.emit)
        h_layout.addWidget(self.btn_go_main)

        root_layout.addWidget(header)

        # 2. 中间主体区（V2：左侧分区导航 + 右侧单页滚动，不再切页）
        body = QWidget(self)
        b_layout = QHBoxLayout(body)
        b_layout.setContentsMargins(0, 0, 0, 0)
        b_layout.setSpacing(0)

        # 侧边栏：只剩标题文字，不要下面那行小字。
        self.nav_list = QListWidget(body)
        self.nav_list.setObjectName("NavList")
        self.nav_list.setFixedWidth(168)
        self._nav_keys = ["engine", "trigger", "hotkeys", "about"]
        for title in ["翻译通道", "触发方式", "全局热键", "关于与状态"]:
            self.nav_list.addItem(QListWidgetItem(title))
        self.nav_list.setCurrentRow(0)
        self.nav_list.currentRowChanged.connect(self._on_nav_changed)
        b_layout.addWidget(self.nav_list)

        # 单页滚动区：四个分区按使用频率排，一页看完。
        self._scroll = QScrollArea(body)
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.NoFrame)
        self._scroll.setStyleSheet("background: transparent;")
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(4, 20, 28, 20)
        content_layout.setSpacing(30)

        self._sections = []
        builders = [
            ("engine", "翻译通道", "选择翻译通道，配置大模型 API 参数；内置通道开箱即用，无需 Key。", self._build_engine_tab),
            ("trigger", "触发方式", "连击空格就地转译的开关与灵敏度。", self._build_trigger_tab),
            ("hotkeys", "全局热键", "点组合键可直接修改，保存后立即生效。", self._build_hotkeys_tab),
            ("about", "关于与状态", "版本、更新、开机自启与各模块运行状态。", self._build_about_tab),
        ]
        for key, title, desc, builder in builders:
            section = QWidget()
            s_layout = QVBoxLayout(section)
            s_layout.setContentsMargins(0, 0, 0, 0)
            s_layout.setSpacing(8)
            lbl_head = QLabel(title)
            lbl_head.setProperty("class", "SectionHead")
            lbl_head.setStyleSheet("padding-left: 24px;")
            s_layout.addWidget(lbl_head)
            lbl_desc = QLabel(desc)
            lbl_desc.setProperty("class", "SectionDesc")
            lbl_desc.setStyleSheet("padding-left: 24px;")
            lbl_desc.setWordWrap(True)
            s_layout.addWidget(lbl_desc)
            s_layout.addWidget(builder())
            content_layout.addWidget(section)
            self._sections.append((key, section))
        content_layout.addStretch()

        self._no_result = QLabel("没有找到相关设置，换个词试试。")
        self._no_result.setStyleSheet(f"color: {theme.WARM_GRAY}; font-size: 13px; padding-left: 24px;")
        self._no_result.setVisible(False)
        content_layout.addWidget(self._no_result)

        self._scroll.setWidget(content)
        self._scroll.verticalScrollBar().valueChanged.connect(self._on_scroll_changed)
        self._navigating = False
        b_layout.addWidget(self._scroll, 1)
        root_layout.addWidget(body, 1)

        # 3. 底部操作栏（主按钮按用户定保持琥珀色 PrimaryBtn）
        footer = QFrame(self)
        footer.setFixedHeight(62)
        footer.setObjectName("SettingsFooter")
        f_layout = QHBoxLayout(footer)
        f_layout.setContentsMargins(28, 0, 28, 0)

        self.lbl_status = QLabel("", footer)
        self.lbl_status.setStyleSheet(f"color: {theme.SUCCESS_DARK}; font-size: 12px; font-weight: 500;")
        f_layout.addWidget(self.lbl_status)

        f_layout.addStretch()

        self.lbl_dirty = QLabel("● 有未保存更改", footer)
        self.lbl_dirty.setStyleSheet(f"color: {theme.ACCENT}; font-size: 12px;")
        self.lbl_dirty.setVisible(False)
        f_layout.addWidget(self.lbl_dirty)

        self.btn_test = QPushButton("测试当前翻译", footer)
        self.btn_test.setProperty("class", "SecondaryBtn")
        self.btn_test.clicked.connect(self._test_translation)
        f_layout.addWidget(self.btn_test)

        self.btn_save = QPushButton("保存并应用", footer)
        self.btn_save.setProperty("class", "PrimaryBtn")
        self.btn_save.clicked.connect(self._save_and_apply)
        f_layout.addWidget(self.btn_save)

        root_layout.addWidget(footer)
        self._connect_dirty_signals()

    def _on_nav_changed(self, idx: int):
        """点左侧分区：滚到对应分区（锚点，不是切页）。"""
        # 导航在分区建好之前就会触发一次初始选中，先放行。
        if not hasattr(self, "_sections"):
            return
        if idx < 0 or idx >= len(self._sections):
            return
        section = self._sections[idx][1]
        if not section.isVisible():
            return
        bar = self._scroll.verticalScrollBar()
        self._navigating = True
        try:
            if section.y() > 0:
                bar.setValue(section.y())
            else:
                self._scroll.ensureWidgetVisible(section)
        finally:
            self._navigating = False

    def _on_scroll_changed(self, value: int):
        """手动滚动时反向高亮左侧分区；锚点跳转触发的滚动不参与。"""
        if self._navigating:
            return
        current = 0
        for i, (_, section) in enumerate(self._sections):
            if section.isVisible() and section.y() <= value + 10:
                current = i
        if self.nav_list.currentRow() != current:
            self.nav_list.blockSignals(True)
            try:
                self.nav_list.setCurrentRow(current)
            finally:
                self.nav_list.blockSignals(False)

    def _apply_search(self, text: str):
        """搜索框过滤分区；搜不到时显示一行提示，不留白页。"""
        visible_count = 0
        for i, (key, section) in enumerate(self._sections):
            visible = section_matches(key, text)
            section.setVisible(visible)
            self.nav_list.item(i).setHidden(not visible)
            if visible:
                visible_count += 1
        self._no_result.setVisible(bool(text.strip()) and visible_count == 0)
        self._scroll.verticalScrollBar().setValue(0)

    def _mark_dirty(self):
        if not getattr(self, "_loading", False):
            self.lbl_dirty.setVisible(True)

    def _connect_dirty_signals(self):
        """值一改就亮底部“有未保存更改”；保存成功后熄灭。"""
        self.chk_triple_space.toggled.connect(lambda _: self._mark_dirty())
        self.slider_interval.valueChanged.connect(lambda _: self._mark_dirty())
        self.spn_interval.valueChanged.connect(lambda _: self._mark_dirty())
        self.cmb_engine.currentIndexChanged.connect(lambda _: self._mark_dirty())
        self.cmb_preset.currentIndexChanged.connect(lambda _: self._mark_dirty())
        self.cmb_prompt_tpl.currentIndexChanged.connect(lambda _: self._mark_dirty())
        self.txt_url.textChanged.connect(lambda _: self._mark_dirty())
        self.txt_key.textChanged.connect(lambda _: self._mark_dirty())
        self.txt_model.textChanged.connect(lambda _: self._mark_dirty())
        self.txt_prompt.textChanged.connect(lambda: self._mark_dirty())
        if hasattr(self, "chk_auto_start"):
            self.chk_auto_start.toggled.connect(lambda _: self._mark_dirty())

    def _set_update_dot(self, visible: bool):
        """关于项右上角的琥珀小圆点：只在检查到新版后出现，
        平时不亮——不做开机自动检查时，不知道有没有新版就不能无故亮点。"""
        item = self.nav_list.item(3)
        if visible:
            pixmap = QPixmap(16, 16)
            pixmap.fill(Qt.GlobalColor.transparent)
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setBrush(QColor(theme.ACCENT))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(4, 4, 8, 8)
            painter.end()
            item.setIcon(QIcon(pixmap))
        else:
            item.setIcon(QIcon())

    # ---------------- 分区：触发方式 ----------------
    def _build_trigger_tab(self) -> QWidget:
        container = QWidget()
        l = QVBoxLayout(container)
        l.setContentsMargins(24, 20, 24, 20)
        l.setSpacing(16)

        # 主卡片: 三击空格就地转译
        card = QFrame()
        card.setProperty("class", "CardFrame")
        c_layout = QVBoxLayout(card)
        c_layout.setContentsMargins(20, 20, 20, 20)
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
        # 滑块本体离屏实测只有 15px 高，thumb 实绘 18px（16px + 1px 边框 x2），
        # 底边被裁；26px 高给 thumb 留足上下边距。
        self.slider_interval.setMinimumHeight(26)

        self.spn_interval = QSpinBox()
        self.spn_interval.setRange(300, 900)
        self.spn_interval.setSingleStep(20)
        self.spn_interval.setSuffix(" ms")
        self.spn_interval.setFixedWidth(110)

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

        # 机制提示：V2 不再是黄色卡片，改成一行素色脚注。
        # 机制提示：重设计里不再是卡片，是一行素色脚注。
        tip_card = QFrame()
        tip_card.setStyleSheet("background: transparent; border: none;")
        t_l = QVBoxLayout(tip_card)
        t_l.setContentsMargins(0, 0, 0, 0)
        lbl_tip_title = QLabel("贴心使用提示")
        lbl_tip_title.setStyleSheet(f"font-weight: 600; color: {theme.WARM_GRAY}; font-size: 12px;")
        t_l.addWidget(lbl_tip_title)

        lbl_tip_content = QLabel("1. 支持两种触发模式：已手动划选文本时，连按 3 次空格直接转译选中文本；光标在行尾时，自动捕捉并替换光标前的中文片段。\n2. 转译过程中右下角伴有呼吸气泡通知，不抢占当前焦点，不打断您的打字心流。")
        lbl_tip_content.setStyleSheet(f"color: {theme.WARM_GRAY}; font-size: 12px; line-height: 1.6;")
        lbl_tip_content.setWordWrap(True)
        t_l.addWidget(lbl_tip_content)

        l.addWidget(tip_card)
        l.addStretch()
        return container

    # ---------------- 分区：翻译引擎 ----------------
    # V2：不再包一层自己的 QScrollArea（外层已经是单页滚动，嵌套滚动
    # 会抢滚轮、压高度），直接返回内容容器；分区标题由外层统一加，
    # 这里不再重复放一个“选择转译通道模式”标题。
    def _build_engine_tab(self) -> QWidget:
        container = QWidget()
        l = QVBoxLayout(container)
        l.setContentsMargins(24, 20, 24, 20)
        l.setSpacing(14)

        # 引擎选择卡片
        card_sel = QFrame()
        card_sel.setProperty("class", "CardFrame")
        cs_l = QVBoxLayout(card_sel)
        cs_l.setContentsMargins(20, 20, 20, 20)
        cs_l.setSpacing(10)

        self.cmb_engine = QComboBox()
        setup_modern_combobox(self.cmb_engine)
        self.cmb_engine.addItems([
            "内置极速通道 (免 API Key，国内毫秒级响应，开箱即用)",
            "🧠 自定义大模型 Pro 通道 (DeepSeek / 通义千问 / OpenAI / 本地 Ollama)"
        ])
        self.cmb_engine.currentIndexChanged.connect(self._on_engine_mode_changed)
        cs_l.addWidget(self.cmb_engine)
        l.addWidget(card_sel)

        # LLM 配置卡片
        self.card_llm = QFrame()
        self.card_llm.setProperty("class", "CardFrame")
        cl_layout = QVBoxLayout(self.card_llm)
        cl_layout.setContentsMargins(20, 20, 20, 20)
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

        return container

    # ---------------- 分区：全局热键 ----------------
    # 同引擎分区，不再包自己的 QScrollArea；行内标题不重复放，
    # 修改方法说明放在卡片底部；徽章点按变输入框，Enter 确认。
    def _build_hotkeys_tab(self) -> QWidget:
        container = QWidget()
        l = QVBoxLayout(container)
        l.setContentsMargins(24, 20, 24, 20)
        l.setSpacing(14)

        card = QFrame()
        card.setProperty("class", "CardFrame")
        c_layout = QVBoxLayout(card)
        c_layout.setContentsMargins(20, 20, 20, 20)
        c_layout.setSpacing(12)

        # 待保存的组合键：点徽章改这里，点底部保存才写 config.json。
        # 非 Windows 上全局钩子不存在，徽章不可点，只作展示。
        self._hotkey_values = normalize_hotkeys(self.config.get("hotkeys"))
        self._hotkey_badges = {}
        self._hotkey_edits = {}
        self._hotkey_cancel_btns = {}
        self._hotkey_hints = {}
        self._editing_action = None

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
            # V2：行不再是浅灰小卡片，改成透明行 + 底部一根细分隔线。
            row = QFrame()
            row.setProperty("class", "HotkeyRow")
            r_l = QVBoxLayout(row)
            r_l.setContentsMargins(2, 10, 2, 10)
            r_l.setSpacing(6)

            # 顶部行：功能名称 + 快捷键徽章
            h_top = QHBoxLayout()
            lbl_name = QLabel(name)
            lbl_name.setStyleSheet(f"font-weight: bold; color: {theme.TEXT_PRIMARY}; font-size: 13px;")
            h_top.addWidget(lbl_name)

            h_top.addStretch()

            badge_text = self._hotkey_values[action] if action is not None else key_text
            # 组合键徽章：浅灰底等宽文字；Windows 下可点，点击后变成输入框。
            if action is not None and IS_WINDOWS:
                lbl_badge = ClickableLabel(badge_text)
                lbl_badge.clicked.connect(lambda _=False, a=action: self._start_hotkey_edit(a))
            else:
                lbl_badge = QLabel(badge_text)
            lbl_badge.setStyleSheet(f"background: {theme.INPUT_FILL}; color: {theme.TEXT_PRIMARY}; font-weight: 600; padding: 3px 10px; border-radius: 6px; font-size: 11px; font-family: {theme.FONT_MONO};")
            if action is not None:
                self._hotkey_badges[action] = lbl_badge
            h_top.addWidget(lbl_badge)

            if action is not None and IS_WINDOWS:
                edit = HotkeyEdit()
                edit.setText(badge_text)
                edit.setFixedWidth(160)
                edit.setStyleSheet(f"font-size: 11px; font-family: {theme.FONT_MONO};")
                edit.confirmed.connect(self._confirm_hotkey_edit)
                edit.cancelled.connect(self._cancel_hotkey_edit)
                edit.invalid.connect(lambda msg: self.lbl_hotkey_status.setText(msg))
                edit.setVisible(False)
                self._hotkey_edits[action] = edit
                h_top.addWidget(edit)

                btn_cancel = QPushButton("取消")
                btn_cancel.setStyleSheet(f"background: transparent; border: none; color: {theme.TEXT_MUTED}; font-size: 12px; padding: 4px 8px;")
                btn_cancel.clicked.connect(self._cancel_hotkey_edit)
                btn_cancel.setVisible(False)
                self._hotkey_cancel_btns[action] = btn_cancel
                h_top.addWidget(btn_cancel)
            r_l.addLayout(h_top)

            # 次行：完整说明文本（开启自适应折行，彻底杜绝文字截断）
            lbl_d = QLabel(desc)
            lbl_d.setStyleSheet(f"color: {theme.TEXT_MUTED}; font-size: 12px; line-height: 1.4;")
            lbl_d.setWordWrap(True)
            r_l.addWidget(lbl_d)

            if action is not None and IS_WINDOWS:
                lbl_hint = QLabel("正在监听按键… Enter 确认，Esc 取消。")
                lbl_hint.setStyleSheet(f"color: {theme.ACCENT}; font-size: 12px;")
                lbl_hint.setVisible(False)
                self._hotkey_hints[action] = lbl_hint
                r_l.addWidget(lbl_hint)

            c_layout.addWidget(row)

        # 修改方法说明 + 恢复默认：放在卡片底部，不随行循环重复。
        self.lbl_hotkey_status = QLabel(
            "修改方法：点组合键变成输入框后直接按下组合键（需带 Alt / Ctrl / Shift，Win 键不支持）；Enter 确认，Esc 取消。"
            if IS_WINDOWS else
            "全局热键仅支持 Windows，当前平台下组合键不可修改；这里只展示默认组合键。"
        )
        self._hotkey_method_text = self.lbl_hotkey_status.text()
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

        return container

    # ---------------- 热键点按修改 ----------------
    def _start_hotkey_edit(self, action: str):
        """点徽章 → 徽章变输入框，监听按键并实时反填。"""
        if self._editing_action is not None and self._editing_action != action:
            self._cancel_hotkey_edit()
        if self._editing_action == action:
            return
        self._editing_action = action
        self._hotkey_badges[action].setVisible(False)
        edit = self._hotkey_edits[action]
        edit.setText(self._hotkey_values[action])
        edit.setVisible(True)
        self._hotkey_cancel_btns[action].setVisible(True)
        self._hotkey_hints[action].setVisible(True)
        edit.setFocus()
        edit.selectAll()
        self.lbl_hotkey_status.setText(
            f"正在修改【{ACTION_NAMES[action]}】：直接按下新组合键，Enter 确认，Esc 取消。"
        )

    def _end_hotkey_edit(self):
        """收起编辑态（徽章回来，输入框/取消/提示隐藏），不改状态行。"""
        action = self._editing_action
        if action is None:
            return
        self._editing_action = None
        self._hotkey_edits[action].setVisible(False)
        self._hotkey_cancel_btns[action].setVisible(False)
        self._hotkey_hints[action].setVisible(False)
        self._hotkey_badges[action].setVisible(True)

    def _confirm_hotkey_edit(self):
        """Enter 确认：校验 → 查重 → 写待保存值，标记未保存。"""
        action = self._editing_action
        if action is None:
            return
        combo = self._hotkey_edits[action].text().strip()
        parsed = parse_hotkey(combo)
        if parsed is None:
            self.lbl_hotkey_status.setText("组合键无效：需带 Alt / Ctrl / Shift，主键用字母、数字、F1-F12 或 Space。")
            return
        combo = parsed[2]
        if combo == self._hotkey_values[action]:
            # 没改：直接收起，不标记未保存。
            self._end_hotkey_edit()
            self.lbl_hotkey_status.setText(self._hotkey_method_text)
            return
        for other, value in self._hotkey_values.items():
            if other != action and value == combo:
                QMessageBox.warning(self, "组合键重复", f"“{combo}”已用于【{ACTION_NAMES[other]}】，请换一个。")
                return
        self._hotkey_values[action] = combo
        self._hotkey_badges[action].setText(combo)
        self._end_hotkey_edit()
        self.lbl_hotkey_status.setText(f"已修改【{ACTION_NAMES[action]}】：{combo}，点底部【保存并应用】后生效。")
        self._mark_dirty()

    def _cancel_hotkey_edit(self):
        """Esc / 点取消 / 失焦：放弃本次修改，徽章值不动。"""
        action = self._editing_action
        if action is None:
            return
        self._end_hotkey_edit()
        self.lbl_hotkey_status.setText("已取消修改，组合键未改动。")

    def _restore_default_hotkeys(self):
        if self._editing_action is not None:
            self._cancel_hotkey_edit()
        self._hotkey_values = dict(DEFAULT_HOTKEYS)
        self._refresh_hotkey_rows()
        self.lbl_hotkey_status.setText("已恢复默认组合键，点底部【保存并应用】后生效。")
        self._mark_dirty()

    def _refresh_hotkey_rows(self):
        for action, badge in self._hotkey_badges.items():
            badge.setText(self._hotkey_values[action])

    # ---------------- 分区：关于与状态 ----------------
    def _build_about_tab(self) -> QWidget:
        container = QWidget()
        l = QVBoxLayout(container)
        l.setContentsMargins(24, 20, 24, 20)
        l.setSpacing(14)

        card = QFrame()
        card.setProperty("class", "CardFrame")
        c_l = QVBoxLayout(card)
        c_l.setContentsMargins(20, 20, 20, 20)
        c_l.setSpacing(12)

        lbl_app_name = QLabel("Manggo Pro Client 桌面客户端")
        lbl_app_name.setFont(QFont("Microsoft YaHei", 12, QFont.Bold))
        lbl_app_name.setStyleSheet(f"color: {theme.ACCENT};")
        c_l.addWidget(lbl_app_name)

        # 真实版本号：以前这里写死的 "v2.0 Pro Edition" 是假版本，已作废；
        # 现在读 packaging/VERSION（见 core/version.py）。
        lbl_ver = QLabel(
            f"版本号：{get_version()}（{get_channel()}）| 纯本地运行"
        )
        lbl_ver.setStyleSheet(f"color: {theme.TEXT_GRAY600}; font-size: 12px;")
        c_l.addWidget(lbl_ver)

        # 在线更新：手动检查 GitHub Releases，有新版按平台引导覆盖安装。
        update_row = QHBoxLayout()
        self.btn_check_update = QPushButton("检查更新")
        self.btn_check_update.clicked.connect(self._on_check_update)
        update_row.addWidget(self.btn_check_update)
        self.lbl_update_status = QLabel("点击检查更新，查看是否有新版本。")
        self.lbl_update_status.setStyleSheet(
            f"color: {theme.TEXT_GRAY600}; font-size: 12px;"
        )
        self.lbl_update_status.setWordWrap(True)
        update_row.addWidget(self.lbl_update_status, 1)
        c_l.addLayout(update_row)

        # 开机自启（仅 Windows）：任务计划方式，登录时静默提权启动，
        # 不走注册表 Run（打包版带 manifest，Run 会在每次开机时弹 UAC）。
        # 初始勾选状态由 _load_values 按任务计划实际状态回填，这里只建控件。
        from core.platform import IS_WINDOWS as _IS_WIN
        if _IS_WIN:
            auto_row = QHBoxLayout()
            self.chk_auto_start = QCheckBox("开机自启", card)
            auto_row.addWidget(self.chk_auto_start)
            lbl_auto_desc = QLabel("登录时通过任务计划静默启动（最高权限，不弹 UAC）", card)
            lbl_auto_desc.setStyleSheet(f"color: {theme.TEXT_GRAY600}; font-size: 12px;")
            lbl_auto_desc.setWordWrap(True)
            auto_row.addWidget(lbl_auto_desc, 1)
            c_l.addLayout(auto_row)

        l.addWidget(card)

        # 运行状态卡片：与应用信息分开，状态一目了然。
        card_status = QFrame()
        card_status.setProperty("class", "CardFrame")
        cs_l = QVBoxLayout(card_status)
        cs_l.setContentsMargins(20, 20, 20, 20)
        cs_l.setSpacing(12)

        # 状态指示：Windows 专属项在其他平台上如实标注，不谎报就绪。
        from core.platform import IS_MAC, IS_WINDOWS
        if IS_WINDOWS:
            hook_status = "● 正常监听中 (无需管理员权限)"
            tts_status = "就绪 (Windows 原生秒发音)"
        elif IS_MAC:
            hook_status = "⚪ 当前平台暂不支持 (仅 Windows)"
            tts_status = "就绪 (macOS 系统 say)"
        else:
            hook_status = "⚪ 当前平台暂不支持 (仅 Windows)"
            tts_status = "🟡 需安装 espeak-ng 后可用"
        status_items = [
            ("键盘底层钩子 (WH_KEYBOARD_LL):", hook_status),
            ("本地历史记录数据库 (SQLite):", "已挂载 (history.sqlite3)"),
            ("离线文字识别引擎 (RapidOCR):", "就绪 (支持中英混排离线识别)"),
            ("语音合成朗读 (TTS):", tts_status)
        ]
        for title, val in status_items:
            h = QHBoxLayout()
            h.addWidget(QLabel(title, styleSheet=f"color: {theme.TEXT_SECONDARY}; font-weight: 500; font-size: 12px;"))
            h.addStretch()
            h.addWidget(QLabel(val, styleSheet=f"color: {theme.SUCCESS_DARK}; font-weight: bold; font-size: 12px;"))
            cs_l.addLayout(h)

        l.addWidget(card_status)
        l.addStretch()
        return container

    # ---------------- 在线更新 ----------------
    def _start_update_worker(self, mode, asset=None):
        self._update_worker = _UpdateWorker(mode, asset=asset, parent=self)
        self._update_worker.done.connect(self._on_update_done)
        if mode == "download":
            self._update_worker.progress.connect(self._on_download_progress)
        self._update_worker.start()

    def _on_check_update(self):
        self.btn_check_update.setEnabled(False)
        self.lbl_update_status.setText("正在检查更新…")
        self._start_update_worker("check")

    def _on_download_progress(self, percent):
        self.lbl_update_status.setText(f"下载中…{percent}%")

    def _on_update_done(self, payload):
        worker = self._update_worker
        is_download = worker is not None and worker.mode == "download"
        self.btn_check_update.setEnabled(True)
        if not payload.get("ok"):
            self.lbl_update_status.setText(f"更新失败：{payload.get('error', '未知错误')}")
            return
        if not is_download:
            self._handle_release(payload["release"])
            return
        self._handle_downloaded(payload["path"])

    def _handle_release(self, release):
        local = get_version()
        remote = release.get("version", "")
        if not updater.is_newer(remote, local):
            self.lbl_update_status.setText(f"已是最新版本（{local}）。")
            self._set_update_dot(False)
            return
        asset = updater.select_asset(release, get_channel())
        if asset is None:
            self.lbl_update_status.setText(
                f"发现新版本 {remote}，但没有当前平台的安装包。"
            )
            return
        self._set_update_dot(True)
        notes = (release.get("body") or "").strip()
        if len(notes) > 500:
            notes = notes[:500] + "…"
        box = QMessageBox(self)
        box.setWindowTitle("发现新版本")
        box.setText(f"新版本 {remote} 已发布（当前 {local}）。\n\n{notes}")
        btn_update = box.addButton("立即更新", QMessageBox.AcceptRole)
        box.addButton("稍后", QMessageBox.RejectRole)
        box.exec()
        if box.clickedButton() is not btn_update:
            self.lbl_update_status.setText(f"已跳过新版本 {remote}。")
            return
        self.btn_check_update.setEnabled(False)
        self.lbl_update_status.setText(f"正在下载 {asset['name']}…")
        self._start_update_worker("download", asset=asset)

    def _handle_downloaded(self, path):
        import sys

        channel = get_channel()
        if sys.platform == "win32" and channel == "安装版":
            reply = QMessageBox.question(
                self,
                "下载完成",
                "安装器已下载，是否现在退出程序并启动安装器进行覆盖安装？\n"
                "（同一目录覆盖安装，历史记录和配置不受影响。）",
            )
            if reply == QMessageBox.Yes:
                subprocess.Popen([path])
                app = QApplication.instance()
                if app is not None:
                    app.quit()
            else:
                self.lbl_update_status.setText(f"安装器已下载到：{path}")
            return
        if sys.platform == "win32":
            box = QMessageBox(self)
            box.setWindowTitle("下载完成")
            box.setText(f"新版便携包已下载到：\n{path}\n\n请退出程序后解压覆盖旧文件。")
            btn_folder = box.addButton("打开下载文件夹", QMessageBox.AcceptRole)
            box.addButton("知道了", QMessageBox.RejectRole)
            box.exec()
            if box.clickedButton() is btn_folder:
                webbrowser.open(updater.download_dir())
            self.lbl_update_status.setText(f"已下载到：{path}")
            return
        if sys.platform == "darwin":
            webbrowser.open(path)
            QMessageBox.information(
                self, "下载完成", "安装磁盘映像已打开，请把它拖到 Applications 覆盖旧版。"
            )
            self.lbl_update_status.setText(f"已下载到：{path}")
            return
        webbrowser.open(path)
        QMessageBox.information(
            self,
            "下载完成",
            "安装包已用系统默认方式打开，请按提示完成安装；\n"
            "也可以手动执行：sudo dpkg -i " + path,
        )
        self.lbl_update_status.setText(f"已下载到：{path}")

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
            self.btn_go_main.setText(f"打开主工作台 ({self._hotkey_values['workbench']})")
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

        # 开机自启以任务计划实际状态为准（任务可能在设置外被删），
        # 查不到时退回配置文件里的值。
        chk_auto = getattr(self, "chk_auto_start", None)
        if chk_auto is not None:
            try:
                from core.autostart import is_autostart_enabled
                chk_auto.setChecked(is_autostart_enabled())
            except Exception:
                chk_auto.setChecked(bool(self.config.get("auto_start", False)))

    def _gather_config(self) -> dict:
        return {
            "engine": "llm" if self.cmb_engine.currentIndex() == 1 else "free",
            "hotkeys": dict(getattr(self, "_hotkey_values", normalize_hotkeys(self.config.get("hotkeys")))),
            "triple_space_enabled": self.chk_triple_space.isChecked(),
            "auto_start": self.chk_auto_start.isChecked() if hasattr(self, "chk_auto_start") else bool(self.config.get("auto_start", False)),
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
        if self._editing_action is not None:
            self._cancel_hotkey_edit()
        new_cfg = self._gather_config()
        err = validate_hotkeys(new_cfg.get("hotkeys"))
        if err:
            QMessageBox.warning(self, "热键无效", err + "，请重新修改后再保存。")
            return
        self.config = new_cfg
        save_config(new_cfg)
        self.config_changed.emit(new_cfg)
        if hasattr(self, "btn_go_main"):
            self.btn_go_main.setText(f"打开主工作台 ({new_cfg['hotkeys']['workbench']})")
        self.lbl_dirty.setVisible(False)
        self.lbl_status.setText("✓ 配置已保存并实时生效")
        QMessageBox.information(self, "保存成功", "所有偏好配置已成功保存并立即生效！")
        self.hide()
