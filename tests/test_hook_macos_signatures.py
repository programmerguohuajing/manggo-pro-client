"""core/hook_macos 的 ctypes 签名声明守卫（标准库 unittest，无需 macOS）。

1.0.26 的真实崩溃：stop() 调 CFMachPortInvalidate 时该函数没声明
argtypes，ctypes 把 64 位 tap 指针按 C int 截断成 32 位，函数拿到
垃圾地址 SIGSEGV（崩溃报告 Thread 0: CFMachPortInvalidate + libffi）。
沙箱/CI 都没有 CoreGraphics 可跑，只能用源码级断言守住：本模块里
每个带指针参数的函数都必须有 argtypes（或 restype）声明，且
CFRelease 必须在两处声明（start 的 self._cf 与合成按键的 _cf_lib，
两个 CDLL 实例互不通用）。

跑法（仓库根目录）：python3 tests/test_hook_macos_signatures.py
"""

import os
import unittest

_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "core", "hook_macos.py",
)

_POINTER_FUNCS = (
    "CGEventTapCreate", "CGEventGetIntegerValueField", "CGEventGetFlags",
    "CGEventTapEnable", "CFMachPortCreateRunLoopSource",
    "CFMachPortInvalidate", "CFRunLoopGetCurrent", "CFRunLoopAddSource",
    "CFRunLoopRun", "CFRunLoopStop", "CFRelease",
    "CGEventCreateKeyboardEvent", "CGEventSetFlags", "CGEventPost",
)


class SignaturesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(_PATH, encoding="utf-8") as fh:
            cls.src = fh.read()

    def test_every_pointer_func_declared(self):
        for name in _POINTER_FUNCS:
            declared = (f"{name}.argtypes" in self.src) or (f"{name}.restype" in self.src)
            self.assertTrue(declared, f"{name} missing argtypes/restype declaration")

    def test_invalidate_declares_void_p(self):
        self.assertIn("CFMachPortInvalidate.argtypes = [ctypes.c_void_p]", self.src)

    def test_cfrelease_declared_on_both_handles(self):
        # start() 的 self._cf 与 post_key 的 _cf_lib() 各一份，缺一不可。
        self.assertGreaterEqual(self.src.count("CFRelease.argtypes"), 2)


if __name__ == "__main__":
    unittest.main()
