# -*- coding: utf-8 -*-
"""widgets.py — 通用控件：卡片 / 表单行 / 数值框 / 结果表 / 文件面板 / 预览。

表单规范（taste-skill §4.6）：标签在输入之上，提示文字在下方；错误在字段下方内联。
"""
import os
import subprocess
import sys

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QBrush, QColor, QDesktopServices, QFont, QPixmap
from PySide6.QtCore import QUrl
from PySide6.QtWidgets import (QButtonGroup, QCheckBox, QComboBox, QDoubleSpinBox, QFrame, QGridLayout,
                               QHBoxLayout, QHeaderView, QLabel, QLineEdit, QListWidget, QListWidgetItem, QProgressBar,
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
              suffix="", width=None, on_change=None):
    sp = QDoubleSpinBox()
    sp.setRange(lo, hi)
    sp.setDecimals(decimals)
    sp.setSingleStep(step)
    sp.setValue(value)
    sp.setSuffix(" " + suffix if suffix else "")
    mono(sp)
    sp.setMinimumWidth(96)
    sp.setButtonSymbols(QDoubleSpinBox.UpDownArrows)
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
        self.lab = QLabel("尚未生成。点「① 生成」出图到临时目录，再点「② 导出」写入你的目录。")
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
        self.bar.setFixedHeight(6)
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


# ================================================================ 表格化表单（v1.0.1）
class Row(QWidget):
    """标签在左、控件在右的一行（紧凑表格化）。"""

    def __init__(self, label, widget, label_w=84, hint=None, parent=None):
        super().__init__(parent)
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(2)
        h = QHBoxLayout()
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(8)
        lab = QLabel(label)
        lab.setObjectName("FieldLabel")
        lab.setFixedWidth(label_w)
        lab.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        h.addWidget(lab)
        h.addWidget(widget, 1)
        v.addLayout(h)
        self.hint = None
        if hint:
            self.hint = QLabel(hint)
            self.hint.setObjectName("FieldHint")
            self.hint.setWordWrap(True)
            self.hint.setContentsMargins(label_w + 8, 0, 0, 0)
            v.addWidget(self.hint)
        self.widget = widget


class RowGrid(QWidget):
    """每行 2 个 Row 的紧凑网格（避免纵向长条滚动）。"""

    def __init__(self, cols=2, parent=None):
        super().__init__(parent)
        self._g = QGridLayout(self)
        self._g.setContentsMargins(0, 0, 0, 0)
        self._g.setHorizontalSpacing(14)
        self._g.setVerticalSpacing(7)
        self._cols = cols
        self._n = 0
        for c in range(cols):
            self._g.setColumnStretch(c, 1)

    def add(self, row, span=False):
        if span:
            if self._n % self._cols:
                self._n += self._cols - (self._n % self._cols)
            self._g.addWidget(row, self._n // self._cols, 0, 1, self._cols)
            self._n += self._cols
        else:
            self._g.addWidget(row, self._n // self._cols, self._n % self._cols)
            self._n += 1
        return row

    def add_wide(self, w):
        if self._n % self._cols:
            self._n += self._cols - (self._n % self._cols)
        self._g.addWidget(w, self._n // self._cols, 0, 1, self._cols)
        self._n += self._cols
        return w

    def next_row(self):
        if self._n % self._cols:
            self._n += self._cols - (self._n % self._cols)


def seg_field(label, options, value=None, on_change=None, label_w=84, compact=False):
    """分段单选（替代下拉）：options = [(value, text)]。"""
    w = QWidget()
    h = QHBoxLayout(w)
    h.setContentsMargins(0, 0, 0, 0)
    h.setSpacing(4)
    grp = QButtonGroup(w)
    grp.setExclusive(True)
    btns = {}
    for i, (val, txt) in enumerate(options):
        b = QPushButton(txt)
        b.setCheckable(True)
        b.setObjectName("Seg")
        b.setCursor(Qt.PointingHandCursor)
        if compact:
            b.setMinimumWidth(0)
        grp.addButton(b, i)
        h.addWidget(b)
        btns[val] = b
        if (value is None and i == 0) or (value is not None and val == value):
            b.setChecked(True)
    h.addStretch(1)
    w.value = lambda: grp.checkedButton().property("segval") if grp.checkedButton() else None
    for val, b in btns.items():
        b.setProperty("segval", val)
    if on_change:
        grp.idClicked.connect(lambda *_: on_change())
    w._grp, w._btns = grp, btns
    w.set_value = lambda v: btns[v].setChecked(True) if v in btns else None
    row = Row(label, w, label_w=label_w)
    row.seg = w
    return row


def flute_field(label, materials, value=None, on_change=None, label_w=84, per_row=5):
    """楞型紧凑按钮组：每个按钮显示「代号 t=厚度」，按 per_row 换行（避免超宽裁切）。"""
    w = QWidget()
    h = QGridLayout(w)
    h.setContentsMargins(0, 0, 0, 0)
    h.setHorizontalSpacing(3)
    h.setVerticalSpacing(3)
    grp = QButtonGroup(w)
    grp.setExclusive(True)
    btns = {}
    for i, (code, t) in enumerate(materials):
        b = QPushButton(f"{code} t={t:g}")
        b.setCheckable(True)
        b.setObjectName("FluteBtn")
        b.setCursor(Qt.PointingHandCursor)
        b.setProperty("fcode", code)
        grp.addButton(b, i)
        h.addWidget(b, i // per_row, i % per_row)
        btns[code] = b
        if (value is None and i == 0) or (value == code):
            b.setChecked(True)
    h.setColumnStretch(per_row, 1)
    for code, b in btns.items():
        b.setProperty("segval", code)
    w.value = lambda: grp.checkedButton().property("segval") if grp.checkedButton() else None
    w.set_value = lambda v: btns[v].setChecked(True) if v in btns else None
    if on_change:
        grp.idClicked.connect(lambda *_: on_change())
    w._grp, w._btns = grp, btns
    row = Row(label, w, label_w=label_w)
    row.flute = w
    return row


class ScaleField(QWidget):
    """比例：自动（默认）/ 手动 1:x。"""

    def __init__(self, on_change=None, parent=None):
        super().__init__(parent)
        h = QHBoxLayout(self)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(6)
        self.chk_auto = QCheckBox("自动")
        self.chk_auto.setChecked(True)
        self.sp = QDoubleSpinBox()
        self.sp.setRange(0.2, 100.0)
        self.sp.setDecimals(1)
        self.sp.setSingleStep(0.5)
        self.sp.setValue(6.0)
        self.sp.setPrefix("1:")
        self.sp.setEnabled(False)
        mono(self.sp)
        self.lab = QLabel("（按图幅自动选档）")
        self.lab.setObjectName("FieldHint")
        h.addWidget(self.chk_auto)
        h.addWidget(self.sp)
        h.addWidget(self.lab)
        h.addStretch(1)
        self.chk_auto.toggled.connect(self._sync)
        if on_change:
            self.chk_auto.toggled.connect(lambda *_: on_change())
            self.sp.valueChanged.connect(lambda *_: on_change())

    def _sync(self):
        auto = self.chk_auto.isChecked()
        self.sp.setEnabled(not auto)
        self.lab.setText("（按图幅自动选档）" if auto else "（手动：画不下时仅提示，不阻断）")

    def value(self):
        return None if self.chk_auto.isChecked() else float(self.sp.value())

    def reset(self):
        self.chk_auto.setChecked(True)


class GroupTable(QTableWidget):
    """分组结果表：标题行（加粗、浅底）+ 键值行。"""

    def __init__(self, parent=None):
        super().__init__(0, 2, parent)
        self.horizontalHeader().setVisible(False)
        self.verticalHeader().setVisible(False)
        self.setShowGrid(False)
        self.setEditTriggers(QTableWidget.NoEditTriggers)
        self.setSelectionMode(QTableWidget.ContiguousSelection)
        self.setFocusPolicy(Qt.ClickFocus)
        self.horizontalHeader().setStretchLastSection(True)
        self.setColumnWidth(0, 196)
        self.setWordWrap(True)
        self.verticalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)

    def set_groups(self, groups):
        n = sum(len(rows) + (1 if title else 0) for title, rows in groups)
        self.setRowCount(n)
        i = 0
        for title, rows in groups:
            if title:
                a = QTableWidgetItem(title)
                a.setForeground(QBrush(QColor(theme.ACCENT)))
                f = a.font()
                f.setBold(True)
                a.setFont(f)
                self.setItem(i, 0, a)
                self.setItem(i, 1, QTableWidgetItem(""))
                i += 1
            for k, v in rows:
                a = QTableWidgetItem(str(k))
                b = QTableWidgetItem(str(v))
                if k.startswith("—"):
                    f = a.font()
                    f.setBold(True)
                    a.setFont(f)
                mono(b, 10)
                b.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.setItem(i, 0, a)
                self.setItem(i, 1, b)
                i += 1
        self.resizeRowsToContents()

    # 兼容旧调用
    def set_rows(self, rows):
        self.set_groups([(None, rows)])
