# -*- coding: utf-8 -*-
"""layout_check.py — 版面客观检测（不靠肉眼）：
  A) 文字压线：文字包围盒 vs 同轴折线段 / 图框内框线 的相交检测
  B) 自适应缩放效率：实际用比例 vs 该区域能容纳的最大比例（差值 = 浪费的档位）
输出按模块打印，供修版前后对比。用法：python layout_check.py [仅测某模块]
"""
import importlib.util
import math
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "core"))

CORE = os.path.join(HERE, "core")
FRAME_INNER = dict(x0=32.0, x1=408.0, y0=12.0, y1=285.0)   # dwgframe 内框（A3）


def load(name, path):
    s = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


def seg_rect_hit(p, q, r):
    """线段 pq 与矩形 r=(x0,y0,x1,y1) 是否相交（含端点在框内）。"""
    (x0, y0, x1, y1) = r
    if x1 < x0:
        x0, x1 = x1, x0
    if y1 < y0:
        y0, y1 = y1, y0

    def inside(pt):
        return x0 <= pt[0] <= x1 and y0 <= pt[1] <= y1

    if inside(p) or inside(q):
        return True
    # 4 条边的 2D 线段相交
    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    def inter(a, b, c, d):
        d1, d2 = cross(c, d, a), cross(c, d, b)
        d3, d4 = cross(a, b, c), cross(a, b, d)
        return ((d1 > 0) != (d2 > 0)) and ((d3 > 0) != (d4 > 0))

    edges = [((x0, y0), (x1, y0)), ((x1, y0), (x1, y1)), ((x1, y1), (x0, y1)), ((x0, y1), (x0, y0))]
    return any(inter(p, q, c, d) for c, d in edges)


def _content_axes(fig):
    """真正的内容轴：排除图框叠加轴（zorder≥50）与归一化轴测轴（范围 0-1）。"""
    out = []
    for ax in fig.get_axes():
        if ax.get_zorder() >= 50:
            continue
        xl = ax.get_xlim()
        if xl[1] <= 1.5:
            continue
        out.append(ax)
    return out


def check_fig(fig, tag, ignore_prefixes=("字体：",)):
    """→ (文字压线清单, 越框文字清单)"""
    renderer = fig.canvas.get_renderer()
    hits, outside = [], []
    for ax in _content_axes(fig):
        texts = [t for t in ax.texts if t.get_text().strip()]
        lines = [ln for ln in ax.lines if len(ln.get_xdata()) >= 2]
        for t in texts:
            s = t.get_text()
            if any(s.startswith(p) for p in ignore_prefixes):
                continue
            bb_ = t.get_bbox_patch()                     # 带底色遮罩的标注（白底）不算压线
            if bb_ is not None:
                fc = bb_.get_facecolor()
                if len(fc) < 4 or fc[3] > 0.05:
                    continue
            try:
                bb = t.get_window_extent(renderer=renderer)
            except Exception:
                continue
            tr = ax.transData
            rect = (bb.x0, bb.y0, bb.x1, bb.y1)
            for ln in lines:
                xs, ys = ln.get_xdata(), ln.get_ydata()
                for i in range(len(xs) - 1):
                    p = tr.transform((xs[i], ys[i]))
                    q = tr.transform((xs[i + 1], ys[i + 1]))
                    if math.dist(p, q) < 3.0:            # 忽略极短线段（刻度等）
                        continue
                    if seg_rect_hit(p, q, rect):
                        inv = ax.transData.inverted()
                        a = inv.transform((bb.x0, bb.y0))
                        b = inv.transform((bb.x1, bb.y1))
                        d0 = (xs[i], ys[i])
                        d1 = (xs[i + 1], ys[i + 1])
                        hits.append((tag, s[:30],
                                     (round(min(a[0], b[0]), 1), round(min(a[1], b[1]), 1),
                                      round(max(a[0], b[0]), 1), round(max(a[1], b[1]), 1)),
                                     (round(d0[0], 1), round(d0[1], 1), round(d1[0], 1), round(d1[1], 1))))
                        break
                else:
                    continue
                break
    # 图框：文字越过内框线（按当前轴数据坐标判断；内容轴与图框同坐标系 mm）
    for ax in _content_axes(fig):
        for t in ax.texts:
            x, y = t.get_position()
            if not (FRAME_INNER["x0"] - 1 <= x <= FRAME_INNER["x1"] + 1):
                continue
            if y > FRAME_INNER["y1"] - 1 or y < FRAME_INNER["y0"] + 1:
                outside.append((tag, t.get_text()[:26], round(x, 1), round(y, 1)))
    return hits, outside


def fit_efficiency(fig, region, tag):
    """实际比例 vs 区域可容纳最大比例：返回 (scale_used, best_fit_scale, 浪费档位数)。"""
    fr = load("drawutil_", os.path.join(CORE, "drawutil.py"))
    used = getattr(fig, "_scale_used", None)
    if used is None:
        return None
    # 用图纸上所有线段在数据坐标下的外接框推算“内容尺寸”
    xs0 = ys0 = 1e18
    xs1 = ys1 = -1e18
    for ax in _content_axes(fig):
        for ln in ax.lines:
            for x, y in zip(ln.get_xdata(), ln.get_ydata()):
                xs0, ys0 = min(xs0, x), min(ys0, y)
                xs1, ys1 = max(xs1, x), max(ys1, y)
    if xs0 > xs1:
        return None
    w, h = (xs1 - xs0) * used, (ys1 - ys0) * used        # 内容数据尺寸（还原成 mm 数据）
    best = fr.pick_scale(w, h, region[0], region[1], fr.SCALES)
    return (used, best, _grade_gap(used, best))


def _grade_gap(used, best):
    order = [0.2, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 6.0, 8.0, 10.0, 15.0, 20.0]
    try:
        return order.index(best) - order.index(used)
    except ValueError:
        return None


def main():
    only = sys.argv[1] if len(sys.argv) > 1 else None
    cases = []

    sc = load("sc", os.path.join(CORE, "sheet_core.py"))
    sd = load("sd", os.path.join(CORE, "sheet_draw.py"))
    bc = load("bc", os.path.join(CORE, "block_core.py"))
    bd = load("bd", os.path.join(CORE, "block_draw.py"))
    gc = load("gc", os.path.join(CORE, "grid_core.py"))
    gd = load("gd", os.path.join(CORE, "grid_draw.py"))

    cases.append(("片材", "sheet", lambda: sd.build_sheet(sc.Params(L=400, W=300, H=15)), (244.0, 196.0)))
    cases.append(("片材-小", "sheet", lambda: sd.build_sheet(sc.Params(L=60, W=40, H=3)), (244.0, 196.0)))
    cases.append(("片材-大", "sheet", lambda: sd.build_sheet(sc.Params(L=1600, W=1000, H=30)), (244.0, 196.0)))
    for tag, args in (("仿形块-1000", dict(L=1000, W=100, H=100, sl=50, sw=70, sh=50, gap=40)),
                      ("仿形块-200短", dict(L=200, W=60, H=40, sl=40, sw=50, sh=30, gap=30)),
                      ("仿形块-2500长", dict(L=2500, W=150, H=200, sl=60, sw=100, sh=60, gap=60))):
        def mk(args=args):
            p = bc.Params(**args)
            e, r, d = bc.report(p)
            return bd.build_sheet(p, d)
        cases.append((tag, "block", mk, (244.0, 128.0)))
    for tag, args in (("网格-580", dict(L=580, W=380, H=380, pl=65, pw=38, ph=85, t=5, version=1)),
                      ("网格-1100", dict(L=1100, W=800, H=700, pl=200, pw=150, ph=200, t=7, version=2))):
        def mk(args=args):
            p = gc.Params(**args)
            e, r, d = gc.report(p)
            return gd.build_sheet(p, d)
        cases.append((tag, "grid", mk, (187.0, 247.0)))  # 实测内容范围（含折边预留）

    # 纸箱三型（用户反馈「纸箱图 1 尺寸标注压图线」）
    c201 = load("c201", os.path.join(CORE, "box0201_core.py"))
    s201 = load("s201", os.path.join(CORE, "box0201_sheets.py"))
    c310 = load("c310", os.path.join(CORE, "box0310_core.py"))
    s310 = load("s310", os.path.join(CORE, "box0310_sheets.py"))
    c312 = load("c312", os.path.join(CORE, "box0312_core.py"))
    s312 = load("s312", os.path.join(CORE, "box0312_sheets.py"))
    cases.append(("纸箱0201-400", "box", lambda: s201.build_sheet(c201.Params(L=400, W=300, H=200)), (236.0, 162.0)))
    cases.append(("纸箱0201-小", "box", lambda: s201.build_sheet(c201.Params(L=250, W=180, H=120, t=3)), (236.0, 162.0)))
    cases.append(("纸箱0201-大", "box", lambda: s201.build_sheet(c201.Params(L=900, W=600, H=400)), (236.0, 162.0)))
    cases.append(("纸箱0310-400", "box", lambda: s310.build_sheet(c310.Params(L=400, W=300, H=200)), (240.0, 166.0)))
    cases.append(("纸箱0310-混合板厚", "box", lambda: s310.build_sheet(
        c310.Params(L=1200, W=800, H=600, t=12, t_sleeve=12, t_cap_bot=7)), (240.0, 166.0)))
    cases.append(("纸箱0312-400", "box", lambda: s312.build_sheet(c312.Params(L=400, W=300, H=200)), (240.0, 166.0)))
    cases.append(("纸箱0312-大", "box", lambda: s312.build_sheet(c312.Params(L=1100, W=800, H=620, t=10, t_base=10)), (240.0, 166.0)))

    for tag, mod, mk, region in cases:
        if only and only not in tag and only != mod:
            continue
        fig = mk()
        fig.canvas.draw()
        hits, outside = check_fig(fig, tag)
        eff = fit_efficiency(fig, region, tag)
        print(f"\n=== {tag} ===")
        print(f"  比例：用 1:{eff[0]:g} · 该区最大可容 1:{eff[1]:g} · 浪费档位 {eff[2]}"
              if eff else "  比例：未知")
        print(f"  压线文字：{len(hits)} 处" + ("" if not hits else ""))
        for h in hits[:10]:
            print(f"     · 「{h[1]}」 文字框 x{h[2][0]}~{h[2][2]} y{h[2][1]}~{h[2][3]}"
                  f"  线 {h[3][0]},{h[3][1]}→{h[3][2]},{h[3][3]}")
        if outside:
            print(f"  越内框文字：{len(outside)} 处")
            for o in outside[:5]:
                print(f"     · 「{o[1]}」 at ({o[2]}, {o[3]})")
        plt.close(fig)


if __name__ == "__main__":
    main()
