"""
历史记录与生词本管理窗口
"""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QCheckBox, QMessageBox
)
import pyperclip

from core.database import db

class HistoryWindow(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Manggo 历史记录 & 生词本")
        self.resize(720, 480)

        self._init_ui()
        self.refresh_data()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        # 1. 检索与筛选栏
        h_filter = QHBoxLayout()
        self.txt_search = QLineEdit(self)
        self.txt_search.setPlaceholderText("搜索历史原文或译文...")
        self.txt_search.textChanged.connect(self.refresh_data)
        h_filter.addWidget(self.txt_search)

        self.chk_starred_only = QCheckBox("仅查看生词本 (星标)", self)
        self.chk_starred_only.stateChanged.connect(self.refresh_data)
        h_filter.addWidget(self.chk_starred_only)

        self.btn_clear = QPushButton("清空常规历史", self)
        self.btn_clear.clicked.connect(self._clear_unstarred)
        h_filter.addWidget(self.btn_clear)

        layout.addLayout(h_filter)

        # 2. 数据表格
        self.table = QTableWidget(self)
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["生词本", "时间", "来源", "原文", "译文"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.cellDoubleClicked.connect(self._copy_cell_content)
        layout.addWidget(self.table)

        lbl_tip = QLabel("💡 提示：双击单元格可快速复制该项内容。点击星标可直接将条目加入/移出生词本。", self)
        lbl_tip.setStyleSheet("color: #7f8c8d; font-size: 11px;")
        layout.addWidget(lbl_tip)

    def refresh_data(self):
        keyword = self.txt_search.text()
        only_starred = self.chk_starred_only.isChecked()
        records = db.list_records(keyword=keyword, only_starred=only_starred)

        self.table.setRowCount(len(records))
        type_map = {
            "triple_space": "三次空格",
            "selection": "划词翻译",
            "ocr": "截图OCR",
            "main_win": "主工作台",
            "manual": "通用"
        }

        for row_idx, r in enumerate(records):
            # 星标按钮
            star_text = "★" if r["is_starred"] else "☆"
            item_star = QTableWidgetItem(star_text)
            item_star.setTextAlignment(Qt.AlignCenter)
            item_star.setData(Qt.UserRole, r["id"])
            self.table.setItem(row_idx, 0, item_star)

            # 时间
            item_time = QTableWidgetItem(str(r["created_at"])[:16])
            self.table.setItem(row_idx, 1, item_time)

            # 来源
            item_src_type = QTableWidgetItem(type_map.get(r["source_type"], r["source_type"]))
            self.table.setItem(row_idx, 2, item_src_type)

            # 原文
            item_src = QTableWidgetItem(r["source_text"])
            self.table.setItem(row_idx, 3, item_src)

            # 译文
            item_tgt = QTableWidgetItem(r["target_text"])
            self.table.setItem(row_idx, 4, item_tgt)

    def _copy_cell_content(self, row, col):
        if col == 0:
            # 切换星标
            rec_id = self.table.item(row, 0).data(Qt.UserRole)
            is_starred = db.toggle_star(rec_id)
            self.table.item(row, 0).setText("★" if is_starred else "☆")
        else:
            item = self.table.item(row, col)
            if item:
                pyperclip.copy(item.text())
                QMessageBox.information(self, "已复制", f"已复制到剪贴板:\n{item.text()[:50]}")

    def _clear_unstarred(self):
        if QMessageBox.question(self, "确认清空", "是否确定清空未收藏的常规翻译历史？（生词本中的星标词汇将被完整保留）") == QMessageBox.Yes:
            db.clear_all()
            self.refresh_data()
