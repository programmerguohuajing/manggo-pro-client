"""设置页搜索：关键字到分区的匹配（Qt-free，可单测）。

V2 单页布局里，搜索框输入关键字后只显示匹配的分区；
匹配规则是双向子串：查询词包含关键字，或关键字包含查询词，
这样搜“热”“API”“空格”都能命中，不要求用户输入完整词。
"""

SECTION_KEYWORDS = {
    "engine": ["引擎", "通道", "免费", "大模型", "api", "key", "服务商", "预设", "模型", "prompt", "url"],
    "trigger": ["空格", "触发", "转译", "灵敏度", "划选", "输入框", "连击"],
    "hotkeys": ["热键", "快捷键", "alt", "录制", "组合键", "截图", "工作台", "语音", "听写"],
    "about": ["版本", "更新", "状态", "关于", "钩子", "历史", "识别", "朗读", "数据库"],
}


def section_matches(key: str, query: str) -> bool:
    """该分区是否匹配搜索词；空查询返回 True（显示全部）。"""
    q = (query or "").strip().lower()
    if not q:
        return True
    return any(kw in q or q in kw for kw in SECTION_KEYWORDS.get(key, []))
