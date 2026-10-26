"""
截图提取遮罩模块：全屏十字光标框选截图并自动调用 OCR 识别与翻译
"""
import io
from PIL import Image
from PySide6.QtCore import Qt, QRect, QPoint, Signal
from PySide6.QtWidgets import QWidget, QApplication
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QPixmap, QCursor, QFont, QGuiApplication

class SnippingWidget(QWidget):
    screenshot_captured = Signal(object)  # 发射 PIL Image

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool
        )
        self.setCursor(Qt.CrossCursor)
        self.begin_point = QPoint()
        self.end_point = QPoint()
        self.is_snipping = False
        self.full_screen_pixmap = None

    def start_snipping(self):
        # 获取覆盖所有屏幕的整体虚拟矩形
        screens = QGuiApplication.screens()
        total_rect = QRect()
        for s in screens:
            total_rect = total_rect.united(s.geometry())

        self.setGeometry(total_rect)

        # 捕获主屏幕与全屏快照
        primary = QGuiApplication.primaryScreen()
        self.full_screen_pixmap = primary.grabWindow(0, total_rect.x(), total_rect.y(), total_rect.width(), total_rect.height())

        self.begin_point = QPoint()
        self.end_point = QPoint()
        self.is_snipping = False

        self.show()
        self.raise_()
        self.activateWindow()

    def paintEvent(self, event):
        if not self.full_screen_pixmap:
            return

        painter = QPainter(self)
        # 1. 绘制底层屏幕截图
        painter.drawPixmap(0, 0, self.full_screen_pixmap)

        # 2. 绘制全屏半透明遮罩
        painter.fillRect(self.rect(), QColor(0, 0, 0, 110))

        # 3. 如果正在框选，将框选区域重新高亮（画回原图）
        if self.is_snipping:
            select_rect = QRect(self.begin_point, self.end_point).normalized()
            if not select_rect.isEmpty():
                # 挖空高亮原图
                painter.drawPixmap(select_rect, self.full_screen_pixmap, select_rect)

                # 绘制边框
                pen = QPen(QColor(46, 204, 113), 2, Qt.SolidLine)
                painter.setPen(pen)
                painter.setBrush(Qt.NoBrush)
                painter.drawRect(select_rect)

                # 绘制尺寸提示标签
                tip_text = f"{select_rect.width()} × {select_rect.height()}"
                painter.setFont(QFont("Microsoft YaHei", 9))
                painter.setPen(QColor(255, 255, 255))
                painter.drawText(select_rect.x() + 4, select_rect.y() - 6 if select_rect.y() > 20 else select_rect.y() + 18, tip_text)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.begin_point = event.pos()
            self.end_point = event.pos()
            self.is_snipping = True
            self.update()
        elif event.button() == Qt.RightButton:
            # 右键取消截图
            self.hide()

    def mouseMoveEvent(self, event):
        if self.is_snipping:
            self.end_point = event.pos()
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.is_snipping:
            self.is_snipping = False
            self.end_point = event.pos()
            select_rect = QRect(self.begin_point, self.end_point).normalized()
            self.hide()

            if select_rect.width() > 10 and select_rect.height() > 10:
                # 截取框选部分转为 PIL Image
                cropped_pixmap = self.full_screen_pixmap.copy(select_rect)
                image = cropped_pixmap.toImage()

                # 将 QImage 转换为 PIL Image
                buf = image.bits().tobytes()
                pil_img = Image.frombuffer(
                    "RGBA", (image.width(), image.height()), buf, "raw", "BGRA", 0, 1
                ).convert("RGB")

                self.screenshot_captured.emit(pil_img)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.hide()
