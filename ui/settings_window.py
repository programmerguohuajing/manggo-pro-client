"""
设置面板与偏好配置
"""
import os
import json
from typing import Callable
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QComboBox, QSpinBox, QPushButton, QCheckBox, QGroupBox,
    QMessageBox, QTextEdit
)
from PySide6.QtGui import QFont, QIcon

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

class SettingsWindow(QWidget):
    config_changed = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Manggo Pro - 输入框就地转译设置")
        self.setFixedSize(520, 560)
        self.config = load_config()

        self._init_ui()
        self._load_values()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(14)

        # 1. 快捷转译开关
        grp_trigger = QGroupBox("快捷转译行为", self)
        l_trigger = QVBoxLayout(grp_trigger)

        self.chk_triple_space = QCheckBox("启用【连续三次空格】就地转译（中文 -> 英文）", self)
        self.chk_triple_space.setFont(QFont("Microsoft YaHei", 9, QFont.Bold))
        l_trigger.addWidget(self.chk_triple_space)

        h_interval = QHBoxLayout()
        h_interval.addWidget(QLabel("触发连击判定时间窗口 (毫秒):", self))
        self.spn_interval = QSpinBox(self)
        self.spn_interval.setRange(300, 1000)
        self.spn_interval.setSingleStep(50)
        self.spn_interval.setSuffix(" ms")
        h_interval.addWidget(self.spn_interval)
        l_trigger.addLayout(h_interval)

        lbl_desc = QLabel("💡 提示：在任意聊天框或文本输入区敲完中文后，连按 3 次空格即可自动消除空格并将文字直接替换为英文！", self)
        lbl_desc.setWordWrap(True)
        lbl_desc.setStyleSheet("color: #7f8c8d; font-size: 11px;")
        l_trigger.addWidget(lbl_desc)

        layout.addWidget(grp_trigger)

        # 2. 翻译引擎选择
        grp_engine = QGroupBox("翻译通道设置 (支持 Pro 级大模型)", self)
        l_engine = QVBoxLayout(grp_engine)

        h_mode = QHBoxLayout()
        h_mode.addWidget(QLabel("当前翻译引擎:", self))
        self.cmb_engine = QComboBox(self)
        self.cmb_engine.addItems(["内置免费通道 (免 Key，即开即用)", "自定义大模型 Pro 通道 (DeepSeek / 通义千问 / OpenAI)"])
        self.cmb_engine.currentIndexChanged.connect(self._on_engine_changed)
        h_mode.addWidget(self.cmb_engine)
        l_engine.addLayout(h_mode)

        # LLM 设置区域
        self.widget_llm = QWidget(self)
        l_llm_fields = QVBoxLayout(self.widget_llm)
        l_llm_fields.setContentsMargins(0, 5, 0, 0)

        h_url = QHBoxLayout()
        h_url.addWidget(QLabel("API Base URL:", self))
        self.txt_url = QLineEdit(self)
        self.txt_url.setPlaceholderText("https://api.deepseek.com/v1")
        h_url.addWidget(self.txt_url)
        l_llm_fields.addLayout(h_url)

        h_key = QHBoxLayout()
        h_key.addWidget(QLabel("API Key:", self))
        self.txt_key = QLineEdit(self)
        self.txt_key.setEchoMode(QLineEdit.Password)
        self.txt_key.setPlaceholderText("sk-...")
        h_key.addWidget(self.txt_key)
        l_llm_fields.addLayout(h_key)

        h_model = QHBoxLayout()
        h_model.addWidget(QLabel("模型名称:", self))
        self.txt_model = QLineEdit(self)
        self.txt_model.setPlaceholderText("deepseek-chat")
        h_model.addWidget(self.txt_model)
        l_llm_fields.addLayout(h_model)

        l_llm_fields.addWidget(QLabel("翻译 Prompt (润色与地道表达):", self))
        self.txt_prompt = QTextEdit(self)
        self.txt_prompt.setFixedHeight(60)
        l_llm_fields.addWidget(self.txt_prompt)

        l_engine.addWidget(self.widget_llm)
        layout.addWidget(grp_engine)

        # 3. 保存与测试按钮
        h_btns = QHBoxLayout()
        self.btn_test = QPushButton("测试转译", self)
        self.btn_test.clicked.connect(self._test_translation)
        h_btns.addWidget(self.btn_test)

        h_btns.addStretch()

        self.btn_save = QPushButton("保存配置", self)
        self.btn_save.setStyleSheet("background-color: #27ae60; color: white; font-weight: bold; padding: 6px 16px; border-radius: 4px;")
        self.btn_save.clicked.connect(self._save_and_apply)
        h_btns.addWidget(self.btn_save)

        layout.addLayout(h_btns)

    def _load_values(self):
        self.chk_triple_space.setChecked(self.config.get("triple_space_enabled", True))
        self.spn_interval.setValue(self.config.get("max_interval_ms", 550))
        is_llm = self.config.get("engine", "free") == "llm"
        self.cmb_engine.setCurrentIndex(1 if is_llm else 0)
        self.widget_llm.setVisible(is_llm)

        self.txt_url.setText(self.config.get("llm_api_url", "https://api.deepseek.com/v1"))
        self.txt_key.setText(self.config.get("llm_api_key", ""))
        self.txt_model.setText(self.config.get("llm_model", "deepseek-chat"))
        self.txt_prompt.setPlainText(self.config.get("llm_prompt", ""))

    def _on_engine_changed(self, idx):
        self.widget_llm.setVisible(idx == 1)

    def _test_translation(self):
        from core.translator import TranslationManager
        cfg = self._gather_config()
        mgr = TranslationManager(cfg)
        test_src = "明天下午两点我们在会议室讨论这个方案。"
        try:
            res = mgr.translate_to_en(test_src)
            QMessageBox.information(self, "测试成功", f"原文: {test_src}\n\n译文: {res}")
        except Exception as e:
            QMessageBox.critical(self, "测试失败", f"错误原因: {e}")

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

    def _save_and_apply(self):
        new_cfg = self._gather_config()
        self.config = new_cfg
        save_config(new_cfg)
        self.config_changed.emit(new_cfg)
        QMessageBox.information(self, "已保存", "配置已成功保存并立即生效！")
        self.hide()
