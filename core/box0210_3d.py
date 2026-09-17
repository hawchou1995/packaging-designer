# -*- coding: utf-8 -*-
"""FEFCO 0210 - 3D outputs: OCP solids (STEP/STL) + isometric renderer (PNG/SVG).

Renderer: hand-rolled painter-algorithm isometric projection, vector output.
Solids: OpenCascade (OCP) boxes per panel; top lid+tuck can be rotated (open view).
"""
import os
import math

import numpy as np

from box0210_core import Params, panels


# ---------------------------------------------------------------- item model
def build_items(p: Params, open_top: bool = False, open_angle: float = -110.0):
    """Panels as boxes; 'top' group optionally rotated about the back-top hinge (FEFCO 0210)."""
    hinge = (p.W / 2.0, p.t / 2.0 + p.Hm)  # (y, z) of back wall top fold (outer edge)
    items = []
    for q in panels(p):
        rot = ("x", hinge[0], hinge[1], open_angle) if (open_top and q["group"] == "top") else None
        items.append(dict(name=q["name"], size=q["size"], center=q["center"], rot=rot))
    return items


def build_items_from(panels_list, open_top: bool = False):
    """Generic builder: each panel dict may carry 'open': (axis, c1, c2, angle)."""
    items = []
    for q in panels_list:
        o = q.get("open") if open_top else None
        items.append(dict(name=q["name"], size=q["size"], center=q["center"],
                          group=q.get("group", "static"),
                          rot=(o[0], o[1], o[2], o[3]) if o else None))
    return items


def _rot(axis, pt, c1, c2, deg):
    a = math.radians(deg)
    ca, sa = math.cos(a), math.sin(a)
    if axis == "x":          # rotate in the y-z plane about the X axis at (y=c1, z=c2)
        x, y, z = pt
        d1, d2 = y - c1, z - c2
        return (x, c1 + d1 * ca - d2 * sa, c2 + d1 * sa + d2 * ca)
    # rotate in the x-z plane about the Y axis at (x=c1, z=c2)
    x, y, z = pt
    d1, d2 = x - c1, z - c2
    return (c1 + d1 * ca - d2 * sa, y, c2 + d1 * sa + d2 * ca)


def item_corners(it):
    cx, cy, cz = it["center"]
    dx, dy, dz = it["size"]
    cs = [(cx - dx / 2, cy - dy / 2, cz - dz / 2), (cx + dx / 2, cy - dy / 2, cz - dz / 2),
          (cx + dx / 2, cy + dy / 2, cz - dz / 2), (cx - dx / 2, cy + dy / 2, cz - dz / 2),
          (cx - dx / 2, cy - dy / 2, cz + dz / 2), (cx + dx / 2, cy - dy / 2, cz + dz / 2),
          (cx + dx / 2, cy + dy / 2, cz + dz / 2), (cx - dx / 2, cy + dy / 2, cz + dz / 2)]
    if it.get("rot"):
        ax, c1, c2, deg = it["rot"]
        cs = [_rot(ax, c, c1, c2, deg) for c in cs]
    return cs


def item_center_world(it):
    r = it.get("rot")
    if r:
        return _rot(r[0], it["center"], r[1], r[2], r[3])
    return it["center"]


FACES = [(0, 1, 2, 3), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]


def scene_bbox(items):
    pts = [c for it in items for c in item_corners(it)]
    xs = [c[0] for c in pts]; ys = [c[1] for c in pts]; zs = [c[2] for c in pts]
    return (min(xs), min(ys), min(zs), max(xs), max(ys), max(zs))


# ---------------------------------------------------------------- renderer
def _camera(azim_deg=-45.0, elev_deg=35.264):
    a, e = math.radians(azim_deg), math.radians(elev_deg)
    cam = np.array([math.cos(e) * math.cos(a), math.cos(e) * math.sin(a), math.sin(e)])
    up = np.array([0.0, 0.0, 1.0])
    right = np.cross(up, cam)
    right /= np.linalg.norm(right)
    upv = np.cross(cam, right)
    return cam, right, upv


def _poly2_area(pts):
    s = 0.0
    n = len(pts)
    for i in range(n):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % n]
        s += x1 * y2 - x2 * y1
    return 0.5 * s


def _clip_convex(poly, clip):
    """Sutherland-Hodgman: part of `poly` inside convex polygon `clip` (both lists of (x, y))."""
    def inside(p, a, b):
        return (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0]) >= 0.0

    out = list(poly)
    for i in range(len(clip)):
        a, b = clip[i], clip[(i + 1) % len(clip)]
        new = []
        m = len(out)
        for j in range(m):
            p, q = out[j], out[(j + 1) % m]
            pin, qin = inside(p, a, b), inside(q, a, b)
            if pin:
                new.append(p)
            if pin != qin:
                d1 = (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0])
                d2 = (b[0] - a[0]) * (q[1] - a[1]) - (b[1] - a[1]) * (q[0] - a[0])
                t = d1 / (d1 - d2)
                new.append((p[0] + t * (q[0] - p[0]), p[1] + t * (q[1] - p[1])))
        out = new
        if not out:
            return []
    return out


def _depth_at(pt2, p2, p3, cam):
    """View depth of the planar face (p2/p3 = projected/3D corners) at projected point pt2."""
    (x0, y0), (x1, y1), (x2, y2) = p2[0], p2[1], p2[2]
    px, py = pt2
    det = (x1 - x0) * (y2 - y0) - (x2 - x0) * (y1 - y0)
    if abs(det) < 1e-12:
        return None
    w1 = ((px - x0) * (y2 - y0) - (x2 - x0) * (py - y0)) / det
    w2 = ((x1 - x0) * (py - y0) - (px - x0) * (y1 - y0)) / det
    w0 = 1.0 - w1 - w2
    return w0 * float(np.dot(p3[0], cam)) + w1 * float(np.dot(p3[1], cam)) + w2 * float(np.dot(p3[2], cam))


def project_items(items, azim=-45.0, elev=35.264):
    """Returns list of (depth, poly2d, shade) in occlusion-correct order (far -> near).

    Ordering: pairwise overlap test (2D bbox + convex clip) -> compare true depths at the
    overlap centroid -> topological sort. Robust for big faces at different heights.
    """
    cam, right, up = _camera(azim, elev)
    light = np.array([-0.40, -0.60, 0.85])
    light /= np.linalg.norm(light)
    base = np.array([0.84, 0.70, 0.50])  # kraft tone
    recs = []
    for it in items:
        cs = item_corners(it)
        ctr = np.array(item_center_world(it))
        for fi in FACES:
            poly = [np.array(cs[i]) for i in fi]
            e1 = poly[1] - poly[0]
            e2 = poly[2] - poly[1]
            n = np.cross(e1, e2)
            ln = np.linalg.norm(n)
            if ln < 1e-12:
                continue
            n = n / ln
            fc = np.mean(np.array(poly), axis=0)
            if np.dot(n, fc - ctr) < 0:
                n = -n
            shade = 0.45 + 0.55 * max(0.0, float(np.dot(n, light)))
            p2 = [(float(np.dot(q, right)), float(np.dot(q, up))) for q in poly]
            mdepth = float(max(np.dot(q, cam) for q in poly))
            recs.append((mdepth, p2, shade, poly))

    n = len(recs)
    preds = [set() for _ in range(n)]          # preds[i]: faces that must be drawn before i
    for i in range(n):
        p2i = recs[i][1]
        xi = [q[0] for q in p2i]
        yi = [q[1] for q in p2i]
        for j in range(i + 1, n):
            p2j = recs[j][1]
            xj = [q[0] for q in p2j]
            yj = [q[1] for q in p2j]
            if max(xi) <= min(xj) or max(xj) <= min(xi) or max(yi) <= min(yj) or max(yj) <= min(yi):
                continue
            A = p2i if _poly2_area(p2i) >= 0 else p2i[::-1]
            B = p2j if _poly2_area(p2j) >= 0 else p2j[::-1]
            ov = _clip_convex(A, B)
            if len(ov) < 3 or abs(_poly2_area(ov)) < 1e-3:
                continue
            cx = sum(q[0] for q in ov) / len(ov)
            cy = sum(q[1] for q in ov) / len(ov)
            di = _depth_at((cx, cy), p2i, recs[i][3], cam)
            dj = _depth_at((cx, cy), p2j, recs[j][3], cam)
            if di is None or dj is None:
                continue
            if di > dj + 1e-9:          # i in front of j at the overlap -> j first
                preds[i].add(j)
            elif dj > di + 1e-9:
                preds[j].add(i)
            else:
                # coplanar overlap (same plane, e.g. wall top strip vs flap top face):
                # no true occluder; draw the SMALLER face first so the larger lid
                # surface wins the fill and strips/slivers stay underneath (else the
                # tie-break is arbitrary and flips between regions -> stray edge lines)
                ai = abs(_poly2_area(p2i))
                aj = abs(_poly2_area(p2j))
                if ai > aj + 1e-9:
                    preds[i].add(j)
                elif aj > ai + 1e-9:
                    preds[j].add(i)

    order = []
    remaining = set(range(n))
    while remaining:
        ready = [k for k in remaining if not (preds[k] & remaining)]
        if not ready:               # cycle safety: force the farthest
            ready = [min(remaining, key=lambda k: recs[k][0])]
        ready.sort(key=lambda k: recs[k][0])   # far first among available
        k = ready[0]
        order.append(k)
        remaining.discard(k)

    return [(recs[k][0], recs[k][1], recs[k][2]) for k in order], base


def draw_scene(ax, items, style="shaded", azim=-45.0, elev=35.264, lw=0.35):
    from matplotlib.patches import Polygon
    faces, base = project_items(items, azim, elev)
    xs, ys = [], []
    for i, (depth, p2, shade) in enumerate(faces):
        if style == "line":
            fc = "white"
        else:
            fc = tuple(np.clip(base * shade, 0, 1))
        ax.add_patch(Polygon(p2, closed=True, facecolor=fc,
                             edgecolor=(0.15, 0.12, 0.10), linewidth=lw, zorder=i + 1))
        xs += [p[0] for p in p2]
        ys += [p[1] for p in p2]
    mx = (max(xs) - min(xs)) * 0.05 + 1
    my = (max(ys) - min(ys)) * 0.05 + 1
    ax.set_xlim(min(xs) - mx, max(xs) + mx)
    ax.set_ylim(min(ys) - my, max(ys) + my)
    ax.set_aspect("equal")
    ax.axis("off")


# ---------------------------------------------------------------- sheet + standalone
def _font():
    from matplotlib import font_manager
    import matplotlib.pyplot as plt
    for fp in ("C:/Windows/Fonts/msyh.ttc", "C:/Windows/Fonts/simhei.ttf"):
        if os.path.exists(fp):
            try:
                font_manager.fontManager.addfont(fp)
                name = font_manager.FontProperties(fname=fp).get_name()
                plt.rcParams["font.sans-serif"] = [name, "DejaVu Sans"]
                plt.rcParams["axes.unicode_minus"] = False
                return name
            except Exception:
                continue
    return "DejaVu Sans"


def build_axo_sheet(p: Params, page=(420.0, 297.0), items_closed=None, items_open=None,
                    title=None, cap2=None, notes=None):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fam = _font()
    pw, ph = page
    fig = plt.figure(figsize=(pw / 25.4, ph / 25.4))
    ax1 = fig.add_axes([0.03, 0.20, 0.45, 0.62])
    ax2 = fig.add_axes([0.52, 0.20, 0.45, 0.62])
    if items_closed is None:
        items_closed = build_items(p, open_top=False)
    if items_open is None:
        items_open = build_items(p, open_top=True)
    draw_scene(ax1, items_closed, "shaded")
    draw_scene(ax2, items_open, "shaded")
    ax1.set_title("闭合状态（等轴测）", fontsize=10)
    ax2.set_title(cap2 or "开盖状态（上盖板+插舌开启 110°）", fontsize=10)
    fig.text(0.5, 0.93, title or "FEFCO 0210 直插式双插盒 · 轴测图（立体建模）", ha="center",
             fontsize=13, fontweight="bold")
    fig.text(0.5, 0.885,
             f"BC 双瓦楞 t={p.t:g} · 外尺寸 {p.L:g}×{p.W:g}×{p.H:g} mm · 等轴测投影（无比例）",
             ha="center", fontsize=8.5)
    if notes is None:
        notes = [
            f"模型：面板厚度实体 {p.t:g} mm；盖板深 {p.lid_depth:g}；插舌 {p.tuck_depth:g}×{p.tuck_w:g}；"
            f"防尘翼 {p.dust_depth:g}×{p.dust_len:g}；粘舌 {p.glue_w:g}。",
            "闭合数模外廓 bbox 实测 = 400 × 300 × 200 mm（见验证输出）；"
            "文件：03_三维模型-闭合.step/.stl、03_三维模型-开盖.stl。",
        ]
    for i, s in enumerate(notes):
        fig.text(0.5, 0.135 - i * 0.035, s, ha="center", fontsize=7, color="0.15")
    fig.text(0.5, 0.02, f"字体：{fam}", ha="center", fontsize=5, color="0.5")
    return fig


def render_view(p: Params, open_top: bool, basepath: str, dpi: int = 300, items=None, title=None):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    _font()
    if items is None:
        items = build_items(p, open_top)
    fig = plt.figure(figsize=(150 / 25.4, 115 / 25.4))
    ax = fig.add_axes([0.02, 0.06, 0.96, 0.88])
    draw_scene(ax, items, "shaded")
    if title is None:
        label = "闭合" if not open_top else "开盖"
        title = f"FEFCO 0210 · BC t={p.t:g} · {p.L:g}×{p.W:g}×{p.H:g}（外）· {label}"
    ax.set_title(title, fontsize=9)
    out = []
    for ext in ("png", "svg"):
        fp = f"{basepath}.{ext}"
        fig.savefig(fp, dpi=dpi)
        out.append(fp)
    plt.close(fig)
    return out


# ---------------------------------------------------------------- STL (numpy)
def _tri_normal(a, b, c):
    n = np.cross(np.subtract(b, a), np.subtract(c, a))
    ln = np.linalg.norm(n)
    return n / ln if ln > 1e-12 else n


def write_stl_file(p: Params, open_top: bool, path: str, items=None):
    """Binary STL written from the same panel boxes as the STEP model."""
    import struct
    if items is None:
        items = build_items(p, open_top)
    tris = []
    for it in items:
        cs = [np.array(c, dtype=float) for c in item_corners(it)]
        ctr = np.array(item_center_world(it), dtype=float)
        for q in FACES:
            for (i, j, k) in ((0, 1, 2), (0, 2, 3)):
                a, b, c = cs[q[i]], cs[q[j]], cs[q[k]]
                n = _tri_normal(a, b, c)
                fcen = (a + b + c) / 3.0
                if np.dot(n, fcen - ctr) < 0:
                    a, b, c, n = a, c, b, -n
                tris.append((n, a, b, c))
    with open(path, "wb") as fh:
        fh.write(b"FEFCO 0210 straight tuck carton - parametric generator".ljust(80, b" "))
        fh.write(struct.pack("<I", len(tris)))
        for (n, a, b, c) in tris:
            fh.write(struct.pack("<3f", float(n[0]), float(n[1]), float(n[2])))
            for q in (a, b, c):
                fh.write(struct.pack("<3f", float(q[0]), float(q[1]), float(q[2])))
            fh.write(struct.pack("<H", 0))
    return path


def stl_check(path: str):
    """Read back a binary STL: triangle count + bbox (mm)."""
    import struct
    with open(path, "rb") as fh:
        fh.read(80)
        (n,) = struct.unpack("<I", fh.read(4))
        pmin = [1e18] * 3
        pmax = [-1e18] * 3
        for _ in range(n):
            data = fh.read(50)
            vals = struct.unpack("<12f", data[:48])
            for vi in (3, 6, 9):
                for k in range(3):
                    v = vals[vi + k]
                    pmin[k] = min(pmin[k], v)
                    pmax[k] = max(pmax[k], v)
    return n, (pmin[0], pmin[1], pmin[2], pmax[0], pmax[1], pmax[2])


def add_iso_panels(fig, items_closed, items_open, cap1="闭合状态", cap2="开盖状态"):
    """Add two stacked isometric axes on the right column of a combined sheet."""
    axc = fig.add_axes([0.700, 0.575, 0.268, 0.285])   # 避开右下标题栏（框）
    axo = fig.add_axes([0.700, 0.235, 0.268, 0.285])
    draw_scene(axc, items_closed, "shaded")
    draw_scene(axo, items_open, "shaded")
    axc.set_title(cap1, fontsize=8.5)
    axo.set_title(cap2, fontsize=8.5)
    return axc, axo


# ---------------------------------------------------------------- OCP solids
def export_solids(p: Params, open_top: bool, step_path=None, items=None):
    """Build one compound of panel solids; export STEP. Returns bbox tuple."""
    from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
    from OCP.BRep import BRep_Builder
    from OCP.TopoDS import TopoDS_Compound
    from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform
    from OCP.gp import gp_Pnt, gp_Vec, gp_Trsf, gp_Ax1, gp_Dir
    from OCP.Bnd import Bnd_Box
    from OCP.BRepBndLib import BRepBndLib
    from OCP.STEPControl import STEPControl_Writer, STEPControl_AsIs

    if items is None:
        items = build_items(p, open_top)
    comp = TopoDS_Compound()
    builder = BRep_Builder()
    builder.MakeCompound(comp)
    for it in items:
        dx, dy, dz = it["size"]
        shp = BRepPrimAPI_MakeBox(gp_Pnt(-dx / 2, -dy / 2, -dz / 2), dx, dy, dz).Shape()
        r = it.get("rot")
        if r:
            ax, c1, c2, ang = r
            if ax == "x":
                axis = gp_Ax1(gp_Pnt(0, c1, c2), gp_Dir(1, 0, 0))
            else:
                axis = gp_Ax1(gp_Pnt(c1, 0, c2), gp_Dir(0, 1, 0))
            tr = gp_Trsf()
            tr.SetRotation(axis, math.radians(ang))
            shp = BRepBuilderAPI_Transform(shp, tr, True).Shape()
        c = item_center_world(it)
        tr2 = gp_Trsf()
        tr2.SetTranslation(gp_Vec(c[0], c[1], c[2]))
        shp = BRepBuilderAPI_Transform(shp, tr2, True).Shape()
        builder.Add(comp, shp)
    if step_path:
        w = STEPControl_Writer()
        w.Transfer(comp, STEPControl_AsIs)
        w.Write(step_path)
    box = Bnd_Box()
    BRepBndLib.Add_s(comp, box)
    mn, mx = box.CornerMin(), box.CornerMax()
    return (mn.X(), mn.Y(), mn.Z(), mx.X(), mx.Y(), mx.Z())


if __name__ == "__main__":
    import sys
    p = Params()
    outdir = sys.argv[1] if len(sys.argv) > 1 else r"D:/Tools/tmp/fefco0210_build/out"
    os.makedirs(outdir, exist_ok=True)
    bb = export_solids(p, False, os.path.join(outdir, "0210_closed.step"))
    print("closed STEP bbox:", [round(v, 3) for v in bb])
    print("closed dims:", round(bb[3] - bb[0], 3), round(bb[4] - bb[1], 3), round(bb[5] - bb[2], 3))
    write_stl_file(p, False, os.path.join(outdir, "0210_closed.stl"))
    write_stl_file(p, True, os.path.join(outdir, "0210_open.stl"))
    for f in ("0210_closed.stl", "0210_open.stl"):
        n, bx = stl_check(os.path.join(outdir, f))
        print(f, "tris:", n, "bbox:", [round(v, 2) for v in bx])
    for f in render_view(p, False, os.path.join(outdir, "0210_axo_closed")):
        print("AXO:", f, os.path.getsize(f))
    for f in render_view(p, True, os.path.join(outdir, "0210_axo_open")):
        print("AXO:", f, os.path.getsize(f))
