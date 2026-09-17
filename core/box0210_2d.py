# -*- coding: utf-8 -*-
"""FEFCO 0210 - 2D outputs: DXF (1:1) + A3 drawing sheet (matplotlib fig)."""
import os
import math

from box0210_core import Params, dieline, layout, report


# ---------------------------------------------------------------- DXF (1:1 mm)
def write_dxf(p: Params, dxf_path: str):
    import ezdxf
    outline, creases, info = dieline(p)
    doc = ezdxf.new("R2010", setup=True)
    doc.header["$INSUNITS"] = 4          # mm
    doc.layers.add("CUT", color=1, lineweight=35)                    # red solid
    doc.layers.add("CREASE", color=5, linetype="DASHED", lineweight=18)  # blue dashed
    doc.layers.add("NOTES", color=7)
    msp = doc.modelspace()
    msp.add_lwpolyline([(x, y, b) for x, y, b in outline], format="xyb",
                       close=True, dxfattribs={"layer": "CUT"})
    for a, b in creases:
        msp.add_line(a, b, dxfattribs={"layer": "CREASE"})
    y_notes = -p.lid_depth - p.tuck_depth - 12.0
    notes = [
        "FEFCO 0210 straight tuck carton / BC double wall t=7.0 / units mm / scale 1:1",
        f"Outer {p.L:g}x{p.W:g}x{p.H:g}  Inner {p.Li:g}x{p.Wi:g}x{p.Hi:g}  Mfr {p.Lm:g}x{p.Wm:g}x{p.Hm:g}",
        f"Blank {info['blank_w']:g}x{info['blank_h']:g}   CUT layer = through cut, CREASE layer = score (dashed)",
        "Origin = band lower-left (back panel bottom-left).  Allowances per public FEFCO 0210 dielines;",
        "no factory correction factors applied (edit parameters to adapt).",
    ]
    for i, s in enumerate(notes):
        msp.add_text(s, height=5.5, dxfattribs={"layer": "NOTES"}).set_placement((0.0, y_notes - i * 9.0))
    doc.saveas(dxf_path)
    return dxf_path


# ---------------------------------------------------------------- sheet helpers
def _font_family():
    from matplotlib import font_manager
    import matplotlib.pyplot as plt
    for fp in ("C:/Windows/Fonts/msyh.ttc", "C:/Windows/Fonts/simhei.ttf",
               "C:/Windows/Fonts/simsun.ttc"):
        if os.path.exists(fp):
            try:
                font_manager.fontManager.addfont(fp)
                name = font_manager.FontProperties(fname=fp).get_name()
                plt.rcParams["font.sans-serif"] = [name, "DejaVu Sans"]
                plt.rcParams["axes.unicode_minus"] = False
                return name, fp
            except Exception:
                continue
    return "DejaVu Sans", None


def dim_h(ax, x1, x2, y, text="", off=2.0, fs=6.5, color="k"):
    ax.annotate("", xy=(x1, y), xytext=(x2, y),
                arrowprops=dict(arrowstyle="<|-|>", color=color, lw=0.5,
                                mutation_scale=5, shrinkA=0, shrinkB=0))
    if text:
        ax.text((x1 + x2) / 2.0, y + off, text, ha="center", va="bottom", fontsize=fs,
                color=color, bbox=dict(fc="white", ec="none", pad=0.4))


def dim_v(ax, y1, y2, x, text="", off=2.0, fs=6.5, color="k"):
    ax.annotate("", xy=(x, y1), xytext=(x, y2),
                arrowprops=dict(arrowstyle="<|-|>", color=color, lw=0.5,
                                mutation_scale=5, shrinkA=0, shrinkB=0))
    if text:
        ax.text(x + off, (y1 + y2) / 2.0, text, ha="left", va="center",
                fontsize=fs, color=color, rotation=90,
                bbox=dict(fc="white", ec="none", pad=0.4))


def g(v):
    return f"{v:g}"


def _today():
    import datetime
    return datetime.date.today().isoformat()


def param_lines_zh(p: Params, info: dict):
    return [
        f"箱型：FEFCO 0210 直插式双插盒（straight tuck carton，上下同侧翻盖+插舌）",
        f"材料：BC 双瓦楞纸板  t = {g(p.t)} mm（参考 GB/T 6544，成箱后约等于楞高）",
        f"外尺寸 L×W×H：{g(p.L)} × {g(p.W)} × {g(p.H)} mm（题给）",
        f"内尺寸：{g(p.Li)} × {g(p.Wi)} × {g(p.Hi)} mm   制造尺寸：{g(p.Lm)} × {g(p.Wm)} × {g(p.Hm)} mm",
        f"换算口径：内 = 外 − 2t；制造 = 内 + t（可参数化替换厂方修正系数）",
        f"盖板深 {g(p.lid_depth)}；插舌深 {g(p.tuck_depth)}、宽 {g(p.tuck_w)}、圆角 R{g(p.tuck_r)}",
        f"防尘翼：深 {g(p.dust_depth)} × 长 {g(p.dust_len)}（每侧让边 {g(p.dust_clr)}）",
        f"粘舌：{g(p.glue_w)} 宽（双瓦楞常用 45–50）",
        f"展开尺寸：{g(info['blank_w'])} × {g(info['blank_h'])} mm，用纸面积 {info['blank_w'] * info['blank_h'] / 1e6:.4f} m²",
        "楞向：平行箱高（竖向）——按 0210 惯例",
        "注：插舌盒配双瓦楞（7mm）属非常规组合，插舌易卡涩，量产后建议实测手感；",
        "　　几何为公开标准口径（FEFCO 0210 / 市面公开刀模图），未含厂方工艺修正。",
    ]


def build_dieline_sheet(p: Params, scale: float = 6.0, page=(420.0, 297.0),
                        items_closed=None, items_open=None):
    """A3 combined sheet: 1:scale dieline (left) + isometric views (right) + notes."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fam, fpath = _font_family()
    outline, creases, info = dieline(p)

    pw, ph = page
    fig = plt.figure(figsize=(pw / 25.4, ph / 25.4))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, pw)
    ax.set_ylim(0, ph)
    ax.set_aspect("equal")
    ax.axis("off")

    xmin = min(pt[0] for pt in outline)
    xmax = max(pt[0] for pt in outline)
    ymin = min(pt[1] for pt in outline)
    ymax = max(pt[1] for pt in outline)
    dw, dh = (xmax - xmin) / scale, (ymax - ymin) / scale
    ox = 35.0 + (277.0 - dw) / 2.0
    oy = 100.0 + (168.0 - dh) / 2.0
    T = lambda x, y: (ox + (x - xmin) / scale, oy + (y - ymin) / scale)

    # --- cut outline (solid) with arc bulge handling ---
    pts = []
    n = len(outline)
    for i in range(n):
        x0, y0, b = outline[i]
        x1, y1, _ = outline[(i + 1) % n]
        pts.append((x0, y0))
        if abs(b) > 1e-9:
            # quarter arcs only (all our bulges are +-tan(22.5deg))
            d = 4.0 * math.atan(b)          # signed sweep
            r = math.hypot(x1 - x0, y1 - y0) / (2.0 * math.sin(abs(d) / 2.0))
            # center: perpendicular offset from chord midpoint
            mx, my = (x0 + x1) / 2.0, (y0 + y1) / 2.0
            # chord direction
            cx, cy = (x1 - x0), (y1 - y0)
            L = math.hypot(cx, cy)
            # distance from chord midpoint to center
            h = math.sqrt(max(r * r - (L / 2.0) ** 2, 0.0))
            # normal direction
            nx, ny = -cy / L, cx / L
            # choose the side: for bulge>0 (CCW) center is left of chord
            sgn = 1.0 if d > 0 else -1.0
            ccx, ccy = mx + sgn * h * nx, my + sgn * h * ny
            t0 = math.atan2(y0 - ccy, x0 - ccx)
            t1 = math.atan2(y1 - ccy, x1 - ccx)
            if d > 0:
                while t1 < t0:
                    t1 += 2 * math.pi
            else:
                while t1 > t0:
                    t1 -= 2 * math.pi
            steps = 10
            for k in range(1, steps + 1):
                t = t0 + (t1 - t0) * k / steps
                pts.append((ccx + r * math.cos(t), ccy + r * math.sin(t)))
    sp = [T(x, y) for x, y in pts]
    sp.append(sp[0])  # close the outline (last vertex -> first vertex rim segment)
    ax.plot([q[0] for q in sp], [q[1] for q in sp], color="k", lw=0.7, solid_joinstyle="round")

    # --- creases (dashed) ---
    for (a, b) in creases:
        (xa, ya), (xb, yb) = T(*a), T(*b)
        ax.plot([xa, xb], [ya, yb], color="k", lw=0.45, ls=(0, (4, 2.4)))

    # --- panel / flap labels ---
    gd = layout(p)
    xmid = lambda a, b: (a + b) / 2.0
    labels = [
        (xmid(gd["X0"], gd["X1"]), gd["Y1"] / 2, "粘舌"),
        (xmid(gd["X1"], gd["X2"]), gd["Y1"] / 2, "背板 L"),
        (xmid(gd["X2"], gd["X3"]), gd["Y1"] / 2, "侧板 W"),
        (xmid(gd["X3"], gd["X4"]), gd["Y1"] / 2, "正面板 L"),
        (xmid(gd["X4"], gd["X5"]), gd["Y1"] / 2, "侧板 W"),
        (xmid(gd["X1"], gd["X2"]), gd["Y1"] + p.lid_depth * 0.5, "上盖板"),
        (xmid(gd["X1"], gd["X2"]), gd["Yt_lid"] + p.tuck_depth * 0.5, "插舌"),
        (xmid(gd["X1"], gd["X2"]), gd["Y0"] - p.lid_depth * 0.5, "下盖板"),
        (xmid(gd["X1"], gd["X2"]), gd["Yb_lid"] - p.tuck_depth * 0.5, "插舌"),
        (xmid(gd["dl0"], gd["dl1"]), gd["Y1"] + p.dust_depth * 0.5, "防尘翼"),
        (xmid(gd["dl0"], gd["dl1"]), gd["Y0"] - p.dust_depth * 0.5, "防尘翼"),
        (xmid(gd["dr0"], gd["dr1"]), gd["Y1"] + p.dust_depth * 0.5, "防尘翼"),
        (xmid(gd["dr0"], gd["dr1"]), gd["Y0"] - p.dust_depth * 0.5, "防尘翼"),
    ]
    for (lx, ly, s) in labels:
        sx, sy = T(lx, ly)
        ax.text(sx, sy, s, ha="center", va="center", fontsize=6.2, color="0.15")

    # --- dimension chains ---
    yb = oy - 8.0
    xs = gd
    chain_x = [xs["X0"], xs["X1"], xs["X2"], xs["X3"], xs["X4"], xs["X5"]]
    for i in range(5):
        x1, x2 = T(chain_x[i], 0)[0], T(chain_x[i + 1], 0)[0]
        v = chain_x[i + 1] - chain_x[i]
        dim_h(ax, x1, x2, yb, g(v))
    tx1, tx2 = T(chain_x[0], 0)[0], T(chain_x[-1], 0)[0]
    dim_h(ax, tx1, tx2, yb - 9.0, "展开长 " + g(chain_x[-1] - chain_x[0]))

    xl = ox - 8.0
    chain_y = [xs["Yb_bot"], xs["Yb_lid"], xs["Y0"], xs["Y1"], xs["Yt_lid"], xs["Yt_top"]]
    for i in range(5):
        y1, y2 = T(0, chain_y[i])[1], T(0, chain_y[i + 1])[1]
        v = chain_y[i + 1] - chain_y[i]
        dim_v(ax, y1, y2, xl, g(v))
    ty1, ty2 = T(0, chain_y[0])[1], T(0, chain_y[-1])[1]
    dim_v(ax, ty1, ty2, xl - 10.0, "展开宽 " + g(chain_y[-1] - chain_y[0]))

    # tuck width + dust length callouts
    ytop = T(0, xs["Yt_top"])[1]
    dim_h(ax, T(gd["Xt0"], 0)[0], T(gd["Xt1"], 0)[0], ytop + 6.0, "插舌宽 " + g(p.tuck_w))
    dim_h(ax, T(gd["dl0"], 0)[0], T(gd["dl1"], 0)[0], T(0, xs["Ydt"])[1] + 6.0, "防尘翼长 " + g(p.dust_len))
    ax.text(T(gd["Xt0"] + 3, xs["Yt_top"] - 3)[0], T(0, xs["Yt_top"] - 3)[1] - 4, f"R{g(p.tuck_r)}",
            fontsize=6, color="0.25")
    # tuck depth / dust depth callouts (right side of blank)
    dim_v(ax, T(0, xs["Yt_lid"])[1], T(0, xs["Yt_top"])[1], T(gd["Xt1"] + 14, 0)[0], "插舌深 " + g(p.tuck_depth))
    dim_v(ax, T(0, xs["Y1"])[1], T(0, xs["Ydt"])[1], T(gd["dr1"] + 12, 0)[0], "防尘翼深 " + g(p.dust_depth))

    # --- title ---
    ax.text(pw / 2, ph - 14, "FEFCO 0210 直插式双插盒 · 展开图（刀模图）", ha="center", va="center",
            fontsize=13, fontweight="bold")
    ax.text(pw / 2, ph - 22,
            f"BC 双瓦楞 t={g(p.t)} · 外尺寸 {g(p.L)}×{g(p.W)}×{g(p.H)} · 比例 1:{scale:g} · 单位 mm · {_today()} · 生成：ZCode 参数化管线",
            ha="center", va="center", fontsize=8)

    # --- legend + notes block (bottom-left, under the dieline) ---
    ax.text(38.0, 89.0, f"图例：实线 = 裁切切口；虚线 = 压线（折痕）；尺寸单位 mm；图样比例 = 纸上 1:{scale:g}",
            ha="left", va="top", fontsize=6.8, color="0.0", fontweight="bold")
    lines = param_lines_zh(p, info)
    y0 = 84.0
    for i, s in enumerate(lines):
        ax.text(38.0, y0 - i * 4.0, s, ha="left", va="top", fontsize=6.4, color="0.1")

    ax.text(38.0, 6.5, f"字体：{fam}（{fpath or 'fallback'}）", fontsize=5.2, color="0.45")

    # --- isometric views (right column) ---
    from box0210_3d import add_iso_panels, build_items
    from box0210_core import open_items
    if items_closed is None:
        items_closed = build_items(p, False)
    if items_open is None:
        items_open = open_items(build_items(p, True), p)
    add_iso_panels(fig, items_closed, items_open,
                   cap1="闭合状态（等轴测）", cap2="开盖状态（上盖板+插舌开启 110°）\n防尘翼已合、平齐箱口）")
    from dwgframe import draw_frame
    draw_frame(fig, page=page, name=f"FEFCO 0210 直插式双插盒 {p.L:g}×{p.W:g}×{p.H:g}",
               material=f"BC 双瓦楞 t={p.t:g}（可折叠）", dwgno="0210-BC-400x300x200",
               scale_str=f"1:{scale:g}", sheet="A3")
    return fig


def save_sheet_png_svg(fig, basepath: str, dpi: int = 200):
    out = []
    for ext in ("png", "svg"):
        fp = f"{basepath}.{ext}"
        fig.savefig(fp, dpi=dpi)
        out.append(fp)
    return out


if __name__ == "__main__":
    import sys
    p = Params()
    outdir = sys.argv[1] if len(sys.argv) > 1 else r"D:/Tools/tmp/fefco0210_build/out"
    os.makedirs(outdir, exist_ok=True)
    dxf = write_dxf(p, os.path.join(outdir, "0210_BC_dieline.dxf"))
    print("DXF:", dxf, os.path.getsize(dxf), "bytes")
    fig = build_dieline_sheet(p)
    files = save_sheet_png_svg(fig, os.path.join(outdir, "0210_sheet1_dieline"))
    for f in files:
        print("SHEET:", f, os.path.getsize(f), "bytes")
