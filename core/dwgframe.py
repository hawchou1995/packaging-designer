# -*- coding: utf-8 -*-
"""GB 风格图框（复刻公司图纸样式）：双边框 + 分区带（1-8 / A-F）+ 标题栏 + 第一角投影符号。

用法：
    from dwgframe import draw_frame
    fig = plt.figure(figsize=(420/25.4, 297/25.4))
    draw_frame(fig, name="...", material="...", dwgno="...", scale_str="1:5")
可叠加在既有图纸上（独立 overlay 轴，不干扰内容轴）。
"""


def _txt_w(s, fs):
    """粗略文本宽度（mm）：CJK/全角 ≈ 1.0 em，半角 ≈ 0.55 em；1pt = 0.3528mm。"""
    w = 0.0
    for ch in s:
        w += 1.0 if ord(ch) > 0x2E80 else 0.55
    return w * fs * 0.3528


def _split_at(s, pos):
    a, b = s[:pos].rstrip(" ；;、,/|"), s[pos:].lstrip(" ；;、,/|")
    return a, b


def _fit_lines(txt, max_mm, fs, max_lines=2):
    """把 txt 折到 ≤max_lines 行内塞进 max_mm；必要时按 0.3pt 步进缩小字号（下限 fs-2.4）。

    返回 (lines, fs_used)。双行时在所有候选断点中取“最长行最短”的切法。
    """
    fs_used = fs
    n_hi = len(txt)
    while fs_used > fs - 2.4 - 1e-9:
        if _txt_w(txt, fs_used) <= max_mm:
            return [txt], fs_used
        if max_lines >= 2:
            best, best_key = None, None
            for i in range(1, n_hi):
                a, b = _split_at(txt, i)
                if not a or not b:
                    continue
                wa, wb = _txt_w(a, fs_used), _txt_w(b, fs_used)
                if wa > max_mm or wb > max_mm:
                    continue
                # 优先在标点/空格处断行：命中分隔符减 6mm 等效惩罚
                pen = 0.0 if txt[i - 1] in " ；;、,/|" or txt[i] in " ；;、,/|" else 6.0
                key = max(wa, wb) + pen
                if best_key is None or key < best_key:
                    best, best_key = (a, b), key
            if best:
                return [best[0], best[1]], fs_used
        fs_used -= 0.3
    return [txt], fs


def _today():
    import datetime
    return datetime.date.today().isoformat()


def draw_frame(fig, page=(420.0, 297.0), *, name="", material="瓦楞纸板",
               dwgno="", version="A", scale_str="1:5", sheet="A3",
               page_no=1, page_total=1, company="上海银轮热交换系统有限公司",
               designed="", drawn="", proofed="", checked="", process="", standard="",
               approved="", date="",
               fs=7.2, tick_fs=6.4, lw=0.55):
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, page[0])
    ax.set_ylim(0, page[1])
    ax.axis("off")
    ax.set_zorder(50)
    ax.patch.set_alpha(0.0)
    W, H = page
    ml0, m0, ml1, m1 = 25.0, 5.0, 32.0, 12.0   # GB 留装订边：左 25/其余 5；内带线 左 32/其余 12

    ax.plot([ml0, W - m0, W - m0, ml0, ml0], [m0, m0, H - m0, H - m0, m0],
            color="k", lw=lw * 1.8, zorder=51)
    ax.plot([ml1, W - m1, W - m1, ml1, ml1], [m1, m1, H - m1, H - m1, m1],
            color="k", lw=lw, zorder=51)

    # 分区带：横向 8 格（1-8）、纵向 6 格（A-F，自上而下）
    n_x, n_y = 8, 6
    bw = (m1 - m0)
    xs = [ml0 + (W - ml0 - m0) * i / n_x for i in range(n_x + 1)]
    ys = [m0 + (H - 2 * m0) * j / n_y for j in range(n_y + 1)]
    for i in range(1, n_x):
        ax.plot([xs[i], xs[i]], [m0, m1], color="k", lw=lw * 0.7, zorder=51)
        ax.plot([xs[i], xs[i]], [H - m1, H - m0], color="k", lw=lw * 0.7, zorder=51)
    for j in range(1, n_y):
        ax.plot([ml0, ml1], [ys[j], ys[j]], color="k", lw=lw * 0.7, zorder=51)
        ax.plot([W - m1, W - m0], [ys[j], ys[j]], color="k", lw=lw * 0.7, zorder=51)
    for i in range(n_x):
        cx = (xs[i] + xs[i + 1]) / 2.0
        ax.text(cx, (m0 + m1) / 2.0, str(i + 1), ha="center", va="center",
                fontsize=tick_fs, zorder=52)
        ax.text(cx, H - (m0 + m1) / 2.0, str(i + 1), ha="center", va="center",
                fontsize=tick_fs, zorder=52)
    for j in range(n_y):
        cy = (ys[j] + ys[j + 1]) / 2.0
        letter = chr(ord("A") + (n_y - 1 - j))
        ax.text((ml0 + ml1) / 2.0, cy, letter, ha="center", va="center",
                fontsize=tick_fs, zorder=52)
        ax.text(W - (m0 + m1) / 2.0, cy, letter, ha="center", va="center",
                fontsize=tick_fs, zorder=52)

    # ---- 标题栏（GB/T 10609.1 网格化版式 180×56，右下角）----
    tb_w, tb_h = 180.0, 56.0
    x0, y0 = W - m1 - tb_w, m1
    x1, y1 = x0 + tb_w, y0 + tb_h
    ax.plot([x0, x1, x1, x0, x0], [y0, y0, y1, y1, y0], color="k", lw=lw * 1.3, zorder=51)
    xl = x0 + 40.0                                  # 左“签署区” | 右“名称/代号区”
    ax.plot([xl, xl], [y0, y1], color="k", lw=lw, zorder=51)
    xl2 = xl + 16.0                                 # 右区字段提示列
    ax.plot([xl2, xl2], [y0, y1], color="k", lw=lw * 0.8, zorder=51)
    # 标签与值必须一一对应：之前 checked(审核) 落在「校对」格、审核格恒空、日期从不传
    labels = ["设计", "制图", "校对", "审核", "工艺", "标准化", "批准", "日期"]
    vals = [designed, drawn, proofed, checked, process, standard, approved,
            date or _today()]
    rh = tb_h / 8.0
    for i, lab in enumerate(labels):
        yy = y1 - (i + 1) * rh
        if i:
            ax.plot([x0, xl], [yy, yy], color="k", lw=lw * 0.8, zorder=51)
        ax.plot([x0 + 14.0, x0 + 14.0], [yy, yy + rh], color="k", lw=lw * 0.8, zorder=51)
        ax.text(x0 + 2.0, yy + rh / 2, lab, fontsize=fs - 0.4, ha="left", va="center",
                color="0.22", zorder=52)
        if vals[i]:
            ax.text(x0 + 15.5, yy + rh / 2, vals[i], fontsize=fs - 0.6, ha="left",
                    va="center", zorder=52)
    # 右区 5 行：单位 / 名称 / 代号+版本 / 材料+比例+页次 / 幅面+投影
    rows_h = [11.0, 13.0, 10.0, 11.0, 11.0]
    cys = []
    yy = y1
    for h_ in rows_h:
        cys.append((yy + yy - h_) / 2.0)
        yy -= h_
    cuts = [y1 - sum(rows_h[:k]) for k in range(1, 5)]
    for c in cuts:
        ax.plot([xl, x1], [c, c], color="k", lw=lw * 0.8, zorder=51)
    cx2 = (xl2 + x1) / 2.0
    ax.text(xl + 2.0, cys[0], "单位名称", fontsize=fs - 0.4, ha="left", va="center",
            color="0.22", zorder=52)
    ax.text(cx2, cys[0], company, fontsize=fs + 1.6, ha="center", va="center", zorder=52)
    ax.text(xl + 2.0, cys[1], "图样名称", fontsize=fs - 0.4, ha="left", va="center",
            color="0.22", zorder=52)
    nm_lines, nm_fs = _fit_lines(str(name), 132.0, fs + 2.0, max_lines=1)
    ax.text(cx2, cys[1], nm_lines[0], fontsize=nm_fs, ha="center", va="center", zorder=52)
    xs3 = x1 - 26.0
    ax.plot([xs3, xs3], [cuts[1], cuts[2]], color="k", lw=lw * 0.8, zorder=51)
    ax.text(xl + 2.0, cys[2], "图样代号", fontsize=fs - 0.4, ha="left", va="center",
            color="0.22", zorder=52)
    ax.text(xl + 18.0, cys[2], dwgno, fontsize=fs, ha="left", va="center", zorder=52)
    ax.text(xs3 + 2.0, cys[2], "版本", fontsize=fs - 0.4, ha="left", va="center",
            color="0.22", zorder=52)
    ax.text(xs3 + 14.0, cys[2], version, fontsize=fs + 0.6, ha="left", va="center", zorder=52)
    xm, xp = xl + 52.0, xl + 92.0
    ax.plot([xm, xm], [cuts[2], cuts[3]], color="k", lw=lw * 0.8, zorder=51)
    ax.plot([xp, xp], [cuts[2], cuts[3]], color="k", lw=lw * 0.8, zorder=51)
    ax.text(xl + 2.0, cys[3], "材料", fontsize=fs - 0.4, ha="left", va="center",
            color="0.22", zorder=52)
    mat_lines, mat_fs = _fit_lines(str(material), 32.0, fs - 0.4, max_lines=2)
    if len(mat_lines) == 1:
        ax.text(xl + 18.0, cys[3], mat_lines[0], fontsize=mat_fs, ha="left", va="center", zorder=52)
    else:
        ax.text(xl + 18.0, cys[3] + 2.1, mat_lines[0], fontsize=mat_fs, ha="left", va="center", zorder=52)
        ax.text(xl + 18.0, cys[3] - 2.1, mat_lines[1], fontsize=mat_fs, ha="left", va="center", zorder=52)
    ax.text(xm + 2.0, cys[3], "比例", fontsize=fs - 0.4, ha="left", va="center",
            color="0.22", zorder=52)
    ax.text(xm + 12.5, cys[3], scale_str, fontsize=fs + 0.4, ha="left", va="center", zorder=52)
    ax.text(xp + 2.0, cys[3], f"共 {page_total} 页第 {page_no} 页", fontsize=fs - 0.4,
            ha="left", va="center", zorder=52)
    ax.text(xl + 2.0, cys[4], "幅面", fontsize=fs - 0.4, ha="left", va="center",
            color="0.22", zorder=52)
    ax.text(xl + 18.0, cys[4], sheet, fontsize=fs + 0.4, ha="left", va="center", zorder=52)
    xsp = x1 - 34.0
    ax.plot([xsp, xsp], [cuts[3], y0], color="k", lw=lw * 0.8, zorder=51)
    cy5 = cys[4]
    ax.plot([xsp + 5, xsp + 13, xsp + 10.4, xsp + 7.6, xsp + 5],
            [cy5 - 3.2, cy5 - 3.2, cy5 + 3.2, cy5 + 3.2, cy5 - 3.2],
            color="k", lw=lw, zorder=52)
    ax.add_patch(plt_circle((xsp + 20.5, cy5), 3.4, fill=False, lw=lw, zorder=52))
    ax.add_patch(plt_circle((xsp + 20.5, cy5), 1.6, fill=False, lw=lw, zorder=52))
    return ax


def plt_circle(xy, r, **kw):
    from matplotlib.patches import Circle
    return Circle(xy, r, **kw)
