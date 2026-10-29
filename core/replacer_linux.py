"""Linux X11 就地转译替换器：三次空格 → 翻译并替换光标处中文。

与 Windows 的 InPlaceReplacer、macOS 的 MacReplacer 同款流程，
合成按键换成 X11 的 Ctrl 系（XTest，见 core/hook_linux）：

- 策略一：Shift+Home（选到行首，X11 与 Windows 相同）+ Ctrl+C；
- 策略二：Ctrl+A（全选）+ Ctrl+C；含中文且 < 2000 字时用全文；
- 校验（空 / 无中文 / 翻译为空或相同 → 放弃并按 Right 收起选区）；
- 译文写剪贴板 + Ctrl+V 粘贴替换选区。

剪贴板走 pyperclip（需 xclip 或 xsel）。缺失时不崩溃：第一次
剪贴板操作失败即通过 notify 回调明说安装命令（sudo apt install
xclip），而不是让用户对着“未检测到选中文本”干瞪眼。
与 macOS 版相同的两处欠缺（需前台窗口识别，后续补）：无终端/
密码框黑名单、无“翻译耗时里切走窗口则不自动粘贴”校验。
"""

import re
import threading
import time
from typing import Callable, Optional

import pyperclip

from core.hook_linux import (
    open_display,
    xtest_ctrl_key,
    xtest_right,
    xtest_shift_home,
)
from core.logging import debug as _log_debug, error as _log_error, info as _log_info

_CLIPBOARD_HINT = "Linux 剪贴板需要 xclip 或 xsel（例如：sudo apt install xclip）"


class LinuxReplacer:
    """Linux X11 就地替换器（接口对标 MacReplacer 的子集）。"""

    def __init__(
        self,
        translate_func: Callable[[str], str],
        notify_callback: Optional[Callable[[str, str], None]] = None,
    ):
        self.translate_func = translate_func
        self.notify_callback = notify_callback
        self.is_busy = False
        self._clipboard_hint_shown = False

    def contains_chinese(self, text: str) -> bool:
        return bool(re.search(r"[\u4e00-\u9fa5]", text))

    def trigger_triple_space_replace(self):
        if self.is_busy:
            return
        threading.Thread(target=self._do_replace_flow, daemon=True).start()

    def _paste(self) -> str:
        try:
            return pyperclip.paste() or ""
        except Exception:
            self._hint_clipboard()
            return ""

    def _copy(self, text: str):
        try:
            pyperclip.copy(text)
        except Exception:
            self._hint_clipboard()
            _log_debug("CLIPBOARD", "linux copy failed (xclip/xsel missing?)")

    def _hint_clipboard(self):
        if self._clipboard_hint_shown:
            return
        self._clipboard_hint_shown = True
        if self.notify_callback:
            self.notify_callback("failed", _CLIPBOARD_HINT)

    def _copy_and_wait(self, dpy, timeout: float = 0.35) -> str:
        """Ctrl+C 后等剪贴板出现新内容（先清空再等非空，避免旧剪贴板冒充）。"""
        self._copy("")
        time.sleep(0.02)
        xtest_ctrl_key(dpy, "c")
        start = time.time()
        while time.time() - start < timeout:
            text = self._paste()
            if text:
                return text
            time.sleep(0.02)
        return ""

    def _do_replace_flow(self):
        self.is_busy = True
        original_clipboard = ""
        have_backup = False
        last_flow_clipboard = ""
        dpy = open_display()
        if dpy is None:
            _log_error("REPLACER", "linux replace: no X display")
            if self.notify_callback:
                self.notify_callback("failed", "无法连接 X 服务器")
            self.is_busy = False
            return
        try:
            time.sleep(0.04)
            try:
                original_clipboard = self._paste()
                have_backup = True
            except Exception as e:
                _log_debug("CLIPBOARD", f"linux backup failed, restore skipped: {e}")

            # 策略一：行内向前选区（Shift+Home）+ Ctrl+C。
            xtest_shift_home(dpy)
            time.sleep(0.05)
            captured = self._copy_and_wait(dpy)
            last_flow_clipboard = captured
            _log_info("REPLACER", f"linux strategy 1 (line) captured {len(captured)} chars")

            # 策略二：整个输入框（Ctrl+A）+ Ctrl+C。
            xtest_ctrl_key(dpy, "a")
            time.sleep(0.05)
            captured_all = self._copy_and_wait(dpy)
            last_flow_clipboard = captured_all
            _log_info("REPLACER", f"linux strategy 2 (all) captured {len(captured_all)} chars")
            if captured_all and self.contains_chinese(captured_all) and len(captured_all) < 2000:
                captured = captured_all

            clean_text = captured.strip() if captured else ""
            if not clean_text or not self.contains_chinese(clean_text):
                xtest_right(dpy)
                _log_info("REPLACER", "linux aborted: empty or no Chinese")
                self._maybe_restore(have_backup, original_clipboard, last_flow_clipboard)
                return

            translated_en = self.translate_func(clean_text)
            if not translated_en or translated_en == clean_text:
                xtest_right(dpy)
                _log_info("REPLACER", "linux aborted: translation empty or identical")
                self._maybe_restore(have_backup, original_clipboard, last_flow_clipboard)
                return

            self._copy(translated_en)
            time.sleep(0.05)
            xtest_ctrl_key(dpy, "v")
            _log_info("REPLACER", f"linux pasted {len(translated_en)} chars")
        except Exception as e:
            _log_error("REPLACER", f"linux replace flow failed: {e}")
            if self.notify_callback:
                self.notify_callback("failed", "就地转译失败，请重试")
            self._maybe_restore(have_backup, original_clipboard, last_flow_clipboard)
        finally:
            try:
                dpy.close()
            except Exception:
                pass
            self.is_busy = False

    def _maybe_restore(self, have_backup, original_clipboard, last_flow_clipboard):
        """放弃路径：用户没动过剪贴板时才把备份写回去。"""
        if not have_backup:
            return
        try:
            if self._paste() == last_flow_clipboard:
                self._copy(original_clipboard)
        except Exception:
            pass
