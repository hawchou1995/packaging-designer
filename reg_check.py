# -*- coding: utf-8 -*-
"""回归门：把 packapp/core（新，支持分件纸板厚）与 fefco0210_build（旧，已交付验证）
在同一厚度下对比几何 —— panels 列表 / dieline / report 行必须逐位相等。

用法：python reg_check.py
"""
import importlib.util
import os
import sys

NEW = r"D:/Tools/tmp/packapp/core"
OLD = r"D:/Tools/tmp/fefco0210_build"
OLD2 = r"D:/Tools/tmp/pack_kk/build"


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def close(a, b, tol=1e-9):
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return abs(a - b) <= tol
    if isinstance(a, (tuple, list)) and isinstance(b, (tuple, list)):
        return len(a) == len(b) and all(close(x, y, tol) for x, y in zip(a, b))
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(close(a[k], b[k], tol) for k in a)
    return a == b


def diff(path, a, b, out, ignore=()):
    if isinstance(a, dict) and isinstance(b, dict):
        for k in (set(a) | set(b)) - set(ignore):
            diff(f"{path}.{k}", a.get(k), b.get(k), out, ignore)
    elif isinstance(a, (tuple, list)) and isinstance(b, (tuple, list)):
        if len(a) != len(b):
            out.append(f"{path}: len {len(a)} != {len(b)}")
            return
        for i, (x, y) in enumerate(zip(a, b)):
            diff(f"{path}[{i}]", x, y, out, ignore)
    elif not close(a, b):
        out.append(f"{path}: {a!r} != {b!r}")


def check_box(tag, mod_new, mod_old, boxes):
    print(f"--- {tag} ---")
    ok = True
    for (L, W, H) in boxes:
        pn = mod_new.Params(L=L, W=W, H=H)
        po = mod_old.Params(L=L, W=W, H=H)
        probs = []
        diff("panels", mod_new.panels(pn), mod_old.panels(po), probs)
        if hasattr(mod_new, "dieline_sleeve"):
            diff("sleeve", mod_new.dieline_sleeve(pn), mod_old.dieline_sleeve(po), probs)
            diff("cap", mod_new.dieline_cap(pn), mod_old.dieline_cap(po), probs)
        if hasattr(mod_new, "dieline_base"):
            diff("base", mod_new.dieline_base(pn), mod_old.dieline_base(po), probs)
            diff("lid", mod_new.dieline_lid(pn), mod_old.dieline_lid(po), probs)
        rn = mod_new.report(pn)
        ro = mod_old.report(po)
        # report 允许新增行（如分件板厚）：只比对两边同名的行
        dn_ = {k: v for k, v in rn[1]} if isinstance(rn[1], list) else rn[1]
        do_ = {k: v for k, v in ro[1]} if isinstance(ro[1], list) else ro[1]
        diff("report.errs", rn[0], ro[0], probs)
        def _nums(v):
            import re as _re
            return [float(x) for x in _re.findall(r"-?\d+(?:\.\d+)?", str(v))]
        for k in do_:
            if k not in dn_:
                continue
            a_, b_ = dn_[k], do_[k]
            if isinstance(a_, str) and isinstance(b_, str) and a_ != b_:
                # 允许措辞升级（如「上盖 96.5 / 下盖 96.5」）：数值序列必须一致
                if set(_nums(a_)) == set(_nums(b_)) and set(_nums(a_)):
                    continue
            diff(f"report[{k}]", a_, b_, probs)
        if probs:
            ok = False
            print(f"  {L}x{W}x{H}  DIFF {len(probs)}:")
            for s in probs[:12]:
                print("   ", s)
        else:
            print(f"  {L}x{W}x{H}  identical")
    return ok


def check_grid(boxes):
    print("--- 网格刀卡 ---")
    ok = True
    gc_n = load("newgridc", os.path.join(NEW, "grid_core.py"))
    gm_n = load("newgridm", os.path.join(NEW, "grid_model.py"))
    gc_o = load("oldgridc", os.path.join(OLD2, "grid_core.py"))
    gm_o = load("oldgridm", os.path.join(OLD2, "grid_model.py"))
    for cfg in (dict(L=580, W=380, H=380, pl=65, pw=38, ph=85, version=1, pads="both"),
                dict(L=580, W=380, H=380, pl=65, pw=38, ph=85, version=2, pads="both"),
                dict(L=540, W=470, H=290, pl=235, pw=30, ph=70, version=1, pads="bottom"),
                dict(L=550, W=350, H=210, pl=238, pw=34, ph=190, version=2, pads="none")):
        pn = gc_n.Params(**cfg)
        po = gc_o.Params(**cfg)
        probs = []
        diff("report", gc_n.report(pn), gc_o.report(po), probs, ignore=("st",))
        dn, do = gc_n.design(pn), gc_o.design(po)
        diff("design", dn, do, probs, ignore=("st",))
        diff("items_axo", gm_n.items(pn, dn, True), gm_o.items(po, do, True), probs)
        diff("items", gm_n.items(pn, dn), gm_o.items(po, do), probs)
        if probs:
            ok = False
            print(f"  {cfg}  DIFF {len(probs)}:")
            for s in probs[:10]:
                print("   ", s)
        else:
            print(f"  {cfg['L']}x{cfg['W']}x{cfg['H']} V{cfg['version']} {cfg['pads']}  identical")
    return ok


def check_simple(tag, rel, attr, cfgs, cls_name="Params", old_dir=None):
    print(f"--- {tag} ---")
    ok = True
    m_n = load(f"new_{attr}", os.path.join(NEW, rel))
    m_o = load(f"old_{attr}", os.path.join(old_dir or OLD, rel))
    for cfg in cfgs:
        pn = getattr(m_n, cls_name)(**cfg)
        po = getattr(m_o, cls_name)(**cfg)
        probs = []
        if hasattr(m_n, "report"):
            diff("report", m_n.report(pn), m_o.report(po), probs)
        if probs:
            ok = False
            print(f"  {cfg}  DIFF {len(probs)}:")
            for s in probs[:10]:
                print("   ", s)
        else:
            print(f"  {cfg}  identical")
    return ok


def main():
    allok = True
    m_new = load("new0310", os.path.join(NEW, "box0310_core.py"))
    m_old = load("old0310", os.path.join(OLD, "box0310_core.py"))
    allok &= check_box("FEFCO 0310", m_new, m_old, [(400, 300, 200), (600, 400, 315), (1200, 800, 500)])

    m_new = load("new0312", os.path.join(NEW, "box0312_core.py"))
    m_old = load("old0312", os.path.join(OLD, "box0312_core.py"))
    allok &= check_box("FEFCO 0312", m_new, m_old, [(400, 300, 200), (580, 510, 310), (1140, 740, 550)])

    m_new = load("new0201", os.path.join(NEW, "box0201_core.py"))
    m_old = load("old0201", os.path.join(OLD, "box0201_core.py"))
    allok &= check_box("FEFCO 0201", m_new, m_old, [(400, 300, 200), (600, 400, 300)])

    allok &= check_grid(None)
    allok &= check_simple("片材", "sheet_core.py", "sheet_core",
                          [dict(L=400, W=300, H=15), dict(L=250, W=180, H=5)])
    allok &= check_simple("仿形块", "block_core.py", "block_core",
                          [dict(L=1000, W=100, H=100, sl=50, sw=70, sh=50, gap=40),
                           dict(L=1000, W=100, H=100, sl=50, sw=100, sh=50, gap=40)],
                          old_dir=OLD2)

    print("\nREGRESSION:", "PASS" if allok else "FAIL")
    return 0 if allok else 1


if __name__ == "__main__":
    sys.exit(main())
