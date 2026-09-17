# -*- coding: utf-8 -*-
"""FEFCO 0201 (Regular Slotted Container / RSC) - parametric dieline + 3D panels.

BC double wall, outer L x W x H (default 400 x 300 x 200 mm).
Size chain: inner = outer - 2t ; manufacturer = inner + t = outer - t.
Flap practice (public CN sources, 2026-09): outer (meeting) flaps = Wm/2 + gain
(放大系数, +3 mm for 5-8 mm board, compensates inner-flap spring-back);
inner flaps = Wm/2 - reduce ; slot width (double wall) = 10 mm.
Blank layout: [glue lap][end panel W][side panel L][end panel W][side panel L].
"""

from dataclasses import dataclass


@dataclass
class Params:
    L: float = 400.0
    W: float = 300.0
    H: float = 200.0
    t: float = 7.0
    glue_w: float = 45.0
    glue_inset: float = 4.0
    flap_gain: float = 3.0     # outer flap amplification (5-8 mm board -> +3)
    flap_reduce: float = 3.0   # inner flap reduction
    slot_w: float = 10.0       # slot width at panel/flap junctions

    @property
    def Lm(self): return self.L - self.t
    @property
    def Wm(self): return self.W - self.t
    @property
    def Hm(self): return self.H - self.t
    @property
    def Li(self): return self.L - 2 * self.t
    @property
    def Wi(self): return self.W - 2 * self.t
    @property
    def Hi(self): return self.H - 2 * self.t
    @property
    def fo(self): return self.Wm / 2.0 + self.flap_gain    # outer flap depth 149.5
    @property
    def fi(self): return self.Wm / 2.0 - self.flap_reduce  # inner flap depth 143.5


def layout(p: Params):
    X0 = 0.0
    X1 = X0 + p.glue_w       # lap | 端A
    X2 = X1 + p.Wm           # 端A | 侧A
    X3 = X2 + p.Lm           # 侧A | 端B
    X4 = X3 + p.Wm           # 端B | 侧B
    X5 = X4 + p.Lm           # blank right edge
    s = p.slot_w / 2.0
    return dict(X0=X0, X1=X1, X2=X2, X3=X3, X4=X4, X5=X5,
                X2a=X2 - s, X2b=X2 + s, X3a=X3 - s, X3b=X3 + s, X4a=X4 - s, X4b=X4 + s,
                Y0=0.0, Y1=p.Hm,
                Yt_i=p.Hm + p.fi, Yt_o=p.Hm + p.fo,
                Yb_i=-p.fi, Yb_o=-p.fo,
                Yl0=p.glue_inset, Yl1=p.Hm - p.glue_inset, s=s)


def dieline(p: Params):
    g = layout(p)
    X1, X2a, X2b, X3a, X3b, X4a, X4b, X5 = (g[k] for k in
                                            ("X1", "X2a", "X2b", "X3a", "X3b", "X4a", "X4b", "X5"))
    Y0, Y1 = g["Y0"], g["Y1"]
    Yt_i, Yt_o, Yb_i, Yb_o = g["Yt_i"], g["Yt_o"], g["Yb_i"], g["Yb_o"]
    Yl0, Yl1 = g["Yl0"], g["Yl1"]

    outline = [
        (g["X0"], Yl0), (g["X0"], Yl1), (X1, Yl1),      # glue lap (L edge, top, right)
        (X1, Yt_i),                                     # 端A left edge + inner flap left edge
        (X2a, Yt_i),                                    # 端A top flap outer edge
        (X2a, Y1), (X2b, Y1),                           # slot at X2
        (X2b, Yt_o), (X3a, Yt_o),                       # 侧A top flap (outer)
        (X3a, Y1), (X3b, Y1),                           # slot at X3
        (X3b, Yt_i), (X4a, Yt_i),                       # 端B top flap (inner)
        (X4a, Y1), (X4b, Y1),                           # slot at X4
        (X4b, Yt_o), (X5, Yt_o),                        # 侧B top flap (outer) -> right edge
        (X5, Yb_o),                                     # right edge down
        (X4b, Yb_o),                                    # 侧B bottom flap
        (X4b, Y0), (X4a, Y0),                           # slot at X4 (bottom)
        (X4a, Yb_i), (X3b, Yb_i),                       # 端B bottom flap (inner)
        (X3b, Y0), (X3a, Y0),                           # slot at X3
        (X3a, Yb_o), (X2b, Yb_o),                       # 侧A bottom flap (outer)
        (X2b, Y0), (X2a, Y0),                           # slot at X2
        (X2a, Yb_i), (X1, Yb_i),                        # 端A bottom flap (inner) -> left
        (X1, Yl0),                                      # up the left edge to the lap
    ]

    creases = []
    for x in (g["X2"], g["X3"], g["X4"]):
        creases.append(((x, Y0), (x, Y1)))
    creases.append(((X1, Yl0), (X1, Yl1)))              # lap | 端A
    for (a, b) in ((X1, X2a), (X2b, X3a), (X3b, X4a), (X4b, X5)):
        creases.append(((a, Y1), (b, Y1)))              # top flap hinges
        creases.append(((a, Y0), (b, Y0)))              # bottom flap hinges

    info = dict(blank_w=g["X5"] - g["X0"], blank_h=Yt_o - Yb_o,
                Lm=p.Lm, Wm=p.Wm, Hm=p.Hm, Li=p.Li, Wi=p.Wi, Hi=p.Hi, t=p.t,
                fo=p.fo, fi=p.fi, slot_w=p.slot_w, glue_w=p.glue_w,
                panel_x=[g["X0"], g["X1"], g["X2"], g["X3"], g["X4"], g["X5"]])
    return outline, creases, info


def panels(p: Params):
    """3D panels: walls + 4 top / 4 bottom flaps. Flap widths follow hinge spans.

    Stacking: outer flaps are the outer layer, inner flaps tucked one board under.
    'open' tuples: (axis, c1, c2, angle) -> hinge for the open-top view.
    Mapping: 端A=wall_left, 侧A=wall_front, 端B=wall_right, 侧B=wall_back.
    """
    t, Lm, Wm, Hm = p.t, p.Lm, p.Wm, p.Hm
    h = t / 2.0
    zc = p.H / 2.0                 # walls run the full outer height (no rim step)
    z_top = h + Hm                 # 196.5
    s2 = p.slot_w / 2.0
    w_in_A = Wm - s2               # 端A flap (blank-edge side)   288
    w_in_B = Wm - p.slot_w         # 端B flap (both sides slotted) 283
    w_out_A = Lm - p.slot_w        # 侧A flap                      383
    w_out_B = Lm - s2              # 侧B flap (blank-edge side)    388
    out = []

    def add(name, size, center, group="static", open_=None):
        d = dict(name=name, size=size, center=center, group=group)
        if open_:
            d["open"] = open_
        out.append(d)

    add("wall_back", (Lm, t, p.H), (0, Wm / 2, zc), "back")
    add("wall_front", (Lm, t, p.H), (0, -Wm / 2, zc), "front")
    add("wall_left", (t, Wm, p.H), (-Lm / 2, 0, zc), "left")
    add("wall_right", (t, Wm, p.H), (Lm / 2, 0, zc), "right")
    add("glue_lap", (p.glue_w, t, Hm - 8.0), (-Lm / 2 + p.glue_w / 2, Wm / 2 - t, zc))

    # ---- top flaps (render: lid face runs out to the outer envelope so the closed
    #      top reads flush with the walls; fold lines stay as drawn edges) ----
    fov_d = p.W / 2.0 + 1.5    # depth: outer face -> 1.5 mm past centre (151.5)
    add("top_flap_outer_front", (p.L, fov_d, t), (0, -p.W / 2 + fov_d / 2, z_top),
        "front", ("x", -p.W / 2, z_top, 110.0))
    add("top_flap_outer_back", (p.L, fov_d, t), (0, p.W / 2 - fov_d / 2, z_top),
        "back", ("x", p.W / 2, z_top, -110.0))
    add("top_flap_inner_left", (p.fi + h, w_in_A, t),
        ((-p.L / 2 + (-Lm / 2 + p.fi)) / 2.0, 2.5, z_top - t), "left")
    add("top_flap_inner_right", (p.fi + h, w_in_B, t),
        ((p.L / 2 + (Lm / 2 - p.fi)) / 2.0, 0, z_top - t), "right")
    # ---- bottom flaps (mirror; no opening) ----
    fo_b = p.fo - 1.5          # bottom: keep the 3 mm seam gap (not visible from above)
    add("bottom_flap_outer_front", (w_out_A, fo_b, t), (0, -Wm / 2 + fo_b / 2, h), "front")
    add("bottom_flap_outer_back", (w_out_B, fo_b, t), (-2.5, Wm / 2 - fo_b / 2, h), "back")
    add("bottom_flap_inner_left", (p.fi, w_in_A, t), (-Lm / 2 + p.fi / 2, 2.5, t + h), "left")
    add("bottom_flap_inner_right", (p.fi, w_in_B, t), (Lm / 2 - p.fi / 2, 0, t + h), "right")
    return out


def open_items(items, p: "Params"):
    """Open-view state: inner (short) flaps closed and flush with the box rim (+t).
    In the closed view they sit one board lower (under the outer flaps); the 'mid-closing'
    state must show them level with the top, matching real folding geometry."""
    out = []
    for it in items:
        if it.get("name", "").startswith("top_flap_inner"):
            cx, cy, cz = it["center"]
            out.append(dict(it, center=(cx, cy, cz + p.t)))
        else:
            out.append(dict(it))
    return out


def check(p: Params):
    outline, creases, info = dieline(p)
    g = layout(p)
    errs = []
    bw = max(pt[0] for pt in outline) - min(pt[0] for pt in outline)
    bh = max(pt[1] for pt in outline) - min(pt[1] for pt in outline)
    if abs(bw - (2 * p.Lm + 2 * p.Wm + p.glue_w)) > 1e-9:
        errs.append("blank width formula mismatch")
    if abs(bh - (p.Hm + 2 * p.fo)) > 1e-9:
        errs.append("blank height formula mismatch")
    if abs((p.Lm + p.t) - p.L) > 1e-9 or abs((p.Li + 2 * p.t) - p.L) > 1e-9:
        errs.append("size chain broken")
    if not (2 * p.fo > p.Wm):
        errs.append("outer flaps should overlap nominally (2*fo > Wm, 放大系数设计)")
    return errs, info


def report(p: Params):
    errs, info = check(p)
    rows = [
        ("外尺寸 L×W×H", f"{p.L:g} × {p.W:g} × {p.H:g}"),
        ("内尺寸", f"{p.Li:g} × {p.Wi:g} × {p.Hi:g}"),
        ("制造尺寸", f"{p.Lm:g} × {p.Wm:g} × {p.Hm:g}"),
        ("纸板厚度 t", f"{p.t:g}"),
        ("外摇盖深", f"{p.fo:g}（= W制/2 + {p.flap_gain:g}）"),
        ("内摇盖深", f"{p.fi:g}（= W制/2 − {p.flap_reduce:g}）"),
        ("开槽宽", f"{p.slot_w:g}"),
        ("接舌宽", f"{p.glue_w:g}"),
        ("展开尺寸", f"{info['blank_w']:g} × {info['blank_h']:g}"),
        ("展开面积（几何）", f"{info['blank_w'] * info['blank_h'] / 1e6:.4f} m²"),
    ]
    return errs, rows


if __name__ == "__main__":
    p = Params()
    errs, rows = report(p)
    print("=== FEFCO 0201 BC 400x300x200 (outer) - size check ===")
    for k, v in rows:
        print(f"{k:20s}: {v}")
    print("errors:", errs if errs else "none")
