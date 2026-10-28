"""翻译后台线程：网络翻译绝不在界面线程做（2026-10-28 review 问题5）。

离线时免费通道各等 2.5 秒、LLM 加回退约 17.5 秒，同步跑会冻住界面。
用法：start_translate(parent, workers, fn, text, done_slot) —— done 发
{"ok": True, "result": str, "text": str, "elapsed_ms": int} 或
{"ok": False, "error": str, "text": str, "elapsed_ms": int}。
结果槽跑在界面线程（信号跨线程自动排队），可直接更新界面。
workers 是调用方持有的列表，保证线程对象在 finished 之前不被回收；
finished 后自动从列表移除并 deleteLater。
"""

import time

from PySide6.QtCore import QThread, Signal


class TranslateWorker(QThread):
    done = Signal(dict)

    def __init__(self, translate_fn, text, parent=None):
        super().__init__(parent)
        self._fn = translate_fn
        self._text = text

    def run(self):
        start = time.time()
        try:
            result = self._fn(self._text)
            self.done.emit(
                {
                    "ok": True,
                    "result": result,
                    "text": self._text,
                    "elapsed_ms": int((time.time() - start) * 1000),
                }
            )
        except Exception as e:
            self.done.emit(
                {
                    "ok": False,
                    "error": str(e),
                    "text": self._text,
                    "elapsed_ms": int((time.time() - start) * 1000),
                }
            )


def start_translate(parent, workers, translate_fn, text, done_slot):
    worker = TranslateWorker(translate_fn, text, parent=parent)
    worker.done.connect(done_slot)

    def _cleanup():
        try:
            workers.remove(worker)
        except ValueError:
            pass
        worker.deleteLater()

    worker.finished.connect(_cleanup)
    workers.append(worker)
    worker.start()
    return worker
