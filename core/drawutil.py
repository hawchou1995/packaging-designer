# -*- coding: utf-8 -*-
"""drawutil.py — 图纸比例与版面工具（全模块共用）。

比例档：GB/T 14690 常用系列 + 放大档（<1 表示放大，如 0.5 → 2:1）。
自动选档 = **按图幅实际可用区域**取「能放下的最大绘图比例」，不是固定档位。
"""
from itertools import product

SCALES = (10.0, 5.0, 2.0, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 6.0, 8.0, 10.0, 15.0, 20.0)
SCALES = (0.2, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 6.0, 8.0, 10.0, 15.0, 20.0)


def pick_scale(w, h, avail_w, avail_h, scales=SCALES, margin=0.0):
    """取能放进 (avail_w × avail_h) 的**最大**绘图比例（scale 最小者）；放大档优先。

    w/h = 内容在数据空间的尺寸（mm）。margin 为额外留给尺寸线/文字的余量（mm）。
    """
    aw, ah = avail_w - margin, avail_h - margin
    for sc in scales:
        if w / sc <= aw + 1e-9 and h / sc <= ah + 1e-9:
            return float(sc)
    return float(scales[-1])


def wrap_mm(s, width_mm, fs):
    """按中文宽度估算法折行（CJK ≈ fs pt，西文 ≈ 0.55×），返回行列表。
    图纸上的说明文字一律先折到「标题栏左侧」这类硬边界内，再落笔。"""
    cjk = fs * 25.4 / 72.0
    asc = cjk * 0.55
    out, cur, w = [], "", 0.0
    for ch in str(s):
        cw = cjk if ord(ch) > 0x2000 else asc
        if cur and w + cw > width_mm:
            out.append(cur)
            cur, w = "", 0.0
        cur += ch
        w += cw
    if cur:
        out.append(cur)
    return out or [""]


def scale_str(scale: float) -> str:
    """比例文本：1:5 / 2:1（放大）。"""
    scale = float(scale)
    if scale >= 1.0:
        return f"1:{scale:g}"
    return f"{1.0 / scale:g}:1"


def scale_tag(scale: float, auto: bool) -> str:
    return f"比例 {scale_str(scale)}（{'自动' if auto else '手动'}）"


def centered_origin(w, h, x0, y0, avail_w, avail_h, scale, top_anchor=False):
    """把 w×h（数据 mm）居中放进 [x0, x0+avail_w] × [y0, y0+avail_h] 区域，返回图纸原点。"""
    pw, ph = w / scale, h / scale
    if top_anchor:
        return (x0 + max(0.0, (avail_w - pw) / 2.0), y0 + avail_h - ph)
    return (x0 + max(0.0, (avail_w - pw) / 2.0), y0 + max(0.0, (avail_h - ph) / 2.0))
