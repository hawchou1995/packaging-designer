# -*- coding: utf-8 -*-
"""FEFCO 0310 - 2D outputs: DXF (2 blanks in one file) + combined A3 sheet."""
import os

from box0310_core import Params, dieline_sleeve, dieline_cap, layout_cap
from box0210_2d import dim_h, dim_v, g, _font_family, _today, save_sheet_png_svg


def _shift(pts, dx, dy):
    return [(x + dx, y + dy) for (x, y) in pts]


def write_dxf(p: Params, dxf_path: str):
    import ezdxf
    so, sc, si_s = dieline_sleeve(p)
    co_t, cc_t, cuts_t, ci_t = dieline_cap(p, "top")
    co_b, cc_b, cuts_b, ci_b = dieline_cap(p, "bot")
    dy = -(si_s["blank_h"] + 80.0)          # cap blanks placed below the sleeve
    doc = ezdxf.new("R2010", setup=True)
    doc.header["$INSUNITS"] = 4
    doc.layers.add("CUT", color=1, lineweight=35)
    doc.layers.add("CREASE", color=5, linetype="DASHED", lineweight=18)
    doc.layers.add("NOTES", color=7)
    msp = doc.modelspace()
    msp.add_lwpolyline(so, close=True, dxfattribs={"layer": "CUT"})
    cap_set = [(co_b, cc_b, cuts_b, 0.0), (co_t, cc_t, cuts_t, ci_b["blank_w"] + 60.0)]
    for (co, cc, cuts, cdx) in cap_set:
        msp.add_lwpolyline(_shift(co, cdx, dy), close=True, dxfattribs={"layer": "CUT"})
        for a, b in cc:
            msp.add_line((a[0] + cdx, a[1] + dy), (b[0] + cdx, b[1] + dy),
                         dxfattribs={"layer": "CREASE"})
        for a, b in cuts:
            msp.add_line((a[0] + cdx, a[1] + dy), (b[0] + cdx, b[1] + dy),
                         dxfattribs={"layer": "CUT"})
    for a, b in sc:
        msp.add_line(a, b, dxfattribs={"layer": "CREASE"})
    same_caps = abs(p.tc - p.tc2) < 1e-9
    notes = [
        "FEFCO 0310 - Sleeve with Slotted Tray and End-to-End Lid / board t_sleeve=%.1f t_cap_top=%.1f t_cap_bot=%.1f / mm / 1:1"
        % (p.ts, p.tc, p.tc2),
        f"Assembled outer {p.L:g}x{p.W:g}x{p.H:g}  Cap outer {p.L:g}x{p.W:g} inner {p.L-2*p.tcmax:g}x{p.W-2*p.tcmax:g}",
        f"Sleeve outer {p.sleeve_L:g}x{p.sleeve_W:g}x{p.sleeve_H:g} mfr {p.sleeve_Lm:g}x{p.sleeve_Wm:g}"
        + ("  Caps x2 identical" if same_caps else "  Caps differ (see below)"),
        f"Cap bottom: centre {p.cap_Lm_bot:g}x{p.cap_Wm_bot:g} wall blank {p.wall_blank_bot:g}",
        f"Cap top:    centre {p.cap_Lm:g}x{p.cap_Wm:g} wall blank {p.wall_blank:g}",
        f"Top blank = sleeve {si_s['blank_w']:g}x{si_s['blank_h']:g}; cap blanks {ci_b['blank_w']:g}x{ci_b['blank_h']:g} (bottom)"
        f" + {ci_t['blank_w']:g}x{ci_t['blank_h']:g} (top)",
        "CUT layer = cut, CREASE layer = score (dashed). Origin = sleeve blank lower-left.",
    ]
    y_notes = dy - max(ci_t["blank_h"], ci_b["blank_h"]) - 20.0
    for i, s in enumerate(notes):
        msp.add_text(s, height=6, dxfattribs={"layer": "NOTES"}).set_placement((0.0, y_notes - i * 10.0))
    doc.saveas(dxf_path)
    return dxf_path


def param_lines_zh(p: Params, mat_sleeve: str = "BC 双瓦楞纸板",
                   mat_cap: str = "BC 双瓦楞纸板", mat_cap_bot: str = None):
    _, _, si_s = dieline_sleeve(p)
    _, _, _, ci_t = dieline_cap(p, "top")
    _, _, _, ci_b = dieline_cap(p, "bot")
    mat_cap_bot = mat_cap_bot or mat_cap
    same_caps = abs(p.tc - p.tc2) < 1e-9
    area = (si_s["blank_w"] * si_s["blank_h"]
            + ci_t["blank_w"] * ci_t["blank_h"] + ci_b["blank_w"] * ci_b["blank_h"]) / 1e6
    cap_line = (f"盖（×2 同款）：中心 {g(p.cap_Lm)}×{g(p.cap_Wm)} + 四墙；墙深 {g(p.wall_blank)}（BLD）；"
                f"左右墙条全高含四角角片，角片包过相邻墙粘合/打钉" if same_caps else
                f"下盖：中心 {g(p.cap_Lm_bot)}×{g(p.cap_Wm_bot)}，墙深 {g(p.wall_blank_bot)}；"
                f"上盖：中心 {g(p.cap_Lm)}×{g(p.cap_Wm)}，墙深 {g(p.wall_blank)}；四角角片包过相邻墙粘合/打钉")
    return [
        "箱型：FEFCO 0310 围框+两盖（官方名 Sleeve with Slotted Tray and End-to-End Lid）",
        (f"材料：围框 {mat_sleeve} t={g(p.ts)}；盖 {mat_cap} t={g(p.tc)}（参考 GB/T 6544）" if same_caps else
         f"材料：围框 {mat_sleeve} t={g(p.ts)}；下盖 {mat_cap_bot} t={g(p.tc2)}；上盖 {mat_cap} t={g(p.tc)}"),
        f"组装外尺寸：{g(p.L)} × {g(p.W)} × {g(p.H)}（= 盖外尺寸）",
        f"尺寸链：盖内 = 盖外 − 2·t盖 = {g(p.L-2*p.tcmax)}×{g(p.W-2*p.tcmax)}；围框外 = 盖内 − 2×{g(p.gap)} = {g(p.sleeve_L)}×{g(p.sleeve_W)}；围框制造 {g(p.sleeve_Lm)}×{g(p.sleeve_Wm)}",
        f"围框：展开 {g(si_s['blank_w'])} × {g(si_s['blank_h'])}（高 = 外高 − t下盖 − t上盖 = {g(p.sleeve_H)}）；侧缝粘合",
        cap_line,
        f"两盖端对端：每盖罩深 {g(p.d_cover)}（= 围框高/2{'' if p.cover_extra == 0 else ' + ' + g(p.cover_extra)}，两盖在腰线正好对接）",
        f"用纸：围框 {si_s['blank_w']*si_s['blank_h']/1e6:.4f} + 下盖 {ci_b['blank_w']*ci_b['blank_h']/1e6:.4f}"
        f" + 上盖 {ci_t['blank_w']*ci_t['blank_h']/1e6:.4f} = {area:.4f} m²",
        "楞向：平行组装高度（竖向）",
        "注：样式按 FEFCO 官方图（双盖、端对端）；下盖/上盖可分别选楞（板厚不同时展开图各出一张）。",
    ]


def _fits(txt, strip_mm, fontsize, min_mm=1.0):
    """板面文字在图纸上是否放得下（纸面 mm）。"""
    est = 0.0
    for ch in str(txt):
        est += fontsize * 0.3528 * (1.0 if ord(ch) > 0x2E80 else 0.55)
    return est <= strip_mm - min_mm


def _put(ax, x, y, txt, strip_mm, fontsize, color="0.15", min_mm=1.0):
    """放得下才画：宁可少一个板面字，也不让它压折线。"""
    if _fits(txt, strip_mm, fontsize, min_mm):
        ax.text(x, y, txt, fontsize=fontsize, ha="center", va="center", color=color)
        return True
    return False


def build_sheet(p: Params, scale: float = None, page=(420.0, 297.0),
                items_closed=None, items_open=None, meta: dict = None):
    meta = meta or {}
    author = meta.get("author", "包装周哥")
    manual = scale is not None and float(scale) > 0
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fam, fpath = _font_family()
    so, sc, si_s = dieline_sleeve(p)
    gsb = layout_cap(p, "bot")
    gst = layout_cap(p, "top")
    same_caps = abs(p.tc - p.tc2) < 1e-9
    from drawutil import pick_scale, scale_str, scale_tag
    if not manual:
        total_w = max(si_s["blank_w"], gsb["W1"] + 60.0 + gst["W1"])
        total_h = si_s["blank_h"] + 80.0 + max(gsb["H1"], gst["H1"])
        scale = pick_scale(total_w, total_h, 240.0, 166.0)

    pw, ph = page
    fig = plt.figure(figsize=(pw / 25.4, ph / 25.4))
    fig._scale_used, fig._scale_auto = scale, not manual
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, pw)
    ax.set_ylim(0, ph)
    ax.set_aspect("equal")
    ax.axis("off")

    # --- sleeve blank (top) ---
    ox = 42.0 + max(0.0, (246.0 - si_s["blank_w"] / scale) / 2.0)
    oy = 262.0 - si_s["blank_h"] / scale
    T1 = lambda x, y: (ox + x / scale, oy + y / scale)
    sp = [T1(*q) for q in so] + [T1(*so[0])]
    ax.plot([q[0] for q in sp], [q[1] for q in sp], color="k", lw=0.7)
    for (a, b) in sc:
        (xa, ya), (xb, yb) = T1(*a), T1(*b)
        ax.plot([xa, xb], [ya, yb], color="k", lw=0.45, ls=(0, (4, 2.4)))
    xm = lambda a, b: (a + b) / 2.0
    from box0310_core import layout_sleeve
    ls = layout_sleeve(p)
    lab_s = [(xm(0, ls["X1"]), si_s["blank_h"] / 2, "粘舌"),
             (xm(ls["X1"], ls["X2"]), si_s["blank_h"] / 2, "墙 W"),
             (xm(ls["X2"], ls["X3"]), si_s["blank_h"] / 2, "墙 L"),
             (xm(ls["X3"], ls["X4"]), si_s["blank_h"] / 2, "墙 W"),
             (xm(ls["X4"], ls["X5"]), si_s["blank_h"] / 2, "墙 L")]
    for (lx, ly, s) in lab_s:
        sx, sy = T1(lx, ly)
        _strip = (ls["X1"] if s == "粘舌" else
                  (ls["X2"] - ls["X1"] if s == "墙 W" else ls["X3"] - ls["X2"]))
        _put(ax, sx, sy, s, _strip / scale, 6.2)
    for (a, b) in ((0, ls["X1"]), (ls["X1"], ls["X2"]), (ls["X2"], ls["X3"]), (ls["X3"], ls["X4"]), (ls["X4"], ls["X5"])):
        dim_h(ax, T1(a, 0)[0], T1(b, 0)[0], oy - 8.0, g(b - a))
    dim_h(ax, T1(0, 0)[0], T1(ls["X5"], 0)[0], oy - 17.0, "展开长 " + g(ls["X5"]))
    dim_v(ax, T1(0, 0)[1], T1(0, si_s["blank_h"])[1], ox - 8.0, g(si_s["blank_h"]))
    ax.text(T1(0, 0)[0] - 14, oy + 8, "围框（×1）", fontsize=7.5, ha="left", color="0.1")

    # --- cap blanks (bottom row: 下盖 / 上盖，板厚不同则尺寸不同) ---
    caps_w = (gsb["W1"] + gst["W1"]) / scale + 10.0
    cap0 = 42.0 + max(0.0, (246.0 - caps_w) / 2.0)
    cap_ox = [cap0, cap0 + gsb["W1"] / scale + 10.0]
    cap_top_y = oy - 40.0
    for (k, ox2) in enumerate(cap_ox):
        oy2 = cap_top_y - gsb["H1" if k == 0 else "H1"] / scale if False else cap_top_y - (gsb["H1"] if k == 0 else gst["H1"]) / scale
        which = "bot" if k == 0 else "top"
        co, cc, cuts, ci = dieline_cap(p, which)
        gs = gsb if k == 0 else gst
        wb = gs["wb"]
        T2 = lambda x, y, ox2=ox2: (ox2 + x / scale, oy2 + y / scale)
        cp = [T2(*q) for q in co] + [T2(*co[0])]
        ax.plot([q[0] for q in cp], [q[1] for q in cp], color="k", lw=0.7)
        for (a, b) in cc:
            (xa, ya), (xb, yb) = T2(*a), T2(*b)
            ax.plot([xa, xb], [ya, yb], color="k", lw=0.45, ls=(0, (4, 2.4)))
        for (a, b) in cuts:
            (xa, ya), (xb, yb) = T2(*a), T2(*b)
            ax.plot([xa, xb], [ya, yb], color="k", lw=0.7)
        lab_c = [(gs["cx0"] + p.cap_Lm / 2, gs["cy0"] + p.cap_Wm / 2, "盖顶板"),
                 (wb / 2, gs["H1"] / 2, "盖墙+角片"),
                 (gs["W1"] - wb / 2, gs["H1"] / 2, "盖墙+角片"),
                 (wb / 2, gs["H1"] - wb / 2, "角片"), (wb / 2, wb / 2, "角片")]
        for (lx, ly, s) in lab_c:
            sx, sy = T2(lx, ly)
            _strip = wb if s != "盖顶板" else min(p.cap_Lm, p.cap_Wm)
            _put(ax, sx, sy, s, _strip / scale, 5.6)
        cap_name = ("下盖" if k == 0 else "上盖（与下盖同款）") if same_caps else ("下盖" if k == 0 else "上盖")
        ax.text(ox2, oy2 + gs["H1"] / scale + 5, cap_name, fontsize=7.0, ha="left", color="0.1")
        if k == 0 or not same_caps:
            for (a, b) in ((gs["W0"], gs["cx0"]), (gs["cx0"], gs["cx1"]), (gs["cx1"], gs["W1"])):
                dim_h(ax, T2(a, 0)[0], T2(b, 0)[0], oy2 - 8.0, g(b - a))
            dim_h(ax, T2(gs["W0"], 0)[0], T2(gs["W1"], 0)[0], oy2 - 17.0, "展开长 " + g(gs["W1"]))
            for (a, b) in ((gs["H0"], gs["cy0"]), (gs["cy0"], gs["cy1"]), (gs["cy1"], gs["H1"])):
                dim_v(ax, T2(0, a)[1], T2(0, b)[1], ox2 - 7.0, g(b - a))
            dim_v(ax, T2(0, gs["H0"])[1], T2(0, gs["H1"])[1], ox2 - 17.0, "展开高 " + g(gs["H1"]))

    # --- title / legend / notes ---
    ax.text(pw / 2, ph - 20, meta.get("title", "FEFCO 0310 围框+两盖 · 展开图 + 轴测图"),
            ha="center", va="center", fontsize=13, fontweight="bold")
    _cap_t = (f"盖 t={g(p.tc)}" if abs(p.tc - p.tc2) < 1e-9
              else f"上盖 t={g(p.tc)} / 下盖 t={g(p.tc2)}")
    ax.text(pw / 2, ph - 27,
            meta.get("caption",
                     f"围框 t={g(p.ts)} · {_cap_t} · 组装外尺寸 {g(p.L)}×{g(p.W)}×{g(p.H)}"
                     f" · {scale_tag(scale, not manual)} · 单位 mm · {_today()} · 生成：{author}"),
            ha="center", va="center", fontsize=8)
    ax.text(38.0, 89.0, f"图例：实线 = 裁切切口；虚线 = 压线（折痕）；尺寸单位 mm；图样比例 = 纸上 1:{scale:g}",
            ha="left", va="top", fontsize=6.8, color="0.0", fontweight="bold")
    lines = meta.get("param_lines") or param_lines_zh(
        p, meta.get("mat_sleeve", "BC 双瓦楞纸板"), meta.get("mat_cap", "BC 双瓦楞纸板"),
        meta.get("mat_cap_bot"))
    for i, s in enumerate(lines):
        ax.text(38.0, 84.0 - i * 4.0, s, ha="left", va="top", fontsize=6.2, color="0.1")
    ax.text(38.0, 14.0, f"字体：{fam}（{fpath or 'fallback'}）", fontsize=5.2, color="0.45")

    from box0310_core import panels, lift_items
    from box0210_3d import add_iso_panels, build_items_from
    ic = items_closed if items_closed is not None else build_items_from(panels(p), False)
    io = items_open if items_open is not None else lift_items(lift_items(ic, "cap_bot", -70.0), "cap_top", 110.0)
    add_iso_panels(fig, ic, io, cap1="组装状态（等轴测）", cap2="分解状态（上盖提起·下盖分离）")
    from dwgframe import draw_frame
    draw_frame(fig, page=page,
               name=meta.get("name", f"FEFCO 0310 围框+两盖 {p.L:g}×{p.W:g}×{p.H:g}"),
               material=meta.get("material", f"BC 双瓦楞 t={p.tc:g}（可折叠）"),
               dwgno=meta.get("dwgno", "0310-BC-400x300x200"),
               scale_str=scale_str(scale), sheet="A3",
               company=meta.get("company", "上海银轮热交换系统有限公司"),
               designed=meta.get("designed", ""), drawn=meta.get("drawn", ""),
               checked=meta.get("checked", ""), approved=meta.get("approved", ""))
    return fig


if __name__ == "__main__":
    import sys
    p = Params()
    outdir = sys.argv[1] if len(sys.argv) > 1 else r"D:/Tools/tmp/fefco0210_build/out0310"
    os.makedirs(outdir, exist_ok=True)
    dxf = write_dxf(p, os.path.join(outdir, "01_展开图_dieline_1-1.dxf"))
    print("DXF:", dxf, os.path.getsize(dxf), "bytes")
    fig = build_sheet(p)
    for f in save_sheet_png_svg(fig, os.path.join(outdir, "01_图纸-展开图+轴测图_A3")):
        print("SHEET:", f, os.path.getsize(f), "bytes")
