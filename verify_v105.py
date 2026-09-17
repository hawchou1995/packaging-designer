# -*- coding: utf-8 -*-
"""verify_v105.py — 修 P0「FrameDialog 保存后 AttributeError: Accepted」+ 图样栏可填

含**崩溃回归**：直接走页面按钮回调 on_frame_fields（用户就是这样撞到的），
用桩把对话框 exec() 返回 QDialog.DialogCode.Accepted，断言不再抛 AttributeError。
测试设置走临时 INI，绝不写用户注册表。
"""
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
TMPBASE = os.path.join(HERE, "_v105")
shutil.rmtree(TMPBASE, ignore_errors=True)
os.makedirs(TMPBASE, exist_ok=True)
tempfile.tempdir = TMPBASE
os.environ["LOCALAPPDATA"] = TMPBASE

sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "ui"))

from PySide6.QtCore import QSettings as _QS          # noqa: E402
from PySide6.QtWidgets import QApplication           # noqa: E402

import settings as _st                               # noqa: E402

_ISO_INI = os.path.join(TMPBASE, "settings.ini")


def _iso_init(self):
    self.q = _QS(_ISO_INI, _QS.IniFormat)
    for k, v in _st.DEFAULTS.items():
        setattr(self, k, self.q.value(k, v))
    self.open_after = str(self.open_after).lower() in ("true", "1")


_st.Settings.__init__ = _iso_init

import theme                                         # noqa: E402
import app as main_app                               # noqa: E402
import dialogs as dl                                 # noqa: E402
import backend as be                                 # noqa: E402

RES = []


def check(name, ok, detail=""):
    RES.append((name, bool(ok), detail))
    print(f"  {'✓' if ok else '✗'} {name}" + (f" — {detail}" if detail else ""))


def main():
    app = QApplication.instance() or QApplication([])
    app.setStyleSheet(theme.qss())
    win = main_app.MainWindow()

    print("\n=== ① P0 崩溃回归：FrameDialog 保存 ===")
    fd = dl.FrameDialog(win.settings)
    keys = [k for k, _ in dl.FrameDialog.FIELDS]
    check("字段含图样名称/代号/版本/材料",
          all(k in keys for k in ("dwg_name", "dwg_no", "dwg_version", "dwg_material")),
          f"{len(keys)} 个字段")
    fd.edits["dwg_name"].setText("PM150 油冷器 瓦楞网格")
    fd.edits["dwg_no"].setText("SNP210-260320")
    fd.edits["dwg_version"].setText("B")
    fd.edits["dwg_material"].setText("AAA 围框 + ABC 两盖")
    try:
        fd.on_save()                       # 旧版这里之后 d.Accepted 取不到 → AttributeError
        ok_save = True
        err = ""
    except Exception as e:
        ok_save, err = False, repr(e)
    check("保存不再抛异常", ok_save, err)
    s = win.settings
    check("四个图样值已入库",
          (s.dwg_name, s.dwg_no, s.dwg_version, s.dwg_material) ==
          ("PM150 油冷器 瓦楞网格", "SNP210-260320", "B", "AAA 围框 + ABC 两盖"))

    print("\n=== ② 页面回调（用户点「图框字段…」的真实路径）===")
    pg = win.pages[0]
    hits = {}
    orig = dl.FrameDialog

    class Stub(orig):
        def exec(self):
            return dl.QDialog.DialogCode.Accepted

    dl.FrameDialog = Stub
    try:
        pg.on_frame_fields()
        check("on_frame_fields 走通（不再报 Accepted）", True)
    except Exception as e:
        check("on_frame_fields 走通（不再报 Accepted）", False, repr(e))
    finally:
        dl.FrameDialog = orig
    check("回调后状态栏提示重新生成", "重新" in pg.busy.status.text() or "图框字段" in pg.busy.status.text(),
          pg.busy.status.text()[:40])
    hits["placeholder"] = dl.FrameDialog.PLACEHOLDER.get("dwg_name", "")
    check("图样名称有占位提示（默认=自动）", "自动" in hits["placeholder"], hits["placeholder"])

    print("\n=== ③ 出图端：留空=自动 / 填了=按填的 ===")
    from core import dwgframe                                        # noqa: F401
    import importlib.util

    def load(n, p):
        sp = importlib.util.spec_from_file_location(n, p)
        m = importlib.util.module_from_spec(sp)
        sp.loader.exec_module(m)
        return m

    sc = load("sc", os.path.join(HERE, "core", "sheet_core.py"))
    sd = load("sd", os.path.join(HERE, "core", "sheet_draw.py"))
    blank = be.frame_meta({})
    check("frame_meta 留空时四键为空", blank["dwg_name"] == "" and blank["dwg_no"] == "")
    f1 = sd.build_sheet(sc.Params(L=400, W=300, H=15), meta=blank)
    t1 = [x.get_text() for x in [a for a in f1.get_axes() if a.get_zorder() >= 50][0].texts]
    check("留空 → 图框写自动值", t1[t1.index("图样代号") + 1].startswith("SHEET-"),
          t1[t1.index("图样代号") + 1])
    f2 = sd.build_sheet(sc.Params(L=400, W=300, H=15), meta=be.frame_meta(s.frame()))
    t2 = [x.get_text() for x in [a for a in f2.get_axes() if a.get_zorder() >= 50][0].texts]
    check("填了 → 图框用填的值",
          t2[t2.index("图样名称") + 1] == "PM150 油冷器 瓦楞网格"
          and t2[t2.index("版本") + 1] == "B",
          f"{t2[t2.index('图样名称') + 1]} / {t2[t2.index('版本') + 1]}")

    print("\n=== 结果 ===")
    bad = [r for r in RES if not r[1]]
    print(f"{len(RES) - len(bad)}/{len(RES)} 通过")
    for n, _, d in bad:
        print("  失败:", n, d)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
