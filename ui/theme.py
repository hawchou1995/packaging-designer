# -*- coding: utf-8 -*-
"""theme.py — 视觉令牌 + 全局 QSS。

设计读（taste-skill §0）：工程/生产工具，受众 = 包装工程师（信任优先、信息密度高、装饰低）。
拨盘：DESIGN_VARIANCE 3（对称、可预测）· MOTION_INTENSITY 2（仅 hover/active）· VISUAL_DENSITY 6（数据可读优先）
约束：单一强调色（深青 #0F766E）、圆角统一 4px、输入标签在上、数字用等宽字体、无 emoji / 无装饰性色点 / 无破折号装饰。
"""
import os

ACCENT = "#0F766E"
ACCENT_HOVER = "#11857C"
ACCENT_PRESS = "#0B5D57"
ACCENT_SOFT = "#E6F2F0"

BG = "#F0F2F4"
CARD = "#FBFCFC"
RAIL = "#20252A"
RAIL_HOVER = "#2B3138"
RAIL_TEXT = "#C9CFD6"
BORDER = "#DBDFE4"
BORDER_STRONG = "#C3C9D0"

TEXT = "#1B1E22"
TEXT2 = "#5A6169"
TEXT3 = "#8A9099"

OK = "#15803D"
WARN = "#B45309"
ERR = "#BE1F2E"

RADIUS = "4px"
UI_FONT = '"Microsoft YaHei UI", "Segoe UI", sans-serif'
MONO_FONT = '"Consolas", "JetBrains Mono", monospace'


def qss():
    return f"""
QWidget {{
    background: {BG};
    color: {TEXT};
    font-family: {UI_FONT};
    font-size: 12px;
}}
QLabel {{ background: transparent; }}
QToolTip {{
    background: {RAIL}; color: #F2F4F6; border: 0; padding: 4px 6px;
}}
/* ---------- 左导航 ---------- */
#Rail {{ background: {RAIL}; }}
#RailTitle {{ color: #FFFFFF; font-size: 15px; font-weight: 600; }}
#RailSub {{ color: {TEXT3}; font-size: 10px; }}
QPushButton#NavItem {{
    background: transparent; color: {RAIL_TEXT}; border: 0; border-left: 3px solid transparent;
    padding: 8px 10px 8px 9px; text-align: left; font-size: 12.5px; border-radius: 0px;
}}
QPushButton#NavItem:hover {{ background: {RAIL_HOVER}; color: #FFFFFF; }}
QPushButton#NavItem:checked {{
    background: {RAIL_HOVER}; color: #FFFFFF; border-left: 3px solid {ACCENT}; font-weight: 600;
}}
#AppIconBtn {{ background: transparent; border: 0; padding: 6px; border-radius: {RADIUS}; }}
#AppIconBtn:hover {{ background: {RAIL_HOVER}; }}
#RailFoot {{ color: {TEXT3}; font-size: 10px; }}
/* ---------- 卡片 ---------- */
#Card {{ background: {CARD}; border: 1px solid {BORDER}; border-radius: {RADIUS}; }}
#CardTitle {{ font-size: 12.5px; font-weight: 600; color: {TEXT}; }}
#PageTitle {{ font-size: 16px; font-weight: 600; }}
#PageSub {{ font-size: 11.5px; color: {TEXT2}; }}
#FieldLabel {{ font-size: 11.5px; color: {TEXT2}; }}
#FieldHint {{ font-size: 10.5px; color: {TEXT3}; }}
#SectionLabel {{ font-size: 11px; color: {TEXT3}; }}
#Mono {{ font-family: {MONO_FONT}; }}
#Stat {{ font-family: {MONO_FONT}; font-size: 13px; font-weight: 600; }}
#StatSuffix {{ font-size: 10.5px; color: {TEXT3}; }}
/* ---------- 输入 ---------- */
QLineEdit, QDoubleSpinBox, QSpinBox, QComboBox {{
    background: #FFFFFF; border: 1px solid {BORDER_STRONG}; border-radius: {RADIUS};
    padding: 2px 6px; min-height: 22px; selection-background-color: {ACCENT};
}}
QLineEdit:focus, QDoubleSpinBox:focus, QSpinBox:focus, QComboBox:focus {{
    border: 1px solid {ACCENT};
}}
QLineEdit:disabled, QDoubleSpinBox:disabled, QSpinBox:disabled, QComboBox:disabled {{
    background: #F4F5F7; color: {TEXT3};
}}
QLineEdit[readOnly="true"] {{ background: #F4F5F7; }}
QDoubleSpinBox, QSpinBox {{ font-family: {MONO_FONT}; }}
QComboBox::drop-down {{ border: 0; width: 18px; }}
QComboBox QAbstractItemView {{
    background: #FFFFFF; border: 1px solid {BORDER_STRONG}; selection-background-color: {ACCENT_SOFT};
    selection-color: {TEXT}; outline: 0;
}}
QCheckBox {{ spacing: 6px; }}
QCheckBox::indicator {{ width: 14px; height: 14px; border: 1px solid {BORDER_STRONG};
    border-radius: 2px; background: #FFFFFF; }}
QCheckBox::indicator:checked {{ background: {ACCENT}; border: 1px solid {ACCENT};
    image: none; }}
QRadioButton {{ spacing: 6px; }}
QRadioButton::indicator {{ width: 14px; height: 14px; border: 1px solid {BORDER_STRONG};
    border-radius: 7px; background: #FFFFFF; }}
QRadioButton::indicator:checked {{ border: 4px solid {ACCENT}; background: #FFFFFF; }}
/* ---------- 按钮 ---------- */
QPushButton {{
    background: #FFFFFF; border: 1px solid {BORDER_STRONG}; border-radius: {RADIUS};
    padding: 4px 12px; min-height: 22px; color: {TEXT};
}}
QPushButton:hover {{ border: 1px solid {ACCENT}; color: {ACCENT}; }}
QPushButton:pressed {{ background: {ACCENT_SOFT}; }}
QPushButton:disabled {{ color: {TEXT3}; border: 1px solid {BORDER}; background: #F4F5F7; }}
QPushButton#Primary {{
    background: {ACCENT}; color: #FFFFFF; border: 1px solid {ACCENT}; font-weight: 600;
    padding: 5px 16px;
}}
QPushButton#Primary:hover {{ background: {ACCENT_HOVER}; border: 1px solid {ACCENT_HOVER}; color: #FFFFFF; }}
QPushButton#Primary:pressed {{ background: {ACCENT_PRESS}; }}
QPushButton#Primary:disabled {{ background: #A9BFBC; border: 1px solid #A9BFBC; color: #F2F5F4; }}
QPushButton#Ghost {{ background: transparent; border: 0; color: {ACCENT}; padding: 2px 4px; }}
QPushButton#Seg, QPushButton#FluteBtn {{
    background: #FFFFFF; border: 1px solid {BORDER_STRONG}; border-radius: {RADIUS};
    padding: 3px 10px; min-height: 20px; color: {TEXT2};
}}
QPushButton#Seg:hover, QPushButton#FluteBtn:hover {{ border: 1px solid {ACCENT}; color: {ACCENT}; }}
QPushButton#Seg:checked, QPushButton#FluteBtn:checked {{
    background: {ACCENT}; border: 1px solid {ACCENT}; color: #FFFFFF; font-weight: 600;
}}
QPushButton#FluteBtn {{ padding: 3px 7px; }}
QPushButton#Ghost:hover {{ color: {ACCENT_PRESS}; text-decoration: underline; }}
/* ---------- 列表 / 进度 ---------- */
QListWidget {{
    background: #FFFFFF; border: 1px solid {BORDER}; border-radius: {RADIUS}; padding: 2px;
}}
QListWidget::item {{ padding: 3px 4px; }}
QListWidget::item:selected {{ background: {ACCENT_SOFT}; color: {TEXT}; }}
QProgressBar {{
    background: {ACCENT_SOFT}; border: 0; border-radius: 2px; height: 4px; text-align: center;
}}
QProgressBar::chunk {{ background: {ACCENT}; border-radius: 2px; }}
QScrollArea {{ border: 0; background: transparent; }}
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 0; }}
QScrollBar::handle:vertical {{ background: #C6CBD1; border-radius: 5px; min-height: 24px; }}
QScrollBar::handle:vertical:hover {{ background: #A9AFB6; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; width: 0; }}
QScrollBar:horizontal {{ background: transparent; height: 10px; }}
QScrollBar::handle:horizontal {{ background: #C6CBD1; border-radius: 5px; min-width: 24px; }}
QTableWidget {{ background: #FFFFFF; border: 1px solid {BORDER}; border-radius: {RADIUS};
    gridline-color: {BORDER}; }}
QTableWidget::item {{ padding: 2px 6px; }}
QHeaderView::section {{ background: {BG}; border: 0; border-bottom: 1px solid {BORDER};
    padding: 3px 6px; color: {TEXT2}; font-weight: 600; }}
QDialog {{ background: {BG}; }}
QTabWidget::pane {{ border: 1px solid {BORDER}; border-radius: {RADIUS}; background: {CARD}; }}
QTabBar::tab {{ background: transparent; border: 0; padding: 6px 12px; color: {TEXT2}; }}
QTabBar::tab:selected {{ color: {ACCENT}; border-bottom: 2px solid {ACCENT}; font-weight: 600; }}
#Hint {{ color: {TEXT2}; font-size: 11.5px; }}
#Ok {{ color: {OK}; font-weight: 600; }}
#Err {{ color: {ERR}; font-weight: 600; }}
#Warn {{ color: {WARN}; font-weight: 600; }}
#AboutHead {{ font-size: 18px; font-weight: 600; }}
#AboutSub {{ color: {TEXT2}; font-size: 12px; }}
#Link {{ color: {ACCENT}; }}
"""


def icon_path(name="app.ico"):
    """资源图标路径：兼容源码运行与 PyInstaller 冻结（_MEIPASS）。"""
    import sys
    cands = []
    base = getattr(sys, "_MEIPASS", None)
    if base:
        cands.append(os.path.join(base, "resources", name))
    here = os.path.dirname(os.path.abspath(__file__))
    cands.append(os.path.join(here, "..", "resources", name))
    cands.append(os.path.join(here, "resources", name))
    cands.append(os.path.join(os.path.dirname(sys.executable), "resources", name))
    cands.append(os.path.join(os.path.dirname(sys.executable), "_internal", "resources", name))
    for c in cands:
        if os.path.exists(c):
            return os.path.abspath(c)
    return os.path.abspath(cands[0])
