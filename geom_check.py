# -*- coding: utf-8 -*-
"""geom_check.py - cross-axis interference checker for sheets."""

import math


def rect_hit(a, b):
    """Two screen rects overlap?"""
    return not (a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1])


def seg_rect_hit(p, q, r, tol=0.75):
    """Segment pq intersects rect r=(x0,y0,x1,y1)?  tol: 需真正侵入多少像素才算（防贴边误报）"""
    x0, y0, x1, y1 = r
    x0, y0, x1, y1 = x0 + tol, y0 + tol, x1 - tol, y1 - tol
    if x1 <= x0 or y1 <= y0:
        return False
    if x1 < x0:
        x0, x1 = x1, x0
    if y1 < y0:
        y0, y1 = y1, y0

    def inside(pt):
        return x0 <= pt[0] <= x1 and y0 <= pt[1] <= y1

    if inside(p) or inside(q):
        return True

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    def inter(a, b, c, d):
        d1 = cross(c, d, a)
        d2 = cross(c, d, b)
        d3 = cross(a, b, c)
        d4 = cross(a, b, d)
        return ((d1 > 0) != (d2 > 0)) and ((d3 > 0) != (d4 > 0))

    edges = [((x0, y0), (x1, y0)), ((x1, y0), (x1, y1)),
             ((x1, y1), (x0, y1)), ((x0, y1), (x0, y0))]
    for c, d in edges:
        if inter(p, q, c, d):
            return True
    return False


FRAME_Z = 50.0


def arrow_segs(ax):
    """尺寸线本体：annotate 产生的 FancyArrowPatch（**不在 ax.lines 里**）。

    返回 [(p, q)]，p/q 是尺寸线**真正的两端**。本项目的尺寸线一律轴对齐，
    所以取包围盒的主方向中线（包围盒含箭头，次方向中线即线所在位置）。
    ⚠️ 不能直接用包围盒对角线：对角线并不是尺寸线，会让相交检测全部失效。
    """
    out = []
    for t in ax.texts:
        ap = getattr(t, "arrow_patch", None)
        if ap is None:
            continue
        try:
            ext = ap.get_extents()
        except Exception:
            continue
        if ext.width <= 0.5 and ext.height <= 0.5:
            continue
        if ext.width >= ext.height:
            ym = (ext.y0 + ext.y1) / 2.0
            out.append(((ext.x0, ym), (ext.x1, ym)))
        else:
            xm = (ext.x0 + ext.x1) / 2.0
            out.append(((xm, ext.y0), (xm, ext.y1)))
    return out


def geom_pool(fig, min_len=3.0):
    """All geometry in screen coords: [(p, q, axes_id)] - lines, arrows, patches."""
    fig.canvas.draw()          # FancyArrowPatch 的 extents 需渲染后才有效
    pool = []
    for ax in fig.get_axes():
        if ax.get_zorder() >= FRAME_Z:
            continue
        tr = ax.transData
        for ln in ax.lines:
            xs, ys = ln.get_xdata(), ln.get_ydata()
            for i in range(len(xs) - 1):
                try:
                    p = tr.transform((xs[i], ys[i]))
                    q = tr.transform((xs[i + 1], ys[i + 1]))
                except Exception:
                    continue
                if math.dist(p, q) >= min_len:
                    pool.append((tuple(p), tuple(q), id(ax)))
        for p, q in arrow_segs(ax):
            if math.dist(p, q) >= min_len:
                pool.append((tuple(p), tuple(q), id(ax)))
        for pt in getattr(ax, "patches", []):
            try:
                xy = pt.get_path().vertices
                xy = pt.get_patch_transform().transform(xy)
                scr = tr.transform(xy)
            except Exception:
                continue
            for i in range(len(scr) - 1):
                p = tuple(scr[i])
                q = tuple(scr[i + 1])
                if math.dist(p, q) >= min_len:
                    pool.append((p, q, id(ax)))
    return pool


def collect_texts(fig, ignore_prefixes=("font",), min_px=0.5):
    """[(text, rect, masked, axes_id)] in screen coords."""
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    out = []
    for ax in fig.get_axes():
        if ax.get_zorder() >= FRAME_Z:
            continue
        for t in ax.texts:
            s = t.get_text().strip()
            if not s or any(s.startswith(p) for p in ignore_prefixes):
                continue
            try:
                bb = t.get_window_extent(renderer=renderer)
            except Exception:
                continue
            if bb.width <= min_px and bb.height <= min_px:
                continue
            masked = False
            bp = t.get_bbox_patch()
            if bp is not None:
                fc = bp.get_facecolor()
                if len(fc) < 4 or fc[3] > 0.05:
                    masked = True
            out.append((s, (bb.x0, bb.y0, bb.x1, bb.y1), masked, id(ax)))
    return out


def _interior_cross(a, b, c, d, tol=0.6):
    """两线段是否在**内部**相交（端点相接不算：链式尺寸共用端点属正常）。"""
    def cr(o, p, q):
        return (p[0] - o[0]) * (q[1] - o[1]) - (p[1] - o[1]) * (q[0] - o[0])

    def on(a1, b1, p):
        return (abs(cr(a1, b1, p)) <= tol
                and min(a1[0], b1[0]) - tol <= p[0] <= max(a1[0], b1[0]) + tol
                and min(a1[1], b1[1]) - tol <= p[1] <= max(a1[1], b1[1]) + tol)

    if on(a, b, c) or on(a, b, d) or on(c, d, a) or on(c, d, b):
        return False                      # 有端点落在另一条线上 → 相接，不算相交
    d1, d2 = cr(c, d, a), cr(c, d, b)
    d3, d4 = cr(a, b, c), cr(a, b, d)
    return ((d1 > 0) != (d2 > 0)) and ((d3 > 0) != (d4 > 0))


def dim_crossings(fig, min_len=3.0):
    """尺寸线相交 / 尺寸线穿过图线（GB/T 4458.4：尺寸线不得与其他图线或尺寸线相交）。

    → [(kind, seg_a, seg_b)]，kind ∈ {"dim×dim", "dim×line"}。
    """
    fig.canvas.draw()          # FancyArrowPatch 的 extents 需渲染后才有效
    out = []
    for ax in fig.get_axes():
        if ax.get_zorder() >= FRAME_Z:
            continue
        dims = [s for s in arrow_segs(ax) if math.dist(s[0], s[1]) >= min_len]
        lines = []
        tr = ax.transData
        for ln in ax.lines:
            xs, ys = ln.get_xdata(), ln.get_ydata()
            for i in range(len(xs) - 1):
                try:
                    p = tuple(tr.transform((xs[i], ys[i])))
                    q = tuple(tr.transform((xs[i + 1], ys[i + 1])))
                except Exception:
                    continue
                if math.dist(p, q) >= min_len:
                    lines.append((p, q))
        for i in range(len(dims)):
            for j in range(i + 1, len(dims)):
                if _interior_cross(dims[i][0], dims[i][1], dims[j][0], dims[j][1]):
                    out.append(("dim×dim", dims[i], dims[j]))
            for (p, q) in lines:
                if _interior_cross(dims[i][0], dims[i][1], p, q):
                    out.append(("dim×line", dims[i], (p, q)))
    return out


def region_hits(fig, mm_rect, page=(420.0, 297.0)):
    """图纸上**禁止文字进入**的区域（标题栏等）→ [(text, rect)]。

    标题栏画在 zorder≥50 的图框轴上，普通压线检测会整个跳过该轴，
    所以必须单独守一道：正文文字一旦伸进标题栏，出图就是废图。
    """
    fig.canvas.draw()
    w_px = fig.get_size_inches()[0] * fig.dpi
    h_px = fig.get_size_inches()[1] * fig.dpi
    sx, sy = w_px / page[0], h_px / page[1]
    x0, y0, x1, y1 = mm_rect
    rect = (x0 * sx, y0 * sy, x1 * sx, y1 * sy)
    out = []
    for ax in fig.get_axes():
        if ax.get_zorder() >= FRAME_Z:
            continue
        for t in ax.texts:
            s = t.get_text().strip()
            if not s:
                continue
            try:
                bb = t.get_window_extent(renderer=fig.canvas.get_renderer())
            except Exception:
                continue
            if rect_hit((bb.x0, bb.y0, bb.x1, bb.y1), rect):
                out.append((s, (bb.x0, bb.y0, bb.x1, bb.y1)))
    return out


def check(fig, min_len=3.0):
    """Return (hits, overlaps).

    hits: (text, rect, seg, kind) with kind in {line, dim, cross, dim+cross}.
    overlaps: (text_a, text_b) with intersecting boxes.
    """
    pool = geom_pool(fig, min_len)
    texts = collect_texts(fig)
    hits = []
    for (s, rect, masked, aid) in texts:
        for (p, q, gid) in pool:
            if seg_rect_hit(p, q, rect):
                kind = []
                if masked:
                    kind.append("dim")
                if gid != aid:
                    kind.append("cross")
                hits.append((s, rect, (p, q), "+".join(kind) or "line"))
                break
    overlaps = []
    for i in range(len(texts)):
        for j in range(i + 1, len(texts)):
            if rect_hit(texts[i][1], texts[j][1]):
                overlaps.append((texts[i][0], texts[j][0], texts[i][1], texts[j][1]))
    return hits, overlaps
