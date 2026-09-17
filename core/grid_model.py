# -*- coding: utf-8 -*-
"""刀卡网格 3D 模型（按层格架 + 隔板堆叠）+ 导出：STEP / STL / DXF(1:1)。

几何约定：整叠居中于原点，Z 从 0 起。
  每层格架：长卡（沿 X，全长=容器内长，槽自顶向下，槽段保留下半幅）
            短卡（沿 Y，全长=容器内宽，槽自底向上，槽段保留上半幅）
  堆叠：底隔板? + 层1 + 隔板 + 层2 + …… + 顶隔板?（层间隔板恒有）
"""
import struct

import numpy as np


def _card_segments(full_len, slot_centers, t):
    """沿长度方向：端余量/槽/格… 段表 [(xa, xb, is_slot)]。"""
    out = []
    prev = 0.0
    for s in slot_centers:
        out.append((prev, s - t / 2, False))     # 端余量或格
        out.append((s - t / 2, s + t / 2, True))
        prev = s + t / 2
    out.append((prev, full_len, False))
    return [(a, b, k) for (a, b, k) in out if b - a > 1e-9]


def _slot_centers(margin, n_slots, pitch, t):
    return [margin + t / 2 + i * pitch for i in range(n_slots)]


def items_layer(p, d):
    """单层格架（轴测图用；z 自 0 起）。"""
    t, Hc = d["t"], d["cell_h"]
    L, W = p.L, p.W
    n_l, n_w = d["n_l"], d["n_w"]
    x0, y0 = -L / 2.0, -W / 2.0
    out = []

    def add(name, size, center):
        out.append(dict(name=name, size=size, center=center))

    xs = _slot_centers(d["margin_l"], d["slots_long"], d["pitch_l"], t)   # 短卡 X 位置
    ys = _slot_centers(d["margin_w"], d["slots_short"], d["pitch_w"], t)  # 长卡 Y 位置
    # 长卡（沿 X），槽自顶向下
    for j, yc in enumerate(ys):
        for (a, b, is_slot) in _card_segments(L, xs, t):
            w = b - a
            cx = x0 + (a + b) / 2
            if not is_slot:
                add(f"L{j:02d}_f{a:07.1f}", (w, t, Hc), (cx, y0 + yc, Hc / 2))
            else:
                add(f"L{j:02d}_s{a:07.1f}", (w, t, Hc / 2), (cx, y0 + yc, Hc / 4))
    # 折边实体：绕竖直折弯线折 90° → 垂直竖板（30 沿箱壁方向 × Hc 高 × t 厚）
    fl = d.get("fold_len", 0.0)
    if d.get("fold_l"):                       # 长卡两端（沿 X 的两端），折边朝 Y 中线折
        for j, yc in enumerate(ys):
            sy = -1.0 if yc > W / 2.0 else 1.0
            add(f"LF{j:02d}_a", (t, fl, Hc), (x0 + t / 2, y0 + yc + sy * fl / 2, Hc / 2))
            add(f"LF{j:02d}_b", (t, fl, Hc),
                (x0 + L - t / 2, y0 + yc + sy * fl / 2, Hc / 2))
    if d.get("fold_w"):                       # 短卡两端（沿 Y 的两端），折边朝 X 中线折
        for i, xc in enumerate(xs):
            sx = -1.0 if xc > L / 2.0 else 1.0
            add(f"SF{i:02d}_a", (fl, t, Hc), (x0 + xc + sx * fl / 2, y0 + t / 2, Hc / 2))
            add(f"SF{i:02d}_b", (fl, t, Hc),
                (x0 + xc + sx * fl / 2, y0 + W - t / 2, Hc / 2))
    # 短卡（沿 Y），槽自底向上（槽段保留上半幅）
    for i, xc in enumerate(xs):
        for (a, b, is_slot) in _card_segments(W, ys, t):
            w = b - a
            cy = y0 + (a + b) / 2
            if not is_slot:
                add(f"S{i:02d}_f{a:07.1f}", (t, w, Hc), (x0 + xc, cy, Hc / 2))
            else:
                add(f"S{i:02d}_s{a:07.1f}", (t, w, Hc / 2), (x0 + xc, cy, 3 * Hc / 4))
    return out


def items(p, d, axo=False):
    """整叠（底/顶 + 各层 + 层间隔板）；axo=True 时仅单层格架。"""
    if axo:
        return items_layer(p, d)
    t, Hc = d["t"], d["cell_h"]
    st = d.get("st", t)
    L, W = p.L, p.W
    out = []
    z = 0.0
    if d["pads"] in ("both", "bottom"):
        out.append(dict(name="pad_bottom", size=(L, W, st), center=(0, 0, z + st / 2)))
        z += st
    for layer in range(d["layers"]):
        for q in items_layer(p, d):
            out.append(dict(name=f"g{layer}_{q['name']}", size=q["size"],
                            center=(q["center"][0], q["center"][1], q["center"][2] + z)))
        z += Hc
        if layer < d["layers"] - 1:
            out.append(dict(name=f"sep_mid_{layer}", size=(L, W, st), center=(0, 0, z + st / 2)))
            z += st
    if d["pads"] in ("both", "top"):
        out.append(dict(name="pad_top", size=(L, W, st), center=(0, 0, z + st / 2)))
        z += st
    return out


# ---------------------------------------------------------------- STL
def _tri_normal(a, b, c):
    n = np.cross(np.subtract(b, a), np.subtract(c, a))
    ln = np.linalg.norm(n)
    return n / ln if ln > 1e-12 else n


def write_stl(path, items_list):
    quads_per_box = [
        ((0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1)),
        ((0, 1, 0), (1, 1, 0), (1, 0, 0), (0, 0, 0)),
        ((0, 0, 0), (1, 0, 0), (1, 0, 1), (0, 0, 1)),
        ((1, 1, 0), (0, 1, 0), (0, 1, 1), (1, 1, 1)),
        ((1, 0, 0), (1, 1, 0), (1, 1, 1), (1, 0, 1)),
        ((0, 1, 0), (0, 0, 0), (0, 0, 1), (0, 1, 1)),
    ]
    tris = []
    for it in items_list:
        dx, dy, dz = it["size"]
        cx, cy, cz = it["center"]
        for quad in quads_per_box:
            vs = [(cx - dx / 2 + u * dx, cy - dy / 2 + v * dy, cz - dz / 2 + w * dz)
                  for (u, v, w) in quad]
            n = _tri_normal(np.array(vs[0]), np.array(vs[1]), np.array(vs[2]))
            tris.append((n, vs[0], vs[1], vs[2]))
            tris.append((n, vs[0], vs[2], vs[3]))
    with open(path, "wb") as fh:
        fh.write(b"\0" * 80)
        fh.write(struct.pack("<I", len(tris)))
        for n, a, b, c in tris:
            fh.write(struct.pack("<3f", float(n[0]), float(n[1]), float(n[2])))
            for v in (a, b, c):
                fh.write(struct.pack("<3f", float(v[0]), float(v[1]), float(v[2])))
            fh.write(struct.pack("<H", 0))
    return len(tris)


def stl_check(path):
    with open(path, "rb") as fh:
        fh.read(80)
        (n,) = struct.unpack("<I", fh.read(4))
        pmin = [1e18] * 3
        pmax = [-1e18] * 3
        for _ in range(n):
            fh.read(12)
            for _v in range(3):
                x, y, z = struct.unpack("<3f", fh.read(12))
                pmin = [min(pmin[0], x), min(pmin[1], y), min(pmin[2], z)]
                pmax = [max(pmax[0], x), max(pmax[1], y), max(pmax[2], z)]
            fh.read(2)
    return n, (pmin[0], pmin[1], pmin[2], pmax[0], pmax[1], pmax[2])


# ---------------------------------------------------------------- STEP
def export_step(path, items_list):
    from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
    from OCP.BRep import BRep_Builder
    from OCP.TopoDS import TopoDS_Compound
    from OCP.gp import gp_Pnt
    from OCP.Bnd import Bnd_Box
    from OCP.BRepBndLib import BRepBndLib
    from OCP.STEPControl import STEPControl_Writer, STEPControl_AsIs
    comp = TopoDS_Compound()
    BRep_Builder().MakeCompound(comp)
    builder = BRep_Builder()
    for it in items_list:
        dx, dy, dz = it["size"]
        cx, cy, cz = it["center"]
        shp = BRepPrimAPI_MakeBox(gp_Pnt(cx - dx / 2, cy - dy / 2, cz - dz / 2), dx, dy, dz).Shape()
        builder.Add(comp, shp)
    w = STEPControl_Writer()
    w.Transfer(comp, STEPControl_AsIs)
    w.Write(path)
    box = Bnd_Box()
    BRepBndLib.Add_s(comp, box)
    mn, mx = box.CornerMin(), box.CornerMax()
    return (mn.X(), mn.Y(), mn.Z(), mx.X(), mx.Y(), mx.Z())


# ---------------------------------------------------------------- DXF（1:1 展开）
def _dedupe(pts):
    out = [pts[0]]
    for q in pts[1:]:
        if abs(q[0] - out[-1][0]) > 1e-9 or abs(q[1] - out[-1][1]) > 1e-9:
            out.append(q)
    return out


def card_outline_long(p, d):
    """长刀卡展开：展开长 = L + 2×折边（折边在同一块板上，折弯线在距端 fold_len 处）。"""
    t, Hc = d["t"], d["cell_h"]
    fl = d.get("fold_len", 0.0) if d.get("fold_l") else 0.0
    x0 = fl                                    # 卡体起点（含左折边）
    pts = [(0.0, 0.0), (x0 + p.L, 0.0), (x0 + p.L, Hc)]
    for s in reversed(_slot_centers(d["margin_l"], d["slots_long"], d["pitch_l"], t)):
        pts += [(x0 + s + t / 2, Hc), (x0 + s + t / 2, Hc / 2),
                (x0 + s - t / 2, Hc / 2), (x0 + s - t / 2, Hc)]
    pts += [(0.0, Hc)]
    return _dedupe(pts)


def card_outline_short(p, d):
    """短刀卡展开：展开长 = W + 2×折边。"""
    t, Hc = d["t"], d["cell_h"]
    fl = d.get("fold_len", 0.0) if d.get("fold_w") else 0.0
    y0 = fl
    pts = [(0.0, 0.0)]
    for s in _slot_centers(d["margin_w"], d["slots_short"], d["pitch_w"], t):
        pts += [(y0 + s - t / 2, 0.0), (y0 + s - t / 2, Hc / 2),
                (y0 + s + t / 2, Hc / 2), (y0 + s + t / 2, 0.0)]
    pts += [(y0 + p.W, 0.0), (y0 + p.W, Hc), (0.0, Hc)]
    return _dedupe(pts)


def write_dxf(p, d, path):
    import ezdxf
    doc = ezdxf.new("R2010")
    doc.layers.add("CUT", color=7)
    doc.layers.add("NOTES", color=8)
    doc.layers.add("FOLD", color=1, linetype="DASHDOT")   # 折弯线
    msp = doc.modelspace()
    t, Hc = d["t"], d["cell_h"]
    msp.add_lwpolyline(card_outline_long(p, d), close=True, dxfattribs={"layer": "CUT"})
    msp.add_text(f"长刀卡 每层 {d['cards_long']} 张（{p.L:g}x{Hc:g}  槽{d['slots_long']}  上开槽 深{Hc/2:g} 距端{d['margin_l']:g}）"
                 f" x{d['layers']}层 = {d['cards_long_total']}张",
                 height=10.0, dxfattribs={"layer": "NOTES"}).set_placement((0.0, Hc + 22.0))
    ox = p.L + 90.0
    msp.add_lwpolyline([(x + ox, y) for x, y in card_outline_short(p, d)],
                       close=True, dxfattribs={"layer": "CUT"})
    msp.add_text(f"短刀卡 每层 {d['cards_short']} 张（{p.W:g}x{Hc:g}  槽{d['slots_short']}  下开槽 深{Hc/2:g} 距端{d['margin_w']:g}）"
                 f" x{d['layers']}层 = {d['cards_short_total']}张",
                 height=10.0, dxfattribs={"layer": "NOTES"}).set_placement((ox, Hc + 22.0))
    y_pad = -p.W - 90.0
    msp.add_lwpolyline([(0, y_pad), (p.L, y_pad), (p.L, y_pad + p.W), (0, y_pad + p.W)],
                       close=True, dxfattribs={"layer": "CUT"})
    msp.add_text(f"隔板 x{d['seps_total']}（中间 {d['seps_mid']} 必有 + 底/顶 {d['seps_tb']}）"
                 f"  {p.L:g}x{p.W:g}  t={t:g}",
                 height=10.0, dxfattribs={"layer": "NOTES"}).set_placement((0.0, y_pad + p.W + 12.0))

    # 折弯线（点划线）：长卡在展开图上距两端 fold_len；短卡同理（偏移 90）
    for (xa, ya) in ((0.0, None),):
        pass
    if d.get("fold_l"):
        for xx in d["fold_lines_L"]:
            msp.add_line((xx, 0.0), (xx, Hc), dxfattribs={"layer": "FOLD"})
    if d.get("fold_w"):
        for yy in d["fold_lines_W"]:
            msp.add_line((ox + yy, 0.0), (ox + yy, Hc), dxfattribs={"layer": "FOLD"})
    if d.get("fold_l") or d.get("fold_w"):
        _fl = d["fold_len"]
        tips = []
        if d.get("fold_l"):
            tips.append(f"长卡两端各 {_fl:g}（展开 {d['blank_L']:g}）")
        if d.get("fold_w"):
            tips.append(f"短卡两端各 {_fl:g}（展开 {d['blank_W']:g}）")
        msp.add_text("折边 FOLD 图层（点划线=折弯线，折 90°）：" + "；".join(tips)
                     + f"；触发条件 边距≤{d['fold_thr']:g}",
                     height=10.0, dxfattribs={"layer": "NOTES"}).set_placement((0.0, -40.0))
    doc.saveas(path)
    return path
