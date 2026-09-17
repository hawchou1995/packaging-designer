# -*- coding: utf-8 -*-
"""price_lib.py — 报价口径（面积 / 单价 / 总价），公式全部照抄飞书《包装物料成本报价表》。

数据来源（2026-09-17 用 lark-cli 读公式原文，非估值）：
  瓦楞纸箱 sheet（ODFC0U）
    标准纸箱（开槽型）: =(长+A+宽+A+80)*(宽+A+高+A+40)/1e6*2
    围框              : =(长+A+80+宽+A)*(高+A+40)/1e6*2        （三瓦行用 +100/+50）
    盖/半盒/托盘      : =(长+A+2*(高+A)+40)*(宽+A+2*(高+A)+40)/1e6
  网格 sheet（NFYrCO）
    刀卡              : =(长+15)*(高+15)*张数/1e6
  隔板 sheet（PalnmW）= 材料单价表（元/㎡），本次并入 flute_lib.FLUTES[*]["price"]
  总价 = Σ(面积 × 单价) + 人工费

注意：A（边料余量）在飞书表里是**逐行手填**的经验值（同表内 15/20/30 混用），
      所以这里只给按楞型档的默认值，界面开放可改 —— 与表内某行取同一 A 时数值逐位一致。
"""
from flute_lib import FLUTES, flute_cls

# A 默认值（按楞型档）：飞书表出现频率最高的取值
ALLOW_DEFAULT = {"single": 15.0, "double": 20.0, "triple": 30.0}
# 刀口余量：单/双瓦 (80, 40)；三瓦 (100, 50) —— 见 r5/r8/r11 与 r14/r19/r21/r27 对照
CUT_EXTRA = {"single": (80.0, 40.0), "double": (80.0, 40.0), "triple": (100.0, 50.0)}
GRID_ALLOW = 15.0          # 网格 sheet：刀卡与隔板一律 +15


def allow_default(code: str) -> float:
    return ALLOW_DEFAULT[flute_cls(code)]


def unit_price(code: str) -> float:
    """材料单价（元/㎡），来自隔板 sheet。"""
    return float(FLUTES[code]["price"])


class Quote:
    """一行报价：件名 / 材料 / 展开长 / 展开宽 / 片数 / 面积 m² / 单价 / 金额。"""

    __slots__ = ("part", "code", "blank_l", "blank_w", "pcs", "area", "price", "amount")

    def __init__(self, part, code, blank_l, blank_w, pcs):
        self.part = part
        self.code = code
        self.blank_l = float(blank_l)
        self.blank_w = float(blank_w)
        self.pcs = float(pcs)
        self.area = self.blank_l * self.blank_w * self.pcs / 1e6
        self.price = unit_price(code)
        self.amount = self.area * self.price

    def rows(self, with_price=True):
        r = [(f"{self.part} · 展开", f"{self.blank_l:g} × {self.blank_w:g} × {self.pcs:g} 件"),
             (f"{self.part} · 面积", f"{self.area:.4f} m²")]
        if with_price:
            r += [(f"{self.part} · 单价", f"{self.price:.2f} 元/m²（{FLUTES[self.code]['material']}）"),
                  (f"{self.part} · 金额", f"¥ {self.amount:.2f}")]
        return r


def q_slotted(part, code, L, W, H, allow=None):
    """开槽型（0201/0210/标准纸箱）：=(长+A+宽+A+80)*(宽+A+高+A+40)/1e6*2"""
    a = allow_default(code) if allow is None else float(allow)
    e1, e2 = CUT_EXTRA[flute_cls(code)]
    return Quote(part, code, L + a + W + a + e1, W + a + H + a + e2, 2)


def q_sleeve(part, code, L, W, H, allow=None):
    """围框（0310 箱体）：=(长+A+80+宽+A)*(高+A+40)/1e6*2"""
    a = allow_default(code) if allow is None else float(allow)
    e1, e2 = CUT_EXTRA[flute_cls(code)]
    return Quote(part, code, L + a + e1 + W + a, H + a + e2, 2)


def q_lid(part, code, L, W, H, allow=None):
    """盖 / 半盒 / 托盘：=(长+A+2*(高+A)+40)*(宽+A+2*(高+A)+40)/1e6（H 为罩深/墙高）"""
    a = allow_default(code) if allow is None else float(allow)
    return Quote(part, code, L + a + 2 * (H + a) + 40, W + a + 2 * (H + a) + 40, 1)


def q_card(part, code, L, H, pcs, allow=GRID_ALLOW):
    """刀卡：=(长+15)*(高+15)*张数/1e6"""
    return Quote(part, code, L + allow, H + allow, pcs)


def total(quotes, labor=0.0, qty=1.0):
    area = sum(q.area for q in quotes)
    paper = sum(q.amount for q in quotes)
    per_set = paper + float(labor)
    return dict(area=area, paper=paper, labor=float(labor), qty=float(qty),
                per_set=per_set, amount=per_set * float(qty))


def summary_rows(quotes, labor=0.0, qty=1.0, with_unit=True):
    """界面 / 参数表用：分件行 + 合计行。"""
    rows = []
    for q in quotes:
        rows += q.rows(with_unit)
    t = total(quotes, labor, qty)
    rows += [("— 面积合计", f"{t['area']:.4f} m²"),
             ("— 纸材合计", f"¥ {t['paper']:.2f}")]
    if labor:
        rows += [("— 人工费", f"¥ {t['labor']:.2f}")]
    rows += [("— 每套", f"¥ {t['per_set']:.2f}")]
    if abs(qty - 1.0) > 1e-9:
        rows += [(f"— 总价（×{qty:g} 套）", f"¥ {t['amount']:.2f}")]
    return rows, t


# ---------------------------------------------------------------- 模块级封装
def quote_box(box, plan, allow=None, labor=0.0, qty=1.0):
    """按箱型 + 计划（backend.box_plan 的输出）出报价。

    分件口径：0201 一片开槽型；0310 围框 + 上盖 + 下盖；0312 底箱 + 天盖。
    """
    p = plan["p"]
    fl = plan["flutes"]
    A = allow or {}
    if box == "0201":
        q = [q_slotted("箱体", fl["body"], p.L, p.W, p.H, A.get("body"))]
    elif box == "0310":
        q = [q_sleeve("围框", fl["sleeve"], p.L, p.W, p.sleeve_H, A.get("sleeve")),
             q_lid("上盖", fl["cap_top"], p.L, p.W, p.d_cover, A.get("cap_top")),
             q_lid("下盖", fl["cap_bottom"], p.L, p.W, p.d_cover, A.get("cap_bottom"))]
    else:
        q = [q_lid("底箱", fl["base"], p.base_L, p.base_W, p.H, A.get("base")),
             q_lid("天盖", fl["lid"], p.L, p.W, p.cover_depth, A.get("lid"))]
    return summary_rows(q, labor, qty)


def quote_grid(plan, code_cards, code_seps=None, allow=GRID_ALLOW,
               labor=0.0, qty=1.0):
    """网格刀卡：长卡/短卡按「张数」计，隔板按张数计（飞书 网格 + 隔板 口径）。"""
    p, d = plan["p"], plan["d"]
    code_seps = code_seps or code_cards
    q = [q_card("长刀卡", code_cards, d["Lc"], d["cell_h"], d["cards_long_total"], allow),
         q_card("短刀卡", code_cards, d["Wc"], d["cell_h"], d["cards_short_total"], allow)]
    if d.get("seps_total"):
        q.append(q_card("隔板", code_seps, p.L, p.W, d["seps_total"], allow))
    return summary_rows(q, labor, qty)
