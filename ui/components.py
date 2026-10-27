"""
展示层共享小组件：只负责长相，不接业务信号之外的逻辑。

主窗口 / 悬浮窗 / 设置诊断面板原来各写一套“朗读 / 复制”按钮与
状态胶囊，这里收敛成同一批构造器，改一处即全站生效。
"""
from PySide6.QtWidgets import QFrame, QLabel, QPushButton

from ui import theme


def make_card(parent=None) -> QFrame:
    """白色圆角卡片（需配合 theme.WINDOW_STYLESHEET / SETTINGS_STYLESHEET 使用）。"""
    card = QFrame(parent)
    card.setProperty("class", "CardFrame")
    return card


def make_section_label(text: str, kind: str = "title", parent=None) -> QLabel:
    """kind: title / desc / field，对应样式表里的 SectionTitle 等 class。"""
    label = QLabel(text, parent)
    label.setProperty(
        "class",
        {"title": "SectionTitle", "desc": "SectionDesc", "field": "FieldLabel"}.get(kind, "SectionTitle"),
    )
    return label


def make_status_badge(text: str, success: bool, parent=None) -> QLabel:
    label = QLabel(text, parent)
    label.setStyleSheet(theme.badge_stylesheet(success))
    return label


def make_action_button(text: str, kind: str = "secondary", parent=None) -> QPushButton:
    """kind: primary / secondary / text，对应样式表里的 PrimaryBtn 等 class。"""
    button = QPushButton(text, parent)
    button.setProperty(
        "class",
        {"primary": "PrimaryBtn", "secondary": "SecondaryBtn", "text": "TextBtn"}.get(kind, "SecondaryBtn"),
    )
    return button


def make_small_button(text: str, parent=None) -> QPushButton:
    """悬浮窗 60x20 的朗读 / 复制小按钮（固定尺寸由调用方设置）。"""
    button = QPushButton(text, parent)
    button.setStyleSheet(theme.small_action_stylesheet())
    return button
