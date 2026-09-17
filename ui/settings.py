# -*- coding: utf-8 -*-
"""settings.py — 应用设置（QSettings 持久化，落在用户配置目录，免管理员权限）。"""
import os

from PySide6.QtCore import QSettings

ORG = "HawChow"
APP = "PackagingDesigner"

DEFAULTS = dict(
    outdir=os.path.join(os.path.expanduser("~"), "Documents", "Packaging"),
    prefix="",
    company="上海银轮热交换系统有限公司",
    designed="", drawn="", checked="", approved="",
    open_after=True,
)


class Settings:
    def __init__(self):
        self.q = QSettings(ORG, APP)
        self.outdir = str(self.q.value("outdir", DEFAULTS["outdir"]))
        self.prefix = str(self.q.value("prefix", DEFAULTS["prefix"]))
        self.company = str(self.q.value("company", DEFAULTS["company"]))
        self.designed = str(self.q.value("designed", DEFAULTS["designed"]))
        self.drawn = str(self.q.value("drawn", DEFAULTS["drawn"]))
        self.checked = str(self.q.value("checked", DEFAULTS["checked"]))
        self.approved = str(self.q.value("approved", DEFAULTS["approved"]))
        self.open_after = str(self.q.value("open_after", DEFAULTS["open_after"])).lower() in ("true", "1")

    def save(self):
        self.q.setValue("outdir", self.outdir)
        self.q.setValue("prefix", self.prefix)
        self.q.setValue("company", self.company)
        self.q.setValue("designed", self.designed)
        self.q.setValue("drawn", self.drawn)
        self.q.setValue("checked", self.checked)
        self.q.setValue("approved", self.approved)
        self.q.setValue("open_after", self.open_after)
        self.q.sync()

    def frame(self):
        """传给 backend 的图框字段。"""
        return dict(company=self.company, designed=self.designed, drawn=self.drawn,
                    checked=self.checked, approved=self.approved)
