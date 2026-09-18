# -*- coding: utf-8 -*-
"""fold_conn_check.py — 折边客观检查（1.0.12 口径）

用户口径（2026-09-18，逐条对应反馈）：
  1. **俯视图**：折边与刀卡本体**垂直**（长卡两端沿 Y、短卡两端沿 X），卡端呈直角"L"；
  2. 折边沿卡长方向只占一个板厚 t（自卡端向内，不越出卡端），且整体落在容器内；
  3. **侧视图**：按展开料画，两端各延长 fold_len_out（= 净长 + t）、同高；原卡端 = **折弯线（点划线）**；
     轮廓四边闭合（含折边段端面）；
  4. 尺寸标注不得压图线（由 layout_check.py 的 [标注] 命中项覆盖）。

逐块断言，不用全局启发式。
"""
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "core"))
import matplotlib                                   # noqa: E402
matplotlib.use("Agg")
import importlib.util                               # noqa: E402

TOL = 0.35          # 纸面 mm 容差（线宽/取整）


def load(n, p):
    s = importlib.util.spec_from_file_location(n, p)
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


def _segs(ax):
    """→ [(p, q, is_fold)]，纸面坐标。"""
    out = []
    for ln in ax.lines:
        st = str(ln.get_linestyle()) not in ("-", "solid", "None")
        xs, ys = ln.get_xdata(), ln.get_ydata()
        for i in range(len(xs) - 1):
            a, b = (xs[i], ys[i]), (xs[i + 1], ys[i + 1])
            if math.dist(a, b) > 1e-9:
                out.append((a, b, st))
    return out


def _on_seg(v, c, d):
    """v 是否落在线段 cd 上（含端点）。"""
    if abs((d[0] - c[0]) * (v[1] - c[1]) - (d[1] - c[1]) * (v[0] - c[0])) > 0.06:
        return False
    return (min(c[0], d[0]) - TOL <= v[0] <= max(c[0], d[0]) + TOL
            and min(c[1], d[1]) - TOL <= v[1] <= max(c[1], d[1]) + TOL)


def _has(segs, p, q, fold=None):
    """线段 pq（或覆盖它的更长线段）是否存在；fold=True 要求点划线。"""
    for (a, b, st) in segs:
        if fold is not None and st != fold:
            continue
        if (math.dist(a, p) < TOL and math.dist(b, q) < TOL) or \
           (math.dist(a, q) < TOL and math.dist(b, p) < TOL):
            return True
        if (_on_seg(p, a, b) and _on_seg(q, a, b)) or (_on_seg(q, a, b) and _on_seg(p, a, b)):
            return True
    return False


def run(tag, cfg):
    gc = load("gc", os.path.join(HERE, "core", "grid_core.py"))
    gd = load("gd", os.path.join(HERE, "core", "grid_draw.py"))
    gm = load("gm", os.path.join(HERE, "core", "grid_model.py"))
    p = gc.Params(**cfg)
    _e, _r, d = gc.report(p)
    t, Hc = d["t"], d["cell_h"]
    if not (d.get("fold_l") or d.get("fold_w")):
        print(f"  {tag}: 无折边 → 跳过")
        return 0
    fig = gd.build_sheet(p, d)
    ax = [a for a in fig.get_axes() if a.get_zorder() < 50 and a.get_xlim()[1] > 1.5][0]
    PLX, ROW1, s = fig._plan_T
    fl_net, fl_out = d["fold_len"], d["fold_len_out"]
    xs = gm._slot_centers(d["margin_l"], d["slots_long"], d["pitch_l"], t)
    ys = gm._slot_centers(d["margin_w"], d["slots_short"], d["pitch_w"], t)

    def T(x, y):
        return (PLX + x * s, ROW1 + y * s)

    _flc = fl_out if d.get("fold_l") else 0.0       # 长卡折边：B 视图右移这么多（让开 C 视图尺寸列）

    def Tb(h, l):                                   # B（旋转 90°：高横向 / 长竖向）
        return ((48.0 + (p.L + _flc) * s + 12.0) + h * s, ROW1 + l * s)

    def Tc(l, h):                                   # C（长横向 / 高竖向）
        return (48.0 + l * s, (ROW1 - 24.0 - Hc * s) + h * s)

    bad = []
    segs = _segs(ax)

    # ---- 1/2 俯视：折边 = 与本体垂直的闭合矩形，贴卡端、在容器内 ----
    tabs = gm._fold_tabs(p, d)
    n_expect = (len(ys) * 2 if d.get("fold_l") else 0) + (len(xs) * 2 if d.get("fold_w") else 0)
    if len(tabs) != n_expect:
        bad.append(f"折边块数 {len(tabs)} ≠ 预期 {n_expect}")
    for tb in tabs:
        x0, x1, y0, y1, is_long, fold_edge = tb
        # 四条边：贴本体料面那条 = 折弯线（点划线），其余三条 = 裁切边（实线）。
        # 用户 2026-09-18：「折边折叠处改为虚线（折弯线），实线意味着裁切，制作时就是裁断的」。
        for key, (a, b) in (("y0", ((x0, y0), (x1, y0))), ("y1", ((x0, y1), (x1, y1))),
                            ("x0", ((x0, y0), (x0, y1))), ("x1", ((x1, y0), (x1, y1)))):
            want_fold = (key == fold_edge)
            if not _has(segs, T(*a), T(*b), fold=want_fold):
                bad.append(f"折边 {a}->{b} 缺边或线型错"
                           f"（{'折弯线须点划线' if want_fold else '裁切边须实线'}）")
        if fold_edge not in ("x0", "x1", "y0", "y1"):
            bad.append(f"折边 fold_edge 取值非法：{fold_edge!r}")
        else:
            # 折弯线 = 折边的**根部**（贴槽口中心线那一侧，距离 ≈ t/2）；
            # 且必须与刀卡本体长度方向垂直（长卡折边 → y 向边；短卡折边 → x 向边）。
            if is_long:
                if fold_edge not in ("y0", "y1"):
                    bad.append(f"长卡折边折弯线应在 y 向边，实际 {fold_edge}")
                else:
                    ye = y0 if fold_edge == "y0" else y1
                    near = min(abs(ye - yc) for yc in ys)
                    if abs(near - t / 2) > 1e-6:
                        bad.append(f"长卡折边折弯线不在根部（距槽心中线 {near:g}，应 {t/2:g}）")
            else:
                if fold_edge not in ("x0", "x1"):
                    bad.append(f"短卡折边折弯线应在 x 向边，实际 {fold_edge}")
                else:
                    xe = x0 if fold_edge == "x0" else x1
                    near = min(abs(xe - xc) for xc in xs)
                    if abs(near - t / 2) > 1e-6:
                        bad.append(f"短卡折边折弯线不在根部（距槽心中线 {near:g}，应 {t/2:g}）")
        dx, dy = abs(x1 - x0), abs(y1 - y0)
        ok = (abs(dx - t) < 1e-6 and abs(dy - fl_net) < 1e-6) if is_long \
            else (abs(dy - t) < 1e-6 and abs(dx - fl_net) < 1e-6)
        if not ok:
            bad.append(f"折边({'长' if is_long else '短'}卡) 投影 {dx:g}×{dy:g} 不符合"
                       f"（应板厚 {t:g} × 净长 {fl_net:g}，且与本体垂直）")
        if not (x0 >= -1e-9 and x1 <= p.L + 1e-9 and y0 >= -1e-9 and y1 <= p.W + 1e-9):
            bad.append(f"折边 ({x0:g},{y0:g})-({x1:g},{y1:g}) 伸出容器外")
    # 卡端端面线（折弯处的转角棱）
    if d.get("fold_l"):
        for yc in ys:
            for xe in (0.0, p.L):
                if not _has(segs, T(xe, yc - t / 2), T(xe, yc + t / 2)):
                    bad.append(f"长卡 y={yc:g} 卡端 x={xe:g} 无端面线")
    if d.get("fold_w"):
        for xc in xs:
            for ye in (0.0, p.W):
                if not _has(segs, T(xc - t / 2, ye), T(xc + t / 2, ye)):
                    bad.append(f"短卡 x={xc:g} 卡端 y={ye:g} 无端面线")

    # ---- 3 侧视图：轮廓闭合 + 折弯线（点划线）位置 ----
    for nm, Bp, h_solid in (("B 短卡", lambda h, l: Tb(h, l), Hc),
                            ("C 长卡", lambda h, l: Tc(l, h), 0.0)):
        is_B = nm.startswith("B")
        fold_on = bool(d.get("fold_w")) if is_B else bool(d.get("fold_l"))
        if not fold_on:
            continue
        body = p.W if is_B else p.L
        l_a, l_b = -fl_out, body + fl_out              # 卡自身坐标：本体 0..body，两端各延 fl_out
        if abs((l_b - l_a) - (d["blank_W"] if is_B else d["blank_L"])) > 1e-6:
            bad.append(f"{nm} 展开长 {l_b - l_a:g} ≠ blank= "
                       f"{d['blank_W'] if is_B else d['blank_L']:g}")
        if not _has(segs, Bp(h_solid, l_a), Bp(h_solid, l_b)):
            bad.append(f"{nm} 侧视 完整长边未贯通（h={h_solid:g}）")
        for le in (l_a, l_b):
            if not _has(segs, Bp(0.0, le), Bp(Hc, le)):
                bad.append(f"{nm} 侧视 端面 l={le:g} 未闭合")
        for le in (0.0, body):
            if not _has(segs, Bp(0.0, le), Bp(Hc, le), fold=True):
                bad.append(f"{nm} 侧视 l={le:g} 折弯线缺失或不是点划线")

    if bad:
        print(f"  {tag}: FAIL ({len(bad)})")
        for b in bad[:12]:
            print("      -", b)
        return 1
    print(f"  {tag}: PASS（折边 {len(tabs)} 块 · 净长 {fl_net:g} · 展开端部 {fl_out:g}）")
    return 0


CASES = [
    ("400×300 格32 t5 双边", dict(L=400, W=300, H=300, pl=32, pw=32, ph=60, t=5.0, version=1)),
    ("580×380 格65 t5 V1", dict(L=580, W=380, H=380, pl=65, pw=38, ph=85, t=5.0, version=1)),
    ("580×380 格65 t5 V2", dict(L=580, W=380, H=380, pl=65, pw=38, ph=85, t=5.0, version=2)),
    ("1140×740 格181 t6 双边", dict(L=1140, W=740, H=550, pl=181, pw=96, ph=100, t=6.0, version=1)),
    ("400×300 格32 关折边", dict(L=400, W=300, H=300, pl=32, pw=32, ph=60, t=5.0, version=1,
                             fold_on=False)),
]

if __name__ == "__main__":
    only = sys.argv[1] if len(sys.argv) > 1 else None
    rc = 0
    for tag, cfg in CASES:
        if only and only not in tag:
            continue
        rc |= run(tag, cfg)
    print("fold_conn_check:", "ALL PASS" if rc == 0 else "有 FAIL")
    sys.exit(rc)
