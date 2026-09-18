# -*- coding: utf-8 -*-
"""dump_fold_lines.py — 把网格俯视图里折边附近的每一条线打出来（坐标+线型），
用于核对「哪些是裁切线、哪些是折弯线、哪些是可见棱线」，不靠肉眼。
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "core"))

import importlib.util                                    # noqa: E402


def load(n, p):
    s = importlib.util.spec_from_file_location(n, p)
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


gc = load("gc", os.path.join(os.path.dirname(os.path.abspath(__file__)), "core", "grid_core.py"))
gd = load("gd", os.path.join(os.path.dirname(os.path.abspath(__file__)), "core", "grid_draw.py"))

TAG = {"cur": "?"}
orig_plot = gd.plt.Axes.plot if hasattr(gd.plt, "Axes") else None


def run(cfg, tag):
    p = gc.Params(**cfg)
    errs, rows, d = gc.report(p)
    fig = gd.build_sheet(p, d)
    ax = [a for a in fig.get_axes() if a.get_zorder() < 50 and a.get_xlim()[1] > 1.5][0]
    print(f"\n=== {tag}: L{p.L:g} W{p.W:g} 边距 {d['margin_l']:.1f}/{d['margin_w']:.1f} "
          f"折边 长={d['fold_l']} 短={d['fold_w']} ===")
    # 俯视图范围：PLX=48, ROW1；内容 y ∈ [ROW1-2, ROW1+W*s+40]
    s = 1.0 / fig._scale_used
    ROW1 = None
    # ROW1 = TOP - W*s，TOP = 264 - 36*s - 2*fl*s
    _fl = d["fold_len"] if d.get("fold_w") else 0.0
    TOP = 264.0 - 36.0 * s - 2.0 * _fl * s
    ROW1 = TOP - p.W * s
    x0r, x1r = 30.0, 48.0 + p.L * s + 60.0
    y0r, y1r = ROW1 - 6.0, ROW1 + p.W * s + 6.0
    segs = []
    for ln in ax.lines:
        xs, ys = ln.get_xdata(), ln.get_ydata()
        for i in range(len(xs) - 1):
            (xa, ya), (xb, yb) = (xs[i], ys[i]), (xs[i + 1], ys[i + 1])
            if not (x0r <= xa <= x1r and x0r <= xb <= x1r):
                continue
            if not (y0r <= ya <= y1r and y0r <= yb <= y1r):
                continue
            L = ((xb - xa) ** 2 + (yb - ya) ** 2) ** 0.5
            if L < 0.4:
                continue
            segs.append((round(xa, 2), round(ya, 2), round(xb, 2), round(yb, 2),
                         round(L, 2), str(ln.get_linestyle()), ln.get_linewidth()))
    # 折算回数据 mm（纸面→数据：x_data=(x-PLX)/s）
    PLX = 48.0
    print(f"  俯视图区域共 {len(segs)} 段（含折边相关）：")
    for a, b, c, e, L, ls, lw in sorted(segs, key=lambda t: (t[1], t[0])):
        da = ((a - PLX) / s, (b - ROW1) / s)
        dc = ((c - PLX) / s, (e - ROW1) / s)
        kind = ("横" if abs(b - e) < 0.3 else "竖" if abs(a - c) < 0.3 else "斜")
        style = "实线" if ls in ("-", "solid") else ("点划线" if "6" in ls or "dashdot" in ls else ls)
        print(f"    纸面({a:7.2f},{b:7.2f})→({c:7.2f},{e:7.2f}) {kind} 长{L:5.2f}pt "
              f"数据({da[0]:7.1f},{da[1]:6.1f})→({dc[0]:7.1f},{dc[1]:6.1f}) {style} lw={lw}")


if __name__ == "__main__":
    run(dict(L=580, W=380, H=380, pl=65, pw=38, ph=85, t=5.0, version=1), "V1 短卡折边")
    run(dict(L=580, W=380, H=380, pl=160, pw=120, ph=85, t=5.0, version=1), "大格两边都折")
