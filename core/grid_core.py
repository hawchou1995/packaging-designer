# -*- coding: utf-8 -*-
"""瓦楞刀卡（网格）参数化设计核心 v2 —— 口径依据《包材需求各部门汇总.xlsx》「刀卡设计公式」
+ 用户 2026-09-17 五项修正：

v2 关键修正（相对 v1）：
  ① 刀卡长度 = 容器内尺寸（卡端伸至箱壁）；槽距卡端 = 边距 margin（≥6，卡端留料固定/防劈裂）
  ② 边距约束：长/短向 margin ≥ 6（不足则减少格数）
  ③ 网格按层制作（每层一件格架，卡高 = 每格高 = ceil5(产品高)）；
     层间隔板：中间必有（层数−1 张）；底部/顶部按指定
  ④ 收容数 = 格数 × 层数（每格每层一件产品）
公式（表格原口径）：
  每格 cell = 产品含缓冲外尺寸（高度向上取整到 5）
  n = ROUNDDOWN((容器内 − 3t) / (cell + MAX(t,6)))；再受 margin ≥ 6 约束
  margin = (内 − cell×n − t×(n+1)) / 2
  层数：堆叠 = 底? + 每层(cell_h) + 层间 t + 顶?  ≤ 容器内高
  长边张数 = 短向格数+1（每层）；短边张数 = 长向格数+1（每层）
"""
import math
from dataclasses import dataclass


def ceil5(x):
    return int(math.ceil(x / 5.0 - 1e-9)) * 5


PAD_LABEL = {"both": "底部+顶部", "bottom": "底部", "top": "顶部", "none": "无"}
MARGIN_MIN = 6.0


@dataclass
class Params:
    L: float = 580.0
    W: float = 380.0
    H: float = 380.0
    pl: float = 65.0
    pw: float = 38.0
    ph: float = 85.0
    t: float = 5.0
    version: int = 1
    input_mode: str = "inner"
    pads: str = "both"          # 顶/底隔板：both/bottom/top/none（中间隔板恒有）
    slot_clear: float = 0.0
    sep_t: float = 0.0         # 隔板厚度；0 → 与刀卡同厚
    name: str = "瓦楞刀卡网格"


def design(p: Params):
    d = {}
    t = p.t
    v = 1 if p.version == 1 else 2
    cell_l = p.pl if v == 1 else p.pw
    cell_w = p.pw if v == 1 else p.pl
    cell_h = ceil5(p.ph)
    d.update(cell_l=cell_l, cell_w=cell_w, cell_h=cell_h, t=t, version=v)

    def n_margin(container, cell, is_insert):
        base = (container - t) if is_insert else (container - 3 * t)
        n = max(int(math.floor(base / (cell + max(t, 6.0)) + 1e-9)), 1)
        margin = (container - cell * n - t * (n + 1)) / 2.0
        while n > 1 and margin < MARGIN_MIN - 1e-9:     # 边距 ≥ 6 硬约束
            n -= 1
            margin = (container - cell * n - t * (n + 1)) / 2.0
        if is_insert:
            margin = (container - cell * n - t * (n + 1)) / 2.0
        return n, margin

    is_ins = (p.input_mode == "insert")
    n_l, margin_l = n_margin(p.L, cell_l, is_ins)
    n_w, margin_w = n_margin(p.W, cell_w, is_ins)
    d.update(n_l=n_l, n_w=n_w, margin_l=margin_l, margin_w=margin_w)

    # 刀卡 = 容器内尺寸全长（卡端伸至箱壁）
    d.update(Lc=p.L, Wc=p.W)

    # 层数：底? + L×cell_h + (L−1)×t(层间) + 顶? ≤ H
    pads = p.pads if p.pads in PAD_LABEL else "both"
    st = p.sep_t if p.sep_t > 0 else t          # 隔板厚度（顶/底/层间）
    pad_tb = {"both": 2, "bottom": 1, "top": 1, "none": 0}[pads]
    pad_total = pad_tb * st

    def stack_h(n):
        return n * cell_h + (n - 1) * st + pad_total

    layers = max(int(math.floor((p.H - pad_total + st) / (cell_h + st) + 1e-9)), 1)
    while layers > 1 and stack_h(layers) > p.H + 1e-9:
        layers -= 1
    d.update(pads=pads, pad_tb=pad_tb, layers=layers, st=st,
             seps_mid=layers - 1, seps_tb=pad_tb, seps_total=layers - 1 + pad_tb,
             H_stack=stack_h(layers), H_slack=p.H - stack_h(layers))

    d.update(cards_long=n_w + 1, cards_short=n_l + 1,
             slots_long=n_l + 1, slots_short=n_w + 1,
             pitch_l=cell_l + t, pitch_w=cell_w + t,
             slot_w=t + p.slot_clear, slot_depth=cell_h / 2.0)

    d["capacity"] = n_l * n_w * layers
    d["cards_long_total"] = d["cards_long"] * layers
    d["cards_short_total"] = d["cards_short"] * layers
    per_layer = (d["cards_long"] * p.L + d["cards_short"] * p.W) * cell_h
    d["area_cards"] = per_layer * layers / 1e6
    d["area_seps"] = d["seps_total"] * p.L * p.W / 1e6
    d["margin_ok"] = (margin_l >= MARGIN_MIN - 1e-9) and (margin_w >= MARGIN_MIN - 1e-9)
    return d


def report(p: Params):
    d = design(p)
    vtxt = "V1 长对长（内衬长向 = 产品长）" if d["version"] == 1 else "V2 长对宽（内衬长向 = 产品宽）"
    rows = [
        ("版本", vtxt),
        ("容器内尺寸", f"{p.L:g} × {p.W:g} × {p.H:g}"),
        ("产品+缓冲", f"{p.pl:g} × {p.pw:g} × {p.ph:g}"),
        ("每格尺寸", f"{d['cell_l']:g} × {d['cell_w']:g} × {d['cell_h']:g}"),
        ("长边格数", f"{d['n_l']}"),
        ("短边格数", f"{d['n_w']}"),
        ("边距（长/短，卡端→槽）", f"{d['margin_l']:g} / {d['margin_w']:g}（≥{MARGIN_MIN:g} ✓）"),
        ("长刀卡", f"每层 {d['cards_long']} 张（{d['Lc']:g}×{d['cell_h']:g}，{d['slots_long']} 槽）"
                   f" × {d['layers']} 层 = {d['cards_long_total']} 张"),
        ("短刀卡", f"每层 {d['cards_short']} 张（{d['Wc']:g}×{d['cell_h']:g}，{d['slots_short']} 槽）"
                   f" × {d['layers']} 层 = {d['cards_short_total']} 张"),
        ("层数", f"{d['layers']}（网格按层制作 = {d['layers']} 件）"),
        ("隔板", f"中间 {d['seps_mid']} 张（必有）+ 底/顶 {d['seps_tb']} 张（{PAD_LABEL[d['pads']]}）"
                 f" = {d['seps_total']} 张 {p.L:g}×{p.W:g}×{d['st']:g}"),
        ("堆叠高度", f"{d['H_stack']:g} ≤ {p.H:g}（余量 {d['H_slack']:g}）"),
        ("收容数", f"{d['capacity']} = {d['n_l']}×{d['n_w']}×{d['layers']}"),
        ("用纸（刀卡/隔板）", f"{d['area_cards']:.4f} / {d['area_seps']:.4f} m²"),
    ]
    errs = []
    if not d["margin_ok"]:
        errs.append("边距 < 6，格数放不下")
    if d["H_stack"] > p.H + 1e-9:
        errs.append("堆叠超限")
    return errs, rows, d


def param_lines_zh(p: Params):
    _, _, d = report(p)
    return [
        f"{p.name}（{'V1 长对长' if d['version'] == 1 else 'V2 长对宽'}）",
        f"容器内尺寸 {p.L:g}×{p.W:g}×{p.H:g}；产品+缓冲 {p.pl:g}×{p.pw:g}×{p.ph:g}",
        f"每格 {d['cell_l']:g}×{d['cell_w']:g}×{d['cell_h']:g}；纸板厚 {d['t']:g}；边距 {d['margin_l']:g}/{d['margin_w']:g}",
        f"格数 {d['n_l']}×{d['n_w']}；层数 {d['layers']}；收容数 {d['capacity']}",
        f"长刀卡 {d['cards_long']} 张/层（{d['Lc']:g}×{d['cell_h']:g}，{d['slots_long']} 槽）×{d['layers']} 层"
        f" = {d['cards_long_total']} 张；",
        f"短刀卡 {d['cards_short']} 张/层（{d['Wc']:g}×{d['cell_h']:g}，{d['slots_short']} 槽）×{d['layers']} 层"
        f" = {d['cards_short_total']} 张",
        f"槽深 {d['slot_depth']:g}（=卡高/2）；槽宽 {d['slot_w']:g}；长卡上开槽 / 短卡下开槽",
        f"隔板：中间 {d['seps_mid']} 张（必有）+ 底/顶 {d['seps_tb']} 张（{PAD_LABEL[d['pads']]}），"
        f"共 {d['seps_total']} 张 {p.L:g}×{p.W:g}×{d['t']:g}",
        f"刀卡长度 = 容器内尺寸（卡端伸至箱壁）；槽距卡端 = 边距（≥6）",
        "口径：n=ROUNDDOWN((内−3t)/(每格+MAX(t,6))) 且边距≥6；收容数=格数×层数",
        "（依据《包材需求各部门汇总.xlsx》「刀卡设计公式」+ 用户修正）",
    ]
