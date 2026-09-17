# -*- coding: utf-8 -*-
"""FEFCO 0210 (Straight Tuck Carton) - parametric dieline + 3D panel model.

All dimensions in mm. Outer size L x W x H, board thickness t.
2D dieline frame: X -> right, Y -> up (origin = blank's lap bottom-left level).
3D frame: X = length, Y = width, Z = height (origin = closed box bottom-left).

Design basis (checked 2026-09-16):
- FEFCO 0210 = straight tuck carton: one-piece, glued side lap, top & bottom
  lids both hinged from the back (L) panel, each with a tuck tongue;
  side (W) panels carry dust flaps; front panel has no cuts.
- Size chain: inner = outer - 2t ; manufacturer = inner + t = outer - t
  (multiple CN sources: packzg / cnzhixiang "new formula" / practice tables).
- Allowances: dust flap length = Wm - 2*(t/2+1)  (clear of front/back inner faces);
  tuck width = Lm - 2*(t+1) (clear of side wall inner faces); lid depth = Wm - t/2.
- t(BC double wall) = 6.5..7.5, default 7.0 (GB/T 6544 practice).
"""

from dataclasses import dataclass, asdict
import math


@dataclass
class Params:
    L: float = 400.0          # outer length
    W: float = 300.0          # outer width
    H: float = 200.0          # outer height
    t: float = 7.0            # board thickness (BC double wall)
    glue_w: float = 45.0      # glue lap width (double wall: 45..50)
    glue_inset: float = 4.0   # glue lap top/bottom inset
    tuck_depth: float = 50.0  # tuck tongue depth (inserted)
    tuck_side_gap: float = 8.0   # per-side reduction of tuck vs lid (t+1)
    tuck_r: float = 6.0       # tuck tongue corner radius
    dust_depth: float = 115.0 # dust flap depth (~0.6*Hm)
    dust_clr: float = None    # per-side clearance vs panels; default t/2+1

    def __post_init__(self):
        if self.dust_clr is None:
            self.dust_clr = self.t / 2.0 + 1.0

    # ---- derived manufacturer / inner sizes ----
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
    def lid_depth(self): return self.Wm - self.t / 2.0
    @property
    def tuck_w(self): return self.Lm - 2 * self.tuck_side_gap
    @property
    def dust_len(self): return self.Wm - 2 * self.dust_clr


def _bulge(a, c, b):
    """DXF bulge for arc a->b around center c (signed; + = CCW)."""
    a1 = math.atan2(a[1] - c[1], a[0] - c[0])
    a2 = math.atan2(b[1] - c[1], b[0] - c[0])
    d = a2 - a1
    while d > math.pi:
        d -= 2 * math.pi
    while d < -math.pi:
        d += 2 * math.pi
    return math.tan(d / 4.0)


def layout(p: Params):
    """All key coordinates of the blank."""
    Lm, Wm, Hm, t = p.Lm, p.Wm, p.Hm, p.t
    X0 = 0.0
    X1 = X0 + p.glue_w           # lap | back
    X2 = X1 + Lm                 # back | W_left
    X3 = X2 + Wm                 # W_left | front
    X4 = X3 + Lm                 # front | W_right
    X5 = X4 + Wm                 # blank right edge
    Y0, Y1 = 0.0, Hm             # band bottom / top (scores for flaps)
    Yl0 = p.glue_inset
    Yl1 = Hm - p.glue_inset
    lid = p.lid_depth
    Yt_lid = Y1 + lid            # top lid | tuck score
    Yt_top = Yt_lid + p.tuck_depth
    Yb_lid = Y0 - lid            # bottom lid | tuck score
    Yb_bot = Yb_lid - p.tuck_depth
    Xt0 = X1 + p.tuck_side_gap
    Xt1 = X2 - p.tuck_side_gap
    c = p.dust_clr
    dl0, dl1 = X2 + c, X3 - c    # W_left dust flap x-range
    dr0, dr1 = X4 + c, X5 - c    # W_right dust flap x-range
    Ydt = Y1 + p.dust_depth
    Ydb = Y0 - p.dust_depth
    r = p.tuck_r
    return dict(X0=X0, X1=X1, X2=X2, X3=X3, X4=X4, X5=X5,
                Y0=Y0, Y1=Y1, Yl0=Yl0, Yl1=Yl1,
                lid=lid, Yt_lid=Yt_lid, Yt_top=Yt_top, Yb_lid=Yb_lid, Yb_bot=Yb_bot,
                Xt0=Xt0, Xt1=Xt1, dl0=dl0, dl1=dl1, dr0=dr0, dr1=dr1,
                Ydt=Ydt, Ydb=Ydb, r=r)


def dieline(p: Params):
    """Return (outline, creases, info).

    outline: closed polyline [[x, y, bulge], ...] bulge applies to segment
             from this vertex to the next (DXF LWPOLYLINE convention).
    creases: list of ((x1,y1),(x2,y2)) score segments.
    """
    g = layout(p)
    X0, X1, X2, X3, X4, X5 = (g[k] for k in ("X0", "X1", "X2", "X3", "X4", "X5"))
    Y0, Y1, Yl0, Yl1 = g["Y0"], g["Y1"], g["Yl0"], g["Yl1"]
    Yt_lid, Yt_top = g["Yt_lid"], g["Yt_top"]
    Yb_lid, Yb_bot = g["Yb_lid"], g["Yb_bot"]
    Xt0, Xt1, r = g["Xt0"], g["Xt1"], g["r"]
    dl0, dl1, dr0, dr1 = g["dl0"], g["dl1"], g["dr0"], g["dr1"]
    Ydt, Ydb = g["Ydt"], g["Ydb"]

    b_tl = _bulge((Xt0, Yt_top - r), (Xt0 + r, Yt_top - r), (Xt0 + r, Yt_top))
    b_tr = _bulge((Xt1 - r, Yt_top), (Xt1 - r, Yt_top - r), (Xt1, Yt_top - r))
    b_br = _bulge((Xt1, Yb_bot + r), (Xt1 - r, Yb_bot + r), (Xt1 - r, Yb_bot))
    b_bl = _bulge((Xt0 + r, Yb_bot), (Xt0 + r, Yb_bot + r), (Xt0, Yb_bot + r))

    outline = [
        [X0, Yl0, 0], [X0, Yl1, 0],            # lap left edge
        [X1, Yl1, 0],                          # lap top edge
        [X1, Yt_lid, 0],                       # up: back left + lid left edge
        [Xt0, Yt_lid, 0],                      # lid/tuck shoulder
        [Xt0, Yt_top - r, b_tl],               # tuck left edge -> arc
        [Xt0 + r, Yt_top, 0],                  # (top-left arc lands here)
        [Xt1 - r, Yt_top, b_tr],               # tuck top edge -> arc
        [Xt1, Yt_top - r, 0],                  # (top-right arc lands here)
        [Xt1, Yt_lid, 0],                      # tuck right edge
        [X2, Yt_lid, 0],                       # shoulder
        [X2, Y1, 0],                           # lid right edge
        [dl0, Y1, 0], [dl0, Ydt, 0],           # dust1 (W_left, top)
        [dl1, Ydt, 0], [dl1, Y1, 0],
        [X3, Y1, 0], [X4, Y1, 0],              # front top edge (cut)
        [dr0, Y1, 0], [dr0, Ydt, 0],           # dust2 (W_right, top)
        [dr1, Ydt, 0], [dr1, Y1, 0],
        [X5, Y1, 0], [X5, Y0, 0],              # right end edge
        [dr1, Y0, 0], [dr1, Ydb, 0],           # dust3 (W_right, bottom)
        [dr0, Ydb, 0], [dr0, Y0, 0],
        [X4, Y0, 0], [X3, Y0, 0],              # front bottom edge (cut)
        [dl1, Y0, 0], [dl1, Ydb, 0],           # dust4 (W_left, bottom)
        [dl0, Ydb, 0], [dl0, Y0, 0],
        [X2, Y0, 0],                           # W_left bottom -> lid
        [X2, Yb_lid, 0],                       # bottom lid right edge
        [Xt1, Yb_lid, 0],                      # shoulder
        [Xt1, Yb_bot + r, b_br],               # tuck right edge -> arc
        [Xt1 - r, Yb_bot, 0],                  # (bottom-right arc lands here)
        [Xt0 + r, Yb_bot, b_bl],               # tuck bottom edge -> arc
        [Xt0, Yb_bot + r, 0],                  # (bottom-left arc lands here)
        [Xt0, Yb_lid, 0],                      # tuck left edge (up)
        [X1, Yb_lid, 0],                       # shoulder
        [X1, Yl0, 0],                          # up: lid left + back left edge
    ]

    creases = [
        # vertical panel scores (tube)
        ((X1, Yl0), (X1, Yl1)),
        ((X2, Y0), (X2, Y1)),
        ((X3, Y0), (X3, Y1)),
        ((X4, Y0), (X4, Y1)),
        # top hinges
        ((X1, Y1), (X2, Y1)),      # top lid
        ((dl0, Y1), (dl1, Y1)),    # dust flap W_left
        ((dr0, Y1), (dr1, Y1)),    # dust flap W_right
        # bottom hinges
        ((X1, Y0), (X2, Y0)),
        ((dl0, Y0), (dl1, Y0)),
        ((dr0, Y0), (dr1, Y0)),
        # lid | tuck scores
        ((Xt0, Yt_lid), (Xt1, Yt_lid)),
        ((Xt0, Yb_lid), (Xt1, Yb_lid)),
    ]

    info = dict(
        blank_w=X5 - X0, blank_h=Yt_top - Yb_bot,
        Lm=p.Lm, Wm=p.Wm, Hm=p.Hm, Li=p.Li, Wi=p.Wi, Hi=p.Hi, t=p.t,
        lid_depth=p.lid_depth, tuck_depth=p.tuck_depth, tuck_w=p.tuck_w,
        dust_depth=p.dust_depth, dust_len=p.dust_len, dust_clr=p.dust_clr,
        glue_w=p.glue_w, tuck_r=p.tuck_r,
        panel_x=[X0, X1, X2, X3, X4, X5],
        score_y=[Y0, Y1], lid_score_y=[Yb_lid, Yt_lid], tuck_top_y=[Yb_bot, Yt_top],
    )
    return outline, creases, info


def panels(p: Params):
    """3D panels as boxes: name, size (dx,dy,dz), center (x,y,z), group.

    Geometry convention: fold axes on panel mid-planes (idealized);
    dust flaps placed one board down from the lid (physical stacking).
    """
    t, Lm, Wm, Hm = p.t, p.Lm, p.Wm, p.Hm
    h = t / 2.0
    z_bot = h                    # bottom flap mid-plane
    z_top = h + Hm               # top score
    lid = p.lid_depth
    out = []
    add = out.append
    # walls (full outer height; mid-plane box): back +y, front -y, left -x, right +x
    add(dict(name="wall_back", size=(Lm, t, p.H), center=(0, Wm / 2, p.H / 2), group="static"))
    add(dict(name="wall_front", size=(Lm, t, p.H), center=(0, -Wm / 2, p.H / 2), group="static"))
    add(dict(name="wall_left", size=(t, Wm, p.H), center=(-Lm / 2, 0, p.H / 2), group="static"))
    add(dict(name="wall_right", size=(t, Wm, p.H), center=(Lm / 2, 0, p.H / 2), group="static"))
    # glue lap glued on inside of right wall (hidden in closed view)
    lap_len = Wm - 2 * 4.0
    add(dict(name="glue_lap", size=(t, lap_len, Hm - 8.0),
             center=(Lm / 2 - t, 0, h + Hm / 2), group="static"))
    # bottom lid (hinged from back, closed) + tuck inside front wall
    y_back_hinge = Wm / 2                     # +146.5 (back wall mid-plane top)
    y_front_in = -(Wm / 2) + h                # -143.0 (front wall inner face)
    lid_center_y = (y_back_hinge + y_front_in) / 2.0
    add(dict(name="bottom_lid", size=(Lm, lid, t), center=(0, lid_center_y, h), group="static"))
    add(dict(name="bottom_tuck", size=(p.tuck_w, t, p.tuck_depth),
             center=(0, y_front_in + t / 2, z_bot + p.tuck_depth / 2), group="static"))
    # top lid: render face covers out to the outer envelope (clean closed look);
    # fold/hinge line at the back outer top edge (build_items rotates about it)
    add(dict(name="top_lid", size=(p.L, p.W, t), center=(0, 0, z_top), group="top"))
    add(dict(name="top_tuck", size=(p.tuck_w, t, p.tuck_depth),
             center=(0, -p.W / 2 + t / 2, z_top - p.tuck_depth / 2), group="top"))
    # dust flaps (both sides); top pair runs out to the envelope, bottom pair as blanked
    dd = p.dust_depth + h
    for sgn, tag in ((-1.0, "l"), (1.0, "r")):
        add(dict(name=f"top_dust_{tag}", size=(dd, p.dust_len, t),
                 center=(sgn * (p.L / 2 - dd / 2), 0, z_top - t), group="static"))
        add(dict(name=f"bottom_dust_{tag}", size=(p.dust_depth, p.dust_len, t),
                 center=(sgn * (Lm / 2 - p.dust_depth / 2), 0, t + h), group="static"))
    return out


def open_items(items, p: "Params"):
    """Open-view state: closed dust flaps flush with the box rim (+t), matching real
    folding geometry (the closed view keeps them one board lower, under the lid)."""
    out = []
    for it in items:
        if it.get("name", "").startswith("top_dust"):
            cx, cy, cz = it["center"]
            out.append(dict(it, center=(cx, cy, cz + p.t)))
        else:
            out.append(dict(it))
    return out


def check(p: Params):
    outline, creases, info = dieline(p)
    g = layout(p)
    errs = []
    # outline closes and bbox matches
    xs = [pt[0] for pt in outline]
    ys = [pt[1] for pt in outline]
    bw = max(xs) - min(xs)
    bh = max(ys) - min(ys)
    if abs(bw - info["blank_w"]) > 1e-9:
        errs.append(f"blank width mismatch {bw} vs {info['blank_w']}")
    if abs(bw - (2 * p.Lm + 2 * p.Wm + p.glue_w)) > 1e-9:
        errs.append("blank width formula mismatch")
    if abs(info["blank_h"] - (p.Hm + 2 * (p.lid_depth + p.tuck_depth))) > 1e-9:
        errs.append("blank height formula mismatch")
    # outer size reconstruction from manufacturer sizes
    if abs((p.Lm + p.t) - p.L) > 1e-9 or abs((p.Wm + p.t) - p.W) > 1e-9 or abs((p.Hm + p.t) - p.H) > 1e-9:
        errs.append("outer = mfr + t violated")
    if abs((p.Li + 2 * p.t) - p.L) > 1e-9:
        errs.append("inner = outer - 2t violated")
    # tuck must clear side wall inner faces
    if p.tuck_w > p.Li - 2:
        errs.append("tuck too wide")
    return errs, info


def report(p: Params):
    errs, info = check(p)
    rows = [
        ("outer L*W*H", f"{p.L:g} x {p.W:g} x {p.H:g}"),
        ("inner", f"{p.Li:g} x {p.Wi:g} x {p.Hi:g}"),
        ("manufacturer", f"{p.Lm:g} x {p.Wm:g} x {p.Hm:g}"),
        ("board t", f"{p.t:g} (BC double wall)"),
        ("lid depth", f"{p.lid_depth:g}"),
        ("tuck depth/width", f"{p.tuck_depth:g} / {p.tuck_w:g}"),
        ("dust depth/len", f"{p.dust_depth:g} / {p.dust_len:g}"),
        ("glue lap", f"{p.glue_w:g}"),
        ("blank size", f"{info['blank_w']:g} x {info['blank_h']:g}"),
        ("blank area", f"{info['blank_w'] * info['blank_h'] / 1e6:.4f} m2"),
    ]
    return errs, rows


if __name__ == "__main__":
    p = Params()
    errs, rows = report(p)
    print("=== FEFCO 0210 BC 400x300x200 (outer) - size check ===")
    for k, v in rows:
        print(f"{k:20s}: {v}")
    print("errors:", errs if errs else "none")
