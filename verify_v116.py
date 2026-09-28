# -*- coding: utf-8 -*-
"""verify_v116.py — 0312「底箱楞型与天盖楞型可随意搭配」（v1.0.16）

根因：_validate 拿底箱与天盖**两个楞型**去卡同一批工艺参数，而 0312 的接舌（粘舌）与
摇盖加放/折减/开槽**全在底箱上**（天盖是墙条全高 + 四角角片包角粘合，没有接舌）→
「底箱 BC + 天盖 C」必被 BC 的 45–50 拦、「底箱 C + 天盖 AAA」必被 C 的 35–40 拦。
现按**参数归属**（PARAM_OWNER：0312→底箱）取默认值/标准区间/校验，界面提示写明归属部件。
测试设置走临时 INI，绝不写用户注册表。
"""
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
TMPBASE = os.path.join(HERE, "_v116")
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
from box0312_core import Params, check, panels       # noqa: E402

OK = []


def ck(name, cond, detail=""):
    OK.append(bool(cond))
    print(f"  {'OK ' if cond else 'X  '} {name}" + (f" — {detail}" if detail else ""))
    return bool(cond)


def plan(fl, params=None, dims=(1140.0, 740.0, 670.0), price=None):
    try:
        return backend.box_plan("0312", dims, flutes=fl, params=params or {}, price=price), None
    except Exception as e:                            # noqa: BLE001
        return None, f"{type(e).__name__}: {e}"


print("=== ① 用户截图组合（底箱 BC 双瓦 + 天盖 C 单瓦，1140×740×670）===")
r, err = plan(dict(base="BC", lid="C"))
ck("可算（原来报 glue_w = 35 超出 45–50）", r is not None, err or "")
ck("接舌宽默认按底箱 = 45（双瓦下限）", r is not None and abs(r["p"].glue_w - 45.0) < 1e-9,
   f"{r['p'].glue_w:g}" if r else "")
ck("摇盖加放默认按底箱 = 3.0（若按天盖单瓦会是 1.0）",
   r is not None and abs(r["p"].flap_gain - 3.0) < 1e-9,
   f"{r['p'].flap_gain:g}" if r else "")
ck("天盖粘舌按其自身楞型 = 35（单瓦），不借底箱的 45",
   r is not None and abs(r["p"].lgw - 35.0) < 1e-9, f"{r['p'].lgw:g}" if r else "")
ck("尺寸链自检无错", r is not None and not check(r["p"]), "")

print("\n=== ② 反向组合（底箱 C 单瓦 + 天盖 AAA 三瓦）===")
r2, err2 = plan(dict(base="C", lid="AAA"))
ck("可算（原来报 glue_w = 50 超出 35–40）", r2 is not None, err2 or "")
ck("接舌宽默认按底箱 = 35（单瓦下限）", r2 is not None and abs(r2["p"].glue_w - 35.0) < 1e-9,
   f"{r2['p'].glue_w:g}" if r2 else "")
ck("天盖粘舌按其自身楞型 = 50（三瓦）", r2 is not None and abs(r2["p"].lgw - 50.0) < 1e-9,
   f"{r2['p'].lgw:g}" if r2 else "")

print("\n=== ③ 真越界仍然拦（校验没被放宽）===")
_, e3 = plan(dict(base="BC", lid="C"), dict(glue_w=40.0))
ck("底箱 BC + 接舌 40 → 拦下", e3 is not None, e3 or "")
ck("报错点名底箱双瓦、区间 45–50", ("45–50" in (e3 or "")) and ("双瓦" in (e3 or "")), e3 or "")
_, e4 = plan(dict(base="C", lid="AAA"), dict(glue_w=55.0))
ck("底箱 C + 接舌 55 → 拦下并点名单瓦 35–40",
   e4 is not None and "35–40" in e4 and "单瓦" in e4, e4 or "")
_, e5 = plan(dict(base="BC", lid="C"), dict(gap=5.0))
ck("间隙仍按 1–3 校验", e5 is not None and "间隙" in e5, e5 or "")
_, e6 = plan(dict(base="BC", lid="C"), dict(slot_w=20.0))
ck("开槽宽仍按底箱楞型校验（双瓦 8–12）", e6 is not None and "8–12" in e6, e6 or "")

print("\n=== ④ 三维闭合外廓（混板厚：天盖 t=4 / 底箱 t=7）===")


def bbox(ps):
    xs, ys, zs = [], [], []
    for it in ps:
        (x, y, z) = it["size"]
        (cx, cy, cz) = it["center"]
        xs += [cx - x / 2, cx + x / 2]
        ys += [cy - y / 2, cy + y / 2]
        zs += [cz - z / 2, cz + z / 2]
    return (round(max(xs) - min(xs), 3), round(max(ys) - min(ys), 3), round(max(zs) - min(zs), 3))


for tag, pp in (("底箱双瓦 t=7 / 天盖单瓦 t=4", Params(L=1140, W=740, H=670, t=4, t_base=7, cover_depth=300)),
                ("底箱单瓦 t=4 / 天盖三瓦 t=15", Params(L=900, W=600, H=500, t=15, t_base=4, cover_depth=250)),
                ("同楞型（旧口径不回归）", Params(L=400, W=300, H=200))):
    ck(f"闭合外廓 = (L, W, H) · {tag}", bbox(panels(pp)) == (pp.L, pp.W, pp.H), str(bbox(panels(pp))))

print("\n=== ⑤ 报价按各自楞型取价 ===")
MIXED, err7 = plan(dict(base="BC", lid="C"), price=dict(labor=0.0, qty=10.0))
SAME, _ = plan(dict(base="BC", lid="BC"), price=dict(labor=0.0, qty=10.0))
ck("混搭报价可算且每套价 > 0", MIXED is not None and MIXED["quote"]["per_set"] > 0,
   f"{MIXED['quote']['per_set']:.2f}" if MIXED and MIXED.get("quote") else (err7 or ""))
ck("材料描述写明底箱/天盖各自的楞型",
   MIXED is not None and "底箱" in MIXED["desc"] and "天盖" in MIXED["desc"]
   and "BC" in MIXED["desc"] and "C" in MIXED["desc"], (MIXED["desc"] if MIXED else ""))
ck("混搭报价 ≠ 同楞型报价（按各自料价分开算）",
   MIXED is not None and SAME is not None
   and abs(MIXED["quote"]["paper"] - SAME["quote"]["paper"]) > 1e-6,
   f"混搭 ¥{MIXED['quote']['paper']:.2f} vs 同楞型 ¥{SAME['quote']['paper']:.2f}"
   if MIXED and SAME else "")

print("\n=== ⑥ 界面（离屏）：混搭可生成 + 提示写明按底箱楞型 ===")
app = QApplication([])                               # noqa: F841
pg = pages.BoxPage(_st.Settings())
pg.f_box.seg.set_value("0312")
pg.on_box_changed()
pg.f_L.widget.setValue(1140.0)
pg.f_W.widget.setValue(740.0)
pg.f_H.widget.setValue(670.0)
pg.flute_rows["base"].flute.set_value("BC")
pg.on_flute_changed()
pg.flute_rows["lid"].flute.set_value("C")
pg.refresh()
ck("界面上「底箱 BC + 天盖 C」不再报错、可生成", pg.btn_gen.isEnabled(),
   pg.busy.status.text()[:70])
ck("接舌宽区间下限 = 45（底箱双瓦）", abs(pg.p_rows["glue_w"].widget.minimum() - 45.0) < 1e-9,
   f"{pg.p_rows['glue_w'].widget.minimum():g}")
hint = pg.p_rows["glue_w"].hint.text() if pg.p_rows["glue_w"].hint else ""
ck("接舌宽提示写明「按底箱楞型」", "按底箱楞型" in hint, hint[:70])
ck("摇盖加放提示也写明按底箱楞型",
   "按底箱楞型" in (pg.p_rows["flap_gain"].hint.text() if pg.p_rows["flap_gain"].hint else ""),
   (pg.p_rows["flap_gain"].hint.text() if pg.p_rows["flap_gain"].hint else "")[:60])
rows = [(pg.table.item(i, 0).text() if pg.table.item(i, 0) else "",
         pg.table.item(i, 1).text() if pg.table.item(i, 1) else "") for i in range(pg.table.rowCount())]
ck("摘要含「粘舌 底箱/天盖」行", any("粘舌" in k for k, _ in rows),
   str([r for r in rows if "粘舌" in r[0]])[:70])
pg.flute_rows["base"].flute.set_value("C")
pg.on_flute_changed()
ck("切回底箱单瓦：区间下限 = 35", abs(pg.p_rows["glue_w"].widget.minimum() - 35.0) < 1e-9,
   f"{pg.p_rows['glue_w'].widget.minimum():g}")
ck("切回后仍可生成", pg.btn_gen.isEnabled(), pg.busy.status.text()[:60])

print("\n=== ⑦ 爆炸图（0310/0312：可见间隙 + 互不穿插 + 明显分离）===")
from box0310_core import panels as _p310, explode_items as _ex310, Params as _P310   # noqa: E402
from box0312_core import panels as _p312, explode_items as _ex312, Params as _P312   # noqa: E402


def _zr(items, group):
    zs = []
    for it in items:
        if it.get("group") == group:
            z, cz = it["size"][2], it["center"][2]
            zs += [cz - z / 2, cz + z / 2]
    return (min(zs), max(zs))


def _h(items):
    zs = []
    for it in items:
        z, cz = it["size"][2], it["center"][2]
        zs += [cz - z / 2, cz + z / 2]
    return max(zs) - min(zs)


print("  0310：")
for tag, kw in (("一半口径 400×300×200", dict(L=400, W=300, H=200)),
                ("固定盖高 100 · 400×300×400",
                 dict(L=400, W=300, H=400, t=7, t_sleeve=7, t_cap_bot=7,
                      cap_h_mode="fixed", cap_h=100.0)),
                ("大箱 1600×1200×900", dict(L=1600, W=1200, H=900, t=7, t_sleeve=7, t_cap_bot=7,
                                          cap_h_mode="fixed", cap_h=100.0))):
    p310 = _P310(**kw)
    ic310, io310 = _p310(p310), _ex310(_p310(p310), p310)
    g = min(max(p310.d_cover, 0.25 * p310.sleeve_H), 0.60 * p310.sleeve_H)
    s0, s1 = _zr(io310, "static")
    b0, b1 = _zr(io310, "cap_bot")
    t0, t1 = _zr(io310, "cap_top")
    gap_b, gap_t = s0 - b1, t0 - s1
    ratio = _h(io310) / _h(ic310)
    ck(f"下盖不穿插围框、留出间隙 · {tag}", gap_b > 0 and gap_b >= 0.9 * g,
       f"间隙 {gap_b:.0f} ≥ {0.9 * g:.0f}（目标 {g:.0f}）")
    ck(f"上盖不穿插围框、留出间隙 · {tag}", gap_t > 0 and gap_t >= 0.9 * g,
       f"间隙 {gap_t:.0f} ≥ {0.9 * g:.0f}（目标 {g:.0f}）")
    ck(f"爆炸态明显拉开（包围盒 ≥ 闭合 ×1.5）· {tag}", ratio >= 1.5, f"×{ratio:.2f}")

print("  0312：")
for tag, kw in (("默认 400×300×200", dict(L=400, W=300, H=200)),
                ("混板厚 1140×740×670（底箱 t=7 / 天盖 t=4）",
                 dict(L=1140, W=740, H=670, t=4, t_base=7, cover_depth=300.0))):
    p312 = _P312(**kw)
    ic312, io312 = _p312(p312), _ex312(_p312(p312), p312)
    g = min(max(p312.cover_depth, 0.25 * p312.H), 0.60 * p312.H)
    b0, b1 = _zr(io312, "static")
    l0, l1 = _zr(io312, "lid")
    gap = l0 - b1
    ratio = _h(io312) / _h(ic312)
    ck(f"天盖不穿插底箱、留出间隙 · {tag}", gap > 0 and gap >= 0.9 * g,
       f"间隙 {gap:.0f} ≥ {0.9 * g:.0f}（目标 {g:.0f}）")
    ck(f"爆炸态明显拉开（包围盒 ≥ 闭合 ×1.5）· {tag}", ratio >= 1.5, f"×{ratio:.2f}")

print("\n=== 结果 ===")
good = sum(1 for x in OK if x)
print(f"{good}/{len(OK)} 通过")
sys.exit(0 if good == len(OK) else 1)