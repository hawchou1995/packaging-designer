# -*- coding: utf-8 -*-
"""读参考图纸，提取 30mm 折边相关的事实（文字标注 + 几何线段），供实现前对齐口径。

只读不写原图；输出到 _foldref/ 供人工核对。
用法：python ref_fold_probe.py <pdf路径> [dwg路径]
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "_foldref")
os.makedirs(OUT, exist_ok=True)

KEY = ("折", "边", "30", "缓冲", "刀卡", "网格", "内衬", "搭", "翻")


def probe_pdf(path):
    import fitz
    doc = fitz.open(path)
    print(f"PDF 页数: {len(doc)}  尺寸: {doc[0].rect}")
    texts, all_words = [], []
    for pno, page in enumerate(doc):
        for w in page.get_text("words"):
            all_words.append((pno, w[4], round(w[0]), round(w[1])))
        txt = page.get_text()
        if txt.strip():
            texts.append((pno, txt))
    print(f"文字片段总数: {len(all_words)}")
    hits = [w for w in all_words if any(k in w[1] for k in KEY)]
    print(f"含关键词的文字: {len(hits)}")
    for h in hits[:80]:
        print(f"   p{h[0]}  «{h[1]}»  @({h[2]},{h[3]})")
    with open(os.path.join(OUT, "words.txt"), "w", encoding="utf-8") as fh:
        for pno, t, x, y in all_words:
            fh.write(f"p{pno}\t({x},{y})\t{t}\n")
    with open(os.path.join(OUT, "text.txt"), "w", encoding="utf-8") as fh:
        for pno, t in texts:
            fh.write(f"=== page {pno} ===\n{t}\n")
    # 线段统计：看看能否量出折边长度（30mm 对应多少 pt）
    segs = []
    for pno, page in enumerate(doc):
        for d in page.get_drawings():
            for it in d["items"]:
                if it[0] == "l":
                    a, b = it[1], it[2]
                    segs.append((pno, round(a.x, 2), round(a.y, 2), round(b.x, 2), round(b.y, 2)))
                elif it[0] == "re":
                    r = it[1]
                    segs.append((pno, round(r.x0, 2), round(r.y0, 2), round(r.x1, 2), round(r.y1, 2)))
    with open(os.path.join(OUT, "segs.txt"), "w", encoding="utf-8") as fh:
        for s in segs:
            fh.write("\t".join(str(v) for v in s) + "\n")
    print(f"线段/矩形记录: {len(segs)}")
    short = [s for s in segs if s[0] == 0 and abs(s[3] - s[1]) < 3 and abs(s[4] - s[2]) > 10]
    print(f"首页竖短线(可能是折弯线): {len(short)}")
    for s in short[:15]:
        print("   ", s)
    return doc


def probe_dwg(path):
    import ezdxf
    try:
        doc = ezdxf.readfile(path)
    except Exception as e:
        print("DWG 直接读取失败（ezdxf 只读 DXF）:", e)
        return None
    print("DXF 可用")
    return doc


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    p = sys.argv[1]
    if p.lower().endswith(".pdf"):
        probe_pdf(p)
    else:
        probe_dwg(p)
    print("\n提取结果目录:", OUT)


if __name__ == "__main__":
    main()
