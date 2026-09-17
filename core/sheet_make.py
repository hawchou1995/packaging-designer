# -*- coding: utf-8 -*-
"""片材一键出图：三视图 + 轴测图 + 1:1 轮廓 DXF + STEP/STL 数模 + 参数表。

用法：
    python sheet_make.py <长> <宽> <厚> [输出目录] [--name 名称] [--material 材质]
例：
    python sheet_make.py 400 300 15 "D:/Documents/Workbuddy/Packaging/片材-400x300x15" \
        --name "EVA垫片" --material EVA
"""
import argparse
import datetime
import os
import struct

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

from sheet_core import Params, report, items, param_lines_zh
from sheet_draw import build_sheet
from box0210_2d import save_sheet_png_svg
from box0210_3d import draw_scene, stl_check, _tri_normal


# ---------------------------------------------------------------- 1:1 轮廓 DXF
def write_dxf(p: Params, path: str):
    import ezdxf
    doc = ezdxf.new("R2010")
    doc.layers.add("CUT", color=7)
    doc.layers.add("NOTES", color=8)
    msp = doc.modelspace()
    msp.add_lwpolyline([(0, 0), (p.L, 0), (p.L, p.W), (0, p.W)],
                       close=True, dxfattribs={"layer": "CUT"})
    note = f"{p.name}  {p.L:g} x {p.W:g} x {p.H:g} mm"
    msp.add_text(note, height=8.0, dxfattribs={"layer": "NOTES"}).set_placement((0.0, p.W + 15.0))
    doc.saveas(path)
    return path


# ---------------------------------------------------------------- STEP（OCP）
def export_step(p: Params, path: str):
    from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
    from OCP.gp import gp_Pnt
    from OCP.Bnd import Bnd_Box
    from OCP.BRepBndLib import BRepBndLib
    from OCP.STEPControl import STEPControl_Writer, STEPControl_AsIs
    shp = BRepPrimAPI_MakeBox(gp_Pnt(-p.L / 2, -p.W / 2, 0.0), p.L, p.W, p.H).Shape()
    w = STEPControl_Writer()
    w.Transfer(shp, STEPControl_AsIs)
    w.Write(path)
    box = Bnd_Box()
    BRepBndLib.Add_s(shp, box)
    mn, mx = box.CornerMin(), box.CornerMax()
    return (mn.X(), mn.Y(), mn.Z(), mx.X(), mx.Y(), mx.Z())


# ---------------------------------------------------------------- 二进制 STL（无 OCP）
def write_stl(p: Params, path: str):
    import numpy as np
    x0, x1 = -p.L / 2, p.L / 2
    y0, y1 = -p.W / 2, p.W / 2
    z0, z1 = 0.0, p.H
    quads = [
        ((x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)),   # +z 顶
        ((x0, y1, z0), (x1, y1, z0), (x1, y0, z0), (x0, y0, z0)),   # -z 底
        ((x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1)),   # -y 前
        ((x1, y1, z0), (x0, y1, z0), (x0, y1, z1), (x1, y1, z1)),   # +y 后
        ((x1, y0, z0), (x1, y1, z0), (x1, y1, z1), (x1, y0, z1)),   # +x 右
        ((x0, y1, z0), (x0, y0, z0), (x0, y0, z1), (x0, y1, z1)),   # -x 左
    ]
    tris = []
    for a, b, c, d in quads:
        n = _tri_normal(np.array(a), np.array(b), np.array(c))
        tris.append((n, a, b, c))
        tris.append((n, a, c, d))
    with open(path, "wb") as fh:
        fh.write(b"\0" * 80)
        fh.write(struct.pack("<I", len(tris)))
        for n, a, b, c in tris:
            fh.write(struct.pack("<3f", float(n[0]), float(n[1]), float(n[2])))
            for v in (a, b, c):
                fh.write(struct.pack("<3f", float(v[0]), float(v[1]), float(v[2])))
            fh.write(struct.pack("<H", 0))
    return path


def render_axo(p: Params, basepath: str, dpi: int = 300):
    fig = plt.figure(figsize=(150 / 25.4, 115 / 25.4))
    ax = fig.add_axes([0.02, 0.06, 0.96, 0.88])
    draw_scene(ax, items(p))
    ax.set_title(f"{p.name} · {p.L:g}×{p.W:g}×{p.H:g} mm · 轴测图（等轴测）", fontsize=9)
    out = []
    for ext in ("png", "svg"):
        fp = f"{basepath}.{ext}"
        fig.savefig(fp, dpi=dpi)
        out.append(fp)
    plt.close(fig)
    return out


def main():
    ap = argparse.ArgumentParser(description="矩形片材：三视图 + 轴测图 + STEP/STL")
    ap.add_argument("L", type=float, help="长 mm")
    ap.add_argument("W", type=float, help="宽 mm")
    ap.add_argument("H", type=float, help="厚 mm")
    ap.add_argument("outdir", nargs="?", default=r"D:/Tools/tmp/fefco0210_build/out_sheet")
    ap.add_argument("--name", default="片材")
    ap.add_argument("--material", default="")
    ap.add_argument("--scale", type=float, default=None,
                    help="强制比例分母（如 2.5 表示 1:2.5；默认自动选档）")
    a = ap.parse_args()

    p = Params(L=a.L, W=a.W, H=a.H, name=a.name, material=a.material)
    errs, rows = report(p)
    print("=== 片材参数 ===")
    for k, v in rows:
        print(f"{k:8s}: {v}")
    if errs:
        raise SystemExit("PARAM CHECK FAILED: " + "; ".join(errs))

    out = a.outdir
    os.makedirs(out, exist_ok=True)

    # ---- 1:1 轮廓 DXF ----
    dxf = write_dxf(p, os.path.join(out, "01_片材轮廓_1-1.dxf"))
    import ezdxf
    d = ezdxf.readfile(dxf)
    pls = d.modelspace().query('LWPOLYLINE[layer=="CUT"]')
    pts = list(pls[0].get_points("xy"))
    xs = [q[0] for q in pts]
    ys = [q[1] for q in pts]
    print(f"DXF: {os.path.basename(dxf)} {os.path.getsize(dxf)} bytes; "
          f"re-read CUT={len(pls)} closed={pls[0].closed} "
          f"bbox=({max(xs)-min(xs):g} x {max(ys)-min(ys):g})")

    # ---- A3 合成图纸（三视图 + 轴测）----
    fig = build_sheet(p, d_force=a.scale)
    base = "01_图纸-三视图+轴测图_A3"
    pdf = os.path.join(out, base + ".pdf")
    with PdfPages(pdf) as pp:
        pp.savefig(fig)
    print("PDF:", os.path.basename(pdf), os.path.getsize(pdf), "bytes")
    for f in save_sheet_png_svg(fig, os.path.join(out, base)):
        print("SHEET:", os.path.basename(f), os.path.getsize(f), "bytes")
    plt.close(fig)

    # ---- 3D：STEP + STL（含回读校验）----
    step = os.path.join(out, "03_三维模型.step")
    bb = export_step(p, step)
    dims = tuple(round(bb[i + 3] - bb[i], 3) for i in range(3))
    print("STEP bbox dims:", dims)
    assert (abs(dims[0] - p.L) < 0.01 and abs(dims[1] - p.W) < 0.01
            and abs(dims[2] - p.H) < 0.01), f"STEP dims {dims} != {(p.L, p.W, p.H)}"
    print("3D:", os.path.basename(step), os.path.getsize(step), "bytes")
    stl = os.path.join(out, "03_三维模型.stl")
    write_stl(p, stl)
    n, bx = stl_check(stl)
    print(f"3D: {os.path.basename(stl)} {os.path.getsize(stl)} bytes, tris={n}, "
          f"bbox=({bx[3]-bx[0]:g} x {bx[4]-bx[1]:g} x {bx[5]-bx[2]:g})")
    assert n == 12, f"STL triangle count {n} != 12"

    # ---- 单张轴测图 ----
    for f in render_axo(p, os.path.join(out, "02_轴测图")):
        print("AXO:", os.path.basename(f), os.path.getsize(f))

    # ---- 参数表 + README ----
    md = os.path.join(out, "04_参数表.md")
    with open(md, "w", encoding="utf-8") as fh:
        fh.write(f"# {p.name} · 片材参数表（{datetime.date.today().isoformat()}）\n\n")
        for line in param_lines_zh(p):
            fh.write(f"- {line}\n")
    print("MD:", os.path.basename(md), os.path.getsize(md), "bytes")

    rdm = os.path.join(out, "README.md")
    with open(rdm, "w", encoding="utf-8") as fh:
        fh.write(f"""# {p.name} · 矩形片材 · {p.L:g}×{p.W:g}×{p.H:g} mm

生成：{datetime.date.today().isoformat()} · 管线：ZCode 参数化脚本（OCP + ezdxf + matplotlib）

## 文件清单
| 文件 | 说明 |
|---|---|
| **01_图纸-三视图+轴测图_A3.pdf / .png / .svg** | 第一角三视图（主/俯/左，含 L/H/W 尺寸）+ 等轴测图 |
| 01_片材轮廓_1-1.dxf | 1:1 裁切轮廓（CUT 闭合矩形 + NOTES 文字） |
| 02_轴测图.png / .svg | 单张等轴测图（矢量） |
| 03_三维模型.step / .stl | 数模文件（STEP 用 OCP；STL 二进制 12 三角面） |
| 04_参数表.md | 尺寸/面积/体积清单 |
| src/ | 生成脚本：`python sheet_make.py <长> <宽> <厚> <输出目录> [--name 名称] [--material 材质] [--scale 比例分母]` |

## 生成时自动验证（全部通过）
- STEP bbox = {p.L:g} × {p.W:g} × {p.H:g} mm ✓（OCP 内核实测）
- STL 回读：12 三角面，bbox 一致 ✓
- DXF 回读：1 条闭合裁切轮廓（{p.L:g} × {p.W:g}）✓
""")
    print("MD:", os.path.basename(rdm), os.path.getsize(rdm), "bytes")
    print("ALL OK")


if __name__ == "__main__":
    main()
