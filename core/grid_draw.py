# -*- coding: utf-8 -*-
"""刀卡网格 A3 合成图（版式仿公司参考图纸）：图框 + 网格俯视图 + 短卡侧视图（旋转 90°）
+ 长卡侧视图 + 技术要求 + 轴测图（单层格架）。

参考版式（地平线 XG盖板 SNP24 图纸）：
  A 俯视图（左上）：刀卡全长伸至箱壁；槽距端边 = 边距
  B 侧视图一（右上）：短板卡旋转 90°（高横向、长竖向、槽口朝左），标注 高 / 槽深
  C 侧视图二（左下）：长刀卡自然向（长横向、高竖向、槽自顶向下），标注 高 / 槽深
"""
import math

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from dwgframe import draw_frame, _txt_w
from box0210_2d import dim_h, dim_v, _font_family, save_sheet_png_svg, _today
from box0210_3d import draw_scene
from grid_core import PAD_LABEL

# 折弯线线型（点划线）：GB 机械制图惯例
FOLD_STYLE = dict(color="k", lw=0.5, ls=(0, (6, 2, 1, 2)), zorder=12)
# 短折弯线用（一个周期 ≈ 4.9pt，1.7mm 的线段也能看出「划—点—划」）
FOLD_STYLE_S = dict(color="k", lw=0.5, ls=(0, (2.2, 1.0, 0.7, 1.0)), zorder=12)
from grid_model import items as model_items, _slot_centers, _fold_tabs


def _slots(margin, n, pitch, t):
    return _slot_centers(margin, n, pitch, t)


def _wrap_text(s, width_mm, fs):
    """按估算字宽折行（中文字宽 ≈ fs·25.4/72，西文 ≈ 0.55×）。图幅上不允许整行铺满。"""
    cjk = fs * 25.4 / 72.0
    asc = cjk * 0.55
    out, cur, w = [], "", 0.0
    for ch in s:
        cw = cjk if ord(ch) > 0x2000 else asc
        if cur and w + cw > width_mm:
            out.append(cur)
            cur, w = "", 0.0
        cur += ch
        w += cw
    if cur:
        out.append(cur)
    return out or [""]


def build_sheet(p, d, scale=None, page=(420.0, 297.0), meta: dict = None):
    meta = meta or {}
    author = meta.get("author", "包装周哥")
    manual = scale is not None and float(scale) > 0
    from drawutil import scale_str as _ss, scale_tag as _st, pick_scale as _ps, SCALES as _SC
    if manual:
        scale = float(scale)
    else:
        t_, Hc_ = d["t"], d["cell_h"]
        _fx = (d.get("fold_len_out", d.get("fold_len", 0.0))
               if (d.get("fold_l") or d.get("fold_w")) else 0.0)
        s_w1 = _ps(p.L + Hc_ + _fx, 1.0, 192.0, 1e9, _SC)       # L+Hc+折边 ≤ 192
        # B 视图说明文字（起点 BX、宽约 41）右端 ≤ 258（轴测区左界）→ 长边预算收到 155
        s_w2 = _ps(p.L + _fx, 1.0, 155.0, 1e9, _SC)
        s_h = _ps(1.0, p.W + Hc_ + 38.0 + _fx, 1e9, 149.4, _SC)  # 纵向：W+Hc+38+折边余量
        scale = max(s_w1, s_w2, s_h)
    fam, fpath = _font_family()
    fig = plt.figure(figsize=(page[0] / 25.4, page[1] / 25.4))
    vtxt = "V1 长对长" if d["version"] == 1 else "V2 长对宽"
    draw_frame(fig, page=page,
               name=meta.get("dwg_name") or f"瓦楞刀卡网格 {p.L:g}×{p.W:g}×{p.H:g} · {vtxt}",
               material=meta.get("dwg_material") or
               ((f"刀卡 t={d['t']:g}" if abs(d.get('st', d['t']) - d['t']) < 1e-9
                 else f"刀卡 t={d['t']:g} / 隔板 t={d.get('st', d['t']):g}") + "（可折叠）"),
               dwgno=meta.get("dwg_no") or f"GRID-{p.L:g}x{p.W:g}x{p.H:g}-V{d['version']}",
               version=meta.get("dwg_version") or "A",
               scale_str=_ss(scale), sheet="A3",
               company=meta.get("company", "上海银轮热交换系统有限公司"),
               designed=meta.get("designed", ""), drawn=meta.get("drawn", ""),
               proofed=meta.get("proofed", ""), checked=meta.get("checked", ""),
               process=meta.get("process", ""), standard=meta.get("standard", ""),
               approved=meta.get("approved", ""), date=meta.get("date", ""))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, page[0])
    ax.set_ylim(0, page[1])
    ax.axis("off")
    ax.set_zorder(10)
    ax.patch.set_alpha(0.0)
    s = 1.0 / scale
    t, Hc = d["t"], d["cell_h"]
    fig._scale_used, fig._scale_auto = scale, not manual
    _fl_out = d.get("fold_len_out", d.get("fold_len", 0.0))
    fwc = _fl_out if d.get("fold_w") else 0.0    # 短卡折边：B 视图两端延长（沿纸面纵向）
    flc = _fl_out if d.get("fold_l") else 0.0    # 长卡折边：C 视图两端延长（沿纸面横向）
    # B（短卡侧视）按展开画：两端各 +折边，纵向会高出 p.W → 版面预算里先把这段让出来
    _fw_lay = fwc
    # 俯视图上方的纵向预算（**纸面绝对值**，约 17mm）：尺寸链带 + 总长/总宽尺寸 + 数字 + 视图名。
    # 原来按比例 36·s，小比例时几乎归零，尺寸数字会顶到图幅标题行 —— 用户 2026-09-18 反馈。
    # 另需保证 B 视图（短卡侧视）顶部不越过 264。
    TOP = 264.0 - max(36.0 * s, 17.0, fwc * s + 1.0)
    ROW1 = TOP - p.W * s                   # 俯视图/短卡视图底边
    ROW2 = ROW1 - 24.0 - Hc * s            # 长卡视图底边（含俯视图标注带）

    def mk(ox, oy):
        return lambda x, y: (ox + x * s, oy + y * s)

    # ---------------- A 俯视图（左上） ----------------
    PLX, PLY = 48.0, ROW1
    T = mk(PLX, PLY)
    fig._plan_T = (PLX, ROW1, s)      # 检查器复用同一变换，避免两边各算一套坐标
    xs_l = _slots(d["margin_l"], d["slots_long"], d["pitch_l"], t)
    ys_w = _slots(d["margin_w"], d["slots_short"], d["pitch_w"], t)
    def line(a, b, horiz, fx):
        (x0, y0), (x1, y1) = (T(a, fx), T(b, fx)) if horiz else (T(fx, a), T(fx, b))
        ax.plot([x0, x1], [y0, y1], color="k", lw=0.7, zorder=11)

    def cut(x0d, y0d, x1d, y1d):
        (a, b), (c, e) = T(x0d, y0d), T(x1d, y1d)
        ax.plot([a, c], [b, e], color="k", lw=0.7, zorder=11)

    def foldln(x0d, y0d, x1d, y1d):
        (a, b), (c, e) = T(x0d, y0d), T(x1d, y1d)
        # 折边根部的折弯线在俯视图里只有板厚 t 长（1:3 时约 1.7mm）→ 标准点划线的
        # 一个周期（6+2+1+2 pt）都画不满，会被看成实线；短线段改用加密点划线。
        st = FOLD_STYLE if math.hypot(c - a, e - b) > 3.2 else FOLD_STYLE_S
        ax.plot([a, c], [b, e], **st)

    fl_net = d.get("fold_len", 30.0)                     # 折边净长（折叠后立边，垂直方向量）
    fl_out = d.get("fold_len_out", fl_net)               # 展开料长 = 净长 + 板厚 t（折弯补偿）
    fold_l, fold_w = bool(d.get("fold_l")), bool(d.get("fold_w"))
    # 折边几何（**折叠后状态**，用户 2026-09-18 定案）：
    #   · 折边 = 卡端折 90° 的竖板，**与刀卡本体垂直**：长卡两端沿 Y 伸出、短卡两端沿 X 伸出；
    #     俯视投影 = 卡端的直角“L”（本体棱线 + 垂直短条），不是本体的延长线；
    #   · 沿卡长方向只占一个板厚 t（自卡端向内，不越出卡端）；
    #   · 折向取容器中心侧 → 折边恒在容器内，不会捅出箱壁。
    tabs = _fold_tabs(p, d)
    # 折弯线（折边根部，= fold_edge 指定的那条边）在本体棱线上的占位。
    # 本体棱线在该区间必须断开，否则实线会把点划线的折弯线盖住（看起来像裁切）。
    span_l, span_s = {}, {}
    for tx0, tx1, ty0, ty1, is_long, fe in tabs:
        if is_long:
            span_l.setdefault(round(ty0 if fe == "y0" else ty1, 6), []).append((tx0, tx1))
        else:
            span_s.setdefault(round(tx0 if fe == "x0" else tx1, 6), []).append((ty0, ty1))

    def _seg(a, b, horiz, fx, gaps):
        """沿 a→b 画线，遇 gaps（同方向区间）断开。"""
        prev = a
        for (g0, g1) in sorted(gaps):
            if g1 <= prev + 1e-9:
                continue
            if g0 >= b - 1e-9:
                break
            if g0 > prev + 1e-9:
                line(prev, g0, horiz, fx)
            prev = max(prev, g1)
        if prev < b - 1e-9:
            line(prev, b, horiz, fx)

    for yc in ys_w:                                      # 长卡（上开槽）
        y_near, y_far = yc - t / 2, yc + t / 2
        for e in (y_near, y_far):
            gaps = [(xc - t / 2, xc + t / 2) for xc in xs_l]
            gaps += span_l.get(round(e, 6), [])
            _seg(0.0, p.L, True, e, gaps)
        line(y_near, y_far, False, 0.0)                  # 卡端面（折弯处的转角棱）
        line(y_near, y_far, False, p.L)
    for xc in xs_l:                                      # 短卡（下开槽）
        x_near, x_far = xc - t / 2, xc + t / 2
        for e in (x_near, x_far):
            _seg(0.0, p.W, False, e, span_s.get(round(e, 6), []))
        line(x_near, x_far, True, 0.0)
        line(x_near, x_far, True, p.W)
    for tx0, tx1, ty0, ty1, is_long, fold_edge in tabs:
        # 折边竖板投影（俯视）：**根部（本体料面侧）那条边 = 折弯线 → 点划线**；
        # 其余三边（折边外端 = 展开料自由边、以及两条板厚投影边）= 裁切边 → 实线。
        # 用户 2026-09-18：「折边折叠处改为虚线（折弯线），实线意味着裁切，制作时就是裁断的」。
        edges = {"x0": (tx0, ty0, tx0, ty1), "x1": (tx1, ty0, tx1, ty1),
                 "y0": (tx0, ty0, tx1, ty0), "y1": (tx0, ty1, tx1, ty1)}
        for key, (a, b, c, e) in edges.items():
            (foldln if key == fold_edge else cut)(a, b, c, e)
    # 尺寸链带（边距 / 板厚 / 格距）：距俯视图 6mm（按比例）→ 标签写在线下方
    yb = T(0, p.W + 6)[1]
    dim_h(ax, T(0, p.W + 6)[0], T(d["margin_l"], p.W + 6)[0], yb, f"{d['margin_l']:g}")
    dim_h(ax, T(d["margin_l"], p.W + 6)[0], T(d["margin_l"] + t, p.W + 6)[0], yb, f"{t:g}", off=4.6)
    dim_h(ax, T(d["margin_l"] + t, p.W + 6)[0], T(d["margin_l"] + t + d["cell_l"], p.W + 6)[0],
          yb, f"{d['cell_l']:g}")
    # 总长尺寸：与尺寸链带用**纸面绝对 9mm** 间距（原来按比例 16·s，小比例时两条线挤在一起，
    # 边距/格距的数字会压在总长尺寸线上 —— 用户 2026-09-18 反馈的「标注干涉」）。
    dim_h(ax, T(0, p.W + 6)[0], T(p.L, p.W + 6)[0], yb + 9.0, f"{p.L:g}", off=1.5)
    # 总宽尺寸 + 尺寸链带：横向间距改为**纸面绝对值**（原来 26·s / 14·s 随比例漂移，
    # 窄板厚（t=5）的「5」字会飘到总宽尺寸线上 —— 用户 2026-09-18 反馈的「标注干涉」）。
    dim_v(ax, T(0, 0)[1], T(0, p.W)[1], T(0, 0)[0] - 14.0, f"{p.W:g}", off=1.5)
    xl = T(0, 0)[0] - 7.0
    dim_v(ax, T(0, 0)[1], T(0, d["margin_w"])[1], xl, f"{d['margin_w']:g}", off=0.0)
    dim_v(ax, T(0, d["margin_w"])[1], T(0, d["margin_w"] + t)[1], xl, f"{t:g}", off=-5.5)
    dim_v(ax, T(0, d["margin_w"] + t)[1], T(0, d["margin_w"] + t + d["cell_w"])[1], xl,
          f"{d['cell_w']:g}", off=0.0)
    _ftxt = ""
    if fold_l or fold_w:
        _which = ("长卡两端 + 短卡两端" if (fold_l and fold_w)
                  else "短卡两端" if fold_w else "长卡两端")
        _ftxt = (f" · {_which}各 {fl_net:g} 折边（折 90° 与刀卡垂直，俯视为卡端直角，"
                 f"展开料端部 {fl_out:g} = {fl_net:g}+t）")
    # 视图名排在**尺寸带之上**（6·s + 16mm），否则会落在总长尺寸线上
    _name = f"网格俯视图（{d['n_l']}×{d['n_w']} 格 × {d['layers']} 层）{_ftxt}"
    _nl = _wrap_text(_name, 236.0, 8)      # 居中长名字会左右越出内框 → 先折行（v1.0.15）
    _tw = max(_txt_w(ln, 8) for ln in _nl)
    _cx = min(max(T(p.L / 2, 0)[0], 36.0 + _tw / 2.0), 406.0 - _tw / 2.0)
    ax.text(_cx, T(0, p.W)[1] + 6.0 * s + 16.0,
            "\n".join(_nl), fontsize=8, ha="center", va="bottom")

    # ---------------- B 短卡侧视图（右上，旋转 90°：高横向 / 长竖向 / 槽口朝左） ----------------
    # 按**展开料**画（用户口径）：卡体两端各延长 fl_out（= 净长 + 板厚）、同高；原卡端 = 折弯线（点划线）；
    # 轮廓闭合（长边 + 两端封口）；高/槽深标注排在图形下方（折边之外），不压图线。
    BX, BY = 48.0 + (p.L + flc) * s + 12.0, ROW1
    Tb = mk(BX, BY)
    sc = _slots(d["margin_w"], d["slots_short"], d["pitch_w"], t)
    l_a, l_b = (-fwc, p.W + fwc) if fwc else (0.0, p.W)
    # 轮廓闭合：长边（高 Hc）+ 两端封口
    ax.plot(*zip(Tb(Hc, l_a), Tb(Hc, l_b)), color="k", lw=0.8)
    ax.plot(*zip(Tb(0, l_a), Tb(Hc, l_a)), color="k", lw=0.8)
    ax.plot(*zip(Tb(0, l_b), Tb(Hc, l_b)), color="k", lw=0.8)
    # 槽口（槽口在 h=0 一侧，深 Hc/2）：h=0 长边遇槽断开（卡自身坐标，0..W 为卡体）
    prev = l_a
    for yc in sc:
        s0, s1 = yc - t / 2, yc + t / 2
        ax.plot(*zip(Tb(0, prev), Tb(0, s0)), color="k", lw=0.8)
        ax.plot(*zip(Tb(0, s0), Tb(Hc / 2, s0), Tb(Hc / 2, s1), Tb(0, s1)), color="k", lw=0.8)
        prev = s1
    ax.plot(*zip(Tb(0, prev), Tb(0, l_b)), color="k", lw=0.8)
    if fwc:
        for le in (0.0, p.W):                           # 原卡端 = 折弯线（点划线）
            ax.plot(*zip(Tb(0, le), Tb(Hc, le)), **FOLD_STYLE)
        dim_v(ax, Tb(0, l_a)[1], Tb(0, 0.0)[1], Tb(-14, 0)[0], f"{fwc:g}", off=0.0)
        dim_v(ax, Tb(0, p.W)[1], Tb(0, l_b)[1], Tb(-14, 0)[0], f"{fwc:g}", off=0.0)
    # 高 / 槽深标注：排在图形下方（折边之外），不压任何图线
    yc1 = Tb(0, l_a)[1] - 9.0
    yc2 = Tb(0, l_a)[1] - 22.0
    dim_h(ax, Tb(0, l_a)[0], Tb(Hc / 2, l_a)[0], yc1, f"{Hc/2:g}", off=1.2)
    dim_h(ax, Tb(0, l_a)[0], Tb(Hc, l_a)[0], yc2, f"{Hc:g}", off=1.5)
    # 视图说明：排在**结构上保证空置的带**里 —— 长卡视图（含其右侧高度尺寸列）之下、
    # 技术要求块之上。原来贴在图下方，正好压在长卡视图的高度尺寸列上（用户 2026-09-18 反馈）。
    cap_y = ROW2 - 1.2
    cap = [f"短刀卡 ×{d['cards_short']}/层（下开槽 · {d['slots_short']} 槽）"]
    if fwc:
        cap.append(f"展开料 {l_b - l_a:g} × {Hc:g}（两端各折 {fwc:g}）")
    ax.text(BX, cap_y, "\n".join(cap), fontsize=8, ha="left", va="top")

    # ---------------- C 长卡侧视图（左下，自然向：长横向 / 高竖向 / 槽自顶向下） ----------------
    # 同 B：按展开料画（两端各延长 fl_out、同高），原卡端 = 折弯线（点划线），轮廓闭合，尺寸不压线。
    CX, CY = 48.0, ROW2
    Tc = mk(CX, CY)
    sl = _slots(d["margin_l"], d["slots_long"], d["pitch_l"], t)
    x_a, x_b = (-flc, p.L + flc) if flc else (0.0, p.L)
    # 轮廓闭合：上下长边（h=0 / h=Hc）+ 两端封口
    ax.plot(*zip(Tc(x_a, 0), Tc(x_b, 0)), color="k", lw=0.8)
    ax.plot(*zip(Tc(x_a, Hc), Tc(x_b, Hc)), color="k", lw=0.8)
    ax.plot(*zip(Tc(x_a, 0), Tc(x_a, Hc)), color="k", lw=0.8)
    ax.plot(*zip(Tc(x_b, 0), Tc(x_b, Hc)), color="k", lw=0.8)
    # 槽口（自顶向下，深 Hc/2）：h=Hc 长边遇槽断开（卡自身坐标，0..L 为卡体）
    prev = x_a
    for xc in sl:
        s0, s1 = xc - t / 2, xc + t / 2
        ax.plot(*zip(Tc(prev, Hc), Tc(s0, Hc)), color="k", lw=0.8)
        ax.plot(*zip(Tc(s0, Hc), Tc(s0, Hc / 2), Tc(s1, Hc / 2), Tc(s1, Hc)), color="k", lw=0.8)
        prev = s1
    ax.plot(*zip(Tc(prev, Hc), Tc(x_b, Hc)), color="k", lw=0.8)
    if flc:
        for xe in (0.0, p.L):                           # 原卡端 = 折弯线（点划线）
            ax.plot(*zip(Tc(xe, 0), Tc(xe, Hc)), **FOLD_STYLE)
    # 尺寸：本体长 + 两端折边（分两层）+ 展开长；高度标在折边**之外**（右侧），不压图线
    # 三条尺寸行的**行距是纸面绝对值**：原来用数据 mm（Hc+10/26/40）→ 大比例时三行只差 1mm，
    # 标签自己叠自己（v1.0.15 修；横向端点仍取数据坐标，不受影响）
    _ry = Tc(0, Hc)[1]
    dim_h(ax, Tc(0.0, Hc + 10)[0], Tc(p.L, Hc + 10)[0], _ry + 5.0, f"{p.L:g}")
    if flc:
        dim_h(ax, Tc(x_a, Hc + 26)[0], Tc(0.0, Hc + 26)[0], _ry + 10.0, f"{flc:g}", off=1.2)
        dim_h(ax, Tc(p.L, Hc + 26)[0], Tc(x_b, Hc + 26)[0], _ry + 10.0,
              f"{flc:g}", off=1.2)
        dim_h(ax, Tc(x_a, Hc + 40)[0], Tc(x_b, Hc + 40)[0], _ry + 15.0,
              f"展开 {x_b - x_a:g}", off=1.5)
    # 高度尺寸：贴在本体右端之外（+6），标签在尺寸线右侧。
    # 不能用 +15：B 视图（右上）的高度/槽深尺寸线横跨 [BX, BX+Hc·s]，
    # 会与本列竖向尺寸线相交（GB/T 4458.4 尺寸线不得相交）——用户 2026-09-18 反馈。
    dim_v(ax, Tc(0, 0)[1], Tc(0, Hc)[1], Tc(x_b, 0)[0] + 6.0, f"{Hc:g}", off=1.0)
    dim_v(ax, Tc(0, Hc)[1], Tc(0, Hc / 2)[1],
          Tc(d["margin_l"] + d["cell_l"] / 2, 0)[0], f"{Hc/2:g}")
    ax.text(Tc((x_a + x_b) / 2, 0)[0], Tc(0, 0)[1] - 2.6,
            f"长刀卡 ×{d['cards_long']}/层（上开槽 · {d['slots_long']} 槽）"
            + (f" · 展开 {x_b - x_a:g}（两端各 {flc:g}）" if d.get("fold_l") else ""),
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
    if d.get("fold_l") or d.get("fold_w"):
        _parts = []
        if d.get("fold_l"):
            _parts.append(f"长刀卡两端各 {d['fold_len']:g}（展开 {d['blank_L']:g}×{Hc:g}，"
                          f"{d['cards_long_total']} 张）")
        if d.get("fold_w"):
            _parts.append(f"短刀卡两端各 {d['fold_len']:g}（展开 {d['blank_W']:g}×{Hc:g}，"
                          f"{d['cards_short_total']} 张）")
        notes.append(f"8. 折边（边距 ≤ {d['fold_thr']:g} 触发，本图 {d['margin_l']:g}/{d['margin_w']:g}）："
                     + "；".join(_parts)
                     + f"；折边与刀卡垂直（卡端折 90° 的竖板，俯视为卡端直角）；"
                       f"侧视图按展开料画，点划线 = 折弯线（距端 {d['fold_len_out']:g} "
                       f"= 净长 {d['fold_len']:g} + 板厚 {d['t']:g}）。")
    if len(notes) > 8:
        notes[0] = "技术要求："
    # 技术要求**必须**折行到标题栏左侧（标题栏占 x ≥ 228）：整行铺到 273 会伸进标题栏。
    lines = []
    for ln in notes:
        seg = _wrap_text(ln, 168.0, 6.8)
        lines.extend([seg[0]] + ["    " + s for s in seg[1:]])
    for i, line in enumerate(lines):
        ax.text(48.0, y0 - i * 7.1, line, fontsize=6.8, color="0.12")

    ax.text(page[0] / 2, page[1] - 19, f"瓦楞刀卡网格 {p.L:g}×{p.W:g}×{p.H:g} · {vtxt} · 俯视图 + 刀卡侧视图",
            fontsize=13, fontweight="bold", ha="center", va="center")
    ax.text(page[0] / 2, page[1] - 25.5,
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
