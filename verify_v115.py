# -*- coding: utf-8 -*-
"""verify_v115.py — 修 0310 两处现场问题（v1.0.15）

① 围框与两盖**混搭楞型**不再报「接骨宽超出标准区间」：接舌只在围框上（两盖是无接舌的
   角片盘），所以接舌宽的默认值/标准区间/校验都按**围框楞型**取；顺带修掉尺寸链里
   写死「上盖必须最厚」的等式（改为 围框外 + 2×间隙 + 2×较厚盖厚 = 盖外，并对每只盖做
   「围框套得进盖内腔」的检查）。
② 盖高新增「固定高度」口径：默认 100、可调；「整体一半」仍可选；两盖高度之和超过
   围框高时必须给出**可行动的报错**，不得静默改用户的盖高。
测试设置走临时 INI，绝不写用户注册表。
"""
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
TMPBASE = os.path.join(HERE, "_v115")
shutil.rmtree(TMPBASE, ignore_errors=True)
os.makedirs(TMPBASE, exist_ok=True)
tempfile.tempdir = TMPBASE
os.environ["LOCALAPPDATA"] = TMPBASE
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "ui"))

import matplotlib                                    # noqa: E402
matplotlib.use("Agg")

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

import backend                                       # noqa: E402
import pages                                         # noqa: E402
from box0310_core import Params, report              # noqa: E402

OK = []


def check(name, cond, detail=""):
    OK.append(bool(cond))
    print(f"  {'OK ' if cond else '✗  '} {name}" + (f" — {detail}" if detail else ""))
    return bool(cond)


def plan(flutes, params, dims=(400, 300, 400), mode="outer"):
    try:
        return backend.box_plan("0310", dims, mode=mode, flutes=flutes, params=params), None
    except Exception as e:                            # noqa: BLE001
        return None, f"{type(e).__name__}: {e}"


MIX = dict(sleeve="BC", cap_top="B", cap_bottom="C")   # 现场组合：围框双瓦 + 两盖单瓦

print("=== ① 混搭楞型的接舌宽（现场报错：glue_w = 35 超出标准区间 45–50）===")
r, err = plan(MIX, dict(cap_h_mode="fixed", cap_h=100.0))
check("围框 BC + 上盖 B / 下盖 C：可算", r is not None, err or "")
check("接舌宽取围框档 45（双瓦）", r is not None and abs(r["p"].glue_w - 45.0) < 1e-9,
      f"{r['p'].glue_w:g}" if r else "")
r2, err2 = plan(dict(sleeve="B", cap_top="BC", cap_bottom="BC"), dict(cap_h_mode="half"))
check("反向混搭（围框单瓦 + 两盖双瓦）：可算", r2 is not None, err2 or "")
check("接舌宽取围框档 35（单瓦）", r2 is not None and abs(r2["p"].glue_w - 35.0) < 1e-9,
      f"{r2['p'].glue_w:g}" if r2 else "")
r3, err3 = plan(MIX, dict(cap_h_mode="half", glue_w=40.0))     # 40 属单瓦档 → 围框双瓦应判越界
check("接舌宽真越界仍然报错（没把校验删掉）",
      r3 is None and "glue_w" in (err3 or "") and "45" in (err3 or ""), err3 or "")
check("报错点名围框楞型", "A版 双瓦" in (err3 or ""), err3 or "")
r4, err4 = plan(MIX, dict(cap_h_mode="fixed", cap_h=100.0, gap=5.0))
check("混搭时间隙仍按 0310 区间（1–3）校验", r4 is None and "间隙" in (err4 or ""), err4 or "")

print("\n=== ② 盖高两口径 ===")
HALF, errH = plan(dict(sleeve="BC", cap_top="BC", cap_bottom="BC"), dict(cap_h_mode="half"))
check("整体一半：罩深 = 围框高/2（旧口径不回归）",
      HALF is not None and abs(HALF["p"].d_cover - HALF["p"].sleeve_H / 2) < 1e-9,
      f"{HALF['p'].d_cover:g}" if HALF else errH)
FIX, errF = plan(dict(sleeve="BC", cap_top="BC", cap_bottom="BC"),
                 dict(cap_h_mode="fixed", cap_h=100.0))
check("固定 100：罩深 = 100、墙板宽 = 100 + t盖/2",
      FIX is not None and abs(FIX["p"].d_cover - 100.0) < 1e-9
      and abs(FIX["p"].wall_blank - (100.0 + FIX["p"].tc / 2)) < 1e-9,
      f"{FIX['p'].d_cover:g} / {FIX['p'].wall_blank:g}" if FIX else errF)
BAD, errB = plan(dict(sleeve="BC", cap_top="BC", cap_bottom="BC"),
                 dict(cap_h_mode="fixed", cap_h=100.0), dims=(400, 300, 200))
check("盖高之和超过围框高：报错", BAD is None, "")
check("报错可行动（上限 / 建议外高 / 可改选一半）",
      all(k in (errB or "") for k in ("大于围框高", "盖高改 ≤", "整体外高 ≥", "整体一半")), errB or "")
EDGE, errE = plan(dict(sleeve="BC", cap_top="BC", cap_bottom="BC"),
                  dict(cap_h_mode="fixed", cap_h=100.0), dims=(400, 300, 214))
check("边界 H = 2×100 + t上 + t下：恰好对接，可算",
      EDGE is not None and abs(2 * EDGE["p"].d_cover - EDGE["p"].sleeve_H) < 1e-9, errE or "")
INN, errI = plan(dict(sleeve="BC", cap_top="BC", cap_bottom="BC"),
                 dict(cap_h_mode="fixed", cap_h=100.0), dims=(380, 280, 400), mode="inner")
check("内尺寸口径下固定 100 同样可用",
      INN is not None and abs(INN["p"].d_cover - 100.0) < 1e-9
      and abs(INN["p"].H - (400 + 2 * INN["p"].tcmax)) < 1e-9, errI or "")
check("固定 100 的用纸量小于整体一半（罩深变小）",
      FIX is not None and HALF is not None and FIX["p"].d_cover < HALF["p"].d_cover, "")
rows = dict(report(Params(cap_h_mode="fixed", cap_h=100.0))[1])
check("参数表出现「盖高口径 = 固定 100（每盖）」", rows.get("盖高口径") == "固定 100（每盖）",
      str(rows.get("盖高口径")))
rows2 = dict(report(Params(cap_h_mode="half"))[1])
check("一半口径在参数表里标注围框高/2",
      str(rows2.get("盖高口径", "")).startswith("整体一半"), str(rows2.get("盖高口径")))

print("\n=== ③ 界面（离屏）===")
app = QApplication([])                               # noqa: F841
win = pages.BoxPage(_st.Settings())
win.f_box.seg.set_value("0310")
win.on_box_changed()
check("0310 默认盖高口径 = 固定高度", win.f_cap_mode.seg.value() == "fixed", win.f_cap_mode.seg.value())
check("0310 默认盖高 = 100", abs(win.f_cap_h.widget.value() - 100.0) < 1e-9,
      f"{win.f_cap_h.widget.value():g}")
win.f_L.widget.setValue(400.0)
win.f_W.widget.setValue(300.0)
win.f_H.widget.setValue(400.0)
win.f_link.widget.setChecked(False)
win.on_flute_changed()
win.flute_rows["sleeve"].flute.set_value("BC")
win.flute_rows["cap_top"].flute.set_value("B")
win.on_flute_changed()
win.flute_rows["cap_bottom"].flute.set_value("C")
win.refresh()
check("界面上混搭楞型不再报错、可生成", win.btn_gen.isEnabled(), win.busy.status.text()[:64])
check("接舌宽区间下限按围框档 = 45（双瓦）",
      abs(win.p_rows["glue_w"].widget.minimum() - 45.0) < 1e-9,
      f"{win.p_rows['glue_w'].widget.minimum():g}")
hint = win.p_rows["glue_w"].hint.text() if win.p_rows["glue_w"].hint else ""
check("接舌宽行提示写明「按围框楞型」", "按围框楞型" in hint, hint[:70])
win.f_cap_mode.seg.set_value("half")
win.on_cap_mode()
check("切「整体一半」：盖高输入框隐藏，仍可生成",
      win.f_cap_h.isHidden() and win.btn_gen.isEnabled(), "")
win.f_cap_mode.seg.set_value("fixed")
win.on_cap_mode()
win.f_H.widget.setValue(200.0)
win._touched()
check("H 太矮：界面拦下并给出可行动的报错",
      (not win.btn_gen.isEnabled()) and "盖高改 ≤" in win.busy.status.text(),
      win.busy.status.text()[:80])
hint2 = win.f_cap_h.hint.text() if win.f_cap_h.hint else ""
check("盖高提示同步为超限告警", ("上限" in hint2) and ("100 >" in hint2), hint2[:70])
win.f_H.widget.setValue(400.0)
win._touched()
check("抬高整体高后恢复可生成", win.btn_gen.isEnabled(), win.busy.status.text()[:60])

print("\n=== ④ 三维闭合外廓（上下盖板厚不同时曾顶穿 3D 包围盒）===")
from box0310_core import panels as _panels


def _bbox(ps):
    xs, ys, zs = [], [], []
    for it in ps:
        (x, y, z) = it["size"]
        (cx, cy, cz) = it["center"]
        xs += [cx - x / 2, cx + x / 2]
        ys += [cy - y / 2, cy + y / 2]
        zs += [cz - z / 2, cz + z / 2]
    return (round(max(xs) - min(xs), 3), round(max(ys) - min(ys), 3), round(max(zs) - min(zs), 3))


for tag, pp in (("上盖薄 / 下盖厚（B+C 混搭）",
                 Params(H=400, t=3, t_sleeve=7, t_cap_bot=4, cap_h_mode="fixed", cap_h=100.0)),
                ("上盖厚 / 下盖薄（C+B 混搭）",
                 Params(H=400, t=4, t_sleeve=7, t_cap_bot=3, cap_h_mode="fixed", cap_h=100.0)),
                ("整体一半口径", Params(H=400, t=3, t_sleeve=7, t_cap_bot=4, cap_h_mode="half"))):
    bb = _bbox(_panels(pp))
    check(f"三维闭合外廓 = (L, W, H) · {tag}", bb == (400.0, 300.0, 400.0), str(bb))

print("\n=== 结果 ===")
good = sum(1 for x in OK if x)
print(f"{good}/{len(OK)} 通过")
sys.exit(0 if good == len(OK) else 1)