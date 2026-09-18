# -*- coding: utf-8 -*-
"""geom_run.py - run the cross-axis checker over all sheet cases."""

import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "core"))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


G = load("geom_check", os.path.join(HERE, "geom_check.py"))
gc = load("gc", os.path.join(HERE, "core", "grid_core.py"))
gd = load("gd", os.path.join(HERE, "core", "grid_draw.py"))
sc = load("sc", os.path.join(HERE, "core", "sheet_core.py"))
sd = load("sd", os.path.join(HERE, "core", "sheet_draw.py"))
bc = load("bc", os.path.join(HERE, "core", "block_core.py"))
bd = load("bd", os.path.join(HERE, "core", "block_draw.py"))
c201 = load("c201", os.path.join(HERE, "core", "box0201_core.py"))
s201 = load("s201", os.path.join(HERE, "core", "box0201_sheets.py"))
c310 = load("c310", os.path.join(HERE, "core", "box0310_core.py"))
s310 = load("s310", os.path.join(HERE, "core", "box0310_sheets.py"))
c312 = load("c312", os.path.join(HERE, "core", "box0312_core.py"))
s312 = load("s312", os.path.join(HERE, "core", "box0312_sheets.py"))

CASES = [
    ("片材", lambda: sd.build_sheet(sc.Params(L=400, W=300, H=15))),
    ("片材-小", lambda: sd.build_sheet(sc.Params(L=180, W=120, H=6))),
    ("仿形块", lambda: mk_block(dict(L=1000, W=100, H=100, sl=50, sw=70, sh=50, gap=40))),
    ("仿形块-小", lambda: mk_block(dict(L=300, W=60, H=40, sl=20, sw=30, sh=20, gap=15))),
    ("纸箱0201-400", lambda: s201.build_sheet(c201.Params(L=400, W=300, H=200))),
    ("纸箱0201-小", lambda: s201.build_sheet(c201.Params(L=200, W=150, H=90))),
    ("纸箱0310-400", lambda: s310.build_sheet(c310.Params(L=400, W=300, H=200))),
    ("纸箱0310-大", lambda: s310.build_sheet(c310.Params(L=900, W=650, H=500,
                                                         t=10, t_sleeve=10, t_cap_bot=10))),
    ("纸箱0312-400", lambda: s312.build_sheet(c312.Params(L=400, W=300, H=200))),
    ("纸箱0312-小", lambda: s312.build_sheet(c312.Params(L=250, W=180, H=120))),
    ("纸箱0312-大", lambda: s312.build_sheet(c312.Params(L=1100, W=800, H=620,
                                                         t=10, t_base=10))),
]
TB = (228.0, 12.0, 408.0, 68.0)      # 标题栏（GB/T 10609.1，右下角 180×56）


def mk_grid(args):
    p = gc.Params(**args)
    _e, _r, d = gc.report(p)
    return gd.build_sheet(p, d)


def mk_block(args):
    p = bc.Params(**args)
    _e, _r, d = bc.report(p)
    return bd.build_sheet(p, d)


GRID = [("网格-580", dict(L=580, W=380, H=380, pl=65, pw=38, ph=85, t=5, version=1)),
        ("网格-400折边", dict(L=400, W=300, H=300, pl=32, pw=32, ph=60, t=5, version=1)),
        ("网格-1100", dict(L=1100, W=800, H=700, pl=200, pw=150, ph=200, t=7, version=2)),
        ("网格-双折边V2", dict(L=1140, W=740, H=740, pl=160, pw=120, ph=120, t=6, version=2)),
        ("网格-小", dict(L=240, W=180, H=180, pl=24, pw=18, ph=45, t=5, version=1))]

only = sys.argv[1] if len(sys.argv) > 1 else None

for tag, args in GRID:
    if only and only not in tag:
        continue
    fig = mk_grid(args)
    hits, overlaps = G.check(fig)
    cross = G.dim_crossings(fig)
    print("=== %s ===" % tag)
    print("  压线 %d 处 / 文字重叠 %d 对 / 尺寸线相交 %d 处 / 进标题栏 %d 处"
          % (len(hits), len(overlaps), len(cross), len(G.region_hits(fig, TB))))
    for h in hits[:12]:
        print("    · 「%s」 kind=%s rect=%s" % (h[0][:26], h[3],
                                               tuple(round(v) for v in h[1])))
    for o in overlaps[:8]:
        print("    · 重叠「%s」×「%s」" % (o[0][:22], o[1][:22]))
    for c in cross[:8]:
        print("    · %s seg%s→%s" % (c[0], tuple(round(v) for v in c[1][0]),
                                     tuple(round(v) for v in c[1][1])))
    plt.close(fig)

for tag, mk in CASES:
    if only and only not in tag:
        continue
    try:
        fig = mk()
    except Exception as exc:
        print("=== %s === 跳过：%s" % (tag, exc))
        continue
    hits, overlaps = G.check(fig)
    cross = G.dim_crossings(fig)
    print("=== %s ===" % tag)
    print("  压线 %d 处 / 文字重叠 %d 对 / 尺寸线相交 %d 处 / 进标题栏 %d 处"
          % (len(hits), len(overlaps), len(cross), len(G.region_hits(fig, TB))))
    for h in hits[:12]:
        print("    · 「%s」 kind=%s" % (h[0][:26], h[3]))
    for o in overlaps[:8]:
        print("    · 重叠「%s」×「%s」" % (o[0][:22], o[1][:22]))
    for c in cross[:8]:
        print("    · %s seg%s→%s" % (c[0], tuple(round(v) for v in c[1][0]),
                                     tuple(round(v) for v in c[1][1])))
    plt.close(fig)
