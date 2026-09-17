# -*- coding: utf-8 -*-
"""从参考图（PM150 SNP210，1:5）里量出「刀卡两端折边」的实际画法：
   - 折边长度/厚度（换回真实 mm）
   - 折边相对刀卡本体的方向（沿长度 or 垂直）
   - 折弯线是怎么画的（实线/虚线、位置）
只在 _foldref/segs.txt 上做几何分析，不碰原图。
"""
import math
import os

HERE = os.path.dirname(os.path.abspath(__file__))
SEGS = os.path.join(HERE, "_foldref", "segs.txt")
PT_PER_MM_REAL = 2.83465 / 5.0          # 图幅 1:5


def load():
    segs = []
    for line in open(SEGS, encoding="utf-8"):
        p = line.rstrip("\n").split("\t")
        if len(p) != 5:
            continue
        x0, y0, x1, y1 = (float(v) for v in p[1:])
        segs.append((x0, y0, x1, y1))
    return segs


def mm(v):
    return v / PT_PER_MM_REAL


def main():
    segs = load()
    print(f"线段 {len(segs)} 条；1mm 实际 = {PT_PER_MM_REAL:.4f} pt（图幅 1:5）")
    # 只保留长度 > 3pt 的线段，避免 CAD 输出的碎线
    big = []
    for x0, y0, x1, y1 in segs:
        L = math.hypot(x1 - x0, y1 - y0)
        if L > 3.0:
            big.append((x0, y0, x1, y1, L))
    print(f"其中 > 3pt 的 {len(big)} 条")

    # 找“长条轮廓”：很长的水平轮廓线（刀卡侧视的长边）
    horiz = [s for s in big if abs(s[1] - s[3]) < 0.8 and s[4] > 40]
    horiz.sort(key=lambda s: -s[4])
    print("\n=== 长水平线（候选刀卡轮廓长边）Top 12 ===")
    for s in horiz[:12]:
        print(f"  y={s[1]:7.2f}  x {s[0]:7.2f}→{s[2]:7.2f}   长 {mm(s[4]):7.1f}mm  (纸面 {s[4]:.1f}pt)")
    if horiz:
        ytops = sorted({round(s[1], 1) for s in horiz})
        print("  y 值集合:", ytops[:20])

    # 找“折边小矩形”：短的一对平行线，长 ≈ 30mm（=17.0pt）左右
    print("\n=== 长度在 8~40pt 的线段，按长度分布 ===")
    buckets = {}
    for x0, y0, x1, y1, L in big:
        if 8 <= L <= 40:
            buckets.setdefault(round(L), []).append((x0, y0, x1, y1))
    for L in sorted(buckets):
        print(f"  {L:4d}pt = {mm(L):6.1f}mm  ×{len(buckets[L]):3d}   例如 {[(round(a,1),round(b,1),round(c,1),round(d,1)) for a,b,c,d in buckets[L][:2]]}")

    # 针对 y 在长线附近、长度≈30mm 的竖线（折边高度/折弯线）
    print("\n=== 长度≈30mm(15~19pt) 的线段全部列出 ===")
    for L in range(15, 20):
        for x0, y0, x1, y1 in buckets.get(L, []):
            kind = "竖" if abs(x0 - x1) < 0.8 else ("横" if abs(y0 - y1) < 0.8 else "斜")
            print(f"  {L}pt≈{mm(L):4.1f}mm {kind}  ({x0:.1f},{y0:.1f})→({x1:.1f},{y1:.1f})  y范围 {min(y0,y1):.1f}~{max(y0,y1):.1f}")


if __name__ == "__main__":
    main()
