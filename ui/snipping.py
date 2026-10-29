"""
截图提取遮罩模块：全屏十字光标框选截图并自动调用 OCR 识别与翻译
"""
import io
from PIL import Image
from PySide6.QtCore import Qt, QRect, QPoint, Signal
from PySide6.QtWidgets import QWidget, QApplication
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QPixmap, QCursor, QFont, QGuiApplication

from ui import theme
from core.logging import debug as _log_debug

class SnippingWidget(QWidget):
    screenshot_captured = Signal(object)  # 发射 PIL Image
    snipping_failed = Signal(str)  # 抓屏失败原因（接 toast，不弹遮罩）

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

        # macOS 未给“屏幕录制”权限时 grabWindow 只返回黑图（或空图）：
        # 原来会直接弹一个全屏黑遮罩，用户看到的就是“黑屏”，还继续跑 OCR。
        # 这里先验：空图或 5x5 采样全黑 → 不弹遮罩，直接报权限原因。
        if self._grab_is_blank():
            self.snipping_failed.emit(
                "截图失败：未能获取屏幕内容。请在系统设置 → 隐私与安全性 → "
                "屏幕录制中允许 ManggoProClient，然后重试。"
            )
            return

        self.begin_point = QPoint()
        self.end_point = QPoint()
        self.is_snipping = False

        self.setWindowState(Qt.WindowFullScreen)
        self.show()
        self.raise_()
        self.activateWindow()
        try:
            import ctypes
            hwnd = int(self.winId())
            ctypes.windll.user32.SetWindowPos(hwnd, -1, 0, 0, 0, 0, 0x0001 | 0x0002 | 0x0040)
            ctypes.windll.user32.SetForegroundWindow(hwnd)
        except Exception as e:
            _log_debug("SNIPPING", f"SetWindowPos/SetForegroundWindow failed: {e}")

    def _grab_is_blank(self):
        """抓到的图是否为空/全黑（macOS 无屏幕录制权限时的典型产物）。"""
        pm = self.full_screen_pixmap
        if pm is None or pm.isNull():
            return True
        img = pm.toImage()
        w, h = img.width(), img.height()
        if w == 0 or h == 0:
            return True
        for gx in range(5):
            for gy in range(5):
                x = min(w - 1, int((gx + 0.5) * w / 5))
                y = min(h - 1, int((gy + 0.5) * h / 5))
                if img.pixelColor(x, y).rgb() & 0xFFFFFF != 0:
                    return False
        return True

    def _to_device_rect(self, logical_rect):
        """逻辑坐标矩形 → 设备像素矩形。

        鼠标事件给的是逻辑坐标，但 QPixmap.copy 与 drawPixmap 的源矩形
        要的是设备像素；125%–200% 缩放下不换算，截到的就是错位区域
        （2026-10-28 review 小问题）。离屏 dpr=1 验不出，须真机验。
        多屏 DPI 不一致时以主屏 dpr 为准，是近似值。
        """
        dpr = self.full_screen_pixmap.devicePixelRatio()
        return QRect(
            int(logical_rect.x() * dpr),
            int(logical_rect.y() * dpr),
            int(logical_rect.width() * dpr),
            int(logical_rect.height() * dpr),
        )

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
                painter.drawPixmap(select_rect, self.full_screen_pixmap, self._to_device_rect(select_rect))

                # 绘制边框
                pen = QPen(QColor(255, 255, 255), 1.5, Qt.DashLine)
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
                cropped_pixmap = self.full_screen_pixmap.copy(self._to_device_rect(select_rect))
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
