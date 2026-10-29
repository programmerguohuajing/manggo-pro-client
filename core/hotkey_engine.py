"""平台无关的热键判定引擎：组合键 + 连续三次空格。

从 core/hook.py 的 Windows 低级钩子回调里抽出来的纯判定逻辑
（修饰键严格相等、按住重复只吞不触发、三次空格计数与复位），
不依赖 Win32 / CGEvent / X11，三个平台的后端只负责把各自的按键
事件翻译成 (主键名, 修饰键集合, 是否按下, 是否重复) 再喂进来。

主键名用配置字符串里的名字（'Q'、'W'、'Space'、'F1'……），
修饰键只用 'Alt'、'Ctrl'、'Shift'（配置只允许这三个；macOS 的
Option 键在后端映射成 'Alt'，Cmd 不进热键判定）。

引擎只做判定、不调回调：handle_key_down 返回 (动作名或 None,
是否吞键)，调用方（各平台后端）按动作名找自己的回调另起线程触发
（与 Windows 钩子一致：回调绝不能拖住按键回调本身）。

返回约定（handle_key_down）：
- (动作名, True)：组合键命中，调用方触发该动作，并且吞掉这次按键。
- ('triple_space', False)：三次空格命中，调用方触发就地转译，
  但空格本身不吞（三个空格要落到输入框里，替换器再处理）。
- (None, True)：按住主键的自动重复，只吞不重新触发。
- (None, False)：普通按键，放行；非修饰键还会把空格计数清零。
抬起事件（handle_key_up）只清按住态，永不触发、永不吞键。
"""

import threading
import time
from typing import FrozenSet, List, Optional, Tuple

# 修饰键本身：按下/抬起都不触发、不计数、不清零（Windows 钩子里
# 排除的 Shift/Ctrl/Alt/Win/VK_PROCESSKEY 在名字层面就是这几个）。
_MODIFIER_KEYS = frozenset({"Alt", "Ctrl", "Shift", "Cmd"})


class HotkeyEngine:
    """热键判定引擎。调用方（各平台后端）按事件顺序喂按键。"""

    def __init__(
        self,
        actions: List[Tuple[str, FrozenSet[str], str]],
        max_interval: float = 0.75,
    ):
        """actions：[(动作名, 修饰键集合, 主键名)]。

        调用方只把“有回调”的动作放进来（没回调的组合键直接放行，
        不吞键；macOS 上 workbench/voice 不在首批范围就是这么处理的）。
        """
        self.max_interval = max_interval
        # Linux 双线程喂事件（XGrabKey 组合键 + XRecord 三次空格）：
        # 判定表与按住态必须加锁，否则两个线程同时喂会互相污染。
        self._lock = threading.RLock()
        self._table: List[Tuple[FrozenSet[str], str, str]] = []
        self._set_table(actions)
        # (修饰键排序元组, 主键名)：当前按住未抬起的组合键（防重复触发）。
        self._down = set()
        self._space_down = False
        self.space_count = 0
        self.last_space_time = 0.0

    def _set_table(self, actions):
        self._table = [(frozenset(mods), key, action) for action, mods, key in actions]

    def update_actions(self, actions):
        """重建判定表（设置页改键后即时生效，不用重启后端）。"""
        with self._lock:
            self._set_table(actions)
            self._down.clear()
            self._space_down = False
            self.space_count = 0
            self.last_space_time = 0.0

    def matches_combo(self, main_key: str, mods_down: FrozenSet[str]) -> bool:
        """只查表、不改状态：Linux 的 XRecord 线程用它过滤组合键
        （组合键由 XGrabKey 线程专责触发，Record 线程跳过它们，
        否则同一按键会被两个线程各喂一次，触发权会被先喂的抢走）。"""
        with self._lock:
            mods = frozenset(mods_down)
            return any(
                main_key == table_key and mods == table_mods
                for table_mods, table_key, _action in self._table
            )

    def handle_key_down(
        self,
        main_key: str,
        mods_down: FrozenSet[str],
        is_repeat: bool = False,
        now: Optional[float] = None,
    ) -> Tuple[Optional[str], bool]:
        """处理一次按键按下。返回 (触发动作或 None, 是否吞键)。"""
        with self._lock:
            return self._handle_key_down_locked(main_key, mods_down, is_repeat, now)

    def _handle_key_down_locked(
        self, main_key, mods_down, is_repeat, now
    ) -> Tuple[Optional[str], bool]:
        if now is None:
            now = time.time()
        mods = frozenset(mods_down)

        # 修饰键本身：不触发、不计数、不清零（Windows 同款排除）。
        if main_key in _MODIFIER_KEYS:
            return None, False

        # 组合键：修饰键集合必须严格相等（Alt+Shift+Q 不能触发 Alt+Q）。
        for table_mods, table_key, action in self._table:
            if main_key == table_key and mods == table_mods:
                held = (tuple(sorted(table_mods)), table_key)
                if held in self._down:
                    return None, True  # 按住重复：只吞，不重新触发
                self._down.add(held)
                return action, True

        # 连续三次空格就地转译（无 Alt / Ctrl 干扰；空格本身不吞）。
        if main_key == "Space" and "Alt" not in mods and "Ctrl" not in mods:
            if is_repeat or self._space_down:
                return None, False  # 按住空格的自动重复不计数
            self._space_down = True
            delta = now - self.last_space_time if self.last_space_time > 0 else 0
            if self.last_space_time > 0 and delta <= self.max_interval:
                self.space_count += 1
            else:
                self.space_count = 1
            self.last_space_time = now
            if self.space_count >= 3:
                self.space_count = 0
                self.last_space_time = 0.0
                return "triple_space", False
            return None, False

        # 其他主键：空格计数清零（Windows 同款；修饰键已在上面排除）。
        if self.space_count > 0:
            self.space_count = 0
            self.last_space_time = 0.0
        return None, False

    def handle_key_up(self, main_key: str) -> None:
        """处理一次按键抬起：清按住态（组合键下次按下可重新触发）。"""
        with self._lock:
            if self._down:
                self._down = {k for k in self._down if k[1] != main_key}
            if main_key == "Space":
                self._space_down = False
