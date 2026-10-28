"""
UI 展示层唯一色板与样式来源。

规则：
- 所有窗口只用这里的 token / 样式函数，不再各写一套十六进制颜色。
- 色板以设置窗口原有的琥珀主题为准（#EA580C 系），悬浮窗 / 主窗口
  原来用的 #e67e22 / #27ae60 统一收敛到这套色板，行为与布局不变。
- SETTINGS_STYLESHEET 由 settings_window.py 原样迁移至此，内容未改，
  settings_window.py 改为从这里导入，避免两份样式漂移。
"""

# ---- 色板（方案 A · 留白 + 托盘图标橙色，2026-10-28 定稿） ----
# 全应用只用两档文字色 + 一档细线 + 一个主题色；其余旧 token 全部
# 收敛到这组值上，名字保留以免各窗口的引用处大面积改动。
ACCENT = "#EA580C"
ACCENT_DARK = "#C2410C"
ACCENT_DEEP = "#9A3412"
ACCENT_SOFT_BG = "#FFF7ED"
ACCENT_SOFT_BORDER = "#FDBA74"
ACCENT_PALE = "#FFEDD5"
ACCENT_BG = "#FFFAF5"

INK = "#232120"
SECONDARY = "#8A857C"

TEXT = "#232120"
TEXT_PRIMARY = "#232120"
TEXT_SECONDARY = "#232120"
TEXT_MUTED = "#8A857C"
TEXT_FAINT = "#8A857C"
TEXT_GRAY600 = "#8A857C"

BORDER = "#ECECEE"
BORDER_STRONG = "#ECECEE"
SURFACE = "#FFFFFF"
SURFACE_MUTED = "#F7F7F8"
SURFACE_GRAY = "#F7F7F8"
APP_BG = "#FFFFFF"

# V2 名字保留，值已是方案 A：白底 + 暖炭文字 + 暖灰次要文字，
# 细分隔线代替色块卡片；橙色只做点缀（当前项竖线、开关开启态、
# 文字链、保存主按钮）。
PAPER = "#FFFFFF"
WARM_GRAY = "#8A857C"
WARM_FAINT = "#8A857C"
HAIRLINE = "#ECECEE"
INPUT_FILL = "#F7F7F8"

SUCCESS = "#27AE60"
SUCCESS_DARK = "#059669"
SUCCESS_BG = "#DCFCE7"
SUCCESS_TEXT = "#15803D"
ERROR_BG = "#FEE2E2"
ERROR_TEXT = "#B91C1C"
ERROR_BORDER = "#FEB2B2"
ERROR_DARK = "#C53030"
ERROR_BG_LIGHT = "#FFF5F5"
ERROR_TEXT_DARK = "#742A2A"
ERROR_HINT_DARK = "#9B2C2C"
DANGER = "#EF4444"
WARNING_BG = "#FFFBEB"
WARNING_BORDER = "#FDE68A"
WARNING_TITLE = "#92400E"
WARNING_TEXT = "#B45309"

STAR = "#EA580C"
STAR_INACTIVE = "#D6D3D1"
DARK_BG = "#1F2937"
DARK_PANEL = "#374151"
TOAST_TRANSLATING = "#EA580C"
TOAST_SUCCESS = "#FFFFFF"
TOAST_ERROR = "#FFFFFF"

FONT_FAMILY = '"Microsoft YaHei", "Segoe UI", sans-serif'
FONT_MONO = 'Consolas, "Segoe UI", monospace'


def badge_stylesheet(success: bool) -> str:
    """状态小胶囊（设置窗口测试诊断面板、托盘状态行共用）。"""
    if success:
        return (
            f"background: {SUCCESS_BG}; color: {SUCCESS_TEXT}; font-weight: bold; "
            "padding: 4px 10px; border-radius: 12px; font-size: 11px;"
        )
    return (
        f"background: {ERROR_BG}; color: {ERROR_TEXT}; font-weight: bold; "
        "padding: 4px 10px; border-radius: 12px; font-size: 11px;"
    )


def small_action_stylesheet() -> str:
    """悬浮窗里 60x20 的朗读 / 复制小按钮：安静文字按钮，暖灰字 + 细线边。"""
    return (
        f"font-size: 11px; border: 1px solid {BORDER_STRONG}; border-radius: 4px; "
        f"color: {SECONDARY}; background: transparent;"
    )


def ghost_button_stylesheet(color: str = TEXT_FAINT) -> str:
    """无框图标按钮（悬浮窗关闭 / 星标）。"""
    return f"border: none; color: {color}; cursor: pointer;"


def toast_stylesheet(status: str) -> str:
    """Toast 墨色小 pill：三种状态同一墨底，转译中图标取主题橙，
    成功 / 失败图标为白色，状态只靠图标形状区分。"""
    text = TOAST_TRANSLATING if status == "translating" else "#FFFFFF"
    return f"""
        QWidget {{
            background-color: rgba(35, 33, 32, 0.92);
            border-radius: 8px;
            border: 1px solid rgba(255, 255, 255, 0.15);
        }}
        QLabel {{
            color: {text};
            background: transparent;
            border: none;
        }}
    """


# 托盘右键菜单：跟设置窗口同一套琥珀主题，原生菜单不再裸奔。
TRAY_MENU_STYLESHEET = f"""
    QMenu {{
        background-color: {SURFACE};
        border: 1px solid {BORDER};
        border-radius: 8px;
        padding: 6px;
    }}
    QMenu::item {{
        padding: 6px 18px 6px 12px;
        border-radius: 6px;
        color: {TEXT_PRIMARY};
        font-size: 12px;
    }}
    QMenu::item:selected {{
        background-color: {ACCENT_PALE};
        color: {ACCENT_DARK};
    }}
    QMenu::item:disabled {{
        color: {TEXT_FAINT};
    }}
    QMenu::separator {{
        height: 1px;
        background: {BORDER};
        margin: 4px 8px;
    }}
"""

# 通用窗口样式：卡片 / 按钮 class / 输入框 / 下拉弹层 / 复选框 / 滑块。
# 方案 A：窗口底统一纯白（QWidget 通用规则在前，class 与控件规则在后，
# 同级选择器以后出现的为准，所以输入框、按钮等仍按各自规则着色）。
WINDOW_STYLESHEET = f"""
QWidget {{
    background-color: {SURFACE};
}}
QSplitter::handle {{
    background: {BORDER};
}}
QSplitter::handle:horizontal {{
    width: 1px;
}}
QSplitter::handle:vertical {{
    height: 1px;
}}
QFrame.CardFrame {{
    background-color: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 12px;
    padding: 16px 18px;
}}
QFrame.CardFrame:hover {{
    border-color: {ACCENT_SOFT_BORDER};
}}
QLabel.SectionTitle {{
    font-size: 14px;
    font-weight: bold;
    color: {TEXT_PRIMARY};
}}
QLabel.SectionDesc {{
    font-size: 12px;
    color: {TEXT_MUTED};
    line-height: 1.4;
}}
QLabel.FieldLabel {{
    font-size: 12px;
    font-weight: 600;
    color: {TEXT_SECONDARY};
}}
QLineEdit, QComboBox, QSpinBox, QTextEdit {{
    background-color: {SURFACE};
    border: 1px solid {BORDER_STRONG};
    border-radius: 6px;
    padding: 7px 10px;
    font-size: 12px;
    color: {TEXT};
    selection-background-color: #EA580C;
}}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QTextEdit:focus {{
    border: 1.5px solid {ACCENT};
    background-color: {ACCENT_BG};
}}
QComboBox::drop-down {{
    border: none;
    width: 26px;
}}
QComboBoxPrivateContainer {{
    border: none;
    background-color: transparent;
}}
QComboBox QAbstractItemView, QComboBox QListView {{
    background-color: {SURFACE};
    color: {TEXT};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 4px;
    outline: none;
    selection-background-color: {ACCENT_PALE};
    selection-color: {ACCENT_DARK};
}}
QComboBox QAbstractItemView::item, QComboBox QListView::item {{
    min-height: 32px;
    padding: 6px 12px;
    color: {TEXT_PRIMARY};
    background-color: {SURFACE};
    border-radius: 6px;
    font-size: 12px;
    border: none;
}}
QComboBox QAbstractItemView::item:hover, QComboBox QListView::item:hover {{
    background-color: {ACCENT_SOFT_BG};
    color: {ACCENT};
}}
QComboBox QAbstractItemView::item:selected, QComboBox QListView::item:selected {{
    background-color: {ACCENT_PALE};
    color: {ACCENT_DARK};
    font-weight: bold;
}}
QPushButton.PrimaryBtn {{
    background-color: {ACCENT};
    color: {SURFACE};
    font-size: 13px;
    font-weight: 600;
    border: none;
    border-radius: 7px;
    padding: 8px 20px;
}}
QPushButton.PrimaryBtn:hover {{
    background-color: {ACCENT_DARK};
}}
QPushButton.PrimaryBtn:pressed {{
    background-color: {ACCENT_DEEP};
}}
QPushButton.SecondaryBtn {{
    background-color: {SURFACE};
    color: {TEXT_SECONDARY};
    font-size: 12px;
    font-weight: 500;
    border: 1px solid {BORDER_STRONG};
    border-radius: 6px;
    padding: 6px 14px;
}}
QPushButton.SecondaryBtn:hover {{
    background-color: {SURFACE_GRAY};
    border-color: {TEXT_FAINT};
}}
QPushButton.TextBtn {{
    background: transparent;
    color: {ACCENT};
    font-size: 12px;
    font-weight: 500;
    border: none;
    padding: 4px 8px;
}}
QPushButton.TextBtn:hover {{
    text-decoration: underline;
}}
QCheckBox {{
    font-size: 13px;
    color: {TEXT_PRIMARY};
    spacing: 8px;
}}
QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border-radius: 4px;
    border: 1px solid {BORDER_STRONG};
    background: {SURFACE};
}}
QCheckBox::indicator:hover {{
    border-color: {ACCENT};
}}
QCheckBox::indicator:checked {{
    background-color: {ACCENT};
    border-color: {ACCENT};
}}
QSlider::groove:horizontal {{
    height: 6px;
    background: {BORDER};
    border-radius: 3px;
}}
QSlider::sub-page:horizontal {{
    background: {ACCENT};
    border-radius: 3px;
}}
QSlider::handle:horizontal {{
    background: {SURFACE};
    border: 2px solid {ACCENT};
    width: 16px;
    height: 16px;
    margin: -5px 0;
    border-radius: 8px;
}}
QSlider::handle:horizontal:hover {{
    background: {ACCENT_PALE};
}}
"""


# ---- 设置窗口样式（原 settings_window.py 原样迁移，内容未改） ----
SETTINGS_STYLESHEET = """
QWidget#SettingsWindow {
    background-color: #FFFFFF;
    font-family: -apple-system, "Segoe UI", "Microsoft YaHei", sans-serif;
}

/* 重设计：导航激活态为浅橙底 + 左侧 3px 橙条 + 橙字加粗 */
QListWidget#NavList {
    background-color: transparent;
    border: none;
    outline: none;
    padding-top: 20px;
}
QListWidget#NavList::item {
    height: 36px;
    margin: 2px 12px;
    padding-left: 12px;
    border-left: 3px solid transparent;
    color: #232120;
    font-size: 14px;
}
QListWidget#NavList::item:hover {
    color: #232120;
}
QListWidget#NavList::item:selected {
    background-color: #FFF7ED;
    border-left: 3px solid #EA580C;
    color: #EA580C;
    font-weight: bold;
}

/* 重设计：卡片统一白底 + #ECECEE 细边 + 16px 圆角；内边距由卡片布局的
   contentsMargins 给（20px），这里不重复加 padding，避免双倍缩进。 */
QFrame.CardFrame {
    background-color: #FFFFFF;
    border: 1px solid #ECECEE;
    border-radius: 16px;
    padding: 0px;
}
QFrame.CardFrame:hover {
    border: 1px solid #ECECEE;
}

/* 重设计：分区标题 15px 加粗深色，下一行配 12px 灰色说明（SectionDesc）。 */
QLabel.SectionHead {
    font-size: 15px;
    font-weight: bold;
    color: #232120;
}

/* 标题规范 */
QLabel.SectionTitle {
    font-size: 14px;
    font-weight: bold;
    color: #232120;
}
QLabel.SectionDesc {
    font-size: 12px;
    color: #8A857C;
    line-height: 1.4;
}
QLabel.FieldLabel {
    font-size: 12px;
    font-weight: 600;
    color: #232120;
}

/* 输入框与下拉框：浅灰底无边框、8px 圆角，聚焦时出现 2px 琥珀边。 */
QLineEdit, QComboBox, QSpinBox, QTextEdit {
    background-color: #F7F7F8;
    border: none;
    border-radius: 8px;
    padding: 7px 10px;
    font-size: 12px;
    color: #232120;
    selection-background-color: #EA580C;
}

/* V2：滑块改细线 + 小圆 thumb，不再是粗彩条 */
QSlider::groove:horizontal {
    height: 3px;
    background-color: #ECECEE;
    border-radius: 1px;
}
QSlider::handle:horizontal {
    width: 16px;
    height: 16px;
    margin: -7px 0;
    border-radius: 8px;
    background-color: #FFFFFF;
    border: 1px solid #D6D3D1;
}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QTextEdit:focus {
    /* 整数宽度：1.5px 分数边框在 Qt 光栅化时上下边渲染不一致，
    底边最容易看起来缺一块（搜索框焦点下边框被遮挡）；边框只向
    内生长，不改变布局尺寸，不会被裁。 */
    border: 2px solid #EA580C;
    background-color: #FFFFFF;
}
/* 微调框上下按钮：加宽到 24px，让 ▲▼ 上下分明、不挤成一小点 */
QSpinBox::up-button, QSpinBox::down-button {
    width: 24px;
    border: none;
}
QComboBox::drop-down {
    border: none;
    width: 26px;
}

/* 下拉菜单弹出层 (彻底消除 Windows 黑色外边框，呈现现代化柔和浅边) */
QComboBoxPrivateContainer {
    border: none;
    background-color: transparent;
}
QComboBox QAbstractItemView, QComboBox QListView {
    background-color: #FFFFFF;
    color: #232120;
    border: 1px solid #ECECEE;
    border-radius: 8px;
    padding: 4px;
    outline: none;
    selection-background-color: #FFEDD5;
    selection-color: #C2410C;
}
QComboBox QAbstractItemView::item, QComboBox QListView::item {
    min-height: 32px;
    padding: 6px 12px;
    color: #232120;
    background-color: #FFFFFF;
    border-radius: 6px;
    font-size: 12px;
    border: none;
}
QComboBox QAbstractItemView::item:hover, QComboBox QListView::item:hover {
    background-color: #FFF7ED;
    color: #EA580C;
}
QComboBox QAbstractItemView::item:selected, QComboBox QListView::item:selected {
    background-color: #FFEDD5;
    color: #C2410C;
    font-weight: bold;
}

/* 按钮规范 */
QPushButton.PrimaryBtn {
    background-color: #EA580C;
    color: #FFFFFF;
    font-size: 13px;
    font-weight: 600;
    border: none;
    border-radius: 7px;
    padding: 8px 20px;
}
QPushButton.PrimaryBtn:hover {
    background-color: #C2410C;
}
QPushButton.PrimaryBtn:pressed {
    background-color: #9A3412;
}

QPushButton.SecondaryBtn {
    background-color: #FFFFFF;
    color: #232120;
    font-size: 12px;
    font-weight: 500;
    border: 1px solid #ECECEE;
    border-radius: 6px;
    padding: 6px 14px;
}
QPushButton.SecondaryBtn:hover {
    background-color: #F7F7F8;
    border-color: #8A857C;
}

QPushButton.TextBtn {
    background: transparent;
    color: #EA580C;
    font-size: 12px;
    font-weight: 500;
    border: none;
    padding: 4px 8px;
}
QPushButton.TextBtn:hover {
    text-decoration: underline;
}

/* 复选框样式 */
QCheckBox {
    font-size: 13px;
    color: #232120;
    spacing: 8px;
}
QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border-radius: 4px;
    border: 1px solid #ECECEE;
    background: #FFFFFF;
}
QCheckBox::indicator:hover {
    border-color: #EA580C;
}
QCheckBox::indicator:checked {
    background-color: #EA580C;
    border-color: #EA580C;
}

/* 热键行：只能用类选择器挂边框——行内裸样式会把 border/padding 漏到子 label 上，
   造成每行出现两条分隔线、行高被撑大（2026-10-28 实测）。 */
QFrame.HotkeyRow {
    background: transparent;
    border-bottom: 1px solid #ECECEE;
}
/* 顶栏/底栏：同样只能用对象名挂边框，行内裸样式会漏给搜索框和按钮。 */
QFrame#SettingsHeader {
    background-color: #FFFFFF;
    border-bottom: 1px solid #ECECEE;
}
QFrame#SettingsFooter {
    background-color: #FFFFFF;
    border-top: 1px solid #ECECEE;
}
/* 搜索框：常驻 2px 透明边框，焦点时只换颜色不改尺寸，底边不再被裁。 */
QLineEdit.SearchBox {
    border: 2px solid transparent;
}
QLineEdit.SearchBox:focus {
    border: 2px solid #EA580C;
    background: #FFFFFF;
}

/* 注意：滑块样式只用上面 V2 那组（细线 + #D6D3D1 拇指边框，无彩条）；
   这里曾经有第二组橙色滑块规则，会把 V2 的覆盖掉，已删除，勿重复添加。 */
"""
