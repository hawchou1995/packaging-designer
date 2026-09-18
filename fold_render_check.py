# -*- coding: utf-8 -*-
"""把 1.0.7 的网格俯视图角部放大导出，供人工核对折边画法（黑=裁切，折弯线=点划线）。"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "core"))
import matplotlib                                  # noqa: E402
matplotlib.use("Agg")
import importlib.util                              # noqa: E402
from PIL import Image                              # noqa: E402


def load(n, p):
    s = importlib.util.spec_from_file_location(n, p)
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


gc = load("gc", os.path.join(HERE, "core", "grid_core.py"))
gd = load("gd", os.path.join(HERE, "core", "grid_draw.py"))

CFG = dict(L=400, W=300, H=300, pl=32, pw=32, ph=60, t=5.0, version=1)
p = gc.Params(**CFG)
_e, _r, d = gc.report(p)
print(f"  算例 {CFG['L']}×{CFG['W']} 格 {CFG['pl']}×{CFG['pw']} t={CFG['t']}"
      f" 边距 {d['margin_l']:.1f}/{d['margin_w']:.1f} 折边 长={d['fold_l']} 短={d['fold_w']}")
os.makedirs(os.path.join(HERE, "_foldview"), exist_ok=True)
fig = gd.build_sheet(p, d)
out = os.path.join(HERE, "_foldview", "v107_full.png")
fig.savefig(out, dpi=300)

im = Image.open(out)
W, H = im.size
px = W / 420.0
s = 1.0 / fig._scale_used
ROW1 = (264.0 - 36.0 * s - 2.0 * 30.0 * s) - 300.0 * s


def P(x, y):
    return (48.0 + x * s) * px, H - (ROW1 + y * s) * px


a = P(-45, -45)
b = P(125, 125)
box = (int(min(a[0], b[0])), int(min(a[1], b[1])),
       int(max(a[0], b[0])), int(max(a[1], b[1])))
crop = im.crop(box)
crop = crop.resize((crop.width * 2, crop.height * 2), Image.LANCZOS)
corner = os.path.join(HERE, "_foldview", "v107_corner.png")
crop.save(corner)
print("  全图:", out)
print("  角部:", corner, crop.size)
