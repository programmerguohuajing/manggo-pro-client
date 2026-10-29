"""macOS 就地转译替换器：三次空格 → 翻译并替换光标处中文。

与 Windows 的 InPlaceReplacer（core/replacer.py）同款流程，
只是合成按键换成 macOS 的 Cmd 系（CGEvent，见 core/hook_macos）：

- 策略一：Shift+Cmd+Left（选到行首，对应 Windows Shift+Home）
  + Cmd+C，拿到光标行；
- 策略二：Cmd+A（全选）+ Cmd+C，拿到全文；含中文且 < 2000 字时
  用全文（多行输入框要全文，不是光标行；单行框里两者相同）；
- 校验（空 / 无中文 / 翻译为空或相同 → 放弃并按 Right 收起选区）；
- 粘贴走可验证流程（1.0.35）：重选后先 Cmd+C 回读，剪贴板恰好
  变回待替换原文才证明选区真的覆盖了它，然后才写译文粘贴；
  粘后回抓全文对账，原文还在（粘成了插入）就清空重贴。

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
    post_delete,
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
        # 忙标志必须在起线程之前置位：旧实现在 _do_replace_flow 里
        # 置位有竞态——两次快速触发能各起一条流程，两条流程抢同一
        # 份剪贴板与选区（1.0.38 日志出现过两条流程交错的记录）。
        self.is_busy = True
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

    def _wait_clipboard(self, timeout: float = 0.6) -> str:
        """等剪贴板出现内容（调用方负责：先清空 → 选区 → 发 Cmd+C）。

        顺序是关键：清空必须在发复制键之前。旧实现 _copy_and_wait
        把清空放在发键之后——目标应用处理 Cmd+C 稍慢时，它写入的
        内容会被随后的清空盖掉，永远抓到空（1.0.30 真机日志实测：
        两条策略都 captured 0 chars）。Windows 版用剪贴板序号检测
        变化、从不清空，所以没这个竞态；这是 macOS 近似版引入的。
        """
        start = time.time()
        while time.time() - start < timeout:
            text = self._paste()
            if text:
                return text
            time.sleep(0.02)
        return ""

    def _do_replace_flow(self):
        original_clipboard = ""
        have_backup = False
        last_flow_clipboard = ""
        try:
            time.sleep(0.04)
            # 静默路径优先：AX 直接读写焦点元素，不发 Cmd 组合键、不动
            # 剪贴板——也就不会让菜单栏「编辑」随每个合成快捷键逐个
            # 闪烁（用户视频反馈），顺带不覆盖用户的剪贴板。AX 不适用
            # 或写后回读校验不过时，完整回退到下面的剪贴板流程。
            try:
                from core import ax_macos
                ax_result = ax_macos.try_replace_focused(
                    self.translate_func, self.contains_chinese)
                if ax_result is True:
                    _log_info("REPLACER", "mac replace done via AX (silent path)")
                    return
                if ax_result is None:
                    # AX 已读到字段并确认没有可译内容：剪贴板流程
                    # 抓到的必然是同一份文本、同样放弃，直接结束，
                    # 省掉一轮白闪菜单栏的合成键（1.0.38 真机实测
                    # 的空转闪烁正是这条）。
                    _log_info("REPLACER", "mac AX: nothing to translate, clipboard flow skipped")
                    return
                if ax_result == ax_macos.RESULT_ABORT:
                    # 混合粘贴失败且撤销没能恢复原文：文档状态未
                    # 确认，整体停止——绝不在这种文档上再跑剪贴板
                    # 流程（它的抓取/证明会被污染文本带偏）。
                    _log_error("REPLACER", "mac AX hybrid aborted: document state unconfirmed, stopping")
                    if self.notify_callback:
                        self.notify_callback(
                            "failed",
                            "替换校验失败且自动撤销未成功，已停止，请检查文档或手动撤销一次")
                    return
                _log_info("REPLACER", "mac AX path not applicable, clipboard flow")
            except Exception as e:
                _log_debug("REPLACER", f"mac AX attempt raised, clipboard flow: {e}")
            try:
                original_clipboard = self._paste()
                have_backup = True
            except Exception as e:
                _log_debug("CLIPBOARD", f"mac backup failed, restore skipped: {e}")

            # 策略一：行内向前选区（Shift+Cmd+Left）+ Cmd+C。
            # 顺序固定：先清空剪贴板，再选区、复制、等内容。
            self._copy("")
            post_shift_cmd_left()
            time.sleep(0.05)
            post_cmd_key("C")
            captured = self._wait_clipboard()
            last_flow_clipboard = captured
            _log_info("REPLACER", f"mac strategy 1 (line) captured {len(captured)} chars: {captured[:30]!r}")

            # 策略二：整个输入框（Cmd+A）+ Cmd+C（同样的抓取顺序）。
            self._copy("")
            post_cmd_key("A")
            time.sleep(0.05)
            post_cmd_key("C")
            captured_all = self._wait_clipboard()
            last_flow_clipboard = captured_all
            _log_info("REPLACER", f"mac strategy 2 (all) captured {len(captured_all)} chars: {captured_all[:30]!r}")
            use_all = False
            # 全文抓取必须至少覆盖行抓取的结果：个别应用（Typora
            # 实测）的 Cmd+A 复制会给出 1 个字符的残缺结果，短于行
            # 结果时不可信，宁可走行策略。
            if captured_all and len(captured_all) >= len(captured) and self.contains_chinese(captured_all):
                if len(captured_all) < 2000:
                    captured = captured_all
                    use_all = True
                else:
                    # Cmd+A 之后当前选区已经是全文：此时再按“光标行”的
                    # 译文 Cmd+V，会把整篇文档替换成一行译文。宁可放弃。
                    post_right()
                    _log_info("REPLACER", f"mac aborted: text too long ({len(captured_all)} chars)")
                    if self.notify_callback:
                        self.notify_callback("failed", "文本过长（≥2000 字），请先选中要翻译的部分")
                    self._maybe_restore(have_backup, original_clipboard, last_flow_clipboard)
                    return

            clean_text = captured.strip() if captured else ""
            if not clean_text or not self.contains_chinese(clean_text):
                post_right()
                _log_info("REPLACER", "mac aborted: empty or no Chinese")
                self._maybe_restore(have_backup, original_clipboard, last_flow_clipboard)
                return

            # 抓取结束先收起选区再去翻译：策略二的全选会一直活着
            # 等网络返回（数秒），这段时间用户敲任何一个键都会把
            # 全文顶掉。粘贴路径在粘前都重新选区并证明，收起不
            # 影响后续；放弃路径本来也会收起，重复一次无害。
            post_right()
            translated_en = self.translate_func(clean_text)
            if not translated_en or translated_en == clean_text:
                post_right()
                _log_info("REPLACER", "mac aborted: translation empty or identical")
                self._maybe_restore(have_backup, original_clipboard, last_flow_clipboard)
                return

            if use_all:
                pasted = self._paste_all_verified(
                    translated_en, clean_text,
                    have_backup, original_clipboard, captured,
                )
            else:
                pasted = self._paste_line_verified(
                    translated_en, clean_text,
                    have_backup, original_clipboard,
                )
            if pasted:
                _log_info("REPLACER", f"mac pasted {len(translated_en)} chars: {translated_en[:30]!r}")
        except Exception as e:
            _log_error("REPLACER", f"mac replace flow failed: {e}")
            if self.notify_callback:
                self.notify_callback("failed", "就地转译失败，请重试")
            self._maybe_restore(have_backup, original_clipboard, last_flow_clipboard)
        finally:
            self.is_busy = False

    # ---- 可验证粘贴（1.0.35） ----
    # 1.0.34 真机（多行文档）证明：reselect_all=True、clipboard_ok=True
    # 时 Cmd+V 仍然落成插入。“发了 Cmd+A”不等于“粘贴那一刻选区
    # 还覆盖着原文”——选区状态从外部读不到，那就用剪贴板证明它：
    # 重选后立刻 Cmd+C，剪贴板恰好变回待替换的原文，选区才算被
    # 证明；粘贴后回抓全文对账，原文还在就趁回抓的全选还活着
    # 清空重贴（注意回抓已把剪贴板覆盖成抓到的内容，重贴前必须
    # 把译文再写回去）。每一步成败都写日志，不再靠猜。

    def _poll_until(self, core: str, timeout: float = 0.35):
        """轮询剪贴板直到其核心文本等于 core，返回 (是否命中, 最后所见)。

        核心文本 = 去掉两端空白后的内容。不同应用复制同一段选区时，
        两端空白/换行的表示并不一致（Typora 等 Electron 编辑器尤其
        明显），逐字节比对会把真选区误判成证明失败；核心一致即证明
        选区确实覆盖了目标文本。调用前剪贴板刚被写成译文（与原文
        核心必然不同，流程前段已校验），不存在旧内容冒充命中。
        """
        start = time.time()
        last = ""
        while time.time() - start < timeout:
            last = self._paste()
            if last.strip() == core:
                return True, last
            time.sleep(0.02)
        last = self._paste()
        return last.strip() == core, last

    def _grab_all(self) -> str:
        self._copy("")
        post_cmd_key("A")
        time.sleep(0.05)
        post_cmd_key("C")
        return self._wait_clipboard()

    def _grab_line(self) -> str:
        self._copy("")
        post_shift_cmd_left()
        time.sleep(0.05)
        post_cmd_key("C")
        return self._wait_clipboard()

    def _abort_paste(self, have_backup, original_clipboard, why: str):
        # 先收起选区再返回：放弃时若把抓取/证明阶段的选区原样留给
        # 用户，他下一次敲键就会把选中的原文顶掉（1.0.35 Typora
        # 实测：证明失败放弃后，原文被用户自己的后续输入吃掉、
        # 文档变空，看起来像应用删了原文）。其他放弃路径都有
        # post_right，这里此前漏了。
        post_right()
        _log_error("REPLACER", f"mac paste aborted: {why}")
        if self.notify_callback:
            self.notify_callback("failed", "粘贴前无法确认选区，已放弃替换（文档未改动）")
        if have_backup:
            self._copy(original_clipboard)
        return False

    def _paste_all_verified(self, translated, clean_text,
                            have_backup, original_clipboard, raw_text="") -> bool:
        proven, last = False, ""
        for attempt in (1, 2):
            self._copy(translated)
            time.sleep(0.04)
            post_cmd_key("A")
            time.sleep(0.06)
            post_cmd_key("C")
            proven, last = self._poll_until(clean_text)
            _log_info("REPLACER", f"mac paste proof attempt {attempt}: {'ok' if proven else 'failed'}")
            if proven:
                break
        if not proven:
            _log_info("REPLACER", f"mac paste proof failed: clipboard last seen {last[:40]!r}")
            return self._abort_paste(have_backup, original_clipboard,
                                     "selection not proven after retries")
        self._copy(translated)
        time.sleep(0.03)
        post_cmd_key("V")
        time.sleep(0.08)
        grabbed = self._grab_all()
        if grabbed == translated or grabbed.strip() == translated.strip():
            post_right()
            _log_info("REPLACER", "mac paste verified: field holds exactly the translation")
            return True
        if clean_text and clean_text in grabbed:
            # 插入而非替换。_grab_all 刚成功全选并复制——拷贝内容
            # 本身证明此刻全文选区是活的：清空、把译文写回剪贴板
            # （回抓已覆盖了它）、重贴，结果确定。
            _log_info("REPLACER", "mac paste repair: original still present, clearing and re-pasting")
            if not post_delete():
                _log_error("REPLACER", "mac paste repair: delete post failed (paste will replace selection instead)")
            time.sleep(0.04)
            self._copy(translated)
            time.sleep(0.03)
            post_cmd_key("V")
            time.sleep(0.08)
            grabbed2 = self._grab_all()
            post_right()
            ok = grabbed2 == translated or grabbed2.strip() == translated.strip()
            _log_info("REPLACER", f"mac paste repair {'verified' if ok else 'failed'}: field={grabbed2[:30]!r}")
            if not ok:
                # 修复已删过全文、译文又没粘稳，输入框正空着——
                # 绝不把空文档留给户：把原文放回去兜底。
                return self._restore_original(
                    raw_text, have_backup, original_clipboard)
            return ok
        post_right()
        _log_info("REPLACER", f"mac paste unverified: field={grabbed[:30]!r}")
        return False

    def _restore_original(self, raw_text, have_backup, original_clipboard) -> bool:
        """修复粘贴失败后的兜底：把抓到的原文原样放回输入框。

        修复路径删过全文，此刻文档可能为空（数据丢失）。重新全选
        并粘回未 strip 的原文，再回抓对账。连恢复都失败时，把原文
        留在剪贴板并弹提示，用户至少能手动 Cmd+V 找回，不至于
        内容凭空消失。返回值恒为 False（本次替换未成功）。
        """
        if not raw_text:
            _log_error("REPLACER", "mac restore skipped: no raw text captured")
            return False
        post_cmd_key("A")
        time.sleep(0.05)
        self._copy(raw_text)
        time.sleep(0.03)
        post_cmd_key("V")
        time.sleep(0.08)
        grabbed = self._grab_all()
        post_right()
        ok = grabbed.strip() == raw_text.strip()
        _log_info("REPLACER", f"mac restore original {'ok' if ok else 'FAILED'}: field={grabbed[:30]!r}")
        if not ok:
            self._copy(raw_text)
            if self.notify_callback:
                self.notify_callback(
                    "failed", "替换失败，原文已放回剪贴板，请手动粘贴找回")
        return False

    def _paste_line_verified(self, translated, clean_text,
                             have_backup, original_clipboard) -> bool:
        proven, last = False, ""
        for attempt in (1, 2):
            self._copy(translated)
            time.sleep(0.04)
            post_shift_cmd_left()
            time.sleep(0.06)
            post_cmd_key("C")
            proven, last = self._poll_until(clean_text)
            _log_info("REPLACER", f"mac paste(line) proof attempt {attempt}: {'ok' if proven else 'failed'}")
            if proven:
                break
        if not proven:
            _log_info("REPLACER", f"mac paste(line) proof failed: clipboard last seen {last[:40]!r}")
            return self._abort_paste(have_backup, original_clipboard,
                                     "line selection not proven after retries")
        self._copy(translated)
        time.sleep(0.03)
        post_cmd_key("V")
        time.sleep(0.08)
        grabbed_line = self._grab_line()
        post_right()
        ok = grabbed_line.strip() == translated.strip()
        _log_info("REPLACER", f"mac paste(line) {'verified' if ok else 'unverified'}: line={grabbed_line[:30]!r}")
        return ok

    def _maybe_restore(self, have_backup, original_clipboard, last_flow_clipboard):
        """放弃路径：用户没动过剪贴板时才把备份写回去。"""
        if not have_backup:
            return
        try:
            if self._paste() == last_flow_clipboard:
                self._copy(original_clipboard)
        except Exception:
            pass
