"""更新发现弹窗：按 ui/theme.py 方案 A（白底 + 琥珀主题）重设计。

替代设置窗口原来那个原生 QMessageBox：原生弹窗不走项目主题，且更新
日志里的 Markdown（**Full Changelog**）是原样显示的。本弹窗只改展示，
行为与原来一致：立即更新 → 接受，稍后 / 关闭 → 拒绝；调用方按返回值
走原有下载流程或写“已跳过”状态。

样式规则（与 theme.py 一致）：
- 颜色与按钮 class 只用 theme token / WINDOW_STYLESHEET，不新写十六进制；
- 分隔线与日志框用对象名选择器挂样式，绝不用裸样式块（裸块会把
  border/padding 漏给子控件，2026-10-28 实测教训）；
- badge 与关闭 × 是叶子控件，行内样式无害。
"""

from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
)

from core import updater
from ui import theme


class UpdateDialog(QDialog):
    """发现新版本弹窗。exec() 返回 Accepted=立即更新，Rejected=稍后/关闭。"""

    def __init__(self, parent, local_version, remote_version, notes):
        super().__init__(parent)
        self.setWindowTitle("发现新版本")
        self.setFixedWidth(440)
        self.setStyleSheet(
            theme.WINDOW_STYLESHEET
            + f"""
QTextBrowser#ChangelogBrowser {{
    background-color: {theme.SURFACE};
    border: 1px solid {theme.BORDER};
    border-radius: 8px;
    padding: 8px 10px;
    font-size: 12px;
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

        # 标题行：标题 + 关闭 ×
        title_row = QHBoxLayout()
        title = QLabel("发现新版本")
        title.setProperty("class", "SectionTitle")
        btn_close = QPushButton("×")
        btn_close.setStyleSheet(theme.ghost_button_stylesheet(theme.TEXT_MUTED))
        btn_close.setFixedSize(24, 24)
        btn_close.clicked.connect(self.reject)
        title_row.addWidget(title)
        title_row.addStretch()
        title_row.addWidget(btn_close)
        root.addLayout(title_row)

        # 版本行：当前 → 新版 + 新版本 badge
        ver_row = QHBoxLayout()
        ver_row.setSpacing(6)
        lbl_cur = QLabel(f"当前 {local_version}")
        lbl_cur.setProperty("class", "SectionDesc")
        lbl_arrow = QLabel("→")
        lbl_arrow.setStyleSheet(f"color: {theme.ACCENT}; font-weight: bold;")
        lbl_new = QLabel(remote_version)
        lbl_new.setProperty("class", "SectionTitle")
        badge = QLabel("新版本")
        badge.setStyleSheet(
            f"background-color: {theme.ACCENT_SOFT_BG}; color: {theme.ACCENT_DARK}; "
            "font-size: 11px; font-weight: bold; border-radius: 10px; padding: 2px 8px;"
        )
        ver_row.addWidget(lbl_cur)
        ver_row.addWidget(lbl_arrow)
        ver_row.addWidget(lbl_new)
        ver_row.addWidget(badge)
        ver_row.addStretch()
        root.addLayout(ver_row)

        # 细分隔线（对象名挂样式，不用裸样式块）
        divider = QFrame()
        divider.setObjectName("DialogDivider")
        divider.setFixedHeight(1)
        root.addWidget(divider)

        # 更新日志：有内容用可滚动富文本框（最高 200px），无内容用一行灰字
        notes_html = updater.release_notes_to_html(notes)
        if notes_html.strip():
            browser = QTextBrowser()
            browser.setObjectName("ChangelogBrowser")
            browser.setMaximumHeight(200)
            browser.setOpenExternalLinks(True)
            browser.setHtml(notes_html)
            pal = browser.palette()
            pal.setColor(QPalette.Link, QColor(theme.ACCENT))
            browser.setPalette(pal)
            root.addWidget(browser)
        else:
            lbl_empty = QLabel("暂无更新说明。")
            lbl_empty.setProperty("class", "SectionDesc")
            root.addWidget(lbl_empty)

        # 底部按钮：右对齐，次按钮 + 主按钮
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_later = QPushButton("稍后")
        btn_later.setProperty("class", "SecondaryBtn")
        btn_later.clicked.connect(self.reject)
        btn_update = QPushButton("立即更新")
        btn_update.setProperty("class", "PrimaryBtn")
        btn_update.clicked.connect(self.accept)
        btn_row.addWidget(btn_later)
        btn_row.addWidget(btn_update)
        root.addLayout(btn_row)
