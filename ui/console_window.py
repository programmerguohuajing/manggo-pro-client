"""
诊断控制台：把原来只能翻 debug_app.log 文件的日志搬到界面里。

- 不自动弹窗，只从托盘菜单打开；打开后每 500ms 轮询日志缓冲追加新记录。
- 级别过滤：默认“INFO 及以上”（钩子逐键 DEBUG 默认不显示，选“全部”才可见）。
- 只读展示：复制全部 / 清空显示（只清内存缓冲，不删日志文件）/ 打开日志文件。
- 不接任何翻译、钩子、数据库逻辑，纯展示层。
"""
import pyperclip
from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtGui import QDesktopServices, QFont
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QPushButton, QPlainTextEdit, QCheckBox,
)

from core.logging import LEVELS, MAX_BUFFER, clear_buffer, format_record, get_records, log_file_path
from ui import theme
from ui.components import make_action_button


class ConsoleWindow(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Manggo Pro - 诊断控制台")
        self.resize(820, 520)
        self.setStyleSheet(theme.WINDOW_STYLESHEET)
        self._last_index = 0
        self._min_level = LEVELS["INFO"]
        self._init_ui()
        self._refresh_all()

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._append_new)
        self._timer.start(500)

    def _init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 12, 14, 12)
        root.setSpacing(10)

        toolbar = QHBoxLayout()
        toolbar.addWidget(QLabel("级别:", self))

        self.cmb_level = QComboBox(self)
        self.cmb_level.addItems(["全部", "INFO 及以上", "WARNING 及以上", "仅 ERROR"])
        self.cmb_level.setCurrentIndex(1)
        self.cmb_level.currentIndexChanged.connect(self._on_level_changed)
        toolbar.addWidget(self.cmb_level)

        self.chk_autoscroll = QCheckBox("自动滚动", self)
        self.chk_autoscroll.setChecked(True)
        toolbar.addWidget(self.chk_autoscroll)

        toolbar.addStretch()

        self.btn_copy = make_action_button("📋 复制全部", "secondary", self)
        self.btn_copy.clicked.connect(self._copy_all)
        toolbar.addWidget(self.btn_copy)

        self.btn_clear = make_action_button("🗑️ 清空显示", "secondary", self)
        self.btn_clear.clicked.connect(self._clear_view)
        toolbar.addWidget(self.btn_clear)

        self.btn_open_file = make_action_button("📂 打开日志文件", "secondary", self)
        self.btn_open_file.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(log_file_path()))
        )
        toolbar.addWidget(self.btn_open_file)
        root.addLayout(toolbar)

        self.txt_log = QPlainTextEdit(self)
        self.txt_log.setReadOnly(True)
        self.txt_log.setFont(QFont("Consolas", 10))
        self.txt_log.setPlaceholderText("暂无日志…（钩子逐键记录为 DEBUG 级，选“全部”才显示）")
        root.addWidget(self.txt_log, 1)

        self.lbl_status = QLabel(self)
        self.lbl_status.setStyleSheet(f"color: {theme.TEXT_MUTED}; font-size: 11px;")
        root.addWidget(self.lbl_status)
        self._update_status()

    def _passes(self, record) -> bool:
        return LEVELS[record["level"]] >= self._min_level

    def _update_status(self):
        total = len(get_records())
        self.lbl_status.setText(
            f"缓冲 {total} 条（上限 {MAX_BUFFER} 条）· 日志文件：{log_file_path()}"
        )

    def _on_level_changed(self, idx: int):
        self._min_level = [LEVELS["DEBUG"], LEVELS["INFO"], LEVELS["WARNING"], LEVELS["ERROR"]][idx]
        self._refresh_all()

    def _refresh_all(self):
        self.txt_log.clear()
        for record in get_records():
            if self._passes(record):
                self.txt_log.appendPlainText(format_record(record))
        self._last_index = len(get_records())
        if self.chk_autoscroll.isChecked():
            self.txt_log.verticalScrollBar().setValue(self.txt_log.verticalScrollBar().maximum())
        self._update_status()

    def _append_new(self):
        records = get_records()
        if len(records) < self._last_index:
            # 缓冲被清空过，重建视图
            self._refresh_all()
            return
        new_records = records[self._last_index:]
        self._last_index = len(records)
        if not new_records:
            return
        for record in new_records:
            if self._passes(record):
                self.txt_log.appendPlainText(format_record(record))
        if self.chk_autoscroll.isChecked():
            self.txt_log.verticalScrollBar().setValue(self.txt_log.verticalScrollBar().maximum())
        self._update_status()

    def _copy_all(self):
        pyperclip.copy(self.txt_log.toPlainText())

    def _clear_view(self):
        clear_buffer()
        self.txt_log.clear()
        self._last_index = 0
        self._update_status()
