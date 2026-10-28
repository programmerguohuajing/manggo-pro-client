"""1.0.16 回调逻辑的单测：用 mock user32 驱动真实的 _hook_callback，
断言所有普通按键都返回 0（放行），只有配置的热键才返回 1（吞键）。

背景：1.0.15 的 LPARAM bug 已修，但用户报告 1.0.16（Setup.exe 安装，
症状与 1.0.15 一模一样）仍无法输入。本测试排除“回调逻辑本身误吞键”
的可能：若普通键在这里返回非 0，说明回调逻辑有第二个 bug；若全过，
则 1.0.16 的回调逻辑无罪，问题出在运行环境（跑的不是 1.0.16、或非回调原因）。

跑法（仓库根目录）：python3 tests/test_hook_callback.py
标准库 unittest，不依赖 Qt/Windows。
"""

import ctypes
import os
import sys
import types
import unittest


sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# core.hook 经 core.replacer 依赖 pyperclip（运行时才用），单测纯标准库，
# 这里先 stub 掉，只保证 import 通过。
if "pyperclip" not in sys.modules:
    _stub = types.ModuleType("pyperclip")
    _stub.copy = lambda text: None
    _stub.paste = lambda: ""
    sys.modules["pyperclip"] = _stub

from core import logging as _diag_logging
import core.hook as hook_mod
from core.hook import GlobalKeyboardHook, KBDLLHOOKSTRUCT, hook_self_check

WM_KEYDOWN = 0x0100
WM_SYSKEYDOWN = 0x0104
WM_KEYUP = 0x0101
WM_SYSKEYUP = 0x0105
VK_MENU = 0x12
VK_CONTROL = 0x11
VK_SHIFT = 0x10
VK_SPACE = 0x20
LLKHF_ALTDOWN = 0x20


class FakeUser32:
    """只实现回调用到的两个函数；CallNextHookEx 恒返回 0（放行）。"""

    def __init__(self, down_vks=()):
        self.down_vks = set(down_vks)
        self.next_calls = []

    def GetAsyncKeyState(self, vk):
        return 0x8000 if vk in self.down_vks else 0

    def CallNextHookEx(self, hook_id, nCode, wParam, lParam):
        self.next_calls.append((nCode, wParam))
        return 0


def _press(hook, vk, wparam=WM_KEYDOWN, flags=0):
    kb = KBDLLHOOKSTRUCT(vk, 0, flags, 0, None)
    return hook._hook_callback(0, wparam, ctypes.pointer(kb))


class CallbackPassThroughTest(unittest.TestCase):
    def setUp(self):
        hook_mod._send_mask_key = lambda: None
        self.hook = GlobalKeyboardHook()
        self.fake = FakeUser32()
        hook_mod.user32 = self.fake

    def test_normal_keys_all_pass(self):
        """普通键（字母/数字/功能键/方向键/Tab/Esc/回车/退格/删除）一律放行。"""
        vks = (
            list(range(0x41, 0x5B))  # A-Z
            + list(range(0x30, 0x3A))  # 0-9
            + list(range(0x70, 0x7C))  # F1-F12
            + [0x25, 0x26, 0x27, 0x28, 0x09, 0x1B, 0x0D, 0x08, 0x2E]
        )
        for vk in vks:
            with self.subTest(vk=hex(vk)):
                self.assertEqual(_press(self.hook, vk, WM_KEYDOWN, 0), 0)
                self.assertEqual(_press(self.hook, vk, WM_KEYUP, 0), 0)

    def test_ctrl_combos_pass(self):
        """Ctrl+C / Ctrl+V 等非热键组合一律放行（用户报的“复制也没反应”绝不能是回调吞的）。"""
        self.fake.down_vks = {VK_CONTROL}
        for vk in (0x43, 0x56, 0x41, 0x5A):
            with self.subTest(vk=hex(vk)):
                self.assertEqual(_press(self.hook, vk, WM_KEYDOWN, 0), 0)

    def test_alt_tab_passes(self):
        """Alt+Tab 不是热键，必须放行。"""
        self.fake.down_vks = {VK_MENU}
        self.assertEqual(_press(self.hook, 0x09, WM_SYSKEYDOWN, LLKHF_ALTDOWN), 0)

    def test_configured_hotkeys_swallow(self):
        """配置的热键（默认 Alt+Q/W/M/Space）才吞键，且抬起后可再次触发。"""
        self.fake.down_vks = {VK_MENU}
        for vk in (ord("Q"), ord("W"), ord("M")):
            with self.subTest(vk=chr(vk)):
                self.assertEqual(_press(self.hook, vk, WM_SYSKEYDOWN, LLKHF_ALTDOWN), 1)
                self.assertEqual(_press(self.hook, vk, WM_SYSKEYUP, LLKHF_ALTDOWN), 0)
        # 按住不放的自动重复：只吞不重复触发。
        self.assertEqual(_press(self.hook, ord("Q"), WM_SYSKEYDOWN, LLKHF_ALTDOWN), 1)
        self.assertEqual(_press(self.hook, ord("Q"), WM_SYSKEYDOWN, LLKHF_ALTDOWN), 1)
        self.assertEqual(_press(self.hook, ord("Q"), WM_SYSKEYUP, LLKHF_ALTDOWN), 0)
        self.assertEqual(_press(self.hook, ord("Q"), WM_SYSKEYDOWN, LLKHF_ALTDOWN), 1)

    def test_triple_space_passes_keys(self):
        """三空格本身也要放行（触发转译是另一条线程的事，不吞空格）。"""
        self.fake.down_vks = set()
        for _ in range(3):
            self.assertEqual(_press(self.hook, VK_SPACE, WM_KEYDOWN, 0), 0)
            self.assertEqual(_press(self.hook, VK_SPACE, WM_KEYUP, 0), 0)

    def test_stuck_space_down_still_passes(self):
        """空格抬起事件丢了（_space_down 卡住），空格照样放行。"""
        self.hook._space_down = True
        self.assertEqual(_press(self.hook, VK_SPACE, WM_KEYDOWN, 0), 0)


    def test_diag_nonzero_next_return_logged(self):
        """1.0.18：链上下一个钩子返回非 0 时，回调必须把这个值记进日志
        （1.0.17 的日志看不见返回值，无法区分“回调吞键”与“下家吞键”）。"""
        _diag_logging.clear_buffer()

        class _FakeNonzero(FakeUser32):
            def CallNextHookEx(self, hook_id, nCode, wParam, lParam):
                return 5

        hook_mod.user32 = _FakeNonzero()
        ret = _press(self.hook, 0x41, WM_KEYDOWN, 0)
        self.assertEqual(ret, 5)
        msgs = " ".join(str(r) for r in _diag_logging.get_records())
        self.assertIn("nonzero", msgs)
        self.assertIn("0x41", msgs)

    def test_diag_callback_count_logged(self):
        """1.0.18：回调计数每 50 次记一条（只记条数不记按键），
        证明回调在真实按键时是不是还在跑、跑到第几次停的。"""
        _diag_logging.clear_buffer()
        for _ in range(50):
            _press(self.hook, 0x41, WM_KEYDOWN, 0)
        msgs = " ".join(str(r) for r in _diag_logging.get_records())
        self.assertIn("callback count=50", msgs)

    def test_diag_first_callback_logged_once(self):
        """1.0.18：第一次回调记一条“跑起来了”，之后不再重复记。"""
        _diag_logging.clear_buffer()
        _press(self.hook, 0x41, WM_KEYDOWN, 0)
        _press(self.hook, 0x42, WM_KEYDOWN, 0)
        msgs = " ".join(str(r) for r in _diag_logging.get_records())
        self.assertEqual(msgs.count("first callback"), 1)

if __name__ == "__main__":
    unittest.main()


class HookSelfCheckTest(unittest.TestCase):
    """启动前自检：正常钩子必须通过；wrapper 坏了必须被拦下来；验完钩子还能用。"""

    def setUp(self):
        hook_mod._send_mask_key = lambda: None
        self.hook = GlobalKeyboardHook()
        hook_mod.user32 = FakeUser32()

    def test_self_check_passes(self):
        ok, detail = hook_self_check(self.hook)
        self.assertTrue(ok, detail)

    def test_self_check_blocks_broken_wrapper(self):
        self.hook._hook_callback = lambda *args: (_ for _ in ()).throw(RuntimeError("boom"))
        ok, detail = hook_self_check(self.hook)
        self.assertFalse(ok)
        self.assertIn("wrapper", detail)

    def test_hook_still_works_after_self_check(self):
        """自检的探针必须原样恢复内层，验完普通键照样放行。"""
        hook_self_check(self.hook)
        self.assertEqual(_press(self.hook, 0x41, WM_KEYDOWN, 0), 0)
        self.assertEqual(_press(self.hook, 0x41, WM_KEYUP, 0), 0)
