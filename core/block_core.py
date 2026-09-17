# -*- coding: utf-8 -*-
"""仿形块（垫块开槽）参数化核心。

口径（对应「包材需求各部门汇总.xlsx」仿形卡槽行：总长 / 槽宽 / 数量 / 间隔 / 两边均分 N / 左边 O / 右边 P=2N−O）：
  给 块长 L × 块宽 W × 块高 H；开槽 长 sl（< L）× 宽 sw（≤ W；sw==W 时为贯穿开槽）× 高 sh（< H）；相邻槽间距 gap
  槽数 n = ROUNDDOWN((L + gap) / (sl + gap))（放得下的最多整数个）
  边距：总量 = L − n·sl − (n−1)·gap
        均分 → 两端各 量/2
        不一致 → 给定左端 margin_left，右端 = 总量 − 左端
  槽宽 sw < W 时按盲槽处理（居中，两侧各 (W−sw)/2）。
"""
import math
from dataclasses import dataclass


@dataclass
class Params:
    L: float = 1000.0
    W: float = 100.0
    H: float = 100.0
    sl: float = 50.0
    sw: float = 70.0
    sh: float = 50.0
    gap: float = 40.0
    margin_left: float = None      # None = 两端均分；否则给左端、右端算
    open_side: str = "front"       # 单边贯穿槽的开口侧：front=前侧(y-)，back=后侧(y+)
    material: str = ""
    name: str = "仿形块"


def design(p: Params):
    d = {}
    if not (0 < p.sl < p.L):
        raise SystemExit("槽长须 0 < sl < 块长 L")
    if not (0 < p.sw <= p.W):
        raise SystemExit("槽宽须 0 < sw ≤ 块宽 W")
    if not (0 < p.sh < p.H):
        raise SystemExit("槽高须 0 < sh < 块高 H")
    n = int(math.floor((p.L + p.gap) / (p.sl + p.gap) + 1e-9))
    if n < 1:
        raise SystemExit("块长放不下 1 个槽")
    used = n * p.sl + (n - 1) * p.gap
    total_m = p.L - used
    m_even = total_m / 2.0
    if p.margin_left is None:
        ml = mr = m_even
        mode = "两端均分"
    else:
        ml = p.margin_left
        mr = total_m - ml
        if ml < -1e-9 or mr < -1e-9:
            raise SystemExit(f"左边距 {ml:g} 超出可用边距总量 {total_m:g}")
        mode = "两端不一致"
    slots = [(ml + i * (p.sl + p.gap), ml + i * (p.sl + p.gap) + p.sl) for i in range(n)]
    through = abs(p.sw - p.W) < 1e-9
    sw_eff = p.W if through else p.sw
    if through:
        sy0, sy1, wy0, wy1, wall_w = 0.0, p.W, None, None, 0.0
    elif p.open_side == "back":
        sy0, sy1 = p.W - p.sw, p.W
        wy0, wy1, wall_w = 0.0, p.W - p.sw, p.W - p.sw
    else:
        sy0, sy1 = 0.0, p.sw
        wy0, wy1, wall_w = p.sw, p.W, p.W - p.sw
    v_net = p.L * p.W * p.H - n * p.sl * sw_eff * p.sh
    d.update(n=n, used=used, margin_total=total_m, margin_even=m_even,
             margin_mode=mode, margin_l=ml, margin_r=mr, slots=slots,
             through=through, sw_eff=sw_eff, side_wall=wall_w,
             sy0=sy0, sy1=sy1, wy0=wy0, wy1=wy1,
             v_block=p.L * p.W * p.H / 1e3, v_net=v_net / 1e3)
    return d


def report(p: Params):
    d = design(p)
    rows = [
        ("垫块", f"{p.L:g} × {p.W:g} × {p.H:g}"),
        ("开槽", f"{p.sl:g} × {p.sw:g} × {p.sh:g}"
                 f"（{'全贯穿（槽宽=块宽）' if d['through'] else f'单边贯穿：{"前" if p.open_side != "back" else "后"}侧开口，对侧墙厚 {d["side_wall"]:g}'}）"),
        ("间距", f"{p.gap:g}"),
        ("可开槽数", f"{d['n']} 个"),
        ("边距（总量）", f"{d['margin_total']:g}"),
        ("边距（{mode}）".format(mode=d["margin_mode"]),
         f"均分参考 {d['margin_even']:g}；实际 左 {d['margin_l']:g} / 右 {d['margin_r']:g}"),
        ("槽位（左端距离）", ", ".join(f"{a:g}~{b:g}" for a, b in d["slots"])),
        ("体积", f"块体 {d['v_block']:.1f} cm³ → 净体积 {d['v_net']:.1f} cm³"),
    ]
    errs = []
    if d["margin_l"] < 0 or d["margin_r"] < 0:
        errs.append("边距为负")
    return errs, rows, d


def param_lines_zh(p: Params):
    _, _, d = report(p)
    return [
        f"{p.name} {p.L:g}×{p.W:g}×{p.H:g}；开槽 {p.sl:g}×{p.sw:g}×{p.sh:g} × {d['n']} 个；间距 {p.gap:g}",
        f"边距：{d['margin_mode']} —— 左 {d['margin_l']:g} / 右 {d['margin_r']:g}（总量 {d['margin_total']:g}，均分参考 {d['margin_even']:g}）",
        f"槽型：{'全贯穿（槽宽 = 块宽）' if d['through'] else f'单边贯穿（{p.open_side} 侧开口，对侧墙厚 {d["side_wall"]:g}）'}；槽深 {p.sh:g}（自顶面）",
        f"净体积 {d['v_net']:.1f} cm³（块体 {d['v_block']:.1f} cm³）",
    ]
