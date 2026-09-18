# -*- coding: utf-8 -*-
"""片材图纸：A3 合成图 = 第一角三视图（主/俯/左）+ 等轴测轴测图 + 参数块。

复用 0210 管线：dim_h/dim_v（白底遮罩标注）、等轴测渲染器 draw_scene、字体助手。
三视图布置（第一角，GB）：主视图在左上，俯视图在其正下方（长对正），
左视图在主视图正右方（高平齐）；尺寸只注一次：长 L（主视图）、厚 H（主视图）、
宽 W（俯视图），避免重复标注。
"""
import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from box0210_2d import _font_family, dim_h, dim_v
from box0210_3d import draw_scene
from sheet_core import Params, items

from drawutil import SCALES          # GB 常用系列 + 放大档（0.2/0.5 → 5:1/2:1）


from drawutil import pick_scale as _pick_scale_u, scale_str as _scale_str, scale_tag as _scale_tag


def _pick_scale(block_w, block_h, avail_w, avail_h):
    return _pick_scale_u(block_w, block_h, avail_w, avail_h, SCALES)


def build_sheet(p: Params, page=(420.0, 297.0), d_force=None, meta: dict = None,
                scale: float = None):
    meta = meta or {}
    author = meta.get("author", "包装周哥")
    manual = scale is not None and float(scale) > 0
    fam, fpath = _font_family()
    fig = plt.figure(figsize=(page[0] / 25.4, page[1] / 25.4))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, page[0])
    ax.set_ylim(0, page[1])
    ax.axis("off")

    gap = 34.0                              # 视图间距（数据 mm，随比例缩放）
    block_w = p.L + gap + p.W
    block_h = p.H + gap + p.W
    # 版面分区：注释带（底部 y 8..60）· 绘图区（y 66..262）· 轴测列（右侧）
    avail_w, avail_h = 244.0, 196.0
    d = float(scale) if (manual or d_force) else _pick_scale(block_w, block_h, avail_w, avail_h)
    s = 1.0 / d
    fig._scale_used, fig._scale_auto = d, not manual
    if block_w * s > avail_w + 0.1 or block_h * s > avail_h + 0.1:
        print(f"提示：比例 1:{d:g} 超出绘图区（{block_w*s:.0f}×{block_h*s:.0f} > "
              f"{avail_w:.0f}×{avail_h:.0f}），可能与轴测列/边距相碰")
    ox = max(50.0, 44.0 + (avail_w - block_w * s) / 2.0)
    # 绘图区垂直居中：数据块 y 范围 = [-(gap+W), +H]
    oy = 66.0 + (avail_h - block_h * s) / 2.0 + (gap + p.W) * s

    def T(x, y):
        return (ox + x * s, oy + y * s)

    def rect(x0, y0, w, h):
        pts = [(x0, y0), (x0 + w, y0), (x0 + w, y0 + h), (x0, y0 + h), (x0, y0)]
        xs, ys = zip(*[T(a, b) for a, b in pts])
        ax.plot(xs, ys, color="k", lw=0.7)

    # 第一角三视图
    rect(0, 0, p.L, p.H)                          # 主视图
    rect(0, -gap - p.W, p.L, p.W)                 # 俯视图（长对正）
    rect(p.L + gap, 0, p.W, p.H)                  # 左视图（高平齐）

    # 尺寸（只注一次：L / H / W）；厚 H 的标注线很短的薄板用横排文字放在左侧空白
    yh = p.H + 9.0
    dim_h(ax, T(0, yh)[0], T(p.L, yh)[0], T(0, yh)[1], f"长 L = {p.L:g}")
    dim_v(ax, T(0, 0)[1], T(0, p.H)[1], T(-9, 0)[0], "")
    ax.text(T(-11, p.H / 2)[0], T(-11, p.H / 2)[1], f"厚 H = {p.H:g}",
            fontsize=6.5, ha="right", va="center", color="k")
    dim_v(ax, T(0, -gap - p.W)[1], T(0, -gap)[1], T(-9, 0)[0], f"宽 W = {p.W:g}", off=-3.4)

    # 视图名（y 用**纸面**偏移 2.6mm，不随比例缩小 —— 数据 mm 偏移在 1:15 时会贴到线上）
    for (x, y, t) in ((p.L / 2, T(0, 0)[1] - 2.6, "主视图"),
                      (p.L / 2, T(0, -gap - p.W)[1] - 2.6, "俯视图"),
                      (p.L + gap + p.W / 2, T(0, 0)[1] - 2.6, "左视图")):
        ax.text(T(x, 0)[0], y, t, fontsize=7.5, ha="center", va="top", color="0.15")

    # 标题 / 备注 / 参数块
    ax.text(page[0] / 2, page[1] - 20, f"{p.name} · 三视图 + 等轴测图（第一角）",
            fontsize=13, fontweight="bold", ha="center", va="center", color="0.05")
    ax.text(page[0] / 2, page[1] - 27,
            f"{p.L:g}×{p.W:g}×{p.H:g} mm · {_scale_tag(d, not manual)} · 单位 mm · "
            f"{datetime.date.today().isoformat()} · 生成：{author}",
            fontsize=8, ha="center", va="center", color="0.15")
    ax.text(40.0, 14.0, f"大字说明：{p.name}；厚度 {p.H:g}mm 薄板，第一角投影（俯视在下、左视在右）",
            fontsize=6.4, color="0.30")

    # 注释块：优先放进"左视图下方"的空区（收紧版面），摆不下则回退左下角
    nx = ox + (p.L + gap) * s + 8.0
    ny = 112.0
    if nx > 214.0:
        nx, ny = 20.0, 56.0
    note_lines = [
        "投影法：第一角（GB）· 单位 mm",
        "三视图与轴测图、STEP/STL 数模同源（改长/宽/厚一键重出）",
        f"参数：{p.L:g} × {p.W:g} × {p.H:g}；面积 {p.area:.4f} m²；体积 {p.volume:.5f} L；对角线 {p.diag:.1f} mm",
    ]
    if p.material:
        note_lines.append(f"材质：{p.material}")
    for i, line in enumerate(note_lines):
        ax.text(nx, ny - i * 8.0, line, fontsize=6.8, color="0.15")
    # 字体信息不能与「大字说明」同行同起点（会完全叠字）
    ax.text(117.0, 14.0, f"字体：{fam}（{fpath or 'fallback'}）", fontsize=5.2, color="0.45")

    # 等轴测（右列，与绘图区对齐，放大占位）
    ax2 = fig.add_axes([0.695, 0.42, 0.275, 0.46])
    draw_scene(ax2, items(p))
    ax2.set_title("轴测图（等轴测）", fontsize=9)
    from dwgframe import draw_frame
    draw_frame(fig, page=page,
               name=meta.get("dwg_name") or f"{p.name} 片材 {p.L:g}×{p.W:g}×{p.H:g}",
               material=meta.get("dwg_material") or (p.material or "—"),
               dwgno=meta.get("dwg_no") or f"SHEET-{p.L:g}x{p.W:g}x{p.H:g}",
               version=meta.get("dwg_version") or "A",
               scale_str=_scale_str(d), sheet="A3",
               company=meta.get("company", "上海银轮热交换系统有限公司"),
               designed=meta.get("designed", ""), drawn=meta.get("drawn", ""),
               proofed=meta.get("proofed", ""), checked=meta.get("checked", ""),
               process=meta.get("process", ""), standard=meta.get("standard", ""),
               approved=meta.get("approved", ""), date=meta.get("date", ""))
    return fig
