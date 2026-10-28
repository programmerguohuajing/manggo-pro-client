"""API Key 存储：Windows 用 DPAPI 加密（2026-10-28 review）。

- protect(text)：Windows 成功时返回 "DPAPI:<base64>"；非 Windows 或
  DPAPI 失败时原样返回明文（降级不断功能，调用方不得因此报错）。
- unprotect(value)："DPAPI:" 开头时解密，失败返回 ""（密钥不可恢复，
  调用方应提示用户重填，绝不能把密文当密钥发出去）；无前缀的旧明文
  原样返回（向后兼容）。
- DPAPI 绑定当前 Windows 用户 + 本机：换用户/换机器后旧密文解不开
  是预期行为（密钥本来就该用户重填），不是 bug。
"""

import base64
import ctypes
from ctypes import wintypes

from core.platform import IS_WINDOWS

_PREFIX = "DPAPI:"


class _DATA_BLOB(ctypes.Structure):
    _fields_ = [
        ("cbData", wintypes.DWORD),
        ("pbData", ctypes.POINTER(ctypes.c_byte)),
    ]


def _blob_from_bytes(data: bytes):
    # buf 必须在调用期间活着，调用方持有返回的第二个元素。
    buf = ctypes.create_string_buffer(data, len(data)) if data else None
    blob = _DATA_BLOB()
    blob.cbData = len(data)
    blob.pbData = ctypes.cast(buf, ctypes.POINTER(ctypes.c_byte)) if buf else None
    return blob, buf


def _bytes_from_blob(blob) -> bytes:
    if not blob.pbData or blob.cbData == 0:
        return b""
    return ctypes.string_at(blob.pbData, blob.cbData)


def protect(text: str) -> str:
    if not IS_WINDOWS or not text:
        return text
    try:
        crypt32 = ctypes.windll.crypt32
        kernel32 = ctypes.windll.kernel32
        in_blob, in_buf = _blob_from_bytes(text.encode("utf-8"))
        out_blob = _DATA_BLOB()
        # CRYPTPROTECT_UI_FORBIDDEN = 0x1：绝不弹窗。
        ok = crypt32.CryptProtectData(
            ctypes.byref(in_blob), None, None, None, None, 0x1, ctypes.byref(out_blob)
        )
        if not ok:
            return text
        try:
            return _PREFIX + base64.b64encode(_bytes_from_blob(out_blob)).decode("ascii")
        finally:
            kernel32.LocalFree(out_blob.pbData)
    except Exception:
        return text


def unprotect(value: str) -> str:
    if not value or not value.startswith(_PREFIX):
        return value
    if not IS_WINDOWS:
        return ""
    try:
        raw = base64.b64decode(value[len(_PREFIX):])
        crypt32 = ctypes.windll.crypt32
        kernel32 = ctypes.windll.kernel32
        in_blob, in_buf = _blob_from_bytes(raw)
        out_blob = _DATA_BLOB()
        ok = crypt32.CryptUnprotectData(
            ctypes.byref(in_blob), None, None, None, None, 0x1, ctypes.byref(out_blob)
        )
        if not ok:
            return ""
        try:
            return _bytes_from_blob(out_blob).decode("utf-8")
        finally:
            kernel32.LocalFree(out_blob.pbData)
    except Exception:
        return ""
