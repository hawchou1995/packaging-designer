# -*- coding: utf-8 -*-
"""包装设计器 Packaging Designer — 应用入口。

运行：python app.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))            # packapp/
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "ui"))

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (QApplication, QButtonGroup, QHBoxLayout, QLabel, QMainWindow,
                               QPushButton, QStackedWidget, QVBoxLayout, QWidget)

import theme
from dialogs import APP_NAME, SettingsDialog
from pages import BlockPage, BoxPage, GridPage, SheetPage
from settings import Settings

NAV = [("片材", "薄板 · 三视图 + 数模"),
       ("仿形垫块", "开槽垫块 · 边距自动"),
       ("网格刀卡", "V1 / V2 排布 · 收容数"),
       ("瓦楞纸箱", "0201 / 0310 / 0312")]


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = Settings()
        self.setWindowTitle(f"{APP_NAME} 1.0")
        ic = theme.icon_path("app.ico")
        if os.path.exists(ic):
            self.setWindowIcon(QIcon(ic))
        self.setMinimumSize(1080, 720)
        self.resize(1180, 780)

        central = QWidget()
        h = QHBoxLayout(central)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(0)

        # ------- 左导航 -------
        rail = QWidget()
        rail.setObjectName("Rail")
        rail.setFixedWidth(196)
        rv = QVBoxLayout(rail)
        rv.setContentsMargins(12, 20, 12, 10)
        rv.setSpacing(4)
        title = QLabel("包装设计器")
        title.setObjectName("RailTitle")
        title.setFixedHeight(30)
        sub = QLabel("Packaging Designer")
        sub.setObjectName("RailSub")
        sub.setFixedHeight(18)
        rv.addWidget(title)
        rv.addWidget(sub)
        rv.addSpacing(14)
        self.group = QButtonGroup(self)
        self.group.setExclusive(True)
        for i, (name, desc) in enumerate(NAV):
            b = QPushButton(f"{name}\n{desc}")
            b.setObjectName("NavItem")
            b.setCheckable(True)
            b.setCursor(Qt.PointingHandCursor)
            self.group.addButton(b, i)
            rv.addWidget(b)
        self.group.button(0).setChecked(True)
        self.group.idClicked.connect(self.on_nav)
        rv.addStretch(1)
        # 左下角应用图标 → 设置 / 关于
        foot = QWidget()
        fh = QHBoxLayout(foot)
        fh.setContentsMargins(0, 0, 0, 0)
        fh.setSpacing(8)
        self.icon_btn = QPushButton()
        self.icon_btn.setObjectName("AppIconBtn")
        pm = QPixmap(theme.icon_path("app_32.png"))
        if not pm.isNull():
            self.icon_btn.setIcon(QIcon(pm))
            self.icon_btn.setIconSize(QSize(26, 26))
        self.icon_btn.setFixedSize(40, 36)
        self.icon_btn.setCursor(Qt.PointingHandCursor)
        self.icon_btn.setToolTip("设置 / 关于")
        self.icon_btn.clicked.connect(self.on_settings)
        fl = QLabel("设置 / 关于")
        fl.setObjectName("RailFoot")
        fh.addWidget(self.icon_btn)
        fh.addWidget(fl)
        fh.addStretch(1)
        rv.addWidget(foot)
        h.addWidget(rail)

        # ------- 页面 -------
        self.stack = QStackedWidget()
        self.pages = [SheetPage(self.settings), BlockPage(self.settings),
                      GridPage(self.settings), BoxPage(self.settings)]
        for p in self.pages:
            self.stack.addWidget(p)
        h.addWidget(self.stack, 1)
        self.setCentralWidget(central)

    def on_nav(self, idx):
        self.stack.setCurrentIndex(idx)

    def on_settings(self):
        dlg = SettingsDialog(self.settings, self)
        if dlg.exec():
            for p in self.pages:
                p.out_edit.setText(self.settings.outdir)
                p.prefix_edit.setText(self.settings.prefix)
            self.pages[2].refresh()


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("PackagingDesigner")
    app.setOrganizationName("HawChow")
    app.setStyleSheet(theme.qss())
    ic = theme.icon_path("app.ico")
    if os.path.exists(ic):
        app.setWindowIcon(QIcon(ic))
    if "--selftest" in sys.argv:
        import backend
        out = sys.argv[sys.argv.index("--selftest") + 1] if len(sys.argv) > sys.argv.index("--selftest") + 1 else "selftest"
        os.makedirs(out, exist_ok=True)
        r = backend.run_sheet(400, 300, 15, os.path.join(out, "sheet"), prefix="ST")
        print("sheet", len(r.files), flush=True)
        r = backend.run_block(1000, 100, 100, 50, 70, 50, 40, os.path.join(out, "block"), prefix="ST")
        print("block", len(r.files), flush=True)
        r = backend.run_grid((580, 380, 380), (65, 38, 85), 5.0, os.path.join(out, "grid"),
                             prefix="ST", slot_w=7.0, version=2)
        print("grid", len(r.files), flush=True)
        for bx, fl in (("0201", dict(body="BC")),
                       ("0310", dict(sleeve="ABC", cap_top="ABC", cap_bottom="BC")),
                       ("0312", dict(base="BC", lid="BC"))):
            r = backend.run_box(bx, (400, 300, 200), os.path.join(out, bx), prefix="ST", flutes=fl)
            print(bx, len(r.files), flush=True)
        print("SELFTEST OK", out, flush=True)
        return 0
    if "--shot-dialog" in sys.argv:      # 自检：渲染设置/关于对话框
        import dialogs
        w = MainWindow()
        w.show()
        app.processEvents()
        dlg = dialogs.SettingsDialog(w.settings, w)
        tab = int(sys.argv[sys.argv.index("--shot-dialog") + 1]) if len(sys.argv) > sys.argv.index("--shot-dialog") + 1 else 0
        dlg.findChild(type(dlg.layout().itemAt(0).widget()), None)  # noqa: B018
        dlg.show()
        app.processEvents()
        try:
            tabs = dlg.layout().itemAt(0).widget()
            tabs.setCurrentIndex(tab if tab in (0, 1) else 0)
        except Exception:
            pass
        app.processEvents()
        out = sys.argv[sys.argv.index("--shot-dialog") + 2] if len(sys.argv) > sys.argv.index("--shot-dialog") + 2 else "dialog.png"
        dlg.grab().save(out)
        print("dialog shot:", out, os.path.getsize(out), "bytes")
        return 0
    w = MainWindow()
    if "--shot" in sys.argv:                 # 自检：渲染窗口截图后退出
        w.resize(1180, 780)
        w.show()
        app.processEvents()
        idx = 0
        for a in sys.argv:
            if a.startswith("--page="):
                idx = int(a.split("=")[1])
        w.group.button(idx).setChecked(True)
        w.stack.setCurrentIndex(idx)
        app.processEvents()
        out = sys.argv[sys.argv.index("--shot") + 1] if len(sys.argv) > sys.argv.index("--shot") + 1 else "shot.png"
        w.grab().save(out)
        print("shot:", out, os.path.getsize(out), "bytes")
        return 0
    w.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
