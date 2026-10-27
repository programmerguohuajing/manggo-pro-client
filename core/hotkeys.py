"""自定义全局热键：组合键字符串与 Windows 虚拟键码之间的转换与校验。

组合键格式：修饰键 + 主键，用 "+" 连接，修饰键顺序固定为 Alt、Ctrl、Shift，
例如 "Alt+Q"、"Ctrl+Shift+S"、"Alt+Space"。

规则（设置页录制与配置加载共用同一套校验）：
- 必须带至少一个修饰键（Alt / Ctrl / Shift），Win 键不支持录入：
  Win 组合键多被系统占用，钩子侧经常抢不到，录了也不可靠。
- 主键只允许字母 A-Z、数字 0-9、F1-F12、Space。
- 4 个动作的组合键不得重复；非法或重复的配置在加载时回退到默认值，
  在设置页保存时直接拒绝保存并提示。
"""

from typing import Dict, FrozenSet, Optional, Tuple

# 动作 key -> 说明（设置页按这个顺序展示）
ACTION_ORDER = ("selection", "screenshot", "workbench", "voice")
ACTION_NAMES = {
    "selection": "划选文本悬浮翻译",
    "screenshot": "全屏截图 OCR 翻译",
    "workbench": "呼出桌面翻译工作台",
    "voice": "语音输入与实时听写",
}

DEFAULT_HOTKEYS: Dict[str, str] = {
    "selection": "Alt+Q",
    "screenshot": "Alt+W",
    "workbench": "Alt+M",
    "voice": "Alt+Space",
}

_MODIFIERS = ("Alt", "Ctrl", "Shift")
_MODIFIER_VK = {"Alt": 0x12, "Ctrl": 0x11, "Shift": 0x10}

_MAIN_KEY_VK = {"Space": 0x20}
for _c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789":
    _MAIN_KEY_VK[_c] = ord(_c)
for _i in range(1, 13):
    _MAIN_KEY_VK[f"F{_i}"] = 0x6F + _i


def parse_hotkey(text: str) -> Optional[Tuple[FrozenSet[str], int, str]]:
    """解析组合键字符串。

    返回 (修饰键集合, 主键虚拟键码, 规范化字符串)，非法返回 None。
    规范化：修饰键按 Alt、Ctrl、Shift 顺序，主键大写，如 "Shift+Ctrl+q" -> "Ctrl+Shift+Q"。
    """
    if not isinstance(text, str):
        return None
    parts = [p.strip() for p in text.split("+")]
    if len(parts) < 2 or any(not p for p in parts):
        return None
    mods = set()
    for part in parts[:-1]:
        name = {"Alt": "Alt", "Control": "Ctrl", "Ctrl": "Ctrl", "Shift": "Shift"}.get(part)
        if name is None:
            return None
        mods.add(name)
    main = parts[-1].upper()
    if main == "SPACE":
        main = "Space"
    vk = _MAIN_KEY_VK.get(main)
    if vk is None or not mods:
        return None
    ordered = [m for m in _MODIFIERS if m in mods]
    return (frozenset(mods), vk, "+".join(ordered + [main]))


def modifier_vks(mods: FrozenSet[str]) -> FrozenSet[int]:
    return frozenset(_MODIFIER_VK[m] for m in mods)


def normalize_hotkeys(raw) -> Dict[str, str]:
    """把配置里的 hotkeys 规整成 4 个动作的完整映射。

    缺失、类型不对、非法、重复的项一律回退：先回退到该动作的默认值，
    默认值也被占了就找一个还没被用的默认值顶上。保证钩子永远有一套
    4 个互不重复、能用的组合键；回退后的结果会在设置页如实显示出来。
    """
    result: Dict[str, str] = {}
    seen = set()
    defaults_pool = [DEFAULT_HOTKEYS[a] for a in ACTION_ORDER]
    for action in ACTION_ORDER:
        candidate = None
        if isinstance(raw, dict):
            parsed = parse_hotkey(raw.get(action, ""))
            if parsed is not None:
                candidate = parsed[2]
        if candidate is None or candidate in seen:
            candidate = DEFAULT_HOTKEYS[action]
        if candidate in seen:
            for d in defaults_pool:
                if d not in seen:
                    candidate = d
                    break
            else:
                candidate = DEFAULT_HOTKEYS[action]  # 理论上到不了：4 动作、4 默认值
        seen.add(candidate)
        result[action] = candidate
    return result


def validate_hotkeys(raw) -> Optional[str]:
    """校验一套待保存的组合键，返回错误文案，无错误返回 None。"""
    if not isinstance(raw, dict):
        return "热键配置格式不正确"
    seen = {}
    for action in ACTION_ORDER:
        text = raw.get(action, "")
        parsed = parse_hotkey(text)
        if parsed is None:
            return f"“{ACTION_NAMES[action]}”的组合键“{text}”无效，请用 Alt / Ctrl / Shift + 字母、数字、F1-F12 或 Space"
        if parsed[2] in seen:
            return f"“{ACTION_NAMES[action]}”与“{ACTION_NAMES[seen[parsed[2]]]}”的组合键重复（{parsed[2]}），请换一个"
        seen[parsed[2]] = action
    return None
