# -*- coding: utf-8 -*-
"""FEFCO 0310 (Sleeve with Slotted Tray and End-to-End Lid) - dieline + 3D panels.

BC double wall, assembled outer L x W x H (default 400 x 300 x 200).
Chain: cap outer = assembled outer; cap inner = outer - 2t; sleeve outer = cap inner - 2*gap.
Sleeve (围框): open glued tube, blank = 2*(sleeve_Lm + sleeve_Wm) + lap, height = sleeve outer H.
Caps (包角托盘盖, x2 identical, end-to-end): center panel + 4 walls; the left/right wall
strips run the full blank height and their corner squares (wall_blank x wall_blank) wrap
the adjacent walls' outer faces (glue/staple). Corner square width = wall_blank (= BLD).
"""

from dataclasses import dataclass


@dataclass
class Params:
    L: float = 400.0
    W: float = 300.0
    H: float = 200.0
    t: float = 7.0              # 上盖纸板厚度（t_cap_top；兼容 = 默认）
    t_sleeve: float = 0.0       # 围框纸板厚度；0 → 与 t 相同
    t_cap_bot: float = 0.0      # 下盖纸板厚度；0 → 与 t 相同
    glue_w: float = 45.0
    glue_inset: float = 4.0
    gap: float = 2.0            # per-side clearance: cap inner vs sleeve outer
    cover_extra: float = 0.0    # 0 -> the two caps meet exactly at the waist line
                                # (each covers sleeve_H/2 = 93; no interpenetration)

    @property
    def tc(self): return self.t                                     # 上盖纸板厚
    @property
    def tc2(self): return self.t_cap_bot if self.t_cap_bot > 0 else self.t   # 下盖纸板厚
    @property
    def ts(self): return self.t_sleeve if self.t_sleeve > 0 else self.t      # 围框纸板厚
    @property
    def tcmax(self): return max(self.tc, self.tc2)                  # 围框须两侧盖都套得进

    @property
    def sleeve_L(self): return self.L - 2 * self.tcmax - 2 * self.gap
    @property
    def sleeve_W(self): return self.W - 2 * self.tcmax - 2 * self.gap
    @property
    def sleeve_Lm(self): return self.sleeve_L - self.ts
    @property
    def sleeve_Wm(self): return self.sleeve_W - self.ts
    @property
    def sleeve_H(self): return self.H - self.tc - self.tc2           # 围框高 = 外高 − 两盖板厚
    @property
    def d_cover(self): return self.sleeve_H / 2.0 + self.cover_extra   # 93（两盖对半）
    @property
    def wall_blank(self): return self.d_cover + self.tc / 2.0          # 上盖角片宽 BLD
    @property
    def wall_blank_bot(self): return self.d_cover + self.tc2 / 2.0     # 下盖角片宽
    @property
    def cap_Lm(self): return self.L - self.tc                # 393（上盖顶板）
    @property
    def cap_Wm(self): return self.W - self.tc
    @property
    def cap_Lm_bot(self): return self.L - self.tc2           # 下盖顶板
    @property
    def cap_Wm_bot(self): return self.W - self.tc2


def layout_sleeve(p: Params):
    X1 = p.glue_w
    X2 = X1 + p.sleeve_Wm
    X3 = X2 + p.sleeve_Lm
    X4 = X3 + p.sleeve_Wm
    X5 = X4 + p.sleeve_Lm
    return dict(X0=0.0, X1=X1, X2=X2, X3=X3, X4=X4, X5=X5,
                Y0=0.0, Y1=p.sleeve_H, Yl0=p.glue_inset, Yl1=p.sleeve_H - p.glue_inset)


def dieline_sleeve(p: Params):
    g = layout_sleeve(p)
    outline = [(g["X0"], g["Yl0"]), (g["X0"], g["Yl1"]), (g["X1"], g["Yl1"]),
               (g["X1"], g["Y1"]), (g["X5"], g["Y1"]), (g["X5"], g["Y0"]),
               (g["X1"], g["Y0"]), (g["X1"], g["Yl0"])]
    creases = [((x, g["Y0"]), (x, g["Y1"])) for x in (g["X2"], g["X3"], g["X4"])]
    creases.append(((g["X1"], g["Yl0"]), (g["X1"], g["Yl1"])))
    info = dict(blank_w=g["X5"], blank_h=g["Y1"],
                sweater=p.sleeve_L, sleeve_W=p.sleeve_W, sleeve_H=p.sleeve_H)
    return outline, creases, info


def layout_cap(p: Params, which: str = "top"):
    """which='top' 上盖 / 'bot' 下盖（板厚可不同 → 展开尺寸不同）。"""
    if which == "bot":
        wb, Lm, Wm = p.wall_blank_bot, p.cap_Lm_bot, p.cap_Wm_bot
    else:
        wb, Lm, Wm = p.wall_blank, p.cap_Lm, p.cap_Wm
    return dict(wb=wb, cx0=wb, cx1=wb + Lm, cy0=wb, cy1=wb + Wm,
                W0=0.0, W1=2 * wb + Lm, H0=0.0, H1=2 * wb + Wm)


def dieline_cap(p: Params, which: str = "top"):
    g = layout_cap(p, which)
    outline = [(g["W0"], g["H0"]), (g["W1"], g["H0"]), (g["W1"], g["H1"]), (g["W0"], g["H1"])]
    creases = [
        ((g["W0"], g["cy0"]), (g["W1"], g["cy0"])),      # horizontal fold (full width)
        ((g["W0"], g["cy1"]), (g["W1"], g["cy1"])),
        ((g["cx0"], g["cy0"]), (g["cx0"], g["cy1"])),    # vertical folds (partial)
        ((g["cx1"], g["cy0"]), (g["cx1"], g["cy1"])),
    ]
    cuts = [                                              # corner-square separation cuts
        ((g["cx0"], g["H0"]), (g["cx0"], g["cy0"])),
        ((g["cx0"], g["cy1"]), (g["cx0"], g["H1"])),
        ((g["cx1"], g["H0"]), (g["cx1"], g["cy0"])),
        ((g["cx1"], g["cy1"]), (g["cx1"], g["H1"])),
    ]
    info = dict(blank_w=g["W1"], blank_h=g["H1"], wb=g["wb"],
                cap_Lm=(p.cap_Lm_bot if which == "bot" else p.cap_Lm),
                cap_Wm=(p.cap_Wm_bot if which == "bot" else p.cap_Wm),
                d_cover=p.d_cover)
    return outline, creases, cuts, info


def panels(p: Params):
    """3D: sleeve (open tube) + bottom cap + top cap; top cap movable for exploded view."""
    tc, h = p.tc, p.tc / 2.0
    tb2, h2 = p.tc2, p.tc2 / 2.0
    ts = p.ts
    Lm, Wm, Hs = p.sleeve_Lm, p.sleeve_Wm, p.sleeve_H
    out = []

    def add(name, size, center, group="static", open_=None):
        d = dict(name=name, size=size, center=center, group=group)
        if open_:
            d["open"] = open_
        out.append(d)

    z0 = tb2               # 围框底面坐在下盖顶板上
    add("sleeve_back", (Lm, ts, Hs), (0, Wm / 2, z0 + Hs / 2))
    add("sleeve_front", (Lm, ts, Hs), (0, -Wm / 2, z0 + Hs / 2))
    add("sleeve_left", (ts, Wm, Hs), (-Lm / 2, 0, z0 + Hs / 2))
    add("sleeve_right", (ts, Wm, Hs), (Lm / 2, 0, z0 + Hs / 2))
    add("sleeve_lap", (p.glue_w, ts, Hs - 8.0), (-Lm / 2 + p.glue_w / 2, Wm / 2 - ts, z0 + Hs / 2))

    wall_h = p.d_cover                     # 95 (folded wall face height)
    # bottom cap: panel z 0..tc2 ; walls run to the full outer envelope (z 0..tc2+wall_h)
    add("cap_bot_panel", (p.cap_Lm_bot, p.cap_Wm_bot, tb2), (0, 0, h2), "cap_bot")
    zbc = (tb2 + wall_h) / 2.0
    wh = tb2 + wall_h
    add("cap_bot_wall_l", (tb2, p.cap_Wm_bot, wh), (-p.cap_Lm_bot / 2, 0, zbc), "cap_bot")
    add("cap_bot_wall_r", (tb2, p.cap_Wm_bot, wh), (p.cap_Lm_bot / 2, 0, zbc), "cap_bot")
    add("cap_bot_wall_f", (p.cap_Lm_bot, tb2, wh), (0, -p.cap_Wm_bot / 2, zbc), "cap_bot")
    add("cap_bot_wall_b", (p.cap_Lm_bot, tb2, wh), (0, p.cap_Wm_bot / 2, zbc), "cap_bot")
    # top cap: panel z H-tc..H ; walls run down to the full outer envelope (z H-tc-wall_h..H)
    add("cap_top_panel", (p.cap_Lm, p.cap_Wm, tc), (0, 0, p.H - h), "cap_top")
    ztc = p.H - (tc + wall_h) / 2.0
    add("cap_top_wall_l", (tc, p.cap_Wm, wh), (-p.cap_Lm / 2, 0, ztc), "cap_top")
    add("cap_top_wall_r", (tc, p.cap_Wm, wh), (p.cap_Lm / 2, 0, ztc), "cap_top")
    add("cap_top_wall_f", (p.cap_Lm, tc, wh), (0, -p.cap_Wm / 2, ztc), "cap_top")
    add("cap_top_wall_b", (p.cap_Lm, tc, wh), (0, p.cap_Wm / 2, ztc), "cap_top")
    return out


def lift_items(items, group="cap_top", dz=130.0):
    out = []
    for it in items:
        if it.get("group") == group:
            cx, cy, cz = it["center"]
            out.append(dict(it, center=(cx, cy, cz + dz)))
        else:
            out.append(dict(it))
    return out


def check(p: Params):
    _, _, i_s = dieline_sleeve(p)
    _, _, _, i_c = dieline_cap(p)
    errs = []
    if abs(i_s["blank_w"] - (2 * (p.sleeve_Lm + p.sleeve_Wm) + p.glue_w)) > 1e-9:
        errs.append("sleeve blank width mismatch")
    if abs(i_s["sleeve_H"] - (p.H - p.tc - p.tc2)) > 1e-9:
        errs.append("sleeve height chain mismatch")
    if abs(i_c["blank_w"] - (p.cap_Lm + 2 * p.wall_blank)) > 1e-9:
        errs.append("cap blank width mismatch")
    if abs(p.cap_Lm - (p.sleeve_L + p.tcmax + 2 * p.gap)) > 1e-9:
        errs.append("cap/sleeve length chain mismatch")
    return errs


def report(p: Params):
    errs = check(p)
    _, _, i_s = dieline_sleeve(p)
    _, _, _, i_ct = dieline_cap(p, "top")
    _, _, _, i_cb = dieline_cap(p, "bot")
    area = (i_s["blank_w"] * i_s["blank_h"]
            + i_ct["blank_w"] * i_ct["blank_h"] + i_cb["blank_w"] * i_cb["blank_h"]) / 1e6
    same_caps = abs(p.tc - p.tc2) < 1e-9
    rows = [
        ("assembled outer", f"{p.L:g} x {p.W:g} x {p.H:g}"),
        ("board t (sleeve/top/bot)", f"{p.ts:g} / {p.tc:g} / {p.tc2:g}"),
        ("cap outer / inner", f"{p.L:g}x{p.W:g} / {p.L - 2 * p.tcmax:g}x{p.W - 2 * p.tcmax:g}"),
        ("sleeve outer", f"{p.sleeve_L:g} x {p.sleeve_W:g} x {p.sleeve_H:g}"),
        ("sleeve mfr", f"{p.sleeve_Lm:g} x {p.sleeve_Wm:g}"),
        ("cover depth d", f"{p.d_cover:g} (each cap; end-to-end)"),
        ("wall blank (BLD)", f"top {p.wall_blank:g} / bot {p.wall_blank_bot:g}"),
        ("cap centre panel", f"top {p.cap_Lm:g}x{p.cap_Wm:g} / bot {p.cap_Lm_bot:g}x{p.cap_Wm_bot:g}"),
        ("sleeve blank", f"{i_s['blank_w']:g} x {i_s['blank_h']:g}"),
        ("cap blank (x2)", f"{i_ct['blank_w']:g}x{i_ct['blank_h']:g} / "
                           f"{i_cb['blank_w']:g}x{i_cb['blank_h']:g}"
                           f"（{'同款' if same_caps else '上/下不同'}）"),
        ("total area", f"{area:.4f} m2"),
    ]
    return errs, rows


if __name__ == "__main__":
    p = Params()
    errs, rows = report(p)
    print("=== FEFCO 0310 BC 400x300x200 (assembled outer) - check ===")
    for k, v in rows:
        print(f"{k:20s}: {v}")
    print("errors:", errs if errs else "none")
