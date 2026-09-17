# -*- coding: utf-8 -*-
"""仿形块 A3 合成图（图框 + 第一角三视图 + 轴测图 + 技术要求）。

三视图：主视图（L×H，槽口朝上）在上；俯视图（L×W，槽布置）在下（长对正）；
左视图（W×H，槽剖面）在主视图右侧（高平齐）。
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from dwgframe import draw_frame
from box0210_2d import dim_h, dim_v, _font_family, save_sheet_png_svg, _today
from box0210_3d import draw_scene
from block_model import items as model_items, draw_axo_clean
from drawutil import scale_str as _scale_str, scale_tag as _scale_tag, SCALES as _SCALES_ALL

SCALES = _SCALES_ALL          # 含放大档（0.2/0.5 → 5:1/2:1）


def _pick(L, avail):
    for dd in SCALES:
        if L / dd <= avail:
            return dd
    return SCALES[-1]


def build_sheet(p, d, page=(420.0, 297.0), meta: dict = None, scale: float = None):
    meta = meta or {}
    author = meta.get("author", "包装周哥")
    manual = scale is not None and float(scale) > 0
    fam, fpath = _font_family()
    fig = plt.figure(figsize=(page[0] / 25.4, page[1] / 25.4))
    # 版面约束：横向 L*s+16+W*s ≤ 244（避开轴测列 292）；纵向 H*s ≤ 56、W*s ≤ 86（避开注释块）
    if manual:
        sc = float(scale)
    else:
        # 三条约束都要满足 → 取**最大**分母（最小图），不是 min
        #   横向：主视图 L + 16 + 左视图 W ≤ 244mm
        #   上界：主视图高 H + 标注带 ≤ 48mm（FY=212，上界 272）
        #   下界：俯视图宽 W ≤ 86mm（保证注释块落在 y≥20）
        sc = max(_pick(p.L + 16 + p.W, 244.0), _pick(p.H, 48.0), _pick(p.W, 86.0))
    fig._scale_used, fig._scale_auto = sc, not manual
    draw_frame(fig, page=page,
               name=meta.get("dwg_name") or f"{p.name} {p.L:g}×{p.W:g}×{p.H:g}",
               material=meta.get("dwg_material") or (p.material or "—"),
               dwgno=meta.get("dwg_no") or f"BLK-{p.L:g}x{p.W:g}x{p.H:g}",
               version=meta.get("dwg_version") or "A",
               scale_str=_scale_str(sc), sheet="A3",
               company=meta.get("company", "上海银轮热交换系统有限公司"),
               designed=meta.get("designed", ""), drawn=meta.get("drawn", ""),
               proofed=meta.get("proofed", ""), checked=meta.get("checked", ""),
               process=meta.get("process", ""), standard=meta.get("standard", ""),
               approved=meta.get("approved", ""), date=meta.get("date", ""))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, page[0]); ax.set_ylim(0, page[1]); ax.axis("off")
    ax.set_zorder(10); ax.patch.set_alpha(0.0)

    s = 1.0 / sc
    Lv, Wv, Hv = p.L * s, p.W * s, p.H * s
    FX = 42.0 + max(0.0, (244.0 - (p.L + 16 + p.W) / sc) / 2.0)   # 主视图原点（左下），横向居中
    FY = 212.0
    TY = FY - 14.0 - Wv                       # 俯视图原点（长对正）

    def Tf(x, y): return (FX + x * s, FY + y * s)
    def Tt(x, y): return (FX + x * s, TY + y * s)
    def Tq(w, h): return (FX + Lv + 16.0 + (p.W - w) * s, FY + h * s)   # 第一角：左视图“前”在右

    # ---- 主视图 ----
    if d["through"]:
        pts = [(0, 0), (p.L, 0), (p.L, p.H)]
        for (a, b) in reversed(d["slots"]):
            pts += [(b, p.H), (b, p.H - p.sh), (a, p.H - p.sh), (a, p.H)]
        pts += [(0, p.H), (0, 0)]
        ax.plot(*zip(*[Tf(x, y) for x, y in pts]), color="k", lw=0.8)
    else:
        rect = [(0, 0), (p.L, 0), (p.L, p.H), (0, p.H), (0, 0)]
        ax.plot(*zip(*[Tf(x, y) for x, y in rect]), color="k", lw=0.8)
        ls = "-" if p.open_side != "back" else (0, (4, 3))
        for (a, b) in d["slots"]:
            ax.plot(*zip(*[Tf(x, y) for x, y in
                           [(a, p.H), (a, p.H - p.sh), (b, p.H - p.sh), (b, p.H)]]),
                    color="k", lw=0.8, linestyle=ls)
    dim_h(ax, Tf(0, p.H + 12)[0], Tf(p.L, p.H + 12)[0], Tf(0, p.H + 12)[1], f"{p.L:g}", fs=7)
    dim_v(ax, Tf(0, 0)[1], Tf(0, p.H)[1], Tf(-20, 0)[0], f"{p.H:g}", fs=7, off=-0.6)
    s0 = d["slots"][0]
    dim_h(ax, Tf(s0[0], p.H + 26)[0], Tf(s0[1], p.H + 26)[0], Tf(0, p.H + 26)[1], f"{p.sl:g}", fs=7)
    ax.text(Tf(p.L / 2, 0)[0], Tf(0, 0)[1] - 2.6, "主视图", fontsize=8, ha="center", va="top")

    # ---- 俯视图：槽位布置 + 边距 ----
    ax.plot(*zip(Tt(0, 0), Tt(p.L, 0), Tt(p.L, p.W), Tt(0, p.W), Tt(0, 0)), color="k", lw=0.8)
    for (a, b) in d["slots"]:
        if d["through"]:
            y0r, y1r = 0.0, p.W
        else:
            y0r, y1r = d["sy0"], d["sy1"]
        ax.add_patch(plt.Rectangle(Tt(a, y0r), (b - a) * s, (y1r - y0r) * s,
                                   facecolor="0.8", edgecolor="k", lw=0.7, zorder=11))
    yb = Tt(0, -10)[1]
    dim_h(ax, Tt(0, -10)[0], Tt(d["margin_l"], -10)[0], yb, f"{d['margin_l']:g}", fs=7, off=-3.0)
    a0, b0 = d["slots"][0]
    dim_h(ax, Tt(a0, -10)[0], Tt(b0, -10)[0], yb, f"{p.sl:g}", fs=7, off=-6.5)
    dim_h(ax, Tt(b0, -10)[0], Tt(b0 + p.gap, -10)[0], yb, f"{p.gap:g}", fs=7, off=-3.0)
    dim_h(ax, Tt(0, -58)[0], Tt(p.L, -58)[0], Tt(0, -58)[1], f"{p.L:g}", fs=7, off=-2.6)
    dim_v(ax, Tt(0, 0)[1], Tt(0, p.W)[1], Tt(-20, 0)[0], f"{p.W:g}", fs=7, off=-0.6)
    if not d["through"]:
        dim_v(ax, Tt(b0 - 4, d["sy0"])[1], Tt(b0 - 4, d["sy1"])[1], Tt(b0 - 4, 0)[0], f"{p.sw:g}", fs=6.4, off=1.5)
    ax.text(Tt(p.L / 2, 0)[0], Tt(0, 0)[1] - 2.6, f"俯视图（开槽 {d['n']} 个 · 间距 {p.gap:g}）",
            fontsize=8, ha="center", va="top")

    # ---- 左视图（第一角，前=右侧）：外形全高 W×H；槽为后置隐藏轮廓（虚线） ----
    rect = [(0, 0), (p.W, 0), (p.W, p.H), (0, p.H), (0, 0)]
    ax.plot(*zip(*[Tq(w, h) for w, h in rect]), color="k", lw=0.8)
    if d["through"]:
        ax.plot(*zip(Tq(0, p.H - p.sh), Tq(p.W, p.H - p.sh)),
                color="k", lw=0.7, linestyle=(0, (4, 3)))
    elif p.open_side == "back":
        ax.plot(*zip(*[Tq(w, h) for w, h in
                       [(p.W, p.H - p.sh), (d["sy0"], p.H - p.sh), (d["sy0"], p.H)]]),
                color="k", lw=0.7, linestyle=(0, (4, 3)))
    else:
        ax.plot(*zip(*[Tq(w, h) for w, h in
                       [(0, p.H - p.sh), (d["sy1"], p.H - p.sh), (d["sy1"], p.H)]]),
                color="k", lw=0.7, linestyle=(0, (4, 3)))
    dim_v(ax, Tq(0, 0)[1], Tq(0, p.H)[1], Tq(-22, 0)[0], f"{p.H:g}", fs=7, off=-0.6)
    dim_v(ax, Tq(0, p.H)[1], Tq(0, p.H - p.sh)[1], Tq(d["sw_eff"] / 2, 0)[0], f"{p.sh:g}", fs=6.4, off=1.5)
    dim_h(ax, Tq(0, p.H + 12)[0], Tq(p.W, p.H + 12)[0], Tq(0, p.H + 12)[1], f"{p.W:g}", fs=7)
    ax.text(Tq(p.W / 2, 0)[0], Tq(0, 0)[1] - 2.6, "左视图", fontsize=8, ha="center", va="top")

    # ---- 技术要求 ----
    notes = [
        "技术要求：",
        f"1. 垫块 {p.L:g}×{p.W:g}×{p.H:g}；开槽 {p.sl:g}×{p.sw:g}×{p.sh:g} × {d['n']} 个；相邻槽间距 {p.gap:g}；",
        f"2. 槽型：{'全贯穿（槽宽 = 块宽）' if d['through'] else f'单边贯穿——{"前" if p.open_side != "back" else "后"}侧开口，对侧墙厚 {d["side_wall"]:g}'}；槽深 {p.sh:g}（自顶面）；",
        f"3. 边距：{d['margin_mode']} —— 左 {d['margin_l']:g} / 右 {d['margin_r']:g}"
        f"（剩余总量 {d['margin_total']:g}，均分参考 {d['margin_even']:g}）；",
        f"4. 槽数算法：n = ROUNDDOWN((块长+间距)/(槽长+间距)) = {d['n']}；",
        "5. 未注圆角 R2、外形棱边去毛刺；未注公差按 GB/T 1804-m。",
    ]
    if p.material:
        notes.append(f"6. 材质：{p.material}。")
    ax.text(page[0] / 2, page[1] - 20, f"{p.name} · 三视图 + 轴测图（第一角）",
            fontsize=13, fontweight="bold", ha="center", va="center")
    ax.text(page[0] / 2, page[1] - 27,
            f"{p.L:g}×{p.W:g}×{p.H:g} mm · 槽 {p.sl:g}×{p.sw:g}×{p.sh:g} ×{d['n']} · "
            f"{_scale_tag(sc, not manual)} · 单位 mm · {_today()} · 生成：{author}",
            fontsize=8, ha="center", va="center", color="0.15")
    y0 = TY - 40.0
    for i, line in enumerate(notes):
        ax.text(42.0, y0 - i * 7.4, line, fontsize=6.8, color="0.12")

    # ---- 轴测图 ----
    ax2 = fig.add_axes([0.615, 0.26, 0.35, 0.34])
    draw_axo_clean(ax2, model_items(p, d))
    ax2.set_title("轴测图", fontsize=8)
    return fig


def render_axo(p, d, basepath, dpi=300):
    fig = plt.figure(figsize=(150 / 25.4, 115 / 25.4))
    ax = fig.add_axes([0.02, 0.06, 0.96, 0.88])
    draw_axo_clean(ax, model_items(p, d))
    ax.set_title(f"{p.name} {p.L:g}×{p.W:g}×{p.H:g} · 槽 {p.sl:g}×{p.sw:g}×{p.sh:g} ×{d['n']} · 轴测图",
                 fontsize=9)
    out = []
    for ext in ("png", "svg"):
        fp = f"{basepath}.{ext}"
        fig.savefig(fp, dpi=dpi)
        out.append(fp)
    plt.close(fig)
    return out
