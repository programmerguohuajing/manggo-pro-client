"""
本地 OCR 识别引擎：基于 RapidOCR (PaddleOCR 算法与权重)
"""
from PIL import Image
from typing import Optional, List

class OCREngine:
    def __init__(self):
        self._engine = None

    def _ensure_engine(self):
        if self._engine is None:
            from rapidocr_onnxruntime import RapidOCR
            self._engine = RapidOCR()

    def recognize_image(self, pil_image: Image.Image) -> str:
        """从 PIL Image 中提取文字"""
        self._ensure_engine()
        # numpy 懒加载：启动时 main.py 会 import ocr_engine，顶层导 numpy
        # 会让一次 numpy 损坏（如 macOS 12 上 Accelerate 缺符号）直接杀掉
        # 整个启动；OCR 真用时才导，坏也只坏 OCR，不坏启动。
        import numpy as np

        # 转换为 numpy 数组
        img_np = np.array(pil_image.convert("RGB"))
        result, _ = self._engine(img_np)
        if not result:
            return ""

        # result 格式为 [[box, text, score], ...]
        lines = [item[1].strip() for item in result if item and len(item) >= 2 and item[1].strip()]
        return "\n".join(lines)

ocr_engine = OCREngine()
