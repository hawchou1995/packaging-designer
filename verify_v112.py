# -*- coding: utf-8 -*-
"""verify_v112.py — 1.0.12 折边版专项验收（3D / DXF / 摘要口径）

断言：
  A. 单层格架 3D 实体 —— 折边是**与刀卡垂直的竖板**（薄向 = 卡长方向），高 = 刀卡高；
  B. 整叠 3D 包围盒 = 容器内尺寸 L×W×H（折边不外凸 → 装配后正好落进容器）；
  C. 层叠高度 = 层数×Hc + 隔板 + 底/顶；
  D. DXF 展开：长/短卡轮廓长度 = L/W + 2×fold_len_out，FOLD 图层点划线在 fold_len_out 与 blank−fold_len_out；
  E. 摘要：折边行/展开行与模型一致。
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "core"))
import importlib.util                               # noqa: E402

OUT = os.path.join(HERE, "_v112")
os.makedirs(OUT, exist_ok=True)
n_ok = n_all = 0


def ck(cond, msg):
    global n_ok, n_all
    n_all += 1
    if cond:
        n_ok += 1
        print("  ✓", msg)
    else:
        print("  ✗", msg)


def load(n, p):
    s = importlib.util.spec_from_file_location(n, p)
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


gc = load("gc", os.path.join(HERE, "core", "grid_core.py"))
gm = load("gm", os.path.join(HERE, "core", "grid_model.py"))

CASES = [("580×380 格65×38 t5 V1", dict(L=580, W=380, H=380, pl=65, pw=38, ph=85, t=5.0, version=1)),
         ("1140×740 格181×96 t6 V2", dict(L=1140, W=740, H=550, pl=181, pw=96, ph=100, t=6.0,
                                         version=2))]

for tag, cfg in CASES:
    print(f"--- {tag} ---")
    p = gc.Params(**cfg)
    _e, _r, d = gc.report(p)
    t, Hc = d["t"], d["cell_h"]
    fl_net, fl_out = d["fold_len"], d["fold_len_out"]
    ck(d["fold_l"] or d["fold_w"], f"折边已触发（长卡={d['fold_l']} 短卡={d['fold_w']}）")

    lay = gm.items_layer(p, d)
    tabs = [q for q in lay if q["name"].startswith(("LF", "SF"))]
    ck(len(tabs) == len(gm._fold_tabs(p, d)),
       f"3D 折边板 {len(tabs)} 块 = 俯视投影 {len(gm._fold_tabs(p, d))} 块")
    bad = []
    for q in tabs:
        dx, dy, dz = q["size"]
        is_long = q["name"].startswith("LF")
        # 长卡折边：薄向 X=t、长向 Y=fl；短卡折边：薄向 Y=t、长向 X=fl；高 = Hc
        ok = (abs(dz - Hc) < 1e-6 and
              (abs(dx - t) < 1e-6 and abs(dy - fl_net) < 1e-6 if is_long
               else abs(dy - t) < 1e-6 and abs(dx - fl_net) < 1e-6))
        if not ok:
            bad.append(f"{q['name']} 尺寸 {dx:g}×{dy:g}×{dz:g}")
    ck(not bad, f"折边板与刀卡垂直、高=刀卡高 {Hc:g}" + ("" if not bad else f"（异常 {bad[:3]}）"))

    it = gm.items(p, d)
    xs = [q["center"][0] + q["size"][0] / 2 for q in it]
    xe = [q["center"][0] - q["size"][0] / 2 for q in it]
    ys = [q["center"][1] + q["size"][1] / 2 for q in it]
    ye = [q["center"][1] - q["size"][1] / 2 for q in it]
    zs = [q["center"][2] + q["size"][2] / 2 for q in it]
    ck(abs((max(xs) - min(xe)) - p.L) < 1e-6 and abs((max(ys) - min(ye)) - p.W) < 1e-6,
       f"整叠包围盒 XY = {max(xs) - min(xe):g}×{max(ys) - min(ye):g} = 容器 {p.L:g}×{p.W:g}（折边不外凸）")
    h_exp = d["layers"] * Hc + d["seps_total"] * d.get("st", t)
    ck(abs(max(zs) - h_exp) < 1e-6, f"整叠高 {max(zs):g} = 预期 {h_exp:g}")

    # DXF
    dxf = gm.write_dxf(p, d, os.path.join(OUT, f"{cfg['version']}_{int(p.L)}.dxf"))
    import ezdxf
    doc = ezdxf.readfile(dxf)
    msp = doc.modelspace()
    folds = [e for e in msp if e.dxf.layer == "FOLD"]
    ck(len(folds) == (2 if d.get("fold_l") else 0) + (2 if d.get("fold_w") else 0),
       f"DXF FOLD 折弯线 {len(folds)} 条（长卡 2 + 短卡 2）")
    ox = p.L + 90.0
    expL = [fl_out, d["blank_L"] - fl_out] if d.get("fold_l") else []
    expW = [ox + fl_out, ox + d["blank_W"] - fl_out] if d.get("fold_w") else []
    pos = sorted(round(e.dxf.start.x, 3) for e in folds
                 if abs(e.dxf.start.x - e.dxf.end.x) < 1e-9)
    exp = sorted(expL + expW)
    ck(len(pos) == len(exp) and all(abs(a - b) < 1e-6 for a, b in zip(pos, exp)),
       f"折弯线位置 {pos} = 预期 {exp}（长卡展开 {d['blank_L']:g} = {p.L:g}+2×{fl_out:g}，"
       f"短卡展开 {d['blank_W']:g}）")
    widths = []
    for e in msp:
        if e.dxf.layer != "CUT" or e.dxftype() != "LWPOLYLINE":
            continue
        pts = [(q[0], q[1]) for q in e.get_points()]
        widths.append(round(max(q[0] for q in pts) - min(q[0] for q in pts), 3))
    ck(any(abs(w - d["blank_L"]) < 1e-6 for w in widths),
       f"DXF 长卡轮廓含折边 = 展开 {d['blank_L']:g}（本图轮廓宽 {sorted(set(widths))}）")
    if d.get("fold_w"):
        ck(any(abs(w - d["blank_W"]) < 1e-6 for w in widths),
           f"DXF 短卡轮廓含折边 = 展开 {d['blank_W']:g}")

    rows = dict(_r)
    ck(any("折边" in k for k in rows), "摘要含折边行")
    ck(any("展开长" in k for k in rows), "摘要含展开长行")
    print()

print(f"=== 结果 ===\n{n_ok}/{n_all} 通过")
sys.exit(0 if n_ok == n_all else 1)
