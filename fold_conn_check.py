# -*- coding: utf-8 -*-
"""_conn_check.py — 折边局部检查（v1.0.7，逐块折边，不用全局启发式）

两个断言，直接对应用户反馈：
 A. **四角闭合**：每块折边矩形的 4 个角点、折弯线两端，都必须有线段端点重合 → 治「线没连起来」
 B. **不横穿刀卡**：折边轮廓端点不得落在别的板体内部 → 治「中间两条实心接缝线」
"""
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "core"))
import matplotlib                                   # noqa: E402
matplotlib.use("Agg")
import importlib.util                               # noqa: E402


def load(n, p):
    s = importlib.util.spec_from_file_location(n, p)
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


def run(tag, cfg):
    gc = load("gc", os.path.join(HERE, "core", "grid_core.py"))
    gd = load("gd", os.path.join(HERE, "core", "grid_draw.py"))
    p = gc.Params(**cfg)
    _e, _r, d = gc.report(p)
    t = d["t"]
    fl = d.get("fold_len_out", d["fold_len"])      # 展开口径 = 净长 + t
    if not (d.get("fold_l") or d.get("fold_w")):
        print(f"  {tag}: 无折边 → 跳过")
        return 0
    fig = gd.build_sheet(p, d)
    ax = [a for a in fig.get_axes() if a.get_zorder() < 50 and a.get_xlim()[1] > 1.5][0]
    PLX, ROW1, s = fig._plan_T          # 复用图纸自己的俯视变换（避免两边各算一套坐标）

    def T(x, y):
        return (PLX + x * s, ROW1 + y * s)

    segs = []
    for ln in ax.lines:
        st = "fold" if str(ln.get_linestyle()) not in ("-", "solid") else "cut"
        xs, ys = ln.get_xdata(), ln.get_ydata()
        for i in range(len(xs) - 1):
            a, b = (xs[i], ys[i]), (xs[i + 1], ys[i + 1])
            if math.dist(a, b) > 0.3:
                segs.append((a, b, st))
    ends = [s_[0] for s_ in segs] + [s_[1] for s_ in segs]

    xs_l = gd._slots(d["margin_l"], d["slots_long"], d["pitch_l"], t)
    ys_w = gd._slots(d["margin_w"], d["slots_short"], d["pitch_w"], t)
    fl_net = d.get("fold_len", 30.0)                # 折边净长（L 立边长度）
    flaps = []
    # L 形折叠口径（用户 2026-09-18 复核）：折边在**容器内侧**、与卡体垂直，
    # 宽 = 板厚 t（贴折弯线那段），长 = 净长 fl_net；折弯线 = 原卡端横跨板厚。
    if d.get("fold_l"):
        for yc in ys_w:
            sy = -1.0 if yc > p.W / 2.0 else 1.0
            y0 = yc + sy * t / 2                    # 立边起点（折弯线外侧料面）
            y1 = y0 + sy * fl_net                   # 立边外端（向容器内）
            x0, x1 = 0.0, t                         # 左端立边（宽 = 板厚）
            flaps.append(("长卡折边(左端)", (min(x0, x1), min(y0, y1)),
                          (max(x0, x1), max(y0, y1)), (0.0, y0), (0.0, y1)))
            x0, x1 = p.L - t, p.L
            flaps.append(("长卡折边(右端)", (min(x0, x1), min(y0, y1)),
                          (max(x0, x1), max(y0, y1)), (p.L, y0), (p.L, y1)))
    if d.get("fold_w"):
        for xc in xs_l:
            sx = -1.0 if xc > p.L / 2.0 else 1.0
            x0 = xc + sx * t / 2
            x1 = x0 + sx * fl_net
            y0, y1 = 0.0, t
            flaps.append(("短卡折边(下端)", (min(x0, x1), min(y0, y1)),
                          (max(x0, x1), max(y0, y1)), (x0, 0.0), (x1, 0.0)))
            y0, y1 = p.W - t, p.W
            flaps.append(("短卡折边(上端)", (min(x0, x1), min(y0, y1)),
                          (max(x0, x1), max(y0, y1)), (x0, p.W), (x1, p.W)))

    def has_end(pt, tol=0.4):
        tp = T(*pt)
        return any(math.dist(e, tp) <= tol for e in ends)

    def inside_other_card(pt):
        x, y = pt
        for xc in xs_l:
            if xc - t / 2 + 0.4 < x < xc + t / 2 - 0.4 and -0.4 < y < p.W + 0.4:
                return f"短卡本体 x={xc:g}"
        for yc in ys_w:
            if yc - t / 2 + 0.4 < y < yc + t / 2 - 0.4 and -0.4 < x < p.L + 0.4:
                return f"长卡本体 y={yc:g}"
        return None

    bad = 0
    for name, (x0, y0), (x1, y1), f0, f1 in flaps:
        corners = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
        for c in corners:
            if not has_end(c):
                print(f"  ✗ {name} 角点未闭合 @{c}")
                bad += 1
            hit = inside_other_card(c)
            if hit:
                print(f"  ✗ {name} 端点横穿 {hit} @{c}")
                bad += 1
    print(f"  {tag}: 折边 {len(flaps)} 块 → 不闭合/横穿 {bad} 处")
    return bad


def main():
    total = 0
    for tag, cfg in (("580 短卡折边", dict(L=580, W=380, H=380, pl=65, pw=38, ph=85, t=5.0, version=1)),
                     ("400 两边都折（角部相接）", dict(L=400, W=300, H=300, pl=32, pw=32, ph=60, t=5.0, version=1)),
                     ("1100 V2 不折", dict(L=1100, W=800, H=700, pl=200, pw=150, ph=200, t=7.0, version=2)),
                     ("300 小箱两边折", dict(L=300, W=250, H=200, pl=90, pw=70, ph=60, t=5.0, version=1))):
        total += run(tag, cfg)
    print("RESULT:", "PASS（折边四角闭合且无横穿）" if total == 0 else f"FAIL {total} 处")
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())
