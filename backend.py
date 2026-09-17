# -*- coding: utf-8 -*-
"""backend.py — 四类设计管线统一后端（GUI / CLI 共用）。

片材：    run_sheet(L, W, H, outdir, ...)
仿形垫块：run_block(L, W, H, sl, sw, sh, gap, outdir, ...)
网格刀卡：run_grid(container, cell, t, outdir, ..., version=1|2)
瓦楞纸箱：box_plan(box, dims, mode, flutes, params)   → 即时计算（界面用，不落盘）
          box_export(box, plan, outdir, prefix, frame) → 出图（线程里跑）
          run_box(...)                                  → = plan + export
辅助：    flute_choices() / flute_defaults(code, box) / ranges_of(code, box) / box_dim_rows()
导出命名：全部文件 =「用户前缀_属性后缀」，落在用户选定目录。
"""
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

_HERE = os.path.dirname(os.path.abspath(__file__))
_CORE = os.path.join(_HERE, "core")
for _p in (_HERE, _CORE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from flute_lib import FLUTES, ranges_for          # noqa: E402

try:
    from box0210_2d import _today
except Exception:                                     # pragma: no cover
    def _today():
        import datetime
        return datetime.date.today().strftime("%Y-%m-%d")


class Result:
    def __init__(self, files, rows, d=None):
        self.files = list(files)
        self.rows = list(rows)
        self.d = d or {}

    def __repr__(self):
        return f"Result({len(self.files)} files)"


def _pre(prefix):
    prefix = (prefix or "").strip()
    return (prefix + "_") if prefix else ""


def _save_pdf_png_svg(fig, outdir, name):
    out = []
    pdf = os.path.join(outdir, name + ".pdf")
    try:
        with PdfPages(pdf) as pp:
            pp.savefig(fig)
    except PermissionError:            # 目标 PDF 被占用 → 落 _新.pdf
        pdf = os.path.join(outdir, name + "_新.pdf")
        with PdfPages(pdf) as pp:
            pp.savefig(fig)
    out.append(pdf)
    for ext in ("png", "svg"):
        fp = os.path.join(outdir, f"{name}.{ext}")
        fig.savefig(fp, dpi=200)
        out.append(fp)
    plt.close(fig)
    return out


def _md(outdir, name, lines):
    fp = os.path.join(outdir, name)
    with open(fp, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    return fp


def frame_meta(frame=None):
    """图框公共字段：单位名称 + 设计/制图/审核/批准（界面「设置」里维护，图框内锁定）。"""
    f = dict(frame or {})
    return dict(company=f.get("company") or "上海银轮热交换系统有限公司",
                designed=f.get("designed", ""), drawn=f.get("drawn", ""),
                checked=f.get("checked", ""), approved=f.get("approved", ""))


def _fmt3(v):
    return " × ".join(f"{x:g}" for x in v)


# ================================================================ 楞型
def flute_choices():
    """[(code, 显示名)] 供界面下拉。"""
    return [(c, f"{f['name']}（t={f['t']:g}）") for c, f in FLUTES.items()]


def ranges_of(code, box=None):
    return ranges_for(FLUTES[code]["t"], box)


def flute_defaults(code, box=None):
    """按楞型给可编辑参数默认值（区间下限/中值；与已交付样箱一致）。"""
    r = ranges_of(code, box)

    def lo(k, dflt):
        v = r.get(k)
        return v[0] if isinstance(v, tuple) else dflt

    def mid(k, dflt):
        v = r.get(k)
        return (v[0] + v[1]) / 2.0 if isinstance(v, tuple) else dflt

    out = dict(glue_w=lo("glue_w", 45.0), flap_gain=lo("flap_gain", 3.0),
               flap_reduce=lo("flap_reduce", 3.0), slot_w=mid("slot_w", 10.0))
    if box in ("0310", "0312"):
        out["gap"] = 2.0            # 盖内/围框外单边间隙（样箱口径 2.0；区间 1–3）
    return out


# ================================================================ 片材
def run_sheet(L, W, H, outdir, prefix="", name="片材", material="", frame=None):
    from sheet_core import Params, report
    from sheet_draw import build_sheet
    from sheet_make import write_dxf, export_step, write_stl, render_axo
    from box0210_3d import stl_check
    p = Params(L=L, W=W, H=H, name=name, material=material)
    errs, rows = report(p)
    if errs:
        raise ValueError("；".join(errs))
    os.makedirs(outdir, exist_ok=True)
    pre = _pre(prefix)
    files = [write_dxf(p, os.path.join(outdir, pre + "片材轮廓_1-1.dxf"))]
    files += _save_pdf_png_svg(build_sheet(p, meta=frame_meta(frame)), outdir,
                               pre + "图纸-三视图+轴测图_A3")
    files += render_axo(p, os.path.join(outdir, pre + "轴测图"))
    stp = os.path.join(outdir, pre + "三维模型.step")
    bb = export_step(p, stp)
    assert abs((bb[3] - bb[0]) - L) < 0.01 and abs((bb[4] - bb[1]) - W) < 0.01
    files.append(stp)
    stl = os.path.join(outdir, pre + "三维模型.stl")
    write_stl(p, stl)
    n, _bx = stl_check(stl)
    assert n == 12
    files.append(stl)
    files.append(_md(outdir, pre + "参数表.md", [
        f"# {name} 参数表", "",
        f"- 外形 {L:g} × {W:g} × {H:g} mm",
        f"- 单面面积 {p.area:.4f} m²；体积 {p.volume:.5f} L；对角线 {p.diag:.1f} mm",
        f"- 材料：{material or '—'}",
    ]))
    return Result(files, rows)


# ================================================================ 仿形垫块
def run_block(L, W, H, sl, sw, sh, gap, outdir, prefix="", margin_left=None,
              open_side="front", name="仿形块", material="", frame=None):
    from block_core import Params, report
    from block_model import items, write_dxf, export_step, write_stl, stl_check
    from block_draw import build_sheet, render_axo
    p = Params(L=L, W=W, H=H, sl=sl, sw=sw, sh=sh, gap=gap,
               margin_left=margin_left, open_side=open_side,
               name=name, material=material)
    errs, rows, d = report(p)
    if errs:
        raise ValueError("；".join(errs))
    os.makedirs(outdir, exist_ok=True)
    pre = _pre(prefix)
    files = [write_dxf(p, d, os.path.join(outdir, pre + "仿形块俯视_1-1.dxf"))]
    files += _save_pdf_png_svg(build_sheet(p, d, meta=frame_meta(frame)),
                               outdir, pre + "图纸-三视图+轴测图_A3")
    files += render_axo(p, d, os.path.join(outdir, pre + "轴测图"))
    it = items(p, d)
    stp = os.path.join(outdir, pre + "三维模型.step")
    bb = export_step(stp, it)
    assert abs((bb[3] - bb[0]) - L) < 0.01 and abs((bb[5] - bb[2]) - H) < 0.01
    files.append(stp)
    stl = os.path.join(outdir, pre + "三维模型.stl")
    write_stl(stl, it)
    stl_check(stl)
    files.append(stl)
    slot_txt = ("全贯穿（槽宽 = 块宽）" if d["through"]
                else f"单边贯穿（{'前' if open_side != 'back' else '后'}侧开口，对侧墙厚 {d['side_wall']:g}）")
    files.append(_md(outdir, pre + "参数表.md", [
        f"# {name} 参数表", "",
        f"- 垫块 {L:g} × {W:g} × {H:g} mm",
        f"- 开槽 {sl:g} × {sw:g} × {sh:g} mm × {d['n']} 个；间距 {gap:g} mm",
        f"- 槽型：{slot_txt}",
        f"- 边距（{d['margin_mode']}）：左 {d['margin_l']:g} / 右 {d['margin_r']:g}（总量 {d['margin_total']:g}）",
        f"- 净体积 {d['v_net']:.1f} cm³（块体 {d['v_block']:.1f} cm³）",
        f"- 材料：{material or '—'}",
    ]))
    return Result(files, rows, d)


# ================================================================ 网格刀卡
def grid_plan(container, cell, t, slot_w=None, sep_t=None, pads="both",
              version=1, name="瓦楞刀卡网格"):
    """即时计算：→ (Params, rows, d)。"""
    from grid_core import Params, report
    L, W, H = container
    pl, pw, ph = cell
    if slot_w is not None and slot_w < t - 1e-9:
        raise ValueError(f"开槽宽 {slot_w:g} mm < 刀卡厚 {t:g} mm：会装配干涉")
    slot_clear = max(0.0, (slot_w - t)) if slot_w else 0.0
    p = Params(L=L, W=W, H=H, pl=pl, pw=pw, ph=ph, t=t, version=version,
               input_mode="inner", pads=pads, slot_clear=slot_clear,
               sep_t=(sep_t or 0.0), name=name)
    errs, rows, d = report(p)
    if errs:
        raise ValueError("；".join(errs))
    return p, rows, d


def run_grid(container, cell, t, outdir, prefix="", slot_w=None, sep_t=None,
             pads="both", version=1, name="瓦楞刀卡网格", frame=None):
    """container=(L,W,H) 容器内尺寸（= 内衬外尺寸）；cell=(l,w,h) 每格；t=刀卡厚。"""
    from grid_model import items, write_dxf, export_step, write_stl, stl_check
    from grid_draw import build_sheet, render_axo
    p, rows, d = grid_plan(container, cell, t, slot_w, sep_t, pads, version, name)
    L, W, H = container
    t_used = p.t
    slot_w_eff = slot_w if slot_w else (t_used + p.slot_clear)
    os.makedirs(outdir, exist_ok=True)
    pre = _pre(prefix)
    files = [write_dxf(p, d, os.path.join(outdir, pre + "刀卡展开图_1-1.dxf"))]
    files += _save_pdf_png_svg(build_sheet(p, d, meta=frame_meta(frame)),
                               outdir, pre + "图纸-网格俯视+刀卡侧视+轴测图_A3")
    files += render_axo(p, d, os.path.join(outdir, pre + "轴测图"))
    it = items(p, d)
    stp = os.path.join(outdir, pre + "三维模型-刀卡网格.step")
    bb = export_step(stp, it)
    assert abs((bb[3] - bb[0]) - L) < 0.02
    files.append(stp)
    stl = os.path.join(outdir, pre + "三维模型-刀卡网格.stl")
    write_stl(stl, it)
    stl_check(stl)
    files.append(stl)
    vtxt = "V1 长对长" if d["version"] == 1 else "V2 长对宽"
    files.append(_md(outdir, pre + "参数表.md", [
        f"# {name}（{vtxt}）参数表", "",
        f"- 容器内尺寸 {L:g} × {W:g} × {H:g} mm；每格 {d['cell_l']:g} × {d['cell_w']:g} × {d['cell_h']:g} mm",
        f"- 格数 长边 {d['n_l']} × 短边 {d['n_w']}；边距 {d['margin_l']:g} / {d['margin_w']:g}（≥6）",
        f"- 层数 {d['layers']}（每层一格格架）；收容数 {d['capacity']}",
        f"- 长刀卡 每层 {d['cards_long']} 张 × {d['layers']} 层 = {d['cards_long_total']} 张（{d['Lc']:g} × {d['cell_h']:g}）",
        f"- 短刀卡 每层 {d['cards_short']} 张 × {d['layers']} 层 = {d['cards_short_total']} 张（{d['Wc']:g} × {d['cell_h']:g}）",
        f"- 隔板 中间 {d['seps_mid']} + 底/顶 {d['seps_tb']} = {d['seps_total']} 张 {L:g} × {W:g} × {d['st']:g}",
        f"- 刀卡厚 {t_used:g}；开槽宽 {slot_w_eff:g}；堆叠高 {d['H_stack']:g} ≤ {H:g}（余量 {d['H_slack']:g}）",
        f"- 用纸：刀卡 {d['area_cards']:.4f} m² + 隔板 {d['area_seps']:.4f} m²",
    ]))
    return Result(files, rows, d)


# ================================================================ 瓦楞纸箱
def _box_resolve(box, flutes):
    f = dict(flutes or {})
    if box == "0201":
        f.setdefault("body", "BC")
    elif box == "0310":
        ct = f.get("cap_top", "BC")
        f.setdefault("cap_top", ct)
        f.setdefault("cap_bottom", f.get("cap_bottom", ct))
        f.setdefault("sleeve", "BC")
    elif box == "0312":
        f.setdefault("base", "BC")
        f.setdefault("lid", "BC")
    else:
        raise ValueError(f"未知箱型 {box}")
    return f


def box_inner_size(box, dims, flutes, params):
    """外尺寸 → 内腔尺寸。"""
    L, W, H = dims
    gap = params.get("gap", 2.0)
    if box == "0201":
        t = FLUTES[flutes["body"]]["t"]
        return (L - 2 * t, W - 2 * t, H - 2 * t)
    if box == "0310":
        ts = FLUTES[flutes["sleeve"]]["t"]
        tc = max(FLUTES[flutes["cap"]]["t"], FLUTES[flutes.get("cap_bot", flutes["cap"])]["t"])
        return (L - 2 * tc - 2 * gap - 2 * ts, W - 2 * tc - 2 * gap - 2 * ts, H - 2 * tc)
    if box == "0312":
        tb = FLUTES[flutes["base"]]["t"]
        tl = FLUTES[flutes["lid"]]["t"]
        return (L - 2 * tl - 2 * gap - 2 * tb, W - 2 * tl - 2 * gap - 2 * tb, H - 2 * tb)
    raise ValueError(box)


def box_outer_size(box, inner, flutes, params):
    """内腔尺寸 → 外尺寸（组装外形）。"""
    Li, Wi, Hi = inner
    gap = params.get("gap", 2.0)
    if box == "0201":
        t = FLUTES[flutes["body"]]["t"]
        return (Li + 2 * t, Wi + 2 * t, Hi + 2 * t)
    if box == "0310":
        ts = FLUTES[flutes["sleeve"]]["t"]
        tc = max(FLUTES[flutes["cap"]]["t"], FLUTES[flutes.get("cap_bot", flutes["cap"])]["t"])
        return (Li + 2 * ts + 2 * gap + 2 * tc, Wi + 2 * ts + 2 * gap + 2 * tc, Hi + 2 * tc)
    if box == "0312":
        tb = FLUTES[flutes["base"]]["t"]
        tl = FLUTES[flutes["lid"]]["t"]
        return (Li + 2 * tb + 2 * gap + 2 * tl, Wi + 2 * tb + 2 * gap + 2 * tl, Hi + 2 * tb)
    raise ValueError(box)


def box_dim_rows(box, p):
    """内 / 制造 / 外 三口径（界面与参数表展示）。"""
    if box == "0201":
        outer, mfr = (p.L, p.W, p.H), (p.Lm, p.Wm, p.Hm)
        inner = (p.Li, p.Wi, p.Hi)
    elif box == "0310":
        outer, mfr = (p.L, p.W, p.H), (p.sleeve_Lm, p.sleeve_Wm, p.sleeve_H)
        inner = (p.sleeve_Lm - p.ts, p.sleeve_Wm - p.ts, p.sleeve_H)
    else:
        outer, mfr = (p.L, p.W, p.H), (p.base_Lm, p.base_Wm, p.base_Hm)
        inner = (p.base_Lm - p.tb, p.base_Wm - p.tb, p.H - 2 * p.tb)
    return [("外尺寸（组装）", _fmt3(outer)), ("制造尺寸", _fmt3(mfr)), ("内尺寸（内腔）", _fmt3(inner))]


def _flute_desc(box, flutes):
    """长描述（技术说明用）。"""
    if box == "0201":
        c = flutes["body"]
        return f"{FLUTES[c]['name']} t={FLUTES[c]['t']:g}"
    if box == "0310":
        cs = FLUTES[flutes["sleeve"]]
        ct = FLUTES[flutes.get("cap_top", "BC")]
        cb = FLUTES[flutes.get("cap_bottom", flutes.get("cap_top", "BC"))]
        if flutes.get("cap_bottom", ct) == flutes.get("cap_top", ct):
            return f"围框 {cs['name']} t={cs['t']:g}；盖（×2） {ct['name']} t={ct['t']:g}"
        return (f"围框 {cs['name']} t={cs['t']:g}；上盖 {ct['name']} t={ct['t']:g}；"
                f"下盖 {cb['name']} t={cb['t']:g}")
    cb_ = FLUTES[flutes["base"]]
    cl = FLUTES[flutes["lid"]]
    return f"底箱 {cb_['name']} t={cb_['t']:g}；天盖 {cl['name']} t={cl['t']:g}"


def _flute_short(box, flutes):
    """短描述（图框「材料」栏，≤32mm 宽；超长时图框自动折两行）。"""
    if box == "0201":
        c = flutes["body"]
        return f"{c} t={FLUTES[c]['t']:g}"
    if box == "0310":
        cs, ct = flutes["sleeve"], flutes.get("cap_top", "BC")
        cb = flutes.get("cap_bottom", ct)
        if cb == ct:
            return f"围框 {cs} t={FLUTES[cs]['t']:g} / 盖×2 {ct} t={FLUTES[ct]['t']:g}"
        return (f"围框 {cs} t={FLUTES[cs]['t']:g} / 上盖 {ct} t={FLUTES[ct]['t']:g} / "
                f"下盖 {cb} t={FLUTES[cb]['t']:g}")
    cb_, cl = flutes["base"], flutes["lid"]
    return f"底箱 {cb_} t={FLUTES[cb_]['t']:g} / 天盖 {cl} t={FLUTES[cl]['t']:g}"


def _validate(box, flutes, params):
    for code in set(flutes.values()):
        r = ranges_of(code, box)
        for k in ("glue_w", "flap_gain", "flap_reduce", "slot_w"):
            v = params.get(k)
            if v is not None and isinstance(r.get(k), tuple):
                lo, hi = r[k]
                if not (lo - 1e-9 <= float(v) <= hi + 1e-9):
                    raise ValueError(f"{k} = {float(v):g} 超出标准区间 {lo:g}–{hi:g}"
                                     f"（{FLUTES[code]['name']}）")
        key = "gap" if box == "0310" else ("box_gap" if box == "0312" else None)
        v = params.get("gap")
        if key and v is not None and isinstance(r.get(key), tuple):
            lo, hi = r[key]
            if not (lo - 1e-9 <= float(v) <= hi + 1e-9):
                raise ValueError(f"间隙 {float(v):g} mm 超出区间 {lo:g}–{hi:g}")


def box_plan(box, dims, mode="outer", flutes=None, params=None, name=None):
    """即时计算（界面每次改参数都调）：→ dict(p=, rows=, meta=, desc=, short=, L/W/H)。"""
    flutes = _box_resolve(box, flutes)
    params = dict(params or {})
    _validate(box, flutes, params)

    fl = dict(flutes)
    if box == "0310":
        fl["cap"] = flutes["cap_top"]
        fl["cap_bot"] = flutes["cap_bottom"]
    inner_in = tuple(dims) if mode == "inner" else None
    outer = box_outer_size(box, dims, fl, params) if mode == "inner" else tuple(float(v) for v in dims)
    L, W, H = (float(v) for v in outer)
    if min(L, W, H) <= 0:
        raise ValueError("尺寸须为正数")
    inner = box_inner_size(box, (L, W, H), fl, params)

    if box == "0201":
        from box0201_core import Params, report
        code = flutes["body"]
        t = FLUTES[code]["t"]
        d = flute_defaults(code, box)
        p = Params(L=L, W=W, H=H, t=t, glue_w=params.get("glue_w", d["glue_w"]),
                   flap_gain=params.get("flap_gain", d["flap_gain"]),
                   flap_reduce=params.get("flap_reduce", d["flap_reduce"]),
                   slot_w=params.get("slot_w", d["slot_w"]))
    elif box == "0310":
        from box0310_core import Params, report
        cs, ct, cb = flutes["sleeve"], flutes["cap_top"], flutes["cap_bottom"]
        d = flute_defaults(ct, box)
        p = Params(L=L, W=W, H=H, t=FLUTES[ct]["t"], t_sleeve=FLUTES[cs]["t"],
                   t_cap_bot=FLUTES[cb]["t"],
                   glue_w=params.get("glue_w", d["glue_w"]),
                   gap=params.get("gap", d["gap"]),
                   cover_extra=params.get("cover_extra", 0.0))
    else:
        from box0312_core import Params, report
        cb_, cl = flutes["base"], flutes["lid"]
        d = flute_defaults(cl, box)
        cover_default = max(30.0, round(H * 0.45))
        p = Params(L=L, W=W, H=H, t=FLUTES[cl]["t"], t_base=FLUTES[cb_]["t"],
                   glue_w=params.get("glue_w", d["glue_w"]),
                   gap=params.get("gap", d["gap"]),
                   cover_depth=params.get("cover_depth", cover_default),
                   flap_gain=params.get("flap_gain", d["flap_gain"]),
                   flap_reduce=params.get("flap_reduce", d["flap_reduce"]),
                   slot_w=params.get("slot_w", d["slot_w"]))
        if not (10.0 <= p.cover_depth <= p.base_Hm + 1e-9):
            raise ValueError(f"罩深 {p.cover_depth:g} mm 须在 10 – {p.base_Hm:g} mm（底箱制造高）之间")

    errs, rows = report(p)
    if errs:
        raise ValueError("；".join(errs))
    nm = name or {"0201": f"FEFCO 0201 开槽箱 {L:g}×{W:g}×{H:g}",
                  "0310": f"FEFCO 0310 围框+两盖 {L:g}×{W:g}×{H:g}",
                  "0312": f"FEFCO 0312 有底无盖+平顶罩盖 {L:g}×{W:g}×{H:g}"}[box]
    desc = _flute_desc(box, flutes)
    short = _flute_short(box, flutes)
    if box == "0201":
        extra = dict(mat=FLUTES[flutes["body"]]["name"],
                     dwgno=f"0201-{flutes['body']}-{L:g}x{W:g}x{H:g}")
    elif box == "0310":
        extra = dict(mat_sleeve=FLUTES[flutes["sleeve"]]["name"],
                     mat_cap=FLUTES[flutes["cap_top"]]["name"],
                     mat_cap_bot=FLUTES[flutes["cap_bottom"]]["name"],
                     dwgno=f"0310-{flutes['sleeve']}+{flutes['cap_top']}"
                           + ("" if flutes["cap_bottom"] == flutes["cap_top"]
                              else "/" + flutes["cap_bottom"]) + f"-{L:g}x{W:g}x{H:g}")
    else:
        extra = dict(mat_base=FLUTES[flutes["base"]]["name"],
                     mat_lid=FLUTES[flutes["lid"]]["name"],
                     dwgno=f"0312-{flutes['base']}+{flutes['lid']}-{L:g}x{W:g}x{H:g}")
    meta = dict(extra, name=nm, material=f"{short}（可折叠）",
                caption=f"{short} · 组装外尺寸 {L:g}×{W:g}×{H:g} · 单位 mm · {_today()} · 生成：ZCode 参数化管线")
    return dict(p=p, rows=rows, meta=meta, desc=desc, short=short, flutes=flutes,
                params=params, L=L, W=W, H=H, inner=inner, mode=mode,
                inner_in=inner_in, name=nm)


def box_export(box, plan, outdir, prefix="", frame=None):
    """出图（耗时；界面放到后台线程里跑）。"""
    from box0210_3d import build_items_from, render_view, export_solids, write_stl_file, stl_check
    p, rows = plan["p"], plan["rows"]
    meta = dict(plan["meta"], **frame_meta(frame))
    L, W, H = plan["L"], plan["W"], plan["H"]
    os.makedirs(outdir, exist_ok=True)
    pre = _pre(prefix)
    files = []
    if box == "0201":
        from box0201_core import panels, open_items
        from box0201_sheets import write_dxf, build_sheet
        ic = build_items_from(panels(p), False)
        io_ = open_items(build_items_from(panels(p), True), p)
        files.append(write_dxf(p, os.path.join(outdir, pre + "展开图_dieline_1-1.dxf")))
        files += _save_pdf_png_svg(build_sheet(p, items_closed=ic, items_open=io_, meta=meta),
                                   outdir, pre + "图纸-展开图+轴测图_A3")
        stp = os.path.join(outdir, pre + "三维模型-闭合.step")
        bb = export_solids(p, False, stp, items=ic)
        d3 = tuple(round(bb[i + 3] - bb[i], 3) for i in range(3))
        assert abs(d3[0] - L) < 0.02 and abs(d3[1] - W) < 0.02 and abs(d3[2] - H) < 0.02, f"bbox {d3}"
        files.append(stp)
        for fn, it_, lab in ((pre + "三维模型-闭合.stl", ic, "闭合"),
                             (pre + "三维模型-开盖.stl", io_, "开盖")):
            fp = os.path.join(outdir, fn)
            write_stl_file(p, False, fp, items=it_)
            stl_check(fp)
            files.append(fp)
            files += render_view(p, lab == "开盖", os.path.join(outdir, pre + f"轴测图-{lab}"),
                                 items=it_, title=f"{plan['name']} · {plan['desc']} · {lab}")
        files.append(_md(outdir, pre + "参数表.md", [
            "# FEFCO 0201 开槽箱 参数表", ""] +
            [f"- {k}：{v}" for k, v in box_dim_rows(box, p)] +
            [f"- 纸板：{plan['desc']}",
             f"- 展开：接舌 {p.glue_w:g} + 2×({p.Lm:g} + {p.Wm:g})；摇盖 外 {p.fo:g} / 内 {p.fi:g}；开槽宽 {p.slot_w:g}"]))
        return Result(files, rows)

    if box == "0310":
        from box0310_core import panels, lift_items
        from box0310_sheets import write_dxf, build_sheet
        ic = build_items_from(panels(p), False)
        io_ = lift_items(lift_items(ic, "cap_bot", -70.0), "cap_top", 110.0)
        files.append(write_dxf(p, os.path.join(outdir, pre + "展开图_dieline_1-1.dxf")))
        files += _save_pdf_png_svg(build_sheet(p, items_closed=ic, items_open=io_, meta=meta),
                                   outdir, pre + "图纸-展开图+轴测图_A3")
        stp = os.path.join(outdir, pre + "三维模型-组装.step")
        bb = export_solids(p, False, stp, items=ic)
        d3 = tuple(round(bb[i + 3] - bb[i], 3) for i in range(3))
        assert abs(d3[0] - L) < 0.05 and abs(d3[1] - W) < 0.05 and abs(d3[2] - H) < 0.05, f"bbox {d3}"
        files.append(stp)
        for fn, it_, lab in ((pre + "三维模型-组装.stl", ic, "组装"),
                             (pre + "三维模型-分解.stl", io_, "分解")):
            fp = os.path.join(outdir, fn)
            write_stl_file(p, False, fp, items=it_)
            stl_check(fp)
            files.append(fp)
            files += render_view(p, lab == "分解", os.path.join(outdir, pre + f"轴测图-{lab}"),
                                 items=it_, title=f"{plan['name']} · {plan['desc']} · {lab}")
        files.append(_md(outdir, pre + "参数表.md", [
            "# FEFCO 0310 围框+两盖 参数表", ""] +
            [f"- {k}：{v}" for k, v in box_dim_rows(box, p)] +
            [f"- 材料：{plan['desc']}",
             f"- 围框制造 {p.sleeve_Lm:g}×{p.sleeve_Wm:g}，高 {p.sleeve_H:g}（= 外高 − t上盖 − t下盖）",
             f"- 上盖中心 {p.cap_Lm:g}×{p.cap_Wm:g}，墙深 {p.wall_blank:g}；下盖中心 {p.cap_Lm_bot:g}×{p.cap_Wm_bot:g}，墙深 {p.wall_blank_bot:g}；罩深 {p.d_cover:g}",
             f"- 盖内腔 {p.L-2*p.tcmax:g}×{p.W-2*p.tcmax:g}（按较厚盖板）；围框外 = 盖内 − 2×{p.gap:g}；两盖腰线对接"]))
        return Result(files, rows)

    from box0312_core import panels, lift_items
    from box0312_sheets import write_dxf, build_sheet
    ic = build_items_from(panels(p), False)
    io_ = lift_items(ic, "lid", 120.0)
    files.append(write_dxf(p, os.path.join(outdir, pre + "展开图_dieline_1-1.dxf")))
    files += _save_pdf_png_svg(build_sheet(p, items_closed=ic, items_open=io_, meta=meta),
                               outdir, pre + "图纸-展开图+轴测图_A3")
    stp = os.path.join(outdir, pre + "三维模型-组装.step")
    bb = export_solids(p, False, stp, items=ic)
    d3 = tuple(round(bb[i + 3] - bb[i], 3) for i in range(3))
    assert abs(d3[0] - L) < 0.05 and abs(d3[1] - W) < 0.05 and abs(d3[2] - H) < 0.05, f"bbox {d3}"
    files.append(stp)
    for fn, it_, lab in ((pre + "三维模型-组装.stl", ic, "组装"),
                         (pre + "三维模型-开盖.stl", io_, "开盖")):
        fp = os.path.join(outdir, fn)
        write_stl_file(p, False, fp, items=it_)
        stl_check(fp)
        files.append(fp)
        files += render_view(p, lab == "开盖", os.path.join(outdir, pre + f"轴测图-{lab}"),
                             items=it_, title=f"{plan['name']} · {plan['desc']} · {lab}")
    files.append(_md(outdir, pre + "参数表.md", [
        "# FEFCO 0312 有底无盖+平顶罩盖 参数表", ""] +
        [f"- {k}：{v}" for k, v in box_dim_rows(box, p)] +
        [f"- 材料：{plan['desc']}",
         f"- 底箱制造 {p.base_Lm:g}×{p.base_Wm:g}×{p.base_Hm:g}；摇盖 外 {p.base_fo:g}/内 {p.base_fi:g}；开槽 {p.slot_w:g}",
         f"- 天盖内腔 {p.L-2*p.tl:g}×{p.W-2*p.tl:g}；罩深 {p.cover_depth:g}；盖墙深 {p.lid_wall_blank:g}"]))
    return Result(files, rows)


def run_box(box, dims, outdir, mode="outer", flutes=None, params=None,
            prefix="", name=None, frame=None):
    """box: '0201' | '0310' | '0312'；dims=(L,W,H) 外尺寸(mode='outer')或内腔(mode='inner')。"""
    plan = box_plan(box, dims, mode=mode, flutes=flutes, params=params, name=name)
    return box_export(box, plan, outdir, prefix=prefix, frame=frame)


# ================================================================ CLI 冒烟
if __name__ == "__main__":
    import time
    out = sys.argv[1] if len(sys.argv) > 1 else r"D:/Tools/tmp/packapp/_smoke"
    os.makedirs(out, exist_ok=True)
    t0 = time.time()
    r = run_sheet(400, 300, 15, os.path.join(out, "sheet"), prefix="SMOKE", name="片材", material="EPE")
    print("sheet ", len(r.files), f"{time.time()-t0:.1f}s")
    t0 = time.time()
    r = run_block(1000, 100, 100, 50, 70, 50, 40, os.path.join(out, "block"), prefix="SMOKE")
    print("block ", len(r.files), f"{time.time()-t0:.1f}s")
    t0 = time.time()
    r = run_grid((580, 380, 380), (65, 38, 85), 5.0, os.path.join(out, "grid_v1"),
                 prefix="SMOKE", slot_w=7.0, version=1)
    print("grid1 ", len(r.files), f"{time.time()-t0:.1f}s", r.rows[4])
    r = run_grid((580, 380, 380), (65, 38, 85), 5.0, os.path.join(out, "grid_v2"),
                 prefix="SMOKE", slot_w=7.0, version=2)
    print("grid2 ", len(r.files), r.rows[4])
    for bx, fl in (("0201", dict(body="BC")),
                   ("0310", dict(sleeve="ABC", cap_top="BC-HS", cap_bottom="BC")),
                   ("0312", dict(base="BC", lid="BC"))):
        t0 = time.time()
        r = run_box(bx, (400, 300, 200), os.path.join(out, bx), prefix="SMOKE", flutes=fl)
        print(bx, len(r.files), f"{time.time()-t0:.1f}s", r.rows[1][1] if len(r.rows) > 1 else "")
    # 即时计算接口（界面用）
    pl = box_plan("0310", (400, 300, 200), mode="outer",
                  flutes=dict(sleeve="ABC", cap_top="ABC", cap_bottom="BC-HS"))
    print("plan 0310 rows:", pl["rows"][1])
    print("plan 0310 dims:", box_dim_rows("0310", pl["p"]))
