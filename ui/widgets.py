# -*- coding: utf-8 -*-
"""widgets.py — 通用控件：卡片 / 表单行 / 数值框 / 结果表 / 文件面板 / 预览。

表单规范（taste-skill §4.6）：标签在输入之上，提示文字在下方；错误在字段下方内联。
"""
import os
import subprocess
import sys

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDesktopServices, QFont, QPixmap
from PySide6.QtCore import QUrl
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDoubleSpinBox, QFrame, QGridLayout,
                               QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem, QProgressBar,
                               QPushButton, QSizePolicy, QTableWidget, QTableWidgetItem,
                               QVBoxLayout, QWidget)

import theme


def mono(widget, size=12):
    f = QFont("Consolas")
    f.setStyleHint(QFont.Monospace)
    f.setPointSize(size)
    widget.setFont(f)
    return widget


class Card(QFrame):
    """白底描边卡片；只在需要层级时使用（taste §4.4）。"""

    def __init__(self, title=None, parent=None):
        super().__init__(parent)
        self.setObjectName("Card")
        self._v = QVBoxLayout(self)
        self._v.setContentsMargins(12, 10, 12, 12)
        self._v.setSpacing(8)
        if title:
            lab = QLabel(title)
            lab.setObjectName("CardTitle")
            self._v.addWidget(lab)

    def body(self):
        return self._v

    def add(self, w):
        self._v.addWidget(w)
        return w


class FieldRow(QWidget):
    """标签在上 / 控件 / 可选提示在下。"""

    def __init__(self, label, widget, hint=None, parent=None):
        super().__init__(parent)
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(3)
        lab = QLabel(label)
        lab.setObjectName("FieldLabel")
        v.addWidget(lab)
        v.addWidget(widget)
        self.hint = None
        if hint:
            self.hint = QLabel(hint)
            self.hint.setObjectName("FieldHint")
            self.hint.setWordWrap(True)
            v.addWidget(self.hint)

    def set_hint(self, text, kind=None):
        if self.hint is None:
            return
        self.hint.setText(text)
        self.hint.setObjectName({"err": "Err", "warn": "Warn", "ok": "Ok"}.get(kind, "FieldHint"))
        self.hint.style().unpolish(self.hint)
        self.hint.style().polish(self.hint)


def num_field(label, value, lo=0.0, hi=1e6, step=1.0, decimals=1, hint=None,
              suffix="mm", width=None, on_change=None):
    sp = QDoubleSpinBox()
    sp.setRange(lo, hi)
    sp.setDecimals(decimals)
    sp.setSingleStep(step)
    sp.setValue(value)
    sp.setSuffix(" " + suffix if suffix else "")
    mono(sp)
    if width:
        sp.setFixedWidth(width)
    if on_change:
        sp.valueChanged.connect(lambda *_: on_change())
    row = FieldRow(label, sp, hint)
    row.widget = sp
    sp._row = row
    return row


def int_field(label, value, lo=1, hi=9999, hint=None, suffix=None, on_change=None):
    from PySide6.QtWidgets import QSpinBox
    sp = QSpinBox()
    sp.setRange(lo, hi)
    sp.setValue(value)
    if suffix:
        sp.setSuffix(" " + suffix)
    mono(sp)
    if on_change:
        sp.valueChanged.connect(lambda *_: on_change())
    row = FieldRow(label, sp, hint)
    row.widget = sp
    return row


def text_field(label, value="", hint=None, placeholder="", on_change=None, width=None):
    le = QLineEdit(value)
    if placeholder:
        le.setPlaceholderText(placeholder)
    if width:
        le.setFixedWidth(width)
    if on_change:
        le.textChanged.connect(lambda *_: on_change())
    row = FieldRow(label, le, hint)
    row.widget = le
    return row


def choice_field(label, options, value=None, hint=None, on_change=None):
    """options: [(value, text)] 或 [text]"""
    cb = QComboBox()
    for o in options:
        if isinstance(o, (tuple, list)):
            cb.addItem(str(o[1]), o[0])
        else:
            cb.addItem(str(o), o)
    if value is not None:
        i = cb.findData(value)
        if i >= 0:
            cb.setCurrentIndex(i)
    if on_change:
        cb.currentIndexChanged.connect(lambda *_: on_change())
    row = FieldRow(label, cb, hint)
    row.widget = cb
    return row


def check_field(label, checked=False, hint=None, on_change=None):
    cb = QCheckBox(label)
    cb.setChecked(checked)
    if on_change:
        cb.toggled.connect(lambda *_: on_change())
    w = QWidget()
    v = QVBoxLayout(w)
    v.setContentsMargins(0, 0, 0, 0)
    v.setSpacing(3)
    v.addWidget(cb)
    if hint:
        h = QLabel(hint)
        h.setObjectName("FieldHint")
        h.setWordWrap(True)
        v.addWidget(h)
    w.widget = cb
    return w


class TwoColForm(QWidget):
    """两列表单网格，标签在上。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.g = QGridLayout(self)
        self.g.setContentsMargins(0, 0, 0, 0)
        self.g.setHorizontalSpacing(10)
        self.g.setVerticalSpacing(8)
        self._r = 0

    def add(self, row, col=0, span=1):
        self.g.addWidget(row, self._r, col, 1, span)
        return row

    def add_wide(self, row):
        self.g.addWidget(row, self._r, 0, 1, 2)
        self._r += 1
        return row

    def next_row(self):
        self._r += 1


class ResultTable(QTableWidget):
    """键值结果表：两列、无表头、可选中复制。"""

    def __init__(self, parent=None):
        super().__init__(0, 2, parent)
        self.horizontalHeader().setVisible(False)
        self.verticalHeader().setVisible(False)
        self.setShowGrid(False)
        self.setEditTriggers(QTableWidget.NoEditTriggers)
        self.setSelectionMode(QTableWidget.ContiguousSelection)
        self.setFocusPolicy(Qt.ClickFocus)
        self.setAlternatingRowColors(False)
        self.horizontalHeader().setStretchLastSection(True)
        self.setColumnWidth(0, 150)

    def set_rows(self, rows, headers=None):
        self.setRowCount(len(rows))
        for i, kv in enumerate(rows):
            k, v = (kv if isinstance(kv, (tuple, list)) else (kv, ""))
            a = QTableWidgetItem(str(k))
            b = QTableWidgetItem(str(v))
            mono(b, 10)
            self.setItem(i, 0, a)
            self.setItem(i, 1, b)
        self.resizeRowsToContents()


class FileList(QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(70)

    def set_files(self, files):
        self.clear()
        for f in files:
            it = QListWidgetItem(os.path.basename(f))
            it.setToolTip(f)
            self.addItem(it)


class PreviewPane(QWidget):
    """生成后预览主图（A3 PNG 缩略）。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(6)
        self.lab = QLabel("尚未生成。设置参数后点击「生成并导出」。")
        self.lab.setObjectName("Hint")
        self.lab.setAlignment(Qt.AlignCenter)
        self.lab.setMinimumHeight(200)
        self.lab.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.lab.setStyleSheet(f"background:#FFFFFF;border:1px solid {theme.BORDER};"
                               f"border-radius:{theme.RADIUS};")
        v.addWidget(self.lab)
        self._path = None

    def show_image(self, path):
        self._path = path
        if not path or not os.path.exists(path):
            self.lab.setPixmap(QPixmap())
            self.lab.setText("未找到预览图")
            return
        pm = QPixmap(path)
        if pm.isNull():
            self.lab.setText("无法读取预览图")
            return
        self.lab.setPixmap(pm.scaled(max(240, self.lab.width() - 8), max(160, self.lab.height() - 8),
                                     Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if self._path:
            self.show_image(self._path)


class BusyBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        h = QHBoxLayout(self)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(8)
        self.bar = QProgressBar()
        self.bar.setRange(0, 0)
        self.bar.setFixedHeight(4)
        self.bar.setVisible(False)
        self.status = QLabel("")
        self.status.setObjectName("Hint")
        h.addWidget(self.bar, 1)
        h.addWidget(self.status, 0)

    def busy(self, text):
        self.bar.setVisible(True)
        self.status.setText(text)
        self.status.setObjectName("Hint")
        self._repolish()

    def info(self, text):
        self.bar.setVisible(False)
        self.status.setText(text)
        self.status.setObjectName("Hint")
        self._repolish()

    def ok(self, text):
        self.bar.setVisible(False)
        self.status.setText(text)
        self.status.setObjectName("Ok")
        self._repolish()

    def err(self, text):
        self.bar.setVisible(False)
        self.status.setText(text)
        self.status.setObjectName("Err")
        self._repolish()

    def _repolish(self):
        self.status.style().unpolish(self.status)
        self.status.style().polish(self.status)


def open_path(path):
    """打开文件 / 目录（Windows：资源管理器或默认程序）。"""
    if not path:
        return False
    if os.path.isdir(path):
        if sys.platform.startswith("win"):
            os.startfile(path)                       # noqa: S606
        else:
            subprocess.Popen(["xdg-open", path])
        return True
    if os.path.exists(path):
        QDesktopServices.openUrl(QUrl.fromLocalFile(path))
        return True
    return False
