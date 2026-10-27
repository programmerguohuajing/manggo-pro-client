"""
平台判定：本项目起家于 Windows，核心的全局钩子、就地替换、
Win+H 听写、SAPI 朗读、单实例互斥体都是 Windows 专属。

跨平台打包的分层（见 packaging/README.md）：
- 全平台可用：PySide6 界面、翻译通道、SQLite 历史、截图 OCR（RapidOCR）、
  托盘、设置、诊断控制台。
- 仅 Windows：全局热键（Alt+Q/W/M/Space）、三次空格就地转译、
  划选翻译的剪贴板抓取、Win+H 语音听写、UIPI 提权、单实例互斥体。
- 朗读：Windows 走 SAPI；macOS 走系统 say；Linux 尝试 espeak，
  未安装则记日志不崩溃。

各模块用这里的常量做守卫，禁止在模块顶层无条件引用
ctypes.windll、win32*、pythoncom，否则 macOS / Linux 包一启动就崩。
"""
import sys

IS_WINDOWS = sys.platform.startswith("win")
IS_MAC = sys.platform == "darwin"
IS_LINUX = sys.platform.startswith("linux")

PLATFORM_NAME = "Windows" if IS_WINDOWS else ("macOS" if IS_MAC else ("Linux" if IS_LINUX else sys.platform))
