# -*- coding: utf-8 -*-
"""刀卡网格 A3 合成图（版式仿公司参考图纸）：图框 + 网格俯视图 + 短卡侧视图（旋转 90°）
+ 长卡侧视图 + 技术要求 + 轴测图（单层格架）。

参考版式（地平线 XG盖板 SNP24 图纸）：
  A 俯视图（左上）：刀卡全长伸至箱壁；槽距端边 = 边距
  B 侧视图一（右上）：短板卡旋转 90°（高横向、长竖向、槽口朝左），标注 高 / 槽深
  C 侧视图二（左下）：长刀卡自然向（长横向、高竖向、槽自顶向下），标注 高 / 槽深
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from dwgframe import draw_frame
from box0210_2d import dim_h, dim_v, _font_family, save_sheet_png_svg, _today
from box0210_3d import draw_scene
from grid_core import PAD_LABEL
from grid_model import items as model_items, _slot_centers


def _slots(margin, n, pitch, t):
    return _slot_centers(margin, n, pitch, t)


def build_sheet(p, d, scale=None, page=(420.0, 297.0), meta: dict = None):
    meta = meta or {}
    author = meta.get("author", "包装周哥")
    manual = scale is not None and float(scale) > 0
    from drawutil import scale_str as _ss, scale_tag as _st, pick_scale as _ps, SCALES as _SC
    if manual:
        scale = float(scale)
    else:
        t_, Hc_ = d["t"], d["cell_h"]
        s_w = _ps(p.L + Hc_, 1.0, 192.0, 1e9, _SC)              # 横向：L+Hc ≤ 192
        s_h = _ps(1.0, p.W + Hc_ + 38.0, 1e9, 149.4, _SC)       # 纵向：W+Hc+38 侧位余量
        scale = max(s_w, s_h)
    fam, fpath = _font_family()
    fig = plt.figure(figsize=(page[0] / 25.4, page[1] / 25.4))
    vtxt = "V1 长对长" if d["version"] == 1 else "V2 长对宽"
    draw_frame(fig, page=page, name=f"瓦楞刀卡网格 {p.L:g}×{p.W:g}×{p.H:g} · {vtxt}",
               material=(f"刀卡 t={d['t']:g}" if abs(d.get('st', d['t']) - d['t']) < 1e-9
                         else f"刀卡 t={d['t']:g} / 隔板 t={d.get('st', d['t']):g}") + "（可折叠）",
               dwgno=f"GRID-{p.L:g}x{p.W:g}x{p.H:g}-V{d['version']}",
               scale_str=_ss(scale), sheet="A3",
               company=meta.get("company", "上海银轮热交换系统有限公司"),
               designed=meta.get("designed", ""), drawn=meta.get("drawn", ""),
               checked=meta.get("checked", ""), approved=meta.get("approved", ""))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, page[0])
    ax.set_ylim(0, page[1])
    ax.axis("off")
    ax.set_zorder(10)
    ax.patch.set_alpha(0.0)
    s = 1.0 / scale
    t, Hc = d["t"], d["cell_h"]
    fig._scale_used, fig._scale_auto = scale, not manual
    TOP = 264.0 - 36.0 * s                 # B 视图上方两条尺寸线占位
    ROW1 = TOP - p.W * s                   # 俯视图/短卡视图底边
    ROW2 = ROW1 - 24.0 - Hc * s            # 长卡视图底边（含俯视图标注带）

    def mk(ox, oy):
        return lambda x, y: (ox + x * s, oy + y * s)

    # ---------------- A 俯视图（左上） ----------------
    PLX, PLY = 48.0, ROW1
    T = mk(PLX, PLY)
    xs_l = _slots(d["margin_l"], d["slots_long"], d["pitch_l"], t)
    ys_w = _slots(d["margin_w"], d["slots_short"], d["pitch_w"], t)
    def line(a, b, horiz, fx):
        (x0, y0), (x1, y1) = (T(a, fx), T(b, fx)) if horiz else (T(fx, a), T(fx, b))
        ax.plot([x0, x1], [y0, y1], color="k", lw=0.7, zorder=11)
    # 长卡（上开槽）：棱线在交叉处断开（槽口），两端封口（板厚 5）
    for yc in ys_w:
        for e in (yc - t / 2, yc + t / 2):
            prev = 0.0
            for xc in xs_l:
                line(prev, xc - t / 2, True, e); prev = xc + t / 2
            line(prev, p.L, True, e)
        line(yc - t / 2, yc + t / 2, False, 0.0)      # 左端封口
        line(yc - t / 2, yc + t / 2, False, p.L)      # 右端封口
    # 短卡（下开槽）：俯视棱线连续（上表面完整），两端封口
    for xc in xs_l:
        for e in (xc - t / 2, xc + t / 2):
            line(0.0, p.W, False, e)
        line(xc - t / 2, xc + t / 2, True, 0.0)
        line(xc - t / 2, xc + t / 2, True, p.W)
    dim_h(ax, T(0, p.W + 22)[0], T(p.L, p.W + 22)[0], T(0, p.W + 22)[1], f"{p.L:g}", off=1.5)
    dim_v(ax, T(0, 0)[1], T(0, p.W)[1], T(-26, 0)[0], f"{p.W:g}", off=1.5)
    yb = T(0, p.W + 6)[1]
    dim_h(ax, T(0, p.W + 6)[0], T(d["margin_l"], p.W + 6)[0], yb, f"{d['margin_l']:g}")
    dim_h(ax, T(d["margin_l"], p.W + 6)[0], T(d["margin_l"] + t, p.W + 6)[0], yb, f"{t:g}", off=4.5)
    dim_h(ax, T(d["margin_l"] + t, p.W + 6)[0], T(d["margin_l"] + t + d["cell_l"], p.W + 6)[0],
          yb, f"{d['cell_l']:g}")
    xl = T(-14, 0)[0]
    dim_v(ax, T(-14, 0)[1], T(-14, d["margin_w"])[1], xl, f"{d['margin_w']:g}", off=0.0)
    dim_v(ax, T(-14, d["margin_w"])[1], T(-14, d["margin_w"] + t)[1], xl, f"{t:g}", off=-5.5)
    dim_v(ax, T(-14, d["margin_w"] + t)[1], T(-14, d["margin_w"] + t + d["cell_w"])[1], xl,
          f"{d['cell_w']:g}", off=0.0)
    ax.text(T(p.L / 2, 0)[0], T(0, 0)[1] - 2.6,
            f"网格俯视图（{d['n_l']}×{d['n_w']} 格 × {d['layers']} 层）",
            fontsize=8, ha="center", va="top")

    # ---------------- B 短卡侧视图（右上，旋转 90°：高横向 / 长竖向 / 槽口朝左） ----------------
    BX, BY = 48.0 + p.L * s + 12.0, ROW1
    Tb = mk(BX, BY)
    sc = _slots(d["margin_w"], d["slots_short"], d["pitch_w"], t)
    ax.plot(*zip(Tb(Hc, 0), Tb(Hc, p.W)), color="k", lw=0.8)
    ax.plot(*zip(Tb(0, p.W), Tb(Hc, p.W)), color="k", lw=0.8)
    ax.plot(*zip(Tb(0, 0), Tb(Hc, 0)), color="k", lw=0.8)
    prev = p.W
    for yc in reversed(sc):
        ax.plot(*zip(Tb(0, prev), Tb(0, yc + t / 2)), color="k", lw=0.8)
        ax.plot(*zip(Tb(0, yc + t / 2), Tb(Hc / 2, yc + t / 2), Tb(Hc / 2, yc - t / 2),
                     Tb(0, yc - t / 2)), color="k", lw=0.8)
        prev = yc - t / 2
    ax.plot(*zip(Tb(0, prev), Tb(0, 0)), color="k", lw=0.8)
    dim_h(ax, Tb(0, p.W + 10)[0], Tb(Hc / 2, p.W + 10)[0], Tb(0, p.W + 10)[1], f"{Hc/2:g}", off=1.2)
    dim_h(ax, Tb(0, p.W + 36)[0], Tb(Hc, p.W + 36)[0], Tb(0, p.W + 36)[1], f"{Hc:g}", off=1.5)
    ax.text(Tb(Hc / 2, 0)[0], Tb(0, 0)[1] - 2.6,
            f"短刀卡 ×{d['cards_short']}/层（下开槽 · {d['slots_short']} 槽）",
            fontsize=8, ha="center", va="top")

    # ---------------- C 长卡侧视图（左下，自然向：长横向 / 高竖向 / 槽自顶向下） ----------------
    CX, CY = 48.0, ROW2
    Tc = mk(CX, CY)
    sl = _slots(d["margin_l"], d["slots_long"], d["pitch_l"], t)
    ax.plot(*zip(Tc(0, 0), Tc(p.L, 0), Tc(p.L, Hc)), color="k", lw=0.8)
    prev = 0.0
    for xc in sl:
        ax.plot(*zip(Tc(prev, Hc), Tc(xc - t / 2, Hc)), color="k", lw=0.8)
        ax.plot(*zip(Tc(xc - t / 2, Hc), Tc(xc - t / 2, Hc / 2), Tc(xc + t / 2, Hc / 2),
                     Tc(xc + t / 2, Hc)), color="k", lw=0.8)
        prev = xc + t / 2
    ax.plot(*zip(Tc(prev, Hc), Tc(p.L, Hc)), color="k", lw=0.8)
    ax.plot(*zip(Tc(0, Hc), Tc(0, 0)), color="k", lw=0.8)
    dim_h(ax, Tc(0, Hc + 10)[0], Tc(p.L, Hc + 10)[0], Tc(0, Hc + 10)[1], f"{p.L:g}")
    dim_v(ax, Tc(0, 0)[1], Tc(0, Hc)[1], Tc(-16, 0)[0], f"{Hc:g}", off=0.0)
    dim_v(ax, Tc(0, Hc)[1], Tc(0, Hc / 2)[1], Tc(d["margin_l"] + d["cell_l"] / 2, 0)[0], f"{Hc/2:g}")
    ax.text(Tc(p.L / 2, 0)[0], Tc(0, 0)[1] - 2.6,
            f"长刀卡 ×{d['cards_long']}/层（上开槽 · {d['slots_long']} 槽）",
            fontsize=8, ha="center", va="top")

    # ---------------- 技术要求（左下，长卡视图之下） ----------------
    y0 = ROW2 - 12.0 * s - 8.0
    notes = [
        "技术要求：",
        f"1. 瓦楞纸板厚度 {d['t']:g}mm，必须可折叠；",
        f"2. 容器内尺寸 {p.L:g}×{p.W:g}×{p.H:g}；网格 {d['n_l']}×{d['n_w']} 格 × {d['layers']} 层（每层一件格架）；",
        f"3. 每层：长刀卡 {d['cards_long']} 张（{p.L:g}×{Hc:g}，{d['slots_long']} 槽）；"
        f"短刀卡 {d['cards_short']} 张（{p.W:g}×{Hc:g}，{d['slots_short']} 槽）；",
        f"4. 刀卡两端伸至箱壁；槽距卡端 = 边距 {d['margin_l']:g}/{d['margin_w']:g}（≥6，端部留料固定防劈）；",
        f"5. 长卡上开槽 / 短卡下开槽，互扣后顶/底平齐；未注开槽尺寸 {d['slot_w']:g}mm（槽深 = 刀卡高/2 = {Hc/2:g}）；",
        f"6. 隔板：中间 {d['seps_mid']} 张（必有）+ 底/顶 {d['seps_tb']} 张（{PAD_LABEL[d['pads']]}），"
        f"共 {d['seps_total']} 张 {p.L:g}×{p.W:g}×{d.get('st', d['t']):g}；堆叠高 {d['H_stack']:g}；",
        f"7. 收容数 {d['n_l']}×{d['n_w']}×{d['layers']} = {d['capacity']} 只"
        f"（刀卡共 {d['cards_long_total']}+{d['cards_short_total']} 张）。",
    ]
    for i, line in enumerate(notes):
        ax.text(48.0, y0 - i * 7.4, line, fontsize=6.8, color="0.12")

    ax.text(page[0] / 2, page[1] - 20, f"瓦楞刀卡网格 {p.L:g}×{p.W:g}×{p.H:g} · {vtxt} · 俯视图 + 刀卡侧视图",
            fontsize=13, fontweight="bold", ha="center", va="center")
    ax.text(page[0] / 2, page[1] - 27,
            f"每格 {d['cell_l']:g}×{d['cell_w']:g}×{d['cell_h']:g} · {d['n_l']}×{d['n_w']} 格 × {d['layers']} 层 · "
            f"{_st(scale, not manual)} · 单位 mm · {_today()} · 生成：{author}",
            fontsize=8, ha="center", va="center", color="0.15")

    # ---------------- 轴测图（单层格架，仅一层网格） ----------------
    ax2 = fig.add_axes([0.615, 0.30, 0.255, 0.46])
    draw_scene(ax2, model_items(p, d, axo=True))
    ax2.set_title("轴测图（单层格架）", fontsize=8)
    return fig


def render_axo(p, d, basepath, dpi=300):
    fig = plt.figure(figsize=(150 / 25.4, 115 / 25.4))
    ax = fig.add_axes([0.02, 0.06, 0.96, 0.88])
    draw_scene(ax, model_items(p, d, axo=True))
    vtxt = "V1 长对长" if d["version"] == 1 else "V2 长对宽"
    ax.set_title(f"瓦楞刀卡网格 {p.L:g}×{p.W:g}×{p.H:g} · {vtxt} · 单层格架 · 轴测图", fontsize=9)
    out = []
    for ext in ("png", "svg"):
        fp = f"{basepath}.{ext}"
        fig.savefig(fp, dpi=dpi)
        out.append(fp)
    plt.close(fig)
    return out
