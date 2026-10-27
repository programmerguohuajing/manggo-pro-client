"""
UI 展示层唯一色板与样式来源。

规则：
- 所有窗口只用这里的 token / 样式函数，不再各写一套十六进制颜色。
- 色板以设置窗口原有的琥珀主题为准（#EA580C 系），悬浮窗 / 主窗口
  原来用的 #e67e22 / #27ae60 统一收敛到这套色板，行为与布局不变。
- SETTINGS_STYLESHEET 由 settings_window.py 原样迁移至此，内容未改，
  settings_window.py 改为从这里导入，避免两份样式漂移。
"""

# ---- 色板 ----
ACCENT = "#EA580C"
ACCENT_DARK = "#C2410C"
ACCENT_DEEP = "#9A3412"
ACCENT_SOFT_BG = "#FFF7ED"
ACCENT_SOFT_BORDER = "#FDBA74"
ACCENT_PALE = "#FFEDD5"
ACCENT_BG = "#FFFAF5"

TEXT = "#111827"
TEXT_PRIMARY = "#1F2937"
TEXT_SECONDARY = "#374151"
TEXT_MUTED = "#6B7280"
TEXT_FAINT = "#9CA3AF"
TEXT_GRAY600 = "#4B5563"

BORDER = "#E5E7EB"
BORDER_STRONG = "#D1D5DB"
SURFACE = "#FFFFFF"
SURFACE_MUTED = "#F9FAFB"
SURFACE_GRAY = "#F3F4F6"
APP_BG = "#F8F9FB"

# V2 高级感色板（设置页新布局专用）：暖纸底 + 墨色文字 + 暖灰次要文字，
# 细分隔线代替色块卡片；琥珀只做点缀（当前项竖线、开关开启态、文字链、
# 保存主按钮），主按钮按用户定保持琥珀色。
INK = "#1C1917"
PAPER = "#FAFAF9"
WARM_GRAY = "#78716C"
WARM_FAINT = "#A8A29E"
HAIRLINE = "#E7E5E4"
INPUT_FILL = "#F5F5F4"

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

STAR = "#F39C12"
DARK_BG = "#1F2937"
DARK_PANEL = "#374151"
TOAST_TRANSLATING = "#61AFEF"
TOAST_SUCCESS = "#98C379"
TOAST_ERROR = "#E06C75"

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
    """悬浮窗里 60x20 的朗读 / 复制小按钮（原内联样式，颜色收敛到色板）。"""
    return (
        f"font-size: 11px; border: 1px solid {BORDER_STRONG}; border-radius: 4px; "
        f"color: {TEXT_SECONDARY};"
    )


def ghost_button_stylesheet(color: str = TEXT_FAINT) -> str:
    """无框图标按钮（悬浮窗关闭 / 星标）。"""
    return f"border: none; color: {color}; cursor: pointer;"


def toast_stylesheet(status: str) -> str:
    """Toast 深色气泡：三种状态只换文字色与图标色，结构不变。"""
    if status == "translating":
        bg, text = "rgba(40, 44, 52, 0.9)", TOAST_TRANSLATING
    elif status == "success":
        bg, text = "rgba(40, 52, 45, 0.9)", TOAST_SUCCESS
    else:
        bg, text = "rgba(52, 40, 40, 0.9)", TOAST_ERROR
    return f"""
        QWidget {{
            background-color: {bg};
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
# 只定义 class 选择器与输入类控件，不改窗口背景，避免套到悬浮卡片上变味。
WINDOW_STYLESHEET = f"""
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
    selection-background-color: #F97316;
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
    image: none;
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
    background-color: #FAFAF9;
    font-family: -apple-system, "Segoe UI", "Microsoft YaHei", sans-serif;
}

/* V2：侧边导航只剩文字，当前项靠左侧 2px 琥珀竖线标识，不用色块背景 */
QListWidget#NavList {
    background-color: transparent;
    border: none;
    outline: none;
    padding-top: 18px;
}
QListWidget#NavList::item {
    height: 42px;
    margin: 2px 8px;
    padding-left: 12px;
    border-left: 2px solid transparent;
    color: #78716C;
    font-size: 14px;
}
QListWidget#NavList::item:hover {
    color: #1C1917;
}
QListWidget#NavList::item:selected {
    background-color: transparent;
    border-left: 2px solid #EA580C;
    color: #1C1917;
    font-weight: bold;
}

/* V2：分区不再是带边框的卡片，卡片容器拍平成透明，分区之间靠间距区分 */
QFrame.CardFrame {
    background-color: transparent;
    border: none;
    border-radius: 0px;
    padding: 0px;
}
QFrame.CardFrame:hover {
    border: none;
}

/* V2：分区标题是 12px 灰色小字，不再是大号加粗标题 */
QLabel.SectionHead {
    font-size: 12px;
    font-weight: 600;
    color: #A8A29E;
}

/* 标题规范 */
QLabel.SectionTitle {
    font-size: 14px;
    font-weight: bold;
    color: #1F2937;
}
QLabel.SectionDesc {
    font-size: 12px;
    color: #6B7280;
    line-height: 1.4;
}
QLabel.FieldLabel {
    font-size: 12px;
    font-weight: 600;
    color: #374151;
}

/* 输入框与下拉框：V2 改成浅灰底无边框，聚焦时才出现琥珀边 */
QLineEdit, QComboBox, QSpinBox, QTextEdit {
    background-color: #F5F5F4;
    border: 1px solid #E7E5E4;
    border-radius: 6px;
    padding: 7px 10px;
    font-size: 12px;
    color: #111827;
    selection-background-color: #F97316;
}

/* V2：滑块改细线 + 小圆 thumb，不再是粗彩条 */
QSlider::groove:horizontal {
    height: 3px;
    background-color: #E7E5E4;
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
    border: 1.5px solid #EA580C;
    background-color: #FFFAF5;
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
    color: #111827;
    border: 1px solid #E5E7EB;
    border-radius: 8px;
    padding: 4px;
    outline: none;
    selection-background-color: #FFEDD5;
    selection-color: #C2410C;
}
QComboBox QAbstractItemView::item, QComboBox QListView::item {
    min-height: 32px;
    padding: 6px 12px;
    color: #1F2937;
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
    color: #374151;
    font-size: 12px;
    font-weight: 500;
    border: 1px solid #D1D5DB;
    border-radius: 6px;
    padding: 6px 14px;
}
QPushButton.SecondaryBtn:hover {
    background-color: #F3F4F6;
    border-color: #9CA3AF;
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
    color: #1F2937;
    spacing: 8px;
}
QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border-radius: 4px;
    border: 1px solid #D1D5DB;
    background: #FFFFFF;
}
QCheckBox::indicator:hover {
    border-color: #EA580C;
}
QCheckBox::indicator:checked {
    background-color: #EA580C;
    border-color: #EA580C;
    image: none;
}

/* 滑块样式 */
QSlider::groove:horizontal {
    height: 6px;
    background: #E5E7EB;
    border-radius: 3px;
}
QSlider::sub-page:horizontal {
    background: #EA580C;
    border-radius: 3px;
}
QSlider::handle:horizontal {
    background: #FFFFFF;
    border: 2px solid #EA580C;
    width: 16px;
    height: 16px;
    margin: -5px 0;
    border-radius: 8px;
}
QSlider::handle:horizontal:hover {
    background: #FFEDD5;
}
"""
