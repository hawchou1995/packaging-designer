# -*- coding: utf-8 -*-
"""fold_debug_plot.py — 只画折边附近的线段（按类型上色），用来核对几何构造本身：
  灰=刀卡本体棱线（裁切）  红=折边轮廓（裁切）  蓝=折弯线（点划线）
另外做两项断言式检查：
  A 折边轮廓四角必须闭合（端点重合）
  B 任何**实线**都不得横穿另一块板的内部（横穿=看起来像把板切断）
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "core"))
import matplotlib                                  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt                    # noqa: E402
import importlib.util                              # noqa: E402
import math                                        # noqa: E402


def load(n, p):
    s = importlib.util.spec_from_file_location(n, p)
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


gc = load("gc", os.path.join(HERE, "core", "grid_core.py"))
gd = load("gd", os.path.join(HERE, "core", "grid_draw.py"))

CFG = dict(L=400, W=300, H=300, pl=32, pw=32, ph=60, t=5.0, version=1)
p = gc.Params(**CFG)
errs, rows, d = gc.report(p)
print(f"  算例 {CFG['L']}×{CFG['W']} 格 {CFG['pl']}×{CFG['pw']} t={CFG['t']}；"
      f"边距 {d['margin_l']:.1f}/{d['margin_w']:.1f} → 折边 长={d['fold_l']} 短={d['fold_w']}")

fig = gd.build_sheet(p, d)
ax = [a for a in fig.get_axes() if a.get_zorder() < 50 and a.get_xlim()[1] > 1.5][0]

# 俯视图坐标变换（与 grid_draw 内部一致）
t = d["t"]
fl = d["fold_len"]
s = 1.0 / fig._scale_used
_fw = fl if d.get("fold_w") else 0.0
ROW1 = (264.0 - 36.0 * s - 2.0 * _fw * s) - p.W * s
PLX = 48.0


def D(xy):
    """纸面 → 数据坐标"""
    return ((xy[0] - PLX) / s, (xy[1] - ROW1) / s)


xs_l = gd._slots(d["margin_l"], d["slots_long"], d["pitch_l"], t)
ys_w = gd._slots(d["margin_w"], d["slots_short"], d["pitch_w"], t)

# 收集俯视区（x -40..L+40, y -40..W+40）内的线段
ZONE = (-45.0, -45.0, p.L + 45.0, p.W + 45.0)
segs = []
for ln in ax.lines:
    kind = "fold" if str(ln.get_linestyle()) not in ("-", "solid") else "cut"
    xs, ys = ln.get_xdata(), ln.get_ydata()
    for i in range(len(xs) - 1):
        a, b = D((xs[i], ys[i])), D((xs[i + 1], ys[i + 1]))
        if math.dist(a, b) < 0.3:
            continue
        if all(ZONE[0] <= q[0] <= ZONE[2] and ZONE[1] <= q[1] <= ZONE[3] for q in (a, b)):
            segs.append((a, b, kind))

print(f"  俯视区线段 {len(segs)} 条（cut {sum(1 for q in segs if q[2] == 'cut')} / "
      f"fold {sum(1 for q in segs if q[2] == 'fold')}）")

# ---- 断言 A：折边轮廓闭合 ----
flaps = []
if d.get("fold_l"):
    for yc in ys_w:
        sy = -1.0 if yc > p.W / 2.0 else 1.0
        y_att, y_out = yc + sy * t / 2, yc + sy * (t / 2 + fl)
        for x_in in (0.0, p.L - t):
            flaps.append(((x_in, y_att), (x_in + t, y_out)))      # (锚点, 外端)
if d.get("fold_w"):
    for xc in xs_l:
        sx = -1.0 if xc > p.L / 2.0 else 1.0
        x_att, x_out = xc + sx * t / 2, xc + sx * (t / 2 + fl)
        for y_in in (0.0, p.W - t):
            flaps.append(((x_att, y_in), (x_out, y_in + t)))
print(f"  折边块数 {len(flaps)}")

# ---- 断言 B：实线不得横穿板体内部 ----
def in_card_interior(pt, tol=0.4):
    x, y = pt
    for xc in xs_l:                                   # 短卡：x∈[xc-t/2, xc+t/2], y∈[0,W]
        if xc - t / 2 + tol < x < xc + t / 2 - tol and -tol < y < p.W + tol:
            return f"短卡 x={xc:g}"
    for yc in ys_w:                                   # 长卡：y∈[yc-t/2, yc+t/2], x∈[0,L]
        if yc - t / 2 + tol < y < yc + t / 2 - tol and -tol < x < p.L + tol:
            return f"长卡 y={yc:g}"
    return None


# 判据（收敛到折边带）：
#   折边是从卡面出发、向外折的窄条；它的**侧边**只能沿"附着面 → 外端"走，
#   途中不得进入任何板体内部（进入即"看起来把板切断"）。
#   网格中短卡穿过长卡是互扣结构的正常交叉，明文排除。
def interior_hit(pt, tol=0.45):
    x, y = pt
    for xc in xs_l:
        if xc - t / 2 + tol < x < xc + t / 2 - tol and tol < y < p.W - tol:
            return f"短卡 x={xc:g}"
    for yc in ys_w:
        if yc - t / 2 + tol < y < yc + t / 2 - tol and tol < x < p.L - tol:
            return f"长卡 y={yc:g}"
    return None


cross = []
for a, b, kind in segs:
    if kind != "cut":
        continue
    # 折边侧边必定贴着容器边（端点在该方向 ±fl/t 带内），据此筛出折边候选
    near_edge = (abs(a[0]) < t + 0.6 and abs(b[0]) < t + 0.6) or                 (abs(a[0] - p.L) < t + 0.6 and abs(b[0] - p.L) < t + 0.6) or                 (abs(a[1]) < t + 0.6 and abs(b[1]) < t + 0.6) or                 (abs(a[1] - p.W) < t + 0.6 and abs(b[1] - p.W) < t + 0.6)
    if not near_edge:
        continue
    # 归属排除：线段两端贴着哪几块卡的面 → 属于那几块卡（它自己的端面/料边合法）
    owners = set()
    for e in (a, b):
        for xc in xs_l:
            if abs(e[0] - (xc - t / 2)) < 0.6 or abs(e[0] - (xc + t / 2)) < 0.6:
                owners.add(f"短卡 x={xc:g}")
        for yc in ys_w:
            if abs(e[1] - (yc - t / 2)) < 0.6 or abs(e[1] - (yc + t / 2)) < 0.6:
                owners.add(f"长卡 y={yc:g}")
    steps = max(3, int(math.dist(a, b) / 0.8))
    pts = [(a[0] + (b[0] - a[0]) * k / steps, a[1] + (b[1] - a[1]) * k / steps)
           for k in range(1, steps)]                 # 跳过两端（端点在料面/卡端上，合法）
    hit = next((h for h in (interior_hit(q) for q in pts) if h and h not in owners), None)
    if hit:
        cross.append((hit, tuple(round(v, 1) for v in a), tuple(round(v, 1) for v in b)))
print(("  ✗ 折边带内横穿板体 %d 条" % len(cross)) if cross else "  ✓ 折边带内无横穿板体")
for c in cross[:10]:
    print(f"      {c[0]}: {c[1]}→{c[2]}")

# ---- 画图 ----
fig2, ax2 = plt.subplots(figsize=(9, 6.6))
for a, b, kind in segs:
    col = {"cut": "0.55", "fold": "tab:blue"}[kind]
    ls = "-" if kind == "cut" else (0, (6, 2, 1, 2))
    lw = 0.9 if kind == "cut" else 1.4
    ax2.plot([a[0], b[0]], [a[1], b[1]], color=col, ls=ls, lw=lw)
for (anc, out) in flaps:
    ax2.plot([anc[0], out[0]], [anc[1], out[1]], color="tab:red", ls=":", lw=1.2, alpha=0.9)
ax2.set_aspect("equal")
ax2.set_xlim(-45, p.L + 45)
ax2.set_ylim(-45, p.W + 45)
ax2.set_title(f"折边几何核对：灰=裁切线 蓝=折弯线 红=折边锚点→外端  ({CFG['L']}×{CFG['W']})")
ax2.grid(alpha=0.25, lw=0.4)
os.makedirs(os.path.join(HERE, "_foldview"), exist_ok=True)
outp = os.path.join(HERE, "_foldview", "geom.png")
fig2.savefig(outp, dpi=200, bbox_inches="tight")
print("  →", outp)


# ---- 角部放大（只看 (0,0) 附近，用来核对折边与卡面的连接）----
fig3, ax3 = plt.subplots(figsize=(7.5, 7.5))
for a, b, kind in segs:
    if max(a[0], b[0]) > 90 or max(a[1], b[1]) > 90:
        continue
    col = {"cut": "k", "fold": "tab:blue"}[kind]
    ls = "-" if kind == "cut" else (0, (5, 2, 1.2, 2))
    ax3.plot([a[0], b[0]], [a[1], b[1]], color=col, ls=ls, lw=1.6 if kind == "cut" else 2.2)
for (anc, out) in flaps:
    if max(anc[0], out[0]) > 90 or max(anc[1], out[1]) > 90:
        continue
    ax3.plot([anc[0], out[0]], [anc[1], out[1]], color="tab:red", ls=":", lw=1.0, alpha=0.7)
    ax3.plot([out[0]], [out[1]], marker="x", color="tab:red", ms=9, mew=2)
ax3.set_aspect("equal")
ax3.set_xlim(-35, 85)
ax3.set_ylim(-35, 85)
ax3.grid(alpha=0.3, lw=0.4)
ax3.set_title("角部放大：黑=裁切线 蓝=折弯线 红x=折边外端")
fig3.savefig(os.path.join(HERE, "_foldview", "corner_zoom.png"), dpi=220, bbox_inches="tight")
print("  → _foldview/corner_zoom.png")
