# -*- coding: utf-8 -*-
"""楞型库：数据源 = 飞书「包材汇总」表（sheet ODFC0U，2026-09-17 lark-cli 实读）
+ 国标/国际口径补全与合理区间（GB/T 6544 / GB/T 6543-2025 / FEFCO）。

每个条目：code 楞型代号、name 材料名、t 纸板厚度 mm、edge 边压 N/m、burst 耐破 kPa、
ranges 供应用校验的绘图参数合理区间（含来源标注）。
"""
import json
import os

FLUTES = {
    "B": dict(code="B", name="A版 单瓦（B 楞）", t=3.0, edge=None, burst=None,
              note="飞书表厚度列缺失→按 GB/T 6544 B 楞典型值补", source="feishu+GB/T6544"),
    "BC": dict(code="BC", name="A版 双瓦（BC 楞）", t=7.0, edge=5550, burst=961,
               note="", source="feishu"),
    "BC-HS": dict(code="BC-HS", name="超密封 K 双瓦（高强 BC）", t=7.0, edge=10000, burst=2400,
                  note="", source="feishu"),
    "C": dict(code="C", name="超密封 K 单瓦（C 楞）", t=4.0, edge=None, burst=None,
              note="飞书表数值列缺失→按 GB/T 6544 C 楞典型值补", source="feishu+GB/T6544"),
    "ABC": dict(code="ABC", name="ABC 三层（超密封）", t=12.0, edge=18500, burst=2295,
                note="", source="feishu"),
    "AAA": dict(code="AAA", name="AAA 三层（超密封）", t=15.0, edge=21000, burst=3100,
                note="", source="feishu"),
}

# 按"楞型类别"给绘图参数的合理区间（应用内校验 + 旁注来源）
RANGES = {
    # 类别键：由厚度自动归类（单瓦/双瓦/三层）
    "single": dict(glue_w=(35.0, 40.0),        # 接舌长度（单瓦）
                   flap_gain=(1.0, 3.0),       # 外摇盖加放（厚度 <5mm 取小）
                   flap_reduce=(1.0, 3.0),
                   slot_w=(6.0, 10.0),         # 开槽宽
                   src="GB/T 6543-2025 通例 + 行业实践"),
    "double": dict(glue_w=(45.0, 50.0),        # 接舌（双瓦）
                   flap_gain=(3.0, 4.5),       # 外摇盖加放（5–8mm 板厚 +3~4.5）
                   flap_reduce=(3.0, 4.5),
                   slot_w=(8.0, 12.0),
                   src="包材需求表（BC 8/5/3.5-4.5）+ GB/T 6543"),
    "triple": dict(glue_w=(50.0, 55.0),        # 接舌（三层瓦楞）
                   flap_gain=(4.0, 6.0),
                   flap_reduce=(4.0, 6.0),
                   slot_w=(10.0, 14.0),
                   src="GB/T 6543 通例（三层加放）"),
}

# 盒型专属区间
RANGES_BOX = {
    "0310": dict(gap=(1.0, 3.0), src="盖内与围框外单边间隙（FEFCO 0310 实践）"),
    "0312": dict(box_gap=(1.0, 3.0), src="天盖与底箱单边间隙（FEFCO 0312 实践）"),
}


def flute_class(t: float) -> str:
    if t < 5.5:
        return "single"
    if t < 10:
        return "double"
    return "triple"


def flute(code: str) -> dict:
    return FLUTES[code]


def ranges_for(t: float, box: str = None) -> dict:
    r = dict(RANGES[flute_class(t)])
    if box in RANGES_BOX:
        r.update(RANGES_BOX[box])
    return r


def dump_json(path: str):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(dict(flutes=FLUTES, ranges=RANGES, box=RANGES_BOX), fh,
                  ensure_ascii=False, indent=2)


if __name__ == "__main__":
    dump_json(os.path.join(os.path.dirname(os.path.abspath(__file__)), "flute_lib.json"))
    for k, v in FLUTES.items():
        print(k, v["t"], v["name"])
