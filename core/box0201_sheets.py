# -*- coding: utf-8 -*-
"""FEFCO 0201 (RSC) - 2D outputs: DXF (1:1) + A3 drawing sheet (matplotlib)."""
import math
import os

from box0201_core import Params, dieline, layout
from box0210_2d import dim_h, dim_v, g, _font_family, _today, save_sheet_png_svg


def write_dxf(p: Params, dxf_path: str):
    import ezdxf
    outline, creases, info = dieline(p)
    doc = ezdxf.new("R2010", setup=True)
    doc.header["$INSUNITS"] = 4
    doc.layers.add("CUT", color=1, lineweight=35)
    doc.layers.add("CREASE", color=5, linetype="DASHED", lineweight=18)
    doc.layers.add("NOTES", color=7)
    msp = doc.modelspace()
    msp.add_lwpolyline([(x, y) for (x, y) in outline], close=True, dxfattribs={"layer": "CUT"})
    for a, b in creases:
        msp.add_line(a, b, dxfattribs={"layer": "CREASE"})
    y_notes = -p.fo - 12.0
    notes = [
        "FEFCO 0201 Regular Slotted Container (RSC) / BC double wall t=7.0 / units mm / scale 1:1",
        f"Outer {p.L:g}x{p.W:g}x{p.H:g}  Inner {p.Li:g}x{p.Wi:g}x{p.Hi:g}  Mfr {p.Lm:g}x{p.Wm:g}x{p.Hm:g}",
        f"Outer flaps {p.fo:g} (=Wm/2+{p.flap_gain:g})  Inner flaps {p.fi:g} (=Wm/2-{p.flap_reduce:g})  Slot {p.slot_w:g}  Lap {p.glue_w:g}",
        f"Blank {info['blank_w']:g}x{info['blank_h']:g}   CUT layer = through cut, CREASE layer = score (dashed)",
        "Origin = blank lower-left. Allowances per public practice; no factory correction factors applied.",
    ]
    for i, s in enumerate(notes):
        msp.add_text(s, height=5.5, dxfattribs={"layer": "NOTES"}).set_placement((0.0, y_notes - i * 9.0))
    doc.saveas(dxf_path)
    return dxf_path


def param_lines_zh(p: Params, info: dict, mat: str = "BC 双瓦楞纸板"):
    return [
        "箱型：FEFCO 0201 标准开槽箱（RSC，上下摇盖对接式）",
        f"材料：{mat} t = {g(p.t)} mm（参考 GB/T 6544，成箱后约等于楞高）",
        f"外尺寸 L×W×H：{g(p.L)} × {g(p.W)} × {g(p.H)} mm（与 0210 对照同口径）",
        f"内尺寸：{g(p.Li)} × {g(p.Wi)} × {g(p.Hi)} mm   制造尺寸：{g(p.Lm)} × {g(p.Wm)} × {g(p.Hm)} mm",
        f"换算口径：内 = 外 − 2t；制造 = 内 + t（可参数化替换厂方修正系数）",
        f"外摇盖深 {g(p.fo)}（= W制/2 + {g(p.flap_gain)} 放大系数，补偿内摇盖回弹）；内摇盖深 {g(p.fi)}（= W制/2 − {g(p.flap_reduce)}）",
        f"开槽宽 {g(p.slot_w)}（双瓦楞常用 8–10）；粘舌 {g(p.glue_w)} 宽（双瓦楞常用 45–50）",
        f"展开尺寸：{g(info['blank_w'])} × {g(info['blank_h'])} mm，用纸面积 {info['blank_w'] * info['blank_h'] / 1e6:.4f} m²",
        "楞向：平行箱高（竖向）",
        "注：闭合后两外摇盖对接（对口间隙按标准 ≤3mm 控制）；几何为公开标准口径（FEFCO 0201 / 市面公开刀模图），",
        "　　未含厂方工艺修正；与 0210 直插盒的完整对照见《对照说明_0210_vs_0201.md》。",
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
    """A3 combined sheet: 1:scale dieline (left) + isometric views (right) + notes.

    scale=None → 按展开图外接框 × 图幅可用区（236×162mm）自动选最大可容纳档。
    """
    meta = meta or {}
    author = meta.get("author", "包装周哥")
    manual = scale is not None and float(scale) > 0
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fam, fpath = _font_family()
    outline, creases, info = dieline(p)
    gd = layout(p)

    pw, ph = page
    fig = plt.figure(figsize=(pw / 25.4, ph / 25.4))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, pw)
    ax.set_ylim(0, ph)
    ax.set_aspect("equal")
    ax.axis("off")

    xmin = min(q[0] for q in outline)
    xmax = max(q[0] for q in outline)
    ymin = min(q[1] for q in outline)
    ymax = max(q[1] for q in outline)
    from drawutil import pick_scale, scale_str, scale_tag
    if not manual:
        scale = pick_scale(xmax - xmin, ymax - ymin, 236.0, 162.0)
    dw, dh = (xmax - xmin) / scale, (ymax - ymin) / scale
    ox = 42.0 + max(0.0, (246.0 - dw) / 2.0)
    oy = 94.0 + max(0.0, (172.0 - dh) / 2.0)
    fig._scale_used, fig._scale_auto = scale, not manual
    T = lambda x, y: (ox + (x - xmin) / scale, oy + (y - ymin) / scale)

    sp = [T(x, y) for (x, y) in outline]
    sp.append(sp[0])
    ax.plot([q[0] for q in sp], [q[1] for q in sp], color="k", lw=0.7, solid_joinstyle="round")

    for (a, b) in creases:
        (xa, ya), (xb, yb) = T(*a), T(*b)
        ax.plot([xa, xb], [ya, yb], color="k", lw=0.45, ls=(0, (4, 2.4)))

    xmid = lambda a, b: (a + b) / 2.0
    labels = [
        (xmid(gd["X0"], gd["X1"]), gd["Y1"] / 2, "粘舌"),
        (xmid(gd["X1"], gd["X2"]), gd["Y1"] / 2, "端板 W"),
        (xmid(gd["X2"], gd["X3"]), gd["Y1"] / 2, "侧板 L"),
        (xmid(gd["X3"], gd["X4"]), gd["Y1"] / 2, "端板 W"),
        (xmid(gd["X4"], gd["X5"]), gd["Y1"] / 2, "侧板 L"),
        (xmid(gd["X1"], gd["X2a"]), gd["Y1"] + p.fi * 0.5, "内摇盖"),
        (xmid(gd["X2b"], gd["X3a"]), gd["Y1"] + p.fo * 0.5, "外摇盖"),
        (xmid(gd["X3b"], gd["X4a"]), gd["Y1"] + p.fi * 0.5, "内摇盖"),
        (xmid(gd["X4b"], gd["X5"]), gd["Y1"] + p.fo * 0.5, "外摇盖"),
        (xmid(gd["X1"], gd["X2a"]), gd["Y0"] - p.fi * 0.5, "内摇盖"),
        (xmid(gd["X2b"], gd["X3a"]), gd["Y0"] - p.fo * 0.5, "外摇盖"),
        (xmid(gd["X3b"], gd["X4a"]), gd["Y0"] - p.fi * 0.5, "内摇盖"),
        (xmid(gd["X4b"], gd["X5"]), gd["Y0"] - p.fo * 0.5, "外摇盖"),
    ]
    # 板面字：条带在图纸上放不下就不画（窄粘舌/薄端板在 1:15 时只剩 3mm）
    _areas = {"粘舌": gd["X1"] - gd["X0"], "端板 W": gd["X2"] - gd["X1"],
              "侧板 L": gd["X3"] - gd["X2"], "内摇盖": p.fi, "外摇盖": p.fo}
    for (lx, ly, s) in labels:
        sx, sy = T(lx, ly)
        _put(ax, sx, sy, s, _areas.get(s, 999.0) / scale, 6.2)

    # dimension chains
    yb = oy - 8.0
    chain_x = [gd["X0"], gd["X1"], gd["X2"], gd["X3"], gd["X4"], gd["X5"]]
    for i in range(5):
        dim_h(ax, T(chain_x[i], 0)[0], T(chain_x[i + 1], 0)[0], yb, g(chain_x[i + 1] - chain_x[i]))
    dim_h(ax, T(chain_x[0], 0)[0], T(chain_x[-1], 0)[0], yb - 9.0,
          "展开长 " + g(chain_x[-1] - chain_x[0]))

    xl = ox - 8.0
    chain_y = [gd["Yb_o"], gd["Y0"], gd["Y1"], gd["Yt_o"]]
    for i in range(3):
        dim_v(ax, T(0, chain_y[i])[1], T(0, chain_y[i + 1])[1], xl, g(chain_y[i + 1] - chain_y[i]))
    dim_v(ax, T(0, chain_y[0])[1], T(0, chain_y[-1])[1], xl - 10.0,
          "展开宽 " + g(chain_y[-1] - chain_y[0]))

    # callouts: inner flap depth + slot width
    dim_v(ax, T(0, gd["Y1"])[1], T(0, gd["Yt_i"])[1], T(gd["X2a"] - 45, 0)[0], "内摇盖深 " + g(p.fi))
    dim_h(ax, T(gd["X4a"], 0)[0], T(gd["X4b"], 0)[0], T(0, gd["Yt_o"])[1] + 6.0, "开槽宽 " + g(p.slot_w))

    # title
    ax.text(pw / 2, ph - 20, meta.get("title", "FEFCO 0201 标准开槽箱（RSC）· 展开图（刀模图）"),
            ha="center", va="center", fontsize=13, fontweight="bold")
    ax.text(pw / 2, ph - 27,
            meta.get("caption",
                     f"{g(p.t)} mm 纸板 · 外尺寸 {g(p.L)}×{g(p.W)}×{g(p.H)} · {scale_tag(scale, not manual)}"
                     f" · 单位 mm · {_today()} · 生成：{author}"),
            ha="center", va="center", fontsize=8)

    # legend + notes (bottom-left, under the dieline)
    ax.text(38.0, 89.0, f"图例：实线 = 裁切切口；虚线 = 压线（折痕）；尺寸单位 mm；图样比例 = 纸上 1:{scale:g}",
            ha="left", va="top", fontsize=6.8, color="0.0", fontweight="bold")
    lines = meta.get("param_lines") or param_lines_zh(p, info, meta.get("mat", "BC 双瓦楞纸板"))
    for i, s in enumerate(lines):
        ax.text(38.0, 84.0 - i * 4.0, s, ha="left", va="top", fontsize=6.4, color="0.1")

    ax.text(38.0, 14.0, f"字体：{fam}（{fpath or 'fallback'}）", fontsize=5.2, color="0.45")

    # isometric views (right column)
    from box0210_3d import add_iso_panels, build_items_from
    if items_closed is None:
        from box0201_core import panels as p201
        items_closed = build_items_from(p201(p), False)
    if items_open is None:
        from box0201_core import panels as p201
        from box0201_core import open_items as o201
        items_open = o201(build_items_from(p201(p), True), p)
    add_iso_panels(fig, items_closed, items_open,
                   cap1="闭合状态（等轴测）", cap2="开盖状态（内短摇盖已合、平齐箱口）\n外长摇盖开启——合盖顺序：先内短、后外长）")
    from dwgframe import draw_frame
    draw_frame(fig, page=page,
               name=meta.get("dwg_name") or meta.get("name") or f"FEFCO 0201 开槽箱（RSC）{p.L:g}×{p.W:g}×{p.H:g}",
               material=meta.get("dwg_material") or meta.get("material") or f"BC 双瓦楞 t={p.t:g}（可折叠）",
               dwgno=meta.get("dwg_no") or meta.get("dwgno") or "0201-BC-400x300x200",
               version=meta.get("dwg_version") or "A",
               scale_str=scale_str(scale), sheet="A3",
               company=meta.get("company", "上海银轮热交换系统有限公司"),
               designed=meta.get("designed", ""), drawn=meta.get("drawn", ""),
               proofed=meta.get("proofed", ""), checked=meta.get("checked", ""),
               process=meta.get("process", ""), standard=meta.get("standard", ""),
               approved=meta.get("approved", ""), date=meta.get("date", ""))
    return fig


if __name__ == "__main__":
    import sys
    p = Params()
    outdir = sys.argv[1] if len(sys.argv) > 1 else r"D:/Tools/tmp/fefco0210_build/out0201"
    os.makedirs(outdir, exist_ok=True)
    dxf = write_dxf(p, os.path.join(outdir, "01_展开图_dieline_1-1.dxf"))
    print("DXF:", dxf, os.path.getsize(dxf), "bytes")
    fig = build_sheet(p)
    for f in save_sheet_png_svg(fig, os.path.join(outdir, "01_展开图-2D带标注_A3")):
        print("SHEET:", f, os.path.getsize(f), "bytes")
