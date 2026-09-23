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


# ---------------- 版面体检（v1.0.15 新增）：越框 / 压标题栏 / 压字 / 线压说明 ----------------
# 旧的两个检查都看不见这些：A) 只在**同一坐标轴内**比文字与线，且带白底遮罩的文字会被跳过；
# B) 只看文字**位置**是否越出内框。于是「注释伸进标题栏」「尺寸数字压注释行」「视图名越框」
# 这类版面缺陷长期报 0（用户 2026-09-23 当场指出）。这里统一折算成纸面 mm 做几何判定。
FRAME = (32.0, 12.0, 408.0, 285.0)          # 内框
TITLE_BLOCK = (228.0, 12.0, 408.0, 68.0)    # 右下标题栏
NOTE_HEADS = ("技术要求", "注：", "图例", "箱型", "材料", "尺寸链", "围框：", "盖（",
              "两盖", "用纸", "楞向", "底箱", "天盖", "展开", "1.", "2.", "3.",
              "4.", "5.", "6.", "7.", "8.")


def seg_rect_hit(p, q, r):
    """线段 pq 与矩形 r 是否相交（端点在框内 or 与四边真正相交）。r=(x0,y0,x1,y1)。"""
    x0, y0, x1, y1 = r
    if x1 < x0:
        x0, x1 = x1, x0
    if y1 < y0:
        y0, y1 = y1, y0

    def ins(pt):
        return x0 <= pt[0] <= x1 and y0 <= pt[1] <= y1

    if ins(p) or ins(q):
        return True

    def cr(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    def inter(a, b, c, d):
        d1, d2 = cr(c, d, a), cr(c, d, b)
        d3, d4 = cr(a, b, c), cr(a, b, d)
        return ((d1 > 0) != (d2 > 0)) and ((d3 > 0) != (d4 > 0))

    return any(inter(p, q, c, d) for c, d in (
        ((x0, y0), (x1, y0)), ((x1, y0), (x1, y1)),
        ((x1, y1), (x0, y1)), ((x0, y1), (x0, y0))))


def collect_mm(fig):
    """内容元素（线段 + 文字）统一折算成纸面 mm；含轴测图轴，排除图框 overlay 轴。"""
    k = 25.4 / fig.dpi
    segs, texts = [], []
    for ax in fig.get_axes():
        if ax.get_zorder() >= 50:
            continue
        tr = ax.transData
        for ln in ax.lines:
            xs, ys = ln.get_xdata(), ln.get_ydata()
            for i in range(len(xs) - 1):
                a = [v * k for v in tr.transform((xs[i], ys[i]))]
                b = [v * k for v in tr.transform((xs[i + 1], ys[i + 1]))]
                if math.dist(a, b) > 0.6:
                    segs.append((a[0], a[1], b[0], b[1]))
        for t in ax.texts:
            s = t.get_text().strip()
            if not s:
                continue
            try:
                bb = t.get_window_extent(renderer=fig.canvas.get_renderer())
            except Exception:
                continue
            texts.append((s, bb.x0 * k, bb.y0 * k, bb.x1 * k, bb.y1 * k))
    return segs, texts


def _in_rect(t, r):
    return (t[1] >= r[0] - 0.3 and t[3] <= r[2] + 0.3
            and t[2] >= r[1] - 0.3 and t[4] <= r[3] + 0.3)


def frame_audit(fig, tag):
    """→ 问题清单 [(类别, 内容, 位置/数量, y)]。"""
    fig.canvas.draw()
    segs, texts = collect_mm(fig)
    out = []
    for t in texts:
        if not _in_rect(t, FRAME):
            out.append(("越框", t[0][:34], round(t[1], 1), round(t[2], 1)))
    for t in texts:
        if _in_rect(t, TITLE_BLOCK):        # 标题栏自带字段不算
            continue
        if not (t[3] < TITLE_BLOCK[0] + 0.3 or t[1] > TITLE_BLOCK[2] - 0.3
                or t[4] < TITLE_BLOCK[1] + 0.3 or t[2] > TITLE_BLOCK[3] - 0.3):
            out.append(("压标题栏", t[0][:34], round(t[1], 1), round(t[2], 1)))
    for i in range(len(texts)):
        for j in range(i + 1, len(texts)):
            a, b = texts[i], texts[j]
            w = min(a[3], b[3]) - max(a[1], b[1])
            h = min(a[4], b[4]) - max(a[2], b[2])
            # 交叠高度要够「一个字高」的 1/4 才算压字：CJK 字体的行框比行距高，
            # 多行文字（同一段落的相邻行）会假阳性 —— 已用视觉复核确认（2026-09-23）。
            if w > 0 and h > 0 and w * h > 1.0 and h >= 0.25 * min(a[4] - a[2], b[4] - b[2]):
                out.append(("压字", f"{a[0][:18]} × {b[0][:18]}", round(w * h, 1),
                            round(max(a[1], b[1]), 1)))
    for t in texts:
        if not t[0].startswith(NOTE_HEADS):
            continue
        n = sum(1 for s in segs
                if seg_rect_hit((s[0], s[1]), (s[2], s[3]), (t[1], t[2], t[3], t[4])))
        if n:
            out.append(("线压说明", t[0][:30], n, round(t[2], 1)))
    return out


def main():
    only = sys.argv[1] if len(sys.argv) > 1 else None
    bad_cases = 0
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
    # v1.0.15 补：用户 2026-09-23 指出的版面缺陷算例（这些在旧检查器下一律报 0）
    cases.append(("0310 固定盖高100", "box", lambda: s310.build_sheet(
        c310.Params(L=400, W=300, H=400, t=7, t_sleeve=7, t_cap_bot=7,
                    cap_h_mode="fixed", cap_h=100.0)), (240.0, 166.0)))
    cases.append(("0312 412×312×194 罩深87", "box", lambda: s312.build_sheet(
        c312.Params(L=412, W=312, H=194, t=7, t_base=7, cover_depth=87.0)), (240.0, 166.0)))
    cases.append(("网格 版1 300×200×150", "grid", lambda: gd.build_sheet(
        gc.Params(L=300, W=200, H=150, pl=40, pw=25, ph=50, t=3, version=1),
        gc.report(gc.Params(L=300, W=200, H=150, pl=40, pw=25, ph=50, t=3, version=1))[2]),
        (187.0, 247.0)))
    cases.append(("网格 版2 1600×1000×900", "grid", lambda: gd.build_sheet(
        gc.Params(L=1600, W=1000, H=900, pl=120, pw=80, ph=150, t=7, version=2),
        gc.report(gc.Params(L=1600, W=1000, H=900, pl=120, pw=80, ph=150, t=7, version=2))[2]),
        (187.0, 247.0)))
    cases.append(("仿形块 2500×150×200", "block", lambda: bd.build_sheet(
        bc.Params(L=2500, W=150, H=200, sl=60, sw=100, sh=60, gap=60),
        bc.report(bc.Params(L=2500, W=150, H=200, sl=60, sw=100, sh=60, gap=60))[2]),
        (244.0, 128.0)))

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
        aud = frame_audit(fig, tag)
        if aud:
            bad_cases += 1
            print(f"  版面体检：{len(aud)} 处（越框/压标题栏/压字/线压说明）")
            for a in aud[:8]:
                print(f"     · {a[0]}：{a[1]}  ({a[2]}, y={a[3]})")
        else:
            print("  版面体检：0 处")
        plt.close(fig)



    if bad_cases:
        print(f"\n版面体检：{bad_cases} 个算例有问题（越框 / 压标题栏 / 压字 / 线压说明）")
        sys.exit(1)
    print("\n版面体检：全部算例通过（越框 / 压标题栏 / 压字 / 线压说明 均为 0）")


def connectivity_check(fig, tag, tol=0.35):
    """俯视图「线要连起来」：每个线段端点必须与另一条线段共享端点（容差 tol 纸面 mm）。

    折弯线（点划线）不参与端点配对——它按制图惯例与料边相接即可，不能因虚线相位误判。
    """
    axes = _content_axes(fig)
    segs = []
    for ax in axes:
        for ln in ax.lines:
            if str(ln.get_linestyle()) not in ("-", "solid"):
                continue
            xs, ys = ln.get_xdata(), ln.get_ydata()
            for i in range(len(xs) - 1):
                p, q = (xs[i], ys[i]), (xs[i + 1], ys[i + 1])
                if math.dist(p, q) > 0.5:
                    segs.append((p, q))
    if not segs:
        return [], 0
    ends = []
    for p, q in segs:
        ends.append(p)
        ends.append(q)
    lonely = []
    for i, e in enumerate(ends):
        hit = 0
        for j, o in enumerate(ends):
            if i // 2 == j // 2:
                continue
            if math.dist(e, o) <= tol:
                hit += 1
        # 端点落在另一条线段的“中间”（T 形接头）也算连通
        for j, (p, q) in enumerate(segs):
            if j == i // 2:
                continue
            if _pt_on_seg(e, p, q, tol):
                hit += 1
        if hit == 0:
            lonely.append((tag, round(e[0], 1), round(e[1], 1)))
    return lonely, len(segs)


def _pt_on_seg(pt, a, b, tol):
    ax_, ay = a
    bx, by = b
    dx, dy = bx - ax_, by - ay
    L2 = dx * dx + dy * dy
    if L2 < 1e-9:
        return False
    t = ((pt[0] - ax_) * dx + (pt[1] - ay) * dy) / L2
    if t <= 0.02 or t >= 0.98:
        return False
    px, py = ax_ + t * dx, ay + t * dy
    return math.dist((px, py), pt) <= tol

if __name__ == "__main__":
    main()
