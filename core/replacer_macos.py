"""macOS 就地转译替换器：三次空格 → 翻译并替换光标处中文。

与 Windows 的 InPlaceReplacer（core/replacer.py）同款流程，
只是合成按键换成 macOS 的 Cmd 系（CGEvent，见 core/hook_macos）：

- 策略一：Shift+Cmd+Left（选到行首，对应 Windows Shift+Home）
  + Cmd+C，拿到光标行；
- 策略二：Cmd+A（全选）+ Cmd+C，拿到全文；含中文且 < 2000 字时
  用全文（多行输入框要全文，不是光标行；单行框里两者相同）；
- 校验（空 / 无中文 / 翻译为空或相同 → 放弃并按 Right 收起选区）；
- 译文写剪贴板 + Cmd+V 粘贴替换选区。

与 Windows 版有意的两处差异（后续可补，不静默假装有）：
- 无窗口黑名单（终端/密码框）：Windows 用 GetForegroundWindow 查
  类名，macOS 需前台窗口识别（CGWindowList），首版先不上；
  密码框里 Cmd+A 选到的是掩码字符、复制不到真实密码，风险有限。
- 无“翻译耗时里用户切走窗口则不自动粘贴”校验：同上，需前台窗口
  识别；首版粘贴前不校验，切走窗口时译文仍会粘到新窗口——
  用户若在翻译耗时里切走窗口，请手动撤销（Cmd+Z）一次。
剪贴板备份/恢复用内容比对近似 Windows 的序号法：放弃路径上，
若当前剪贴板仍等于流程最后一次写的值（即用户没动过它），
才把备份写回去；成功粘贴后不恢复（译文留给用户）。
"""

import re
import threading
import time
from typing import Callable, Optional

import pyperclip

from core.hook_macos import (
    post_cmd_key,
    post_right,
    post_shift_cmd_left,
)
from core.logging import debug as _log_debug, error as _log_error, info as _log_info


class MacReplacer:
    """macOS 就地替换器（接口对标 InPlaceReplacer 的子集）。"""

    def __init__(
        self,
        translate_func: Callable[[str], str],
        notify_callback: Optional[Callable[[str, str], None]] = None,
    ):
        self.translate_func = translate_func
        self.notify_callback = notify_callback
        self.is_busy = False

    def contains_chinese(self, text: str) -> bool:
        return bool(re.search(r"[\u4e00-\u9fa5]", text))

    def trigger_triple_space_replace(self):
        if self.is_busy:
            return
        threading.Thread(target=self._do_replace_flow, daemon=True).start()

    # ---- 剪贴板小工具（pyperclip 跨平台，macOS 走 pbcopy/pbpaste） ----
    def _paste(self) -> str:
        try:
            return pyperclip.paste() or ""
        except Exception:
            return ""

    def _copy(self, text: str):
        try:
            pyperclip.copy(text)
        except Exception as e:
            _log_debug("CLIPBOARD", f"mac copy failed: {e}")

    def _copy_and_wait(self, timeout: float = 0.35) -> str:
        """Cmd+C 后等剪贴板出现新内容（先清空再等非空，避免把旧剪贴板
        当成选中文字——Windows 序号法的 macOS 近似版）。"""
        self._copy("")
        time.sleep(0.02)
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
        try:
            time.sleep(0.04)
            try:
                original_clipboard = self._paste()
                have_backup = True
            except Exception as e:
                _log_debug("CLIPBOARD", f"mac backup failed, restore skipped: {e}")

            # 策略一：行内向前选区（Shift+Cmd+Left）+ Cmd+C。
            post_shift_cmd_left()
            time.sleep(0.05)
            post_cmd_key("C")
            captured = self._copy_and_wait()
            last_flow_clipboard = captured
            _log_info("REPLACER", f"mac strategy 1 (line) captured {len(captured)} chars")

            # 策略二：整个输入框（Cmd+A）+ Cmd+C。
            post_cmd_key("A")
            time.sleep(0.05)
            post_cmd_key("C")
            captured_all = self._copy_and_wait()
            last_flow_clipboard = captured_all
            _log_info("REPLACER", f"mac strategy 2 (all) captured {len(captured_all)} chars")
            if captured_all and self.contains_chinese(captured_all) and len(captured_all) < 2000:
                captured = captured_all

            clean_text = captured.strip() if captured else ""
            if not clean_text or not self.contains_chinese(clean_text):
                post_right()
                _log_info("REPLACER", "mac aborted: empty or no Chinese")
                self._maybe_restore(have_backup, original_clipboard, last_flow_clipboard)
                return

            translated_en = self.translate_func(clean_text)
            if not translated_en or translated_en == clean_text:
                post_right()
                _log_info("REPLACER", "mac aborted: translation empty or identical")
                self._maybe_restore(have_backup, original_clipboard, last_flow_clipboard)
                return

            self._copy(translated_en)
            time.sleep(0.05)
            post_cmd_key("V")
            _log_info("REPLACER", f"mac pasted {len(translated_en)} chars")
        except Exception as e:
            _log_error("REPLACER", f"mac replace flow failed: {e}")
            if self.notify_callback:
                self.notify_callback("failed", "就地转译失败，请重试")
            self._maybe_restore(have_backup, original_clipboard, last_flow_clipboard)
        finally:
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
