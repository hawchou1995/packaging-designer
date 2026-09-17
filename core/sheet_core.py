# -*- coding: utf-8 -*-
"""片材（矩形板材）参数化核心：长 L × 宽 W × 厚 H（mm）。

给 sheet_draw / sheet_make 共用：几何就是一块矩形板，
渲染/三视图/数模全部由这三个数派生，外加可选的名称与材质标注。
"""
from dataclasses import dataclass


@dataclass
class Params:
    L: float = 400.0
    W: float = 300.0
    H: float = 15.0
    name: str = "片材"
    material: str = ""          # 例如 EVA / EPE / 蜂窝纸板 / 中空板 / 胶合板

    @property
    def area(self):
        """单面面积 m²。"""
        return self.L * self.W / 1e6

    @property
    def volume(self):
        """体积（升）；1 L = 1e6 mm³。"""
        return self.L * self.W * self.H / 1e6

    @property
    def diag(self):
        """板面对角线 mm。"""
        return (self.L ** 2 + self.W ** 2) ** 0.5


def items(p: Params):
    """等轴测渲染器 item：单块矩形板，落在 z=0 平面上（与箱类管线同坐标约定）。"""
    return [dict(name=p.name, size=(p.L, p.W, p.H), center=(0.0, 0.0, p.H / 2.0))]


def report(p: Params):
    """(errs, rows)：参数合法性 + 输出行。"""
    errs = []
    if min(p.L, p.W, p.H) <= 0:
        errs.append("L/W/H 必须为正数")
    rows = [
        ("长 L", f"{p.L:g} mm"),
        ("宽 W", f"{p.W:g} mm"),
        ("厚 H", f"{p.H:g} mm"),
        ("单面面积", f"{p.area:.4f} m²"),
        ("体积", f"{p.volume:.5f} L"),
        ("对角线", f"{p.diag:.1f} mm"),
    ]
    return errs, rows


def param_lines_zh(p: Params):
    lines = [
        f"零件：{p.name}（矩形片材）",
        f"外形：长 {p.L:g} × 宽 {p.W:g} × 厚 {p.H:g} mm",
        f"单面面积 {p.area:.4f} m²；体积 {p.volume:.5f} L；对角线 {p.diag:.1f} mm",
    ]
    if p.material:
        lines.append(f"材质：{p.material}")
    lines.append("投影：第一角（GB）；三视图与轴测图、STEP/STL 同源")
    return lines
