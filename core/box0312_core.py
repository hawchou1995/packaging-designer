# -*- coding: utf-8 -*-
"""FEFCO 0312 (Half Slotted Container with Lid) - dieline + 3D panels.

BC double wall, assembled outer L x W x H (default 400 x 300 x 200).
Base  = HSC: glued tube + bottom flaps only (outer flaps meet at centre).
Lid   = flat-top telescoping cap: solid top panel + 4 walls (wrap corners,
        glue/staple) - the top surface is FLAT (no slotted flaps).
Chain: lid outer = assembled outer; lid inner = outer - 2t; base outer = lid inner - 2*gap.
"""

from dataclasses import dataclass


@dataclass
class Params:
    L: float = 400.0
    W: float = 300.0
    H: float = 200.0
    t: float = 7.0              # 天盖（lid）纸板厚度（t_lid；兼容 = 默认）
    t_base: float = 0.0         # 底箱（HSC）纸板厚度；0 → 与 t 相同
    glue_w: float = 45.0
    glue_inset: float = 4.0
    gap: float = 2.0
    cover_depth: float = 90.0   # lid wall face height (罩深)
    flap_gain: float = 3.0      # base bottom outer flap amplification
    flap_reduce: float = 3.0
    slot_w: float = 10.0

    @property
    def tl(self): return self.t                              # 盖纸板厚
    @property
    def tb(self): return self.t_base if self.t_base > 0 else self.t      # 底箱纸板厚

    @property
    def base_L(self): return self.L - 2 * self.tl - 2 * self.gap
    @property
    def base_W(self): return self.W - 2 * self.tl - 2 * self.gap
    @property
    def base_Lm(self): return self.base_L - self.tb          # 375
    @property
    def base_Wm(self): return self.base_W - self.tb          # 275
    @property
    def base_Hm(self): return self.H - self.tb               # 193
    @property
    def lid_Lm(self): return self.L - self.tl                # 393
    @property
    def lid_Wm(self): return self.W - self.tl                # 293
    @property
    def base_fo(self): return self.base_Wm / 2.0 + self.flap_gain
    @property
    def base_fi(self): return self.base_Wm / 2.0 - self.flap_reduce
    @property
    def lid_wall_blank(self): return self.cover_depth + self.tl / 2.0   # 93.5


def _layout_strip(p, wm, lm, h, inset):
    X1 = p.glue_w
    X2 = X1 + wm
    X3 = X2 + lm
    X4 = X3 + wm
    X5 = X4 + lm
    return dict(X0=0.0, X1=X1, X2=X2, X3=X3, X4=X4, X5=X5,
                Y0=0.0, Y1=h, Yl0=inset, Yl1=h - inset,
                s=p.slot_w / 2.0)


def dieline_base(p):
    """Base HSC: strip [lap][W][L][W][L] + bottom flaps (outer on L panels, inner on W)."""
    g = _layout_strip(p, p.base_Wm, p.base_Lm, p.base_Hm, p.glue_inset)
    fo, fi = p.base_fo, p.base_fi
    X1, X2, X3, X4, X5, Y0, Y1 = (g[k] for k in ("X1", "X2", "X3", "X4", "X5", "Y0", "Y1"))
    s = g["s"]
    X2a, X2b, X3a, X3b, X4a, X4b = g["X2"] - s, g["X2"] + s, g["X3"] - s, g["X3"] + s, g["X4"] - s, g["X4"] + s
    Ybi, Ybo = Y0 - fi, Y0 - fo
    outline = [
        (g["X0"], g["Yl0"]), (g["X0"], g["Yl1"]), (X1, g["Yl1"]),
        (X1, Y1), (X5, Y1), (X5, Ybo),
        (X4b, Ybo), (X4b, Y0), (X4a, Y0), (X4a, Ybi), (X3b, Ybi),
        (X3b, Y0), (X3a, Y0), (X3a, Ybo), (X2b, Ybo),
        (X2b, Y0), (X2a, Y0), (X2a, Ybi), (X1, Ybi), (X1, g["Yl0"]),
    ]
    creases = [((x, Y0), (x, Y1)) for x in (g["X2"], g["X3"], g["X4"])]
    creases.append(((X1, g["Yl0"]), (X1, g["Yl1"])))
    for (a, b) in ((X1, X2a), (X2b, X3a), (X3b, X4a), (X4b, X5)):
        creases.append(((a, Y0), (b, Y0)))
    info = dict(blank_w=X5, blank_h=Y1 - Ybo, fo=fo, fi=fi,
                Lm=p.base_Lm, Wm=p.base_Wm, Hm=p.base_Hm)
    return outline, creases, info


def layout_lid(p):
    wb = p.lid_wall_blank
    return dict(wb=wb, cx0=wb, cx1=wb + p.lid_Lm, cy0=wb, cy1=wb + p.lid_Wm,
                W0=0.0, W1=2 * wb + p.lid_Lm, H0=0.0, H1=2 * wb + p.lid_Wm)


def dieline_lid(p):
    """Lid: flat-top cap - centre panel + 4 walls; left/right strips full height with
    corner squares (wrap corners, glue/staple). Top surface is flat (no flap seam)."""
    g = layout_lid(p)
    outline = [(g["W0"], g["H0"]), (g["W1"], g["H0"]), (g["W1"], g["H1"]), (g["W0"], g["H1"])]
    creases = [
        ((g["W0"], g["cy0"]), (g["W1"], g["cy0"])),
        ((g["W0"], g["cy1"]), (g["W1"], g["cy1"])),
        ((g["cx0"], g["cy0"]), (g["cx0"], g["cy1"])),
        ((g["cx1"], g["cy0"]), (g["cx1"], g["cy1"])),
    ]
    cuts = [
        ((g["cx0"], g["H0"]), (g["cx0"], g["cy0"])),
        ((g["cx0"], g["cy1"]), (g["cx0"], g["H1"])),
        ((g["cx1"], g["H0"]), (g["cx1"], g["cy0"])),
        ((g["cx1"], g["cy1"]), (g["cx1"], g["H1"])),
    ]
    info = dict(blank_w=g["W1"], blank_h=g["H1"], wb=g["wb"],
                Lm=p.lid_Lm, Wm=p.lid_Wm, depth=p.cover_depth)
    return outline, creases, cuts, info


def panels(p):
    """3D: base (walls + bottom flaps) + flat-top lid (panel + 4 walls); lid movable."""
    tb, hb = p.tb, p.tb / 2.0
    tl, hl = p.tl, p.tl / 2.0
    out = []

    def add(name, size, center, group="static", open_=None):
        d = dict(name=name, size=size, center=center, group=group)
        if open_:
            d["open"] = open_
        out.append(d)

    # base walls (full outer height; no rim step)
    zc = p.H / 2.0
    add("base_back", (p.base_Lm, tb, p.H), (0, p.base_Wm / 2, zc))
    add("base_front", (p.base_Lm, tb, p.H), (0, -p.base_Wm / 2, zc))
    add("base_left", (tb, p.base_Wm, p.H), (-p.base_Lm / 2, 0, zc))
    add("base_right", (tb, p.base_Wm, p.H), (p.base_Lm / 2, 0, zc))
    add("base_lap", (p.glue_w, tb, p.base_Hm - 8.0), (-p.base_Lm / 2 + p.glue_w / 2, p.base_Wm / 2 - tb, zc))
    # base bottom flaps: outer 139 (render seam) on L panels; inner 134.5 on W panels
    fo_r = p.base_fo - 1.5
    nm = p.base_Wm
    add("base_bf_outer_front", (p.base_Lm - p.slot_w, fo_r, tb), (0, -nm / 2 + fo_r / 2, hb))
    add("base_bf_outer_back", (p.base_Lm - p.slot_w / 2, fo_r, tb), (-2.5, nm / 2 - fo_r / 2, hb))
    add("base_bf_inner_left", (p.base_fi, nm - p.slot_w / 2, tb), (-p.base_Lm / 2 + p.base_fi / 2, 2.5, tb + hb))
    add("base_bf_inner_right", (p.base_fi, nm - p.slot_w, tb), (p.base_Lm / 2 - p.base_fi / 2, 0, tb + hb))
    # lid: flat top panel + four walls running to the full outer envelope (no rim step)
    wh2 = p.cover_depth + tl
    zc2 = p.H - wh2 / 2.0
    add("lid_panel", (p.lid_Lm, p.lid_Wm, tl), (0, 0, p.H - hl), "lid")
    add("lid_wall_l", (tl, p.lid_Wm, wh2), (-p.lid_Lm / 2, 0, zc2), "lid")
    add("lid_wall_r", (tl, p.lid_Wm, wh2), (p.lid_Lm / 2, 0, zc2), "lid")
    add("lid_wall_f", (p.lid_Lm, tl, wh2), (0, -p.lid_Wm / 2, zc2), "lid")
    add("lid_wall_b", (p.lid_Lm, tl, wh2), (0, p.lid_Wm / 2, zc2), "lid")
    add("lid_lap", (p.glue_w, tl, p.cover_depth - 8.0), (-p.lid_Lm / 2 + p.glue_w / 2, p.lid_Wm / 2 - tl, zc2), "lid")
    return out


def lift_items(items, group="lid", dz=120.0):
    out = []
    for it in items:
        if it.get("group") == group:
            cx, cy, cz = it["center"]
            out.append(dict(it, center=(cx, cy, cz + dz)))
        else:
            out.append(dict(it))
    return out


def check(p: Params):
    _, _, ib = dieline_base(p)
    _, _, _, il = dieline_lid(p)
    errs = []
    if abs(ib["blank_w"] - (2 * (p.base_Lm + p.base_Wm) + p.glue_w)) > 1e-9:
        errs.append("base blank width mismatch")
    if abs(ib["blank_h"] - (p.base_Hm + p.base_fo)) > 1e-9:
        errs.append("base blank height mismatch")
    if abs(il["blank_w"] - (p.lid_Lm + 2 * p.lid_wall_blank)) > 1e-9:
        errs.append("lid blank width mismatch")
    if abs(il["blank_h"] - (p.lid_Wm + 2 * p.lid_wall_blank)) > 1e-9:
        errs.append("lid blank height mismatch")
    if abs((p.base_L + 2 * p.gap) - (p.L - 2 * p.tl)) > 1e-9:
        errs.append("base/lid length chain mismatch")
    return errs


def report(p: Params):
    errs = check(p)
    _, _, ib = dieline_base(p)
    _, _, _, il = dieline_lid(p)
    area = (ib["blank_w"] * ib["blank_h"] + il["blank_w"] * il["blank_h"]) / 1e6
    rows = [
        ("assembled outer", f"{p.L:g} x {p.W:g} x {p.H:g}"),
        ("天盖 外 / 内", f"{p.L:g}×{p.W:g} / {p.L - 2 * p.tl:g}×{p.W - 2 * p.tl:g}"),
        ("底箱外尺寸", f"{p.base_L:g} × {p.base_W:g} × {p.base_Hm + p.tb:g}"),
        ("底箱制造", f"{p.base_Lm:g} × {p.base_Wm:g}"),
        ("罩深（天盖墙高）", f"{p.cover_depth:g}"),
        ("天盖墙板宽", f"{p.lid_wall_blank:g}（= 罩深 + t/2）"),
        ("底摇盖 外/内", f"{p.base_fo:g} / {p.base_fi:g}"),
        ("底箱展开", f"{ib['blank_w']:g} × {ib['blank_h']:g}"),
        ("天盖展开", f"{il['blank_w']:g} × {il['blank_h']:g}"),
        ("用纸合计（几何）", f"{area:.4f} m²"),
    ]
    return errs, rows


if __name__ == "__main__":
    p = Params()
    errs, rows = report(p)
    print("=== FEFCO 0312 BC 400x300x200 (assembled outer) - check ===")
    for k, v in rows:
        print(f"{k:20s}: {v}")
    print("errors:", errs if errs else "none")
