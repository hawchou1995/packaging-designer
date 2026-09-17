# -*- coding: utf-8 -*-
"""楞型库：数据源 = 飞书《包装物料成本报价表》
   瓦楞纸箱 sheet（ODFC0U）楞型/厚度/边压/耐破 + 隔板 sheet（PalnmW）材料单价。

每个条目：
  code     应用内代号（也用于文件名/材料栏短串）
  flutes   实际楞型（B / BC / C / AA / ABC / AAA）
  material 飞书「材料名称」原文（报价与材料栏用）
  name     显示名
  t        纸板厚度 mm（几何用）
  edge/burst 边压 N/m / 耐破 kPa（None = 飞书表未维护）
  price    元/㎡（隔板 sheet 采购单价）
  cls      档位 single/double/triple —— 决定余量默认值与参数区间
"""
import json
import os

FLUTES = {
    "B": dict(code="B", flutes="B", cls="single", material="A版单瓦",
              name="A版 单瓦（B 楞）", t=3.0, edge=None, burst=None, price=2.06,
              note="边压/耐破飞书表未维护", source="feishu:隔板+瓦楞纸箱"),
    "BC": dict(code="BC", flutes="BC", cls="double", material="A版双瓦",
               name="A版 双瓦（BC 楞）", t=7.0, edge=None, burst=None, price=2.68,
               note="边压/耐破飞书表未维护", source="feishu:隔板+瓦楞纸箱"),
    "C": dict(code="C", flutes="C", cls="single", material="超密封K单瓦",
              name="超密封 K 单瓦（C 楞）", t=4.0, edge=None, burst=None, price=3.85,
              note="边压/耐破飞书表未维护", source="feishu:隔板+瓦楞纸箱"),
    "BC-K": dict(code="BC-K", flutes="BC", cls="double", material="超密封K双瓦",
                 name="超密封 K 双瓦（BC 楞）", t=7.0, edge=5550, burst=961, price=6.33,
                 note="", source="feishu"),
    "BC-HS": dict(code="BC-HS", flutes="BC", cls="double", material="高强超密封",
                  name="高强超密封（BC 楞）", t=7.0, edge=10000, burst=2400, price=10.80,
                  note="", source="feishu"),
    "AA": dict(code="AA", flutes="AA", cls="double", material="AA双瓦",
               name="AA 双瓦（AA 楞）", t=10.0, edge=None, burst=None, price=11.25,
               note="厚度按 GB/T 6544 A+A 名义值 10mm；边压/耐破飞书表未维护",
               source="feishu:隔板 + GB/T6544"),
    "ABC": dict(code="ABC", flutes="ABC", cls="triple", material="ABC三瓦",
                name="ABC 三瓦", t=12.0, edge=18500, burst=2295, price=15.93,
                note="", source="feishu"),
    "AAA": dict(code="AAA", flutes="AAA", cls="triple", material="AAA三瓦",
                name="AAA 三瓦", t=15.0, edge=21000, burst=3100, price=26.80,
                note="", source="feishu"),
}

# 按楞型档给绘图参数的合理区间（应用内校验 + 旁注来源）
RANGES = {
    "single": dict(glue_w=(35.0, 40.0), flap_gain=(1.0, 3.0), flap_reduce=(1.0, 3.0),
                   slot_w=(6.0, 10.0), src="GB/T 6543-2025 通例 + 行业实践"),
    "double": dict(glue_w=(45.0, 50.0), flap_gain=(3.0, 4.5), flap_reduce=(3.0, 4.5),
                   slot_w=(8.0, 12.0), src="包材需求表（BC 8/5/3.5-4.5）+ GB/T 6543"),
    "triple": dict(glue_w=(50.0, 55.0), flap_gain=(4.0, 6.0), flap_reduce=(4.0, 6.0),
                   slot_w=(10.0, 14.0), src="GB/T 6543 通例（三层加放）"),
}

RANGES_BOX = {
    "0310": dict(gap=(1.0, 3.0), src_box="盖内与围框外单边间隙（FEFCO 0310 实践）"),
    "0312": dict(box_gap=(1.0, 3.0), src_box="天盖与底箱单边间隙（FEFCO 0312 实践）"),
}


def flute_cls(code: str) -> str:
    """楞型档：single / double / triple（按材料表显式定义，不靠厚度猜）。"""
    return FLUTES[code]["cls"]


def flute(code: str) -> dict:
    return FLUTES[code]


def ranges_for(code: str, box: str = None) -> dict:
    """按楞型代号取参数区间（兼容旧签名：可传厚度数值）。"""
    if isinstance(code, (int, float)):
        t = float(code)
        cls = "single" if t < 5.5 else ("double" if t < 10 else "triple")
    else:
        cls = flute_cls(code)
    r = dict(RANGES[cls])
    if box in RANGES_BOX:
        b = dict(RANGES_BOX[box])
        b["src"] = b.pop("src_box", "")
        r.update(b)
    return r


def materials():
    """[(code, 显示名)] 供界面按钮。"""
    return [(c, f["name"]) for c, f in FLUTES.items()]


def dump_json(path: str):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(dict(flutes=FLUTES, ranges=RANGES, box=RANGES_BOX), fh,
                  ensure_ascii=False, indent=2)


if __name__ == "__main__":
    dump_json(os.path.join(os.path.dirname(os.path.abspath(__file__)), "flute_lib.json"))
    for k, v in FLUTES.items():
        print(f"{k:6s} t={v['t']:>4g}  ¥{v['price']:>6.2f}/㎡  {v['name']}")
