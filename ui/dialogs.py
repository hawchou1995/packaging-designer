# -*- coding: utf-8 -*-
"""dialogs.py — 设置 / 关于（左下角应用图标唤起）。"""
import os

from PySide6.QtCore import Qt
from PySide6.QtGui import QDesktopServices, QPixmap
from PySide6.QtCore import QUrl
from PySide6.QtWidgets import (QCheckBox, QDialog, QFormLayout, QHBoxLayout, QLabel,
                               QLineEdit, QPushButton, QTabWidget, QVBoxLayout, QWidget,
                               QFileDialog)

import theme

GITHUB_URL = "https://github.com/hawchou1995/packaging-designer"
AUTHOR = "周豪 · 供应链管理部"
APP_NAME = "包装设计器 Packaging Designer"
VERSION = "1.0.5"
DESC = ("面向瓦楞纸包装的参数量出图工具：片材、仿形垫块、网格刀卡、FEFCO 0201 / 0310 / 0312 纸箱。\n"
        "一次输入即产出 A3 图纸（展开图 + 轴测图 + GB 图框）、1:1 DXF、STEP/STL 数模与参数表。")


class SettingsDialog(QDialog):
    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.setWindowTitle("设置 / 关于")
        self.setMinimumWidth(560)
        v = QVBoxLayout(self)
        v.setContentsMargins(14, 12, 14, 12)
        v.setSpacing(10)
        tabs = QTabWidget()
        tabs.addTab(self._settings_tab(), "设置")
        tabs.addTab(self._about_tab(), "关于")
        v.addWidget(tabs)
        row = QHBoxLayout()
        row.addStretch(1)
        ok = QPushButton("保存")
        ok.setObjectName("Primary")
        ok.clicked.connect(self.on_save)
        cancel = QPushButton("关闭")
        cancel.clicked.connect(self.reject)
        row.addWidget(ok)
        row.addWidget(cancel)
        v.addLayout(row)

    @staticmethod
    def _sec(text):
        lab = QLabel(text)
        lab.setObjectName("FieldHint")
        f = lab.font()
        f.setBold(True)
        lab.setFont(f)
        return lab

    def _settings_tab(self):
        w = QWidget()
        f = QFormLayout(w)
        f.setLabelAlignment(Qt.AlignRight)
        f.setHorizontalSpacing(12)
        f.setVerticalSpacing(8)
        self.e_out = QLineEdit(self.settings.outdir)
        b = QPushButton("浏览…")
        b.clicked.connect(self._pick_dir)
        row = QWidget()
        h = QHBoxLayout(row)
        h.setContentsMargins(0, 0, 0, 0)
        h.addWidget(self.e_out, 1)
        h.addWidget(b)
        f.addRow("默认输出目录", row)
        self.e_prefix = QLineEdit(self.settings.prefix)
        self.e_prefix.setPlaceholderText("可留空；每个文件名 = 前缀 + 属性后缀")
        f.addRow("默认文件名前缀", self.e_prefix)
        self.e_company = QLineEdit(self.settings.company)
        f.addRow("图框 · 单位名称", self.e_company)
        self.e_author = QLineEdit(self.settings.author)
        self.e_author.setPlaceholderText("出现在图纸副标题「生成：…」与参数表里")
        f.addRow("图纸 · 生成人", self.e_author)
        f.addRow("", self._sec("图样栏（留空 = 程序自动生成，可覆盖）"))
        for key, lab, ph in (("dwg_name", "图样名称", "如：片材 400×300×15"),
                             ("dwg_no", "图样代号", "如：SHEET-400x300x15"),
                             ("dwg_version", "版本", "留空 = A"),
                             ("dwg_material", "材料", "如：BC 双瓦楞 t=7（可折叠）")):
            w = QLineEdit(getattr(self.settings, key))
            w.setPlaceholderText(ph)
            setattr(self, "e_" + key, w)
            f.addRow(f"图框 · {lab}", w)
        f.addRow("", self._sec("图框签署栏（与图纸右下角栏位一一对应）"))
        for key, lab in (("designed", "设计"), ("drawn", "制图"), ("proofed", "校对"),
                         ("checked", "审核"), ("process", "工艺"), ("standard", "标准化"),
                         ("approved", "批准")):
            w = QLineEdit(getattr(self.settings, key))
            w.setPlaceholderText("可留空")
            setattr(self, "e_" + key, w)
            f.addRow(f"图框 · {lab}", w)
        self.e_date = QLineEdit(self.settings.date)
        self.e_date.setPlaceholderText("留空 = 生成当天日期")
        f.addRow("图框 · 日期", self.e_date)
        self.c_open = QCheckBox("生成完成后自动打开输出目录")
        self.c_open.setChecked(self.settings.open_after)
        f.addRow("", self.c_open)
        note = QLabel("图框分隔栏为 GB/T 10609.1（ISO 7200）版式；单位名称与签署栏在图框内锁定，只在这里维护。")
        note.setObjectName("FieldHint")
        note.setWordWrap(True)
        f.addRow("", note)
        return w

    def _about_tab(self):
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(16, 16, 16, 16)
        v.setSpacing(10)
        top = QHBoxLayout()
        ic = QLabel()
        pm = QPixmap(theme.icon_path("app_64.png"))
        if not pm.isNull():
            ic.setPixmap(pm)
        ic.setFixedSize(64, 64)
        top.addWidget(ic)
        tt = QVBoxLayout()
        tt.setSpacing(2)
        n = QLabel(APP_NAME)
        n.setObjectName("AboutHead")
        s = QLabel(f"版本 {VERSION} · 开源（MIT）")
        s.setObjectName("AboutSub")
        tt.addWidget(n)
        tt.addWidget(s)
        top.addLayout(tt)
        top.addStretch(1)
        v.addLayout(top)
        d = QLabel(DESC)
        d.setWordWrap(True)
        d.setObjectName("Hint")
        v.addWidget(d)
        v.addSpacing(4)
        rows = [("作者", AUTHOR),
                ("开源地址", GITHUB_URL),
                ("数据来源", "公司包材汇总表（楞型 / 厚度 / 边压 / 耐破）"),
                ("制图依据", "GB/T 10609.1 · GB/T 14689 · GB/T 14690 · GB/T 6543-2025 · GB/T 6544 · FEFCO 目录"),
                ("技术栈", "Python · PySide6 · matplotlib · ezdxf · OpenCascade(OCP) · PyInstaller + NSIS")]
        g = QFormLayout()
        g.setHorizontalSpacing(14)
        g.setVerticalSpacing(6)
        for k, val in rows:
            lab = QLabel(val)
            lab.setWordWrap(True)
            if k == "开源地址":
                lab.setObjectName("Link")
                lab.setText(f'<a href="{GITHUB_URL}" style="color:{theme.ACCENT}">{GITHUB_URL}</a>')
                lab.setOpenExternalLinks(True)
            g.addRow(k, lab)
        v.addLayout(g)
        open_btn = QPushButton("在浏览器中打开开源地址")
        open_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(GITHUB_URL)))
        hb = QHBoxLayout()
        hb.addWidget(open_btn)
        hb.addStretch(1)
        v.addLayout(hb)
        v.addStretch(1)
        return w

    def _pick_dir(self):
        d = QFileDialog.getExistingDirectory(self, "选择默认输出目录", self.e_out.text())
        if d:
            self.e_out.setText(d)

    def on_save(self):
        s = self.settings
        s.outdir = self.e_out.text().strip() or s.outdir
        s.prefix = self.e_prefix.text().strip()
        s.company = self.e_company.text().strip() or s.company
        s.author = self.e_author.text().strip() or s.author
        for key in ("designed", "drawn", "proofed", "checked", "process", "standard",
                    "approved", "date", "dwg_name", "dwg_no", "dwg_version",
                    "dwg_material"):
            setattr(s, key, getattr(self, "e_" + key).text().strip())
        s.open_after = self.c_open.isChecked()
        s.save()
        self.accept()


class FrameDialog(QDialog):
    """只维护图框字段的轻量对话框——在图框里看到空格子时直接开这个填。"""

    FIELDS = (("company", "单位名称"), ("author", "生成人（副标题）"),
              ("dwg_name", "图样名称"), ("dwg_no", "图样代号"), ("dwg_version", "版本"),
              ("dwg_material", "材料"),
              ("designed", "设计"), ("drawn", "制图"), ("proofed", "校对"),
              ("checked", "审核"), ("process", "工艺"), ("standard", "标准化"),
              ("approved", "批准"), ("date", "日期（留空 = 当天）"))

    # 留空 = 用程序自动值（占位提示告诉用户自动值长什么样）
    PLACEHOLDER = {"dwg_name": "留空 = 自动，如：片材 片材 400×300×15",
                   "dwg_no": "留空 = 自动，如：SHEET-400x300x15",
                   "dwg_version": "留空 = A",
                   "dwg_material": "留空 = 自动，如：BC 双瓦楞 t=7（可折叠）",
                   "date": "留空 = 生成当天日期"}

    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.setWindowTitle("图框字段")
        self.setMinimumWidth(430)
        v = QVBoxLayout(self)
        v.setContentsMargins(16, 14, 16, 12)
        v.setSpacing(10)
        f = QFormLayout()
        f.setLabelAlignment(Qt.AlignRight)
        f.setHorizontalSpacing(12)
        f.setVerticalSpacing(7)
        self.edits = {}
        for key, lab in self.FIELDS:
            w = QLineEdit(str(getattr(settings, key, "") or ""))
            ph = self.PLACEHOLDER.get(key)
            if ph:
                w.setPlaceholderText(ph)
            self.edits[key] = w
            f.addRow(lab, w)
        v.addLayout(f)
        hint = QLabel("这些值直接写进图纸右下角图框（GB/T 10609.1）；"
                      "图样名称/代号/版本/材料留空时用程序自动值，填了就按你填的写。"
                      "保存后重新「生成」生效。")
        hint.setObjectName("FieldHint")
        hint.setWordWrap(True)
        v.addWidget(hint)
        row = QHBoxLayout()
        row.addStretch(1)
        ok = QPushButton("保存")
        ok.setObjectName("Primary")
        ok.clicked.connect(self.on_save)
        cancel = QPushButton("关闭")
        cancel.clicked.connect(self.reject)
        row.addWidget(ok)
        row.addWidget(cancel)
        v.addLayout(row)

    def on_save(self):
        for key, w in self.edits.items():
            val = w.text().strip()
            if key == "company" and not val:
                continue
            setattr(self.settings, key, val)
        self.settings.save()
        self.accept()
