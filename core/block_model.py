# -*- coding: utf-8 -*-
"""仿形块 3D（盒体分解）+ 导出：STEP / STL / DXF(俯视 1:1)。"""
import struct

import numpy as np


def items(p, d):
    """沿块长方向分段：边距段 / 槽段（底 + 两侧墙）/ 间隔段。块体落 z 0..H。"""
    x0, y0 = -p.L / 2.0, -p.W / 2.0
    out = []

    def add(name, size, center):
        out.append(dict(name=name, size=size, center=center))

    def seg_full(a, b, tag):
        add(f"{tag}", (b - a, p.W, p.H), (x0 + (a + b) / 2, 0, p.H / 2))

    def seg_slot(a, b):
        add("slot_bottom", (b - a, p.W, p.H - p.sh), (x0 + (a + b) / 2, 0, (p.H - p.sh) / 2))
        if not d["through"]:
            ww = d["wy1"] - d["wy0"]
            add("slot_wall", (b - a, ww, p.sh),
                (x0 + (a + b) / 2, y0 + (d["wy0"] + d["wy1"]) / 2.0, p.H - p.sh / 2))

    prev = 0.0
    for i, (a, b) in enumerate(d["slots"]):
        if a - prev > 1e-9:
            seg_full(prev, a, f"margin_gap_{i}")
        seg_slot(a, b)
        prev = b
    if p.L - prev > 1e-9:
        seg_full(prev, p.L, "margin_end")
    return out


def draw_axo_clean(ax, items_list, azim=-45.0, elev=35.264):
    """工程图学轴测：把盒体分解的共面面片做平面并集 → 生成合成面（面+边一体），
    再按与渲染器相同的遮挡排序绘制 —— 无内部接缝、遮挡正确。"""
    import numpy as np
    from collections import defaultdict
    from matplotlib.patches import Polygon
    from box0210_3d import (_camera, item_corners, FACES,
                            _clip_convex, _depth_at, _poly2_area)
    cam, right, up = _camera(azim, elev)
    light = np.array([-0.40, -0.60, 0.85]); light /= np.linalg.norm(light)
    base = np.array([0.84, 0.70, 0.50])

    # 1) 收集共面可见矩形（按平面分组）
    groups = {}
    for it in items_list:
        cs = item_corners(it)
        ctr = np.array(it["center"], dtype=float)
        for fi in FACES:
            poly = [np.array(cs[i]) for i in fi]
            n = np.cross(poly[1] - poly[0], poly[2] - poly[1])
            ln = np.linalg.norm(n)
            if ln < 1e-12:
                continue
            n = n / ln
            fc = np.mean(np.array(poly), axis=0)
            if np.dot(n, fc - ctr) < 0:
                n = -n
            if np.dot(n, cam) <= 1e-9:            # 背面剔除
                continue
            k = int(np.argmax(np.abs(n)))
            key = (k, round(float(poly[0][k]), 3))
            u_ax, v_ax = [i for i in range(3) if i != k]
            rect = (min(pt[u_ax] for pt in poly), min(pt[v_ax] for pt in poly),
                    max(pt[u_ax] for pt in poly), max(pt[v_ax] for pt in poly))
            groups.setdefault(key, []).append(rect)

    # 2) 每个平面：占位格 → 并集边界 → 闭合环 → 合成面
    faces3d = []
    for (k, off), rects in groups.items():
        u_ax, v_ax = [i for i in range(3) if i != k]
        us = sorted({r[0] for r in rects} | {r[2] for r in rects})
        vs = sorted({r[1] for r in rects} | {r[3] for r in rects})
        occ = [[False] * (len(vs) - 1) for _ in range(len(us) - 1)]
        for (u0, v0, u1, v1) in rects:
            for i in range(len(us) - 1):
                if us[i] >= u0 - 1e-9 and us[i + 1] <= u1 + 1e-9:
                    for j in range(len(vs) - 1):
                        if vs[j] >= v0 - 1e-9 and vs[j + 1] <= v1 + 1e-9:
                            occ[i][j] = True
        segs, adj = [], defaultdict(list)
        for i in range(len(us)):
            for j in range(len(vs) - 1):
                l = occ[i - 1][j] if i > 0 else False
                r_ = occ[i][j] if i < len(us) - 1 else False
                if l != r_:
                    a, b = (us[i], vs[j]), (us[i], vs[j + 1])
                    segs.append((a, b)); adj[a].append(b); adj[b].append(a)
        for j in range(len(vs)):
            for i in range(len(us) - 1):
                dwn = occ[i][j - 1] if j > 0 else False
                up_ = occ[i][j] if j < len(vs) - 1 else False
                if dwn != up_:
                    a, b = (us[i], vs[j]), (us[i + 1], vs[j])
                    segs.append((a, b)); adj[a].append(b); adj[b].append(a)
        visited = set()
        for a, b in segs:
            ek = (a, b) if a <= b else (b, a)
            if ek in visited:
                continue
            loop = [a]; prev, cur = a, b
            visited.add(ek)
            while cur != a and len(loop) < 200:
                loop.append(cur)
                nxt = None
                for cand in adj[cur]:
                    if cand == prev:
                        continue
                    ck = (cur, cand) if cur <= cand else (cand, cur)
                    if ck not in visited:
                        nxt = cand; visited.add(ck); break
                if nxt is None:
                    break
                prev, cur = cur, nxt
            if cur != a or len(loop) < 3:
                continue
            pts = []
            for (u, v) in loop:
                q = np.zeros(3); q[k] = off; q[u_ax] = u; q[v_ax] = v
                pts.append(q)
            nrm = np.zeros(3); nrm[k] = 1.0 if cam[k] > 0 else -1.0
            faces3d.append((pts, nrm))

    # 3) 投影 + 遮挡排序（与渲染器同法）
    recs = []
    for (pts, nrm) in faces3d:
        p2 = [(float(np.dot(q, right)), float(np.dot(q, up))) for q in pts]
        mdepth = float(max(np.dot(q, cam) for q in pts))
        shade = 0.45 + 0.55 * max(0.0, float(np.dot(nrm, light)))
        recs.append([mdepth, p2, shade, pts])
    n = len(recs)
    preds = [set() for _ in range(n)]
    for i in range(n):
        xi = [q[0] for q in recs[i][1]]; yi = [q[1] for q in recs[i][1]]
        for j in range(i + 1, n):
            xj = [q[0] for q in recs[j][1]]; yj = [q[1] for q in recs[j][1]]
            if max(xi) <= min(xj) or max(xj) <= min(xi) or max(yi) <= min(yj) or max(yj) <= min(yi):
                continue
            A = recs[i][1] if _poly2_area(recs[i][1]) >= 0 else recs[i][1][::-1]
            B = recs[j][1] if _poly2_area(recs[j][1]) >= 0 else recs[j][1][::-1]
            ov = _clip_convex(A, B)
            if len(ov) < 3 or abs(_poly2_area(ov)) < 1e-3:
                continue
            cx = sum(q[0] for q in ov) / len(ov)
            cy = sum(q[1] for q in ov) / len(ov)
            di = _depth_at((cx, cy), recs[i][1], recs[i][3], cam)
            dj = _depth_at((cx, cy), recs[j][1], recs[j][3], cam)
            if di is None or dj is None:
                continue
            if di > dj + 1e-9:
                preds[i].add(j)
            elif dj > di + 1e-9:
                preds[j].add(i)
            else:
                ai, aj = abs(_poly2_area(recs[i][1])), abs(_poly2_area(recs[j][1]))
                if ai > aj + 1e-9:
                    preds[i].add(j)
                elif aj > ai + 1e-9:
                    preds[j].add(i)
    order, remaining = [], set(range(n))
    while remaining:
        ready = [k for k in remaining if not (preds[k] & remaining)]
        if not ready:
            ready = [min(remaining, key=lambda k: recs[k][0])]
        ready.sort(key=lambda k: recs[k][0])
        k = ready[0]
        order.append(k)
        remaining.discard(k)

    xs, ys = [], []
    for idx, k in enumerate(order):
        _d, p2, shade, _pts = recs[k]
        ax.add_patch(Polygon(p2, closed=True,
                             facecolor=tuple(np.clip(base * shade, 0, 1)),
                             edgecolor=(0.15, 0.12, 0.10), lw=0.55, zorder=10 + idx))
        xs += [q[0] for q in p2]
        ys += [q[1] for q in p2]
    if xs and ys:
        mx = (max(xs) - min(xs)) * 0.05 + 1
        my = (max(ys) - min(ys)) * 0.05 + 1
        ax.set_xlim(min(xs) - mx, max(xs) + mx)
        ax.set_ylim(min(ys) - my, max(ys) + my)
    ax.set_aspect("equal")
    ax.axis("off")


def write_dxf(p, d, path):
    import ezdxf
    doc = ezdxf.new("R2010")
    doc.layers.add("CUT", color=7)
    doc.layers.add("NOTES", color=8)
    msp = doc.modelspace()
    msp.add_lwpolyline([(0, 0), (p.L, 0), (p.L, p.W), (0, p.W)], close=True,
                       dxfattribs={"layer": "CUT"})
    for (a, b) in d["slots"]:
        if d["through"]:
            ys = (0.0, p.W)
        else:
            ys = (d["sy0"], d["sy1"])
        msp.add_lwpolyline([(a, ys[0]), (b, ys[0]), (b, ys[1]), (a, ys[1])], close=True,
                           dxfattribs={"layer": "CUT"})
    msp.add_text(f"{p.name} {p.L:g}x{p.W:g}x{p.H:g}  开槽 {p.sl:g}x{p.sw:g}x{p.sh:g} x{d['n']}  "
                 f"间距 {p.gap:g}  边距 左{d['margin_l']:g}/右{d['margin_r']:g}",
                 height=12.0, dxfattribs={"layer": "NOTES"}).set_placement((0.0, p.W + 30.0))
    doc.saveas(path)
    return path


# ---------------------------------------------------------------- STL / STEP
def _tri_normal(a, b, c):
    n = np.cross(np.subtract(b, a), np.subtract(c, a))
    ln = np.linalg.norm(n)
    return n / ln if ln > 1e-12 else n


def write_stl(path, items_list):
    quads = [((0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1)),
             ((0, 1, 0), (1, 1, 0), (1, 0, 0), (0, 0, 0)),
             ((0, 0, 0), (1, 0, 0), (1, 0, 1), (0, 0, 1)),
             ((1, 1, 0), (0, 1, 0), (0, 1, 1), (1, 1, 1)),
             ((1, 0, 0), (1, 1, 0), (1, 1, 1), (1, 0, 1)),
             ((0, 1, 0), (0, 0, 0), (0, 0, 1), (0, 1, 1))]
    tris = []
    for it in items_list:
        dx, dy, dz = it["size"]
        cx, cy, cz = it["center"]
        for quad in quads:
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
        builder.Add(comp, BRepPrimAPI_MakeBox(
            gp_Pnt(cx - dx / 2, cy - dy / 2, cz - dz / 2), dx, dy, dz).Shape())
    w = STEPControl_Writer()
    w.Transfer(comp, STEPControl_AsIs)
    w.Write(path)
    box = Bnd_Box()
    BRepBndLib.Add_s(comp, box)
    mn, mx = box.CornerMin(), box.CornerMax()
    return (mn.X(), mn.Y(), mn.Z(), mx.X(), mx.Y(), mx.Z())
