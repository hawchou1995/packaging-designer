# -*- coding: utf-8 -*-
"""FEFCO 0312 - 2D outputs: DXF (base + lid blanks) + combined A3 sheet.

Lid = flat-top telescoping cap (centre panel + 4 walls, wrap corners, glue/staple).
Base = HSC (tube + bottom flaps, outer flaps meet).
"""
import os

from box0312_core import Params, dieline_base, dieline_lid, layout_lid, _layout_strip
from box0210_2d import dim_h, dim_v, g, _font_family, _today, save_sheet_png_svg


def _shift(pts, dx, dy):
    return [(x + dx, y + dy) for (x, y) in pts]


def write_dxf(p: Params, dxf_path: str):
    import ezdxf
    bo, bc, bi = dieline_base(p)
    lo, lc, lcuts, li = dieline_lid(p)
    dx = bi["blank_w"] + 80.0               # lid blank placed right of the base blank
    doc = ezdxf.new("R2010", setup=True)
    doc.header["$INSUNITS"] = 4
    doc.layers.add("CUT", color=1, lineweight=35)
    doc.layers.add("CREASE", color=5, linetype="DASHED", lineweight=18)
    doc.layers.add("NOTES", color=7)
    msp = doc.modelspace()
    msp.add_lwpolyline(_shift(bo, 0, -li["blank_h"]), close=True, dxfattribs={"layer": "CUT"})
    msp.add_lwpolyline(_shift(lo, dx, -li["blank_h"]), close=True, dxfattribs={"layer": "CUT"})
    for a, b in bc:
        msp.add_line((a[0], a[1] - li["blank_h"]), (b[0], b[1] - li["blank_h"]),
                     dxfattribs={"layer": "CREASE"})
    for a, b in lc:
        msp.add_line((a[0] + dx, a[1] - li["blank_h"]), (b[0] + dx, b[1] - li["blank_h"]),
                     dxfattribs={"layer": "CREASE"})
    for a, b in lcuts:
        msp.add_line((a[0] + dx, a[1] - li["blank_h"]), (b[0] + dx, b[1] - li["blank_h"]),
                     dxfattribs={"layer": "CUT"})
    notes = [
        "FEFCO 0312 - Half Slotted Container with Lid (HSC base + flat-top telescoping lid) / board t_base=%.1f t_lid=%.1f / mm / 1:1" % (p.tb, p.tl),
        f"Assembled outer {p.L:g}x{p.W:g}x{p.H:g}  Lid outer {p.L:g}x{p.W:g} inner {p.L-2*p.tl:g}x{p.W-2*p.tl:g}",
        f"Base outer {p.base_L:g}x{p.base_W:g} mfr {p.base_Lm:g}x{p.base_Wm:g}  bottom flaps {p.base_fo:g}/{p.base_fi:g}",
        f"Lid: centre {p.lid_Lm:g}x{p.lid_Wm:g} wall blank {p.lid_wall_blank:g} (cover depth {p.cover_depth:g}) wrap corners glue/staple",
        f"Left blank = base {bi['blank_w']:g}x{bi['blank_h']:g}; right blank = lid {li['blank_w']:g}x{li['blank_h']:g}",
        "CUT layer = cut, CREASE layer = score (dashed). Lid blank at origin; base blank left.",
    ]
    y_notes = -li["blank_h"] - 25.0
    for i, s in enumerate(notes):
        msp.add_text(s, height=6, dxfattribs={"layer": "NOTES"}).set_placement((0.0, y_notes - i * 10.0))
    doc.saveas(dxf_path)
    return dxf_path


def param_lines_zh(p: Params, mat_base: str = "BC 双瓦楞纸板", mat_lid: str = "BC 双瓦楞纸板"):
    _, _, bi = dieline_base(p)
    _, _, _, li = dieline_lid(p)
    area = (bi["blank_w"] * bi["blank_h"] + li["blank_w"] * li["blank_h"]) / 1e6
    return [
        "箱型：FEFCO 0312 有底无盖+盖（官方名 Half Slotted Container with Lid）",
        f"材料：底箱 {mat_base} t={g(p.tb)}；天盖 {mat_lid} t={g(p.tl)}（参考 GB/T 6544）",
        f"组装外尺寸：{g(p.L)} × {g(p.W)} × {g(p.H)}（= 天盖外尺寸）",
        f"尺寸链：盖内 = 盖外 − 2·t盖 = {g(p.L-2*p.tl)}×{g(p.W-2*p.tl)}；底箱外 = 盖内 − 2×{g(p.gap)} = {g(p.base_L)}×{g(p.base_W)}；底箱制造 {g(p.base_Lm)}×{g(p.base_Wm)}",
        f"底箱（HSC，摇盖底）：围框高 {g(p.base_Hm)}（= 外高 − t底）+ 下摇盖（外 {g(p.base_fo)} = W制/2+{g(p.flap_gain)}；内 {g(p.base_fi)}）；开槽 {g(p.slot_w)}",
        f"天盖（平顶罩盖）：顶板 {g(p.lid_Lm)}×{g(p.lid_Wm)}，四墙墙深 {g(p.lid_wall_blank)}（罩深 {g(p.cover_depth)}）；左右墙条全高含四角角片，包角后粘合/打钉；上表面平整",
        f"展开：底箱 {g(bi['blank_w'])}×{g(bi['blank_h'])}；天盖 {g(li['blank_w'])}×{g(li['blank_h'])}",
        f"用纸：底箱 {bi['blank_w']*bi['blank_h']/1e6:.4f} + 天盖 {li['blank_w']*li['blank_h']/1e6:.4f} = {area:.4f} m²",
        "楞向：平行组装高度（竖向）",
        "注：底箱为摇盖对接底；天盖为平顶罩盖（顶面无缝）；样式按 FEFCO 官方口径 + 双瓦楞放大系数。",
    ]


def build_sheet(p: Params, scale: float = 7.5, page=(420.0, 297.0),
                items_closed=None, items_open=None, meta: dict = None):
    meta = meta or {}
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fam, fpath = _font_family()
    bo, bc, bi = dieline_base(p)
    lo, lc, lcuts, li = dieline_lid(p)
    gl = layout_lid(p)

    pw, ph = page
    fig = plt.figure(figsize=(pw / 25.4, ph / 25.4))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, pw)
    ax.set_ylim(0, ph)
    ax.set_aspect("equal")
    ax.axis("off")
    xm = lambda a, b: (a + b) / 2.0

    # ---------------- base blank (left) ----------------
    ox, oy = 16.0, 224.3
    T1 = lambda x, y: (ox + x / scale, oy + y / scale)
    sp = [T1(*q) for q in bo] + [T1(*bo[0])]
    ax.plot([q[0] for q in sp], [q[1] for q in sp], color="k", lw=0.7)
    for (a, b) in bc:
        (xa, ya), (xb, yb) = T1(*a), T1(*b)
        ax.plot([xa, xb], [ya, yb], color="k", lw=0.45, ls=(0, (4, 2.4)))
    lb = _layout_strip(p, p.base_Wm, p.base_Lm, p.base_Hm, p.glue_inset)
    lab_b = [(xm(0, lb["X1"]), lb["Y1"] / 2, "粘舌"),
             (xm(lb["X1"], lb["X2"]), lb["Y1"] / 2, "端板 W"),
             (xm(lb["X2"], lb["X3"]), lb["Y1"] / 2, "侧板 L"),
             (xm(lb["X3"], lb["X4"]), lb["Y1"] / 2, "端板 W"),
             (xm(lb["X4"], lb["X5"]), lb["Y1"] / 2, "侧板 L"),
             (xm(lb["X1"], lb["X2"] - lb["s"]), lb["Y0"] - p.base_fi * 0.5, "内摇盖"),
             (xm(lb["X2"] + lb["s"], lb["X3"] - lb["s"]), lb["Y0"] - p.base_fo * 0.5, "外摇盖"),
             (xm(lb["X3"] + lb["s"], lb["X4"] - lb["s"]), lb["Y0"] - p.base_fi * 0.5, "内摇盖"),
             (xm(lb["X4"] + lb["s"], lb["X5"]), lb["Y0"] - p.base_fo * 0.5, "外摇盖")]
    for (lx, ly, s) in lab_b:
        sx, sy = T1(lx, ly)
        ax.text(sx, sy, s, ha="center", va="center", fontsize=5.8, color="0.15")
    yb1 = T1(0, lb["Y0"] - p.base_fo)[1] - 7.0
    yb2 = T1(0, lb["Y0"] - p.base_fo)[1] - 15.0
    for i in range(5):
        a = [lb["X0"], lb["X1"], lb["X2"], lb["X3"], lb["X4"], lb["X5"]][i]
        b = [lb["X0"], lb["X1"], lb["X2"], lb["X3"], lb["X4"], lb["X5"]][i + 1]
        dim_h(ax, T1(a, 0)[0], T1(b, 0)[0], yb1, g(b - a))
    dim_h(ax, T1(lb["X0"], 0)[0], T1(lb["X5"], 0)[0], yb2, "展开长 " + g(lb["X5"] - lb["X0"]))
    dim_v(ax, T1(0, lb["Y0"] - p.base_fo)[1], T1(0, lb["Y0"])[1], ox - 7.0, g(p.base_fo))
    dim_v(ax, T1(0, lb["Y0"])[1], T1(0, lb["Y1"])[1], ox - 7.0, g(lb["Y1"]))
    ax.text(T1(0, 0)[0] - 14, oy + 20, "底箱（HSC，×1）", fontsize=7.0, ha="left", color="0.1")

    # ---------------- lid blank (right) ----------------
    ox2, oy2 = 205.0, 186.0
    T2 = lambda x, y: (ox2 + x / scale, oy2 + y / scale)
    lp = [T2(*q) for q in lo] + [T2(*lo[0])]
    ax.plot([q[0] for q in lp], [q[1] for q in lp], color="k", lw=0.7)
    for (a, b) in lc:
        (xa, ya), (xb, yb) = T2(*a), T2(*b)
        ax.plot([xa, xb], [ya, yb], color="k", lw=0.45, ls=(0, (4, 2.4)))
    for (a, b) in lcuts:
        (xa, ya), (xb, yb) = T2(*a), T2(*b)
        ax.plot([xa, xb], [ya, yb], color="k", lw=0.7)
    wb = gl["wb"]
    lab_l = [(gl["cx0"] + p.lid_Lm / 2, gl["cy0"] + p.lid_Wm / 2, "盖顶板"),
             (wb / 2, gl["H1"] / 2, "盖墙+角片"),
             (gl["W1"] - wb / 2, gl["H1"] / 2, "盖墙+角片"),
             (wb / 2, gl["H1"] - wb / 2, "角片"), (wb / 2, wb / 2, "角片")]
    for (lx, ly, s) in lab_l:
        sx, sy = T2(lx, ly)
        ax.text(sx, sy, s, ha="center", va="center", fontsize=5.8, color="0.15")
    for (a, b) in ((gl["W0"], gl["cx0"]), (gl["cx0"], gl["cx1"]), (gl["cx1"], gl["W1"])):
        dim_h(ax, T2(a, 0)[0], T2(b, 0)[0], oy2 - 7.0, g(b - a))
    dim_h(ax, T2(gl["W0"], 0)[0], T2(gl["W1"], 0)[0], oy2 - 15.0, "展开长 " + g(gl["W1"] - gl["W0"]))
    xr = T2(gl["W1"], 0)[0] + 6.0
    for (a, b) in ((gl["H0"], gl["cy0"]), (gl["cy0"], gl["cy1"]), (gl["cy1"], gl["H1"])):
        dim_v(ax, T2(0, a)[1], T2(0, b)[1], xr, g(b - a))
    dim_v(ax, T2(0, gl["H0"])[1], T2(0, gl["H1"])[1], xr + 9.0, "展开高 " + g(gl["H1"]))
    ax.text(T2(gl["W1"], 0)[0] + 6.0, oy2 + gl["H1"] / scale + 5, "天盖·平顶罩盖（×1）",
            fontsize=7.0, ha="right", color="0.1")

    # ---------------- title / legend / notes ----------------
    ax.text(pw / 2, ph - 14, meta.get("title", "FEFCO 0312 有底无盖+盖 · 展开图 + 轴测图"),
            ha="center", va="center", fontsize=13, fontweight="bold")
    ax.text(pw / 2, ph - 22,
            meta.get("caption",
                     f"BC 双瓦楞 t={g(p.tl)} · 组装外尺寸 {g(p.L)}×{g(p.W)}×{g(p.H)} · 比例 1:{scale:g} · 单位 mm · {_today()} · 生成：ZCode 参数化管线"),
            ha="center", va="center", fontsize=8)
    ax.text(38.0, 89.0, f"图例：实线 = 裁切切口；虚线 = 压线（折痕）；尺寸单位 mm；图样比例 = 纸上 1:{scale:g}",
            ha="left", va="top", fontsize=6.8, color="0.0", fontweight="bold")
    lines = meta.get("param_lines") or param_lines_zh(
        p, meta.get("mat_base", "BC 双瓦楞纸板"), meta.get("mat_lid", "BC 双瓦楞纸板"))
    for i, s in enumerate(lines):
        ax.text(38.0, 84.0 - i * 4.0, s, ha="left", va="top", fontsize=6.2, color="0.1")
    ax.text(38.0, 6.5, f"字体：{fam}（{fpath or 'fallback'}）", fontsize=5.2, color="0.45")

    from box0312_core import panels, lift_items
    from box0210_3d import add_iso_panels, build_items_from
    ic = items_closed if items_closed is not None else build_items_from(panels(p), False)
    io = items_open if items_open is not None else lift_items(ic, "lid", 120.0)
    add_iso_panels(fig, ic, io, cap1="组装状态（等轴测）", cap2="开盖状态（天盖提起）")
    from dwgframe import draw_frame
    draw_frame(fig, page=page,
               name=meta.get("name", f"FEFCO 0312 有底无盖+平顶罩盖 {p.L:g}×{p.W:g}×{p.H:g}"),
               material=meta.get("material", f"BC 双瓦楞 t={p.tl:g}（可折叠）"),
               dwgno=meta.get("dwgno", "0312-BC-400x300x200"),
               scale_str=f"1:{scale:g}", sheet="A3",
               company=meta.get("company", "上海银轮热交换系统有限公司"),
               designed=meta.get("designed", ""), drawn=meta.get("drawn", ""),
               checked=meta.get("checked", ""), approved=meta.get("approved", ""))
    return fig


if __name__ == "__main__":
    import sys
    p = Params()
    outdir = sys.argv[1] if len(sys.argv) > 1 else r"D:/Tools/tmp/fefco0210_build/out0312"
    os.makedirs(outdir, exist_ok=True)
    dxf = write_dxf(p, os.path.join(outdir, "01_展开图_dieline_1-1.dxf"))
    print("DXF:", dxf, os.path.getsize(dxf), "bytes")
    fig = build_sheet(p)
    for f in save_sheet_png_svg(fig, os.path.join(outdir, "01_图纸-展开图+轴测图_A3")):
        print("SHEET:", f, os.path.getsize(f), "bytes")
