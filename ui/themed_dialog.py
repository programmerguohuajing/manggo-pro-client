"""主题化消息弹窗：按 ui/theme.py 方案 A（白底 + 琥珀）统一全应用提示框。

替代散落在各窗口的原生 QMessageBox：原生弹窗不走项目主题（用户截图：
保存成功弹窗是macOS 系统样式，与设置页的设计语言脱节），且打包版的
标准按钮是英文（OK / Yes / No）。本模块只改展示，语义与原来对齐：
- info / success / warning / error：单按钮（知道了）；
- question：取消 + 确认两按钮，返回 True/False（× 与 Esc 视为取消）；
- choose：自定义按钮组，返回被点按钮下标（× 与 Esc 返回 -1）。

样式规则（与 update_dialog.py 一致）：颜色只用 theme token；按钮用
WINDOW_STYLESHEET 的 PrimaryBtn / SecondaryBtn class；正文与分隔线用
对象名选择器挂样式，不用裸样式块；状态徽章与关闭 × 是叶子控件，
行内样式无害。本弹窗自带样式表，在任何窗口下打开都同一外观。
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from ui import theme

_KINDS = {
    "info": ("i", theme.ACCENT),
    "success": ("✓", theme.SUCCESS),
    "warning": ("!", theme.WARNING_TEXT),
    "error": ("×", theme.DANGER),
    "question": ("?", theme.ACCENT),
}


class ThemedMessageDialog(QDialog):
    """buttons 为 [(文字, "primary"|"secondary"), ...]；
    exec 后 result_index 是被点下标，关闭 / Esc 为 -1。"""

    def __init__(self, parent, kind, title, text, buttons):
        super().__init__(parent)
        self.result_index = -1
        self.setWindowTitle(title)
        self.setFixedWidth(420)
        self.setStyleSheet(
            theme.WINDOW_STYLESHEET
            + f"""
QLabel#DialogBody {{
    font-size: 13px;
    color: {theme.TEXT_PRIMARY};
}}
QFrame#DialogDivider {{
    background-color: {theme.BORDER};
    min-height: 1px;
    max-height: 1px;
}}
"""
        )

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 18, 20, 18)
        root.setSpacing(12)

        # 标题行：状态徽章（彩色圆 + 字形）+ 标题 + 关闭 ×
        glyph, color = _KINDS.get(kind, _KINDS["info"])
        title_row = QHBoxLayout()
        title_row.setSpacing(10)
        badge = QLabel(glyph)
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge.setFixedSize(28, 28)
        badge.setStyleSheet(
            f"background-color: {color}; color: #FFFFFF; font-weight: bold; "
            "font-size: 14px; border-radius: 14px;"
        )
        lbl_title = QLabel(title)
        lbl_title.setProperty("class", "SectionTitle")
        btn_close = QPushButton("×")
        btn_close.setStyleSheet(theme.ghost_button_stylesheet(theme.TEXT_MUTED))
        btn_close.setFixedSize(24, 24)
        btn_close.clicked.connect(self.reject)
        title_row.addWidget(badge)
        title_row.addWidget(lbl_title)
        title_row.addStretch()
        title_row.addWidget(btn_close)
        root.addLayout(title_row)

        divider = QFrame()
        divider.setObjectName("DialogDivider")
        divider.setFixedHeight(1)
        root.addWidget(divider)

        body = QLabel(text)
        body.setObjectName("DialogBody")
        body.setWordWrap(True)
        root.addWidget(body)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        for idx, (label, style) in enumerate(buttons):
            btn = QPushButton(label)
            btn.setProperty(
                "class", "PrimaryBtn" if style == "primary" else "SecondaryBtn"
            )
            btn.clicked.connect(lambda _=False, i=idx: self._choose(i))
            btn_row.addWidget(btn)
        root.addLayout(btn_row)

    def _choose(self, idx):
        self.result_index = idx
        self.accept()


def _run(parent, kind, title, text, buttons) -> int:
    dlg = ThemedMessageDialog(parent, kind, title, text, buttons)
    dlg.exec()
    return dlg.result_index


def info(parent, title, text):
    _run(parent, "info", title, text, [("知道了", "primary")])


def success(parent, title, text):
    _run(parent, "success", title, text, [("知道了", "primary")])


def warning(parent, title, text):
    _run(parent, "warning", title, text, [("知道了", "primary")])


def error(parent, title, text):
    _run(parent, "error", title, text, [("知道了", "primary")])


def question(parent, title, text, yes_text="确定", no_text="取消") -> bool:
    idx = _run(
        parent, "question", title, text,
        [(no_text, "secondary"), (yes_text, "primary")],
    )
    return idx == 1


def choose(parent, kind, title, text, buttons) -> int:
    """buttons 为 [(文字, "primary"|"secondary"), ...]，返回被点下标。"""
    return _run(parent, kind, title, text, buttons)
