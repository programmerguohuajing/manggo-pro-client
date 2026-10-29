"""macOS 剪贴板：直接走 NSPasteboard（ctypes + Objective-C 运行时），
替换 pyperclip 默认的 pbcopy / pbpaste 子进程后端。

根因（1.0.32 真机日志，2026-10-29）：
- 事件抽头正常、accessibility_trusted=True、合成 Cmd+C 投递成功；
- 三次空格：策略一 captured 0 chars，策略二只在框里是纯英文 'Test'
  时抓到了内容；划选：两次 post_ok=True 但 clipboard=0 chars。
- 共同点：只要剪贴板里是中文就读成空，英文能读到。
pyperclip 在没装 PyObjC 时用 pbcopy/pbpaste 子进程，并按 UTF-8 编解码；
但从 Finder / 启动台打开的 .app 没有 LANG/LC_ALL 环境变量，
pbpaste/pbcopy 按 C 区域设置工作：读到的中文输出为空（或乱码），
写进去的中文变成乱码。Cmd+C 其实成功了，是我们读不出来。

这里直接调用 NSPasteboard 的 UTF-8 接口，与区域设置无关；
install() 把 pyperclip.copy / pyperclip.paste 换成本模块实现，
全项目（含 UI 里的“复制”按钮）不用改调用点。
同时在 main.py 里给进程补 LANG=…UTF-8 兜底，万一有别的代码
还走 pbcopy/pbpaste 也不会坏。

本模块 import 在任何平台都不崩；只有 macOS 上 install() 才生效。
"""

import ctypes
import ctypes.util
import sys
import threading

_lock = threading.Lock()
_state = {}


def _load():
    """懒加载 libobjc + AppKit，并声明本模块用到的全部签名。"""
    if _state.get("ready"):
        return _state
    if sys.platform != "darwin":
        raise RuntimeError("NSPasteboard 只在 macOS 可用")
    objc_path = ctypes.util.find_library("objc") or "/usr/lib/libobjc.A.dylib"
    objc = ctypes.CDLL(objc_path)
    # 加载 AppKit 才会注册 NSPasteboard 类，并导出类型常量。
    appkit = ctypes.CDLL("/System/Library/Frameworks/AppKit.framework/AppKit")
    objc.objc_getClass.restype = ctypes.c_void_p
    objc.objc_getClass.argtypes = [ctypes.c_char_p]
    objc.sel_registerName.restype = ctypes.c_void_p
    objc.sel_registerName.argtypes = [ctypes.c_char_p]
    objc.objc_autoreleasePoolPush.restype = ctypes.c_void_p
    objc.objc_autoreleasePoolPush.argtypes = []
    objc.objc_autoreleasePoolPop.restype = None
    objc.objc_autoreleasePoolPop.argtypes = [ctypes.c_void_p]
    msg_addr = ctypes.cast(objc.objc_msgSend, ctypes.c_void_p).value

    # objc_msgSend 在 arm64 上不能按可变参数调用，必须按每个方法的
    # 真实签名各转一个函数指针（Apple Silicon 上用错签名会读到垃圾）。
    def proto(restype, *argtypes):
        return ctypes.CFUNCTYPE(restype, ctypes.c_void_p, ctypes.c_void_p, *argtypes)(msg_addr)

    _state.update(
        objc=objc,
        appkit=appkit,
        msg_id=proto(ctypes.c_void_p),                                   # -(id)foo
        msg_long=proto(ctypes.c_long),                                   # -(NSInteger)foo
        msg_id_id=proto(ctypes.c_void_p, ctypes.c_void_p),               # -(id)foo:(id)
        msg_id_cstr=proto(ctypes.c_void_p, ctypes.c_char_p),             # +(id)foo:(const char*)
        msg_cstr=proto(ctypes.c_char_p),                                 # -(const char*)foo
        msg_bool_id_id=proto(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p),  # -(BOOL)foo:(id)bar:(id)
        cls_pb=objc.objc_getClass(b"NSPasteboard"),
        cls_str=objc.objc_getClass(b"NSString"),
        type_str=ctypes.c_void_p.in_dll(appkit, "NSPasteboardTypeString").value,
        sel=lambda name: objc.sel_registerName(name),
    )
    _state["ready"] = True
    return _state


def _board(s):
    return s["msg_id"](s["cls_pb"], s["sel"](b"generalPasteboard"))


def paste() -> str:
    with _lock:
        s = _load()
        pool = s["objc"].objc_autoreleasePoolPush()
        try:
            ns = s["msg_id_id"](_board(s), s["sel"](b"stringForType:"), s["type_str"])
            if not ns:
                return ""
            raw = s["msg_cstr"](ns, s["sel"](b"UTF8String"))
            return raw.decode("utf-8", errors="replace") if raw else ""
        finally:
            s["objc"].objc_autoreleasePoolPop(pool)


def copy(text) -> None:
    text = "" if text is None else str(text)
    with _lock:
        s = _load()
        pool = s["objc"].objc_autoreleasePoolPush()
        try:
            board = _board(s)
            s["msg_long"](board, s["sel"](b"clearContents"))
            if not text:
                return  # copy("") = 清空剪贴板（调用方用它做“先清空再等非空”）
            ns = s["msg_id_cstr"](
                s["cls_str"], s["sel"](b"stringWithUTF8String:"), text.encode("utf-8")
            )
            if not ns:
                raise RuntimeError("NSString stringWithUTF8String 返回 nil")
            if not s["msg_bool_id_id"](board, s["sel"](b"setString:forType:"), ns, s["type_str"]):
                raise RuntimeError("NSPasteboard setString:forType: 失败")
        finally:
            s["objc"].objc_autoreleasePoolPop(pool)


def change_count() -> int:
    """NSPasteboard.changeCount：剪贴板每被写一次就 +1（对应 Windows 序号）。"""
    with _lock:
        s = _load()
        return int(s["msg_long"](_board(s), s["sel"](b"changeCount")))


def install(log=None) -> bool:
    """把 pyperclip.copy/paste 换成 NSPasteboard 实现。

    只做只读自检（读一次剪贴板），不写探针：写探针会把用户剪贴板里
    的图片/文件等非文本内容冲掉。返回 True 表示已替换；失败时保留
    pyperclip 原后端并记录原因。
    """
    if sys.platform != "darwin":
        return False
    try:
        import pyperclip

        paste()
        change_count()
        pyperclip.copy = copy
        pyperclip.paste = paste
        if log:
            log("mac clipboard backend: NSPasteboard (UTF-8, locale-independent)")
        return True
    except Exception as e:
        if log:
            log(f"mac NSPasteboard install failed, keeping pyperclip backend: {e}")
        return False
