# -*- coding: utf-8 -*-
"""pages.py — 四个模块页（片材 / 仿形垫块 / 网格刀卡 / 瓦楞纸箱）· v1.0.1

版式：参数表格化（标签左、控件右、每行 2 个）· 选择项分段按钮（无下拉）· 楞型紧凑按钮组；
流程：**先生成**（出图到临时目录 + 预览）**再导出**（按「前缀_属性后缀」写到你选的目录）；
比例：默认「自动」（按图幅可用区选最大可容纳档），可切「手动 1:x」。
"""
import os
import shutil
import tempfile
import traceback

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (QFileDialog, QGridLayout, QHBoxLayout, QLabel, QLineEdit,
                               QPushButton, QScrollArea, QSplitter, QVBoxLayout, QWidget)

import backend
import price_lib
from widgets import (BusyBar, Card, FileList, GroupTable, PreviewPane, RowGrid, ScaleField,
                     check_field, flute_field, num_field, open_path, seg_field, text_field)

TMP_ROOT = os.path.join(tempfile.gettempdir(), "PackagingDesigner")


class GenWorker(QThread):
    done = Signal(object)
    fail = Signal(str)

    def __init__(self, fn, parent=None):
        super().__init__(parent)
        self.fn = fn

    def run(self):
        try:
            self.done.emit(self.fn())
        except (Exception, SystemExit) as e:
            self.fail.emit(str(e) or e.__class__.__name__)


def flute_options():
    from flute_lib import FLUTES
    return [(c, f["t"]) for c, f in FLUTES.items()]


class BasePage(QWidget):
    title = ""
    subtitle = ""
    preview_name = None
    temp_key = "page"

    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        self._worker = None
        self._gen_files = []
        self._gen_prefix = ""
        self._gen_sig = None
        self._outdir = settings.outdir

        root = QVBoxLayout(self)
        root.setContentsMargins(14, 12, 14, 10)
        root.setSpacing(8)

        head = QVBoxLayout()
        head.setSpacing(1)
        t = QLabel(self.title)
        t.setObjectName("PageTitle")
        s = QLabel(self.subtitle)
        s.setObjectName("PageSub")
        s.setWordWrap(True)
        head.addWidget(t)
        head.addWidget(s)
        root.addLayout(head)

        split = QSplitter(Qt.Horizontal)
        split.setChildrenCollapsible(False)
        left = QScrollArea()
        left.setWidgetResizable(True)
        lw = QWidget()
        self.form = QVBoxLayout(lw)
        self.form.setContentsMargins(0, 0, 8, 0)
        self.form.setSpacing(8)
        left.setWidget(lw)
        left.setMinimumWidth(560)
        right = QWidget()
        rv = QVBoxLayout(right)
        rv.setContentsMargins(0, 0, 0, 0)
        rv.setSpacing(8)
        self.res_card = Card("计算摘要")
        self.table = GroupTable()
        self.res_card.add(self.table)
        rv.addWidget(self.res_card, 3)
        self.prev_card = Card("图纸预览")
        self.preview = PreviewPane()
        self.prev_card.add(self.preview)
        rv.addWidget(self.prev_card, 2)
        split.addWidget(left)
        split.addWidget(right)
        split.setStretchFactor(0, 5)
        split.setStretchFactor(1, 6)
        split.setSizes([620, 560])
        root.addWidget(split, 1)

        exp = Card("生成 / 导出")
        g = QGridLayout()
        g.setHorizontalSpacing(8)
        g.setVerticalSpacing(5)
        self.out_edit = QLineEdit(settings.outdir)
        browse = QPushButton("浏览…")
        browse.setFixedWidth(64)
        browse.clicked.connect(self.on_browse)
        self.prefix_edit = QLineEdit(settings.prefix)
        self.prefix_edit.setPlaceholderText("例：XG盖板")
        self.prefix_edit.setFixedWidth(170)
        g.addWidget(self._lab("输出目录"), 0, 0)
        g.addWidget(self.out_edit, 0, 1)
        g.addWidget(browse, 0, 2)
        g.addWidget(self._lab("文件名前缀"), 0, 3)
        g.addWidget(self.prefix_edit, 0, 4)
        self.btn_gen = QPushButton("① 生成")
        self.btn_gen.setObjectName("Primary")
        self.btn_gen.setFixedWidth(120)
        self.btn_gen.clicked.connect(self.on_generate)
        self.btn_exp = QPushButton("② 导出")
        self.btn_exp.setFixedWidth(120)
        self.btn_exp.clicked.connect(self.on_export)
        self.btn_exp.setEnabled(False)
        g.addWidget(self.btn_gen, 1, 0)
        g.addWidget(self.btn_exp, 1, 1)
        self.busy = BusyBar()
        g.addWidget(self.busy, 1, 2, 1, 3)
        self.file_list = FileList()
        self.file_list.setFixedHeight(66)
        g.addWidget(self.file_list, 2, 0, 1, 4)
        b1 = QPushButton("打开图纸")
        b1.clicked.connect(self.on_open_main)
        b2 = QPushButton("打开目录")
        b2.clicked.connect(lambda: open_path(self._outdir))
        side = QVBoxLayout()
        side.setSpacing(4)
        side.addWidget(b1)
        side.addWidget(b2)
        g.addLayout(side, 2, 4)
        g.setColumnStretch(1, 1)
        g.setColumnStretch(2, 0)
        exp.body().addLayout(g)
        root.addWidget(exp, 0)

        self.build_form()
        self.refresh()
        self._sync_export_hint()

    # ---------------- 基础 ----------------
    @staticmethod
    def _lab(text):
        lab = QLabel(text)
        lab.setObjectName("FieldLabel")
        return lab

    def card(self, title):
        c = Card(title)
        self.form.addWidget(c)
        return c

    def scale_field(self, on_change=None):
        self.f_scale = ScaleField(on_change=on_change or self._touched)
        return self.f_scale

    def _touched(self, *_):
        self.refresh()
        self._sync_export_hint()

    def build_form(self):
        raise NotImplementedError

    def refresh(self):
        raise NotImplementedError

    def sig(self):
        raise NotImplementedError

    def generate(self, outdir, prefix):
        raise NotImplementedError

    # ---------------- 导出流程 ----------------
    def _tmpdir(self):
        d = os.path.join(TMP_ROOT, self.temp_key)
        shutil.rmtree(d, ignore_errors=True)
        os.makedirs(d, exist_ok=True)
        return d

    def on_browse(self):
        d = QFileDialog.getExistingDirectory(self, "选择输出目录",
                                             self.out_edit.text() or os.path.expanduser("~"))
        if d:
            self.out_edit.setText(d)

    def on_open_main(self):
        files = self._gen_files
        if not files:
            self.busy.info("尚未生成文件")
            return
        pick = None
        for f in files:
            if f.endswith(".pdf") and (self.preview_name is None or self.preview_name in f):
                pick = f
                break
        if pick is None:
            pick = next((f for f in files if f.endswith(".pdf")), None) or files[0]
        if not open_path(pick):
            self.busy.err("文件不存在（可能已被移动）")

    def on_generate(self):
        if self._worker is not None and self._worker.isRunning():
            return
        self.btn_gen.setEnabled(False)
        self.btn_exp.setEnabled(False)
        self.busy.busy("正在生成图纸与模型…（含三维建模，约数秒）")
        tmp = self._tmpdir()
        sig = self.sig()
        prefix = "gen"
        self._worker = GenWorker(lambda: self.generate(tmp, prefix), self)
        self._worker.done.connect(lambda r, s=sig, p=prefix: self._on_generated(r, s, p))
        self._worker.fail.connect(self.on_fail)
        self._worker.start()

    def _on_generated(self, result, sig, prefix):
        self.btn_gen.setEnabled(True)
        self._gen_files = list(result.files)
        self._gen_prefix = prefix
        self._gen_sig = sig
        self.file_list.set_files(self._gen_files)
        self.busy.ok(f"已生成 {len(self._gen_files)} 个文件（临时目录）；点「② 导出」写入目标目录")
        if getattr(result, "rows", None):
            self._render_rows(result.rows)
        png = None
        for f in self._gen_files:
            if f.endswith(".png") and (self.preview_name is None or self.preview_name in f):
                png = f
                break
        if png is None:
            png = next((f for f in self._gen_files if f.endswith(".png")), None)
        self.preview.show_image(png)
        self._sync_export_hint()

    def _sync_export_hint(self):
        if self._gen_sig is None:
            self.btn_exp.setEnabled(False)
            return
        if self._gen_sig != self.sig():
            self.btn_exp.setEnabled(False)
            self.busy.info("参数已修改：请重新「① 生成」后再导出")
        else:
            self.btn_exp.setEnabled(True)

    def on_export(self):
        if not self._gen_files:
            self.busy.err("请先「① 生成」")
            return
        outdir = self.out_edit.text().strip()
        if not outdir:
            self.busy.err("请先选择输出目录")
            return
        try:
            os.makedirs(outdir, exist_ok=True)
        except OSError as e:
            self.busy.err(f"目录不可用：{e}")
            return
        prefix = self.prefix_edit.text().strip()
        pre = (prefix + "_") if prefix else ""
        gpre = self._gen_prefix or ""
        done, errs = [], []
        for f in self._gen_files:
            base = os.path.basename(f)
            # 生成期前缀归一：gen-V1_xxx → 用户前缀-V1_xxx；gen_xxx → 用户前缀_xxx
            if gpre and base.startswith(gpre + "-"):
                tail = base[len(gpre) + 1:]
                ver, _, rest = tail.partition("_")
                base = f"{prefix}-{ver}_{rest}" if prefix else f"{ver}_{rest}"
            elif gpre and base.startswith(gpre + "_"):
                base = pre + base[len(gpre) + 1:]
            else:
                base = pre + base
            dst = os.path.join(outdir, base)
            try:
                shutil.copy2(f, dst)
                done.append(dst)
            except OSError as e:
                errs.append(f"{base}: {e}")
        self._outdir = outdir
        self.file_list.set_files(done)
        if errs:
            self.busy.err(f"导出 {len(done)} 个，失败 {len(errs)} 个：{errs[0]}")
        else:
            self.busy.ok(f"已导出 {len(done)} 个文件到 {outdir}")
        if self.settings.open_after:
            open_path(outdir)

    def on_fail(self, msg):
        self.btn_gen.setEnabled(True)
        self.btn_exp.setEnabled(False)
        self.busy.err(f"生成失败：{msg}")
        traceback.print_exc()

    def frame(self):
        return self.settings.frame()

    def _render_rows(self, rows):
        self.table.set_rows(rows)


# ================================================================ 片材
class SheetPage(BasePage):
    title = "片材"
    subtitle = "输入长 / 宽 / 厚 → 第一角三视图 + 等轴测图 + 1:1 DXF 轮廓 + STEP/STL 数模 + 参数表（A3 图框）。"
    preview_name = "图纸-三视图+轴测图_A3"
    temp_key = "sheet"

    def build_form(self):
        c = self.card("尺寸")
        g = RowGrid(2)
        self.f_name = text_field("名称", "片材", on_change=self._touched)
        self.f_mat = text_field("材料", "", placeholder="EPE / EVA / 蜂窝纸板", on_change=self._touched)
        g.add(self.f_name)
        g.add(self.f_mat)
        self.f_L = num_field("长 L（mm）", 400.0, 1, 20000, 10, 1, on_change=self._touched)
        self.f_W = num_field("宽 W（mm）", 300.0, 1, 20000, 10, 1, on_change=self._touched)
        self.f_H = num_field("厚 T（mm）", 15.0, 0.5, 500, 1, 1, on_change=self._touched)
        g.add(self.f_L)
        g.add(self.f_W)
        g.add(self.f_H)
        c.add(g)
        c2 = self.card("图纸比例")
        g2 = RowGrid(1)
        g2.add(self.scale_field())
        c2.add(g2)
        hint = QLabel("自动 = 按图幅可用区选最大可容纳档（含放大档 2:1 / 5:1）；手动填的数画不下时只提示不阻断。")
        hint.setObjectName("FieldHint")
        hint.setWordWrap(True)
        c2.add(hint)
        self.form.addStretch(1)

    def _p(self):
        from sheet_core import Params
        return Params(L=self.f_L.widget.value(), W=self.f_W.widget.value(),
                      H=self.f_H.widget.value(), name=self.f_name.widget.text() or "片材",
                      material=self.f_mat.widget.text())

    def refresh(self):
        try:
            from sheet_core import report
            p = self._p()
            errs, rows = report(p)
            self.table.set_groups([("尺寸与用量", rows)])
            self.btn_gen.setEnabled(not errs)
            self.busy.info("；".join(errs) if errs else "参数就绪")
        except (Exception, SystemExit) as e:
            self.table.set_rows([("参数错误", str(e))])
            self.btn_gen.setEnabled(False)

    def sig(self):
        p = self._p()
        return (p.L, p.W, p.H, p.name, p.material, self.f_scale.value())

    def generate(self, outdir, prefix):
        p = self._p()
        return backend.run_sheet(p.L, p.W, p.H, outdir, prefix=prefix, name=p.name,
                                 material=p.material, frame=self.frame(),
                                 scale=self.f_scale.value())


# ================================================================ 仿形垫块
class BlockPage(BasePage):
    title = "仿形垫块"
    subtitle = "垫块外形 + 槽 + 间距；边距可均分或指定一侧（另一侧自动）→ 三视图 + 轴测图 + DXF + STEP/STL + 参数表。"
    preview_name = "图纸-三视图+轴测图_A3"
    temp_key = "block"

    def build_form(self):
        c = self.card("垫块与开槽")
        g = RowGrid(2)
        self.f_L = num_field("垫块长 L（mm）", 1000.0, 10, 20000, 10, 1, on_change=self._touched)
        self.f_W = num_field("垫块宽 W（mm）", 100.0, 5, 5000, 5, 1, on_change=self._touched)
        self.f_H = num_field("垫块高 H（mm）", 100.0, 5, 2000, 5, 1, on_change=self._touched)
        self.f_gap = num_field("槽间距（mm）", 40.0, 0, 2000, 5, 1, on_change=self._touched)
        self.f_sl = num_field("槽长（mm）", 50.0, 1, 20000, 5, 1, on_change=self._touched)
        self.f_sw = num_field("槽宽（mm）", 70.0, 1, 5000, 5, 1, on_change=self._touched)
        self.f_sh = num_field("槽深（mm）", 50.0, 1, 2000, 5, 1, on_change=self._touched)
        for r in (self.f_L, self.f_W, self.f_H, self.f_gap, self.f_sl, self.f_sw, self.f_sh):
            g.add(r)
        c.add(g)

        c2 = self.card("边距与开口")
        g2 = RowGrid(2)
        self.f_mm = seg_field("边距方式", [("even", "两端均分"), ("left", "指定左侧")],
                              "even", on_change=self._touched)
        self.f_ml = num_field("左端边距（mm）", 20.0, 0, 5000, 5, 1, on_change=self._touched,
                              hint="仅「指定左侧」时生效")
        self.f_side = seg_field("单边贯穿开口", [("front", "前侧"), ("back", "后侧")],
                                "front", on_change=self._touched)
        g2.add(self.f_mm)
        g2.add(self.f_ml)
        g2.add(self.f_side)
        c2.add(g2)
        c3 = self.card("标识")
        g3 = RowGrid(2)
        self.f_name = text_field("名称", "仿形块", on_change=self._touched)
        self.f_mat = text_field("材料", "", placeholder="EPE / EVA", on_change=self._touched)
        g3.add(self.f_name)
        g3.add(self.f_mat)
        c3.add(g3)
        c4 = self.card("图纸比例")
        g4 = RowGrid(1)
        g4.add(self.scale_field())
        c4.add(g4)
        self.form.addStretch(1)

    def _p(self):
        from block_core import Params
        mode = self.f_mm.seg.value()
        return Params(L=self.f_L.widget.value(), W=self.f_W.widget.value(),
                      H=self.f_H.widget.value(), sl=self.f_sl.widget.value(),
                      sw=self.f_sw.widget.value(), sh=self.f_sh.widget.value(),
                      gap=self.f_gap.widget.value(),
                      margin_left=(self.f_ml.widget.value() if mode == "left" else None),
                      open_side=self.f_side.seg.value(),
                      name=self.f_name.widget.text() or "仿形块",
                      material=self.f_mat.widget.text())

    def _touched(self, *_):
        self.f_ml.widget.setEnabled(self.f_mm.seg.value() == "left")
        super()._touched()

    def refresh(self):
        try:
            from block_core import report
            p = self._p()
            errs, rows, d = report(p)
            self.table.set_groups([("开槽与边距", rows)])
            self.btn_gen.setEnabled(not errs)
            self.busy.info("；".join(errs) if errs else "参数就绪")
        except (Exception, SystemExit) as e:
            self.table.set_rows([("参数错误", str(e))])
            self.btn_gen.setEnabled(False)

    def sig(self):
        p = self._p()
        return (p.L, p.W, p.H, p.sl, p.sw, p.sh, p.gap, p.margin_left, p.open_side,
                p.name, p.material, self.f_scale.value())

    def generate(self, outdir, prefix):
        p = self._p()
        return backend.run_block(p.L, p.W, p.H, p.sl, p.sw, p.sh, p.gap, outdir,
                                 prefix=prefix, margin_left=p.margin_left,
                                 open_side=p.open_side, name=p.name, material=p.material,
                                 frame=self.frame(), scale=self.f_scale.value())


# ================================================================ 网格刀卡
class GridPage(BasePage):
    title = "网格刀卡"
    subtitle = ("内衬外尺寸（= 容器内尺寸）+ 每格尺寸 + 纸板 → 自动对比 V1 长对长 / V2 长对宽"
                "（格数·层数·收容数·刀卡片数）→ 图纸 + 1:1 DXF + STEP/STL + 参数表 + 报价。")
    preview_name = "图纸-网格俯视+刀卡侧视+轴测图_A3"
    temp_key = "grid"

    def build_form(self):
        c = self.card("容器与格子")
        g = RowGrid(2)
        self.f_L = num_field("内衬外长（mm）", 580.0, 20, 20000, 10, 1, on_change=self._touched)
        self.f_W = num_field("内衬外宽（mm）", 380.0, 20, 20000, 10, 1, on_change=self._touched)
        self.f_H = num_field("内衬高（mm）", 380.0, 20, 20000, 10, 1, on_change=self._touched)
        self.f_pl = num_field("每格长（mm）", 65.0, 1, 5000, 1, 1, on_change=self._touched)
        self.f_pw = num_field("每格宽（mm）", 38.0, 1, 5000, 1, 1, on_change=self._touched)
        self.f_ph = num_field("每格高（mm）", 85.0, 1, 5000, 5, 1, on_change=self._touched)
        for r in (self.f_L, self.f_W, self.f_H):
            g.add(r)
        g.next_row()
        for r in (self.f_pl, self.f_pw, self.f_ph):
            g.add(r)
        c.add(g)

        c2 = self.card("纸板与隔板")
        g2 = RowGrid(2)
        self.f_t = num_field("刀卡厚（mm）", 5.0, 1, 20, 0.5, 1, on_change=self._touched)
        self.f_slot = num_field("开槽宽（mm）", 7.0, 1, 30, 0.5, 1, on_change=self._touched)
        self.f_sep = num_field("隔板厚（mm）", 5.0, 1, 30, 0.5, 1, on_change=self._touched)
        self.f_pads = seg_field("顶/底隔板", [("both", "底+顶"), ("bottom", "仅底"),
                                             ("top", "仅顶"), ("none", "无")], "both",
                                on_change=self._touched)
        g2.add(self.f_t)
        g2.add(self.f_slot)
        g2.add(self.f_sep)
        g2.add(self.f_pads)
        c2.add(g2)

        c3 = self.card("做法与报价")
        g3 = RowGrid(2)
        self.f_ver = seg_field("导出方案", [("1", "V1 长对长"), ("2", "V2 长对宽"), ("12", "两个都要")],
                               "12", on_change=self._touched, label_w=84)
        self.f_mat = flute_field("纸板材料", flute_options(), "BC", on_change=self._touched)
        self.f_allow = num_field("边料余量 A（mm）", 15.0, 0, 100, 1, 1, on_change=self._touched,
                                 hint="飞书口径：面积 =(长+A)(宽+A)×张数")
        self.f_labor = num_field("人工费/套（元）", 0.29, 0, 9999, 0.1, 2,
                                 on_change=self._touched)
        self.f_qty = num_field("套数（套）", 1.0, 1, 100000, 1, 0, on_change=self._touched)
        g3.add(self.f_ver, span=True)
        g3.add(self.f_mat, span=True)
        for r in (self.f_allow, self.f_labor, self.f_qty):
            g3.add(r)
        c3.add(g3)

        c4 = self.card("图纸比例")
        g4 = RowGrid(1)
        g4.add(self.scale_field())
        c4.add(g4)
        self.form.addStretch(1)

    def _args(self):
        return dict(container=(self.f_L.widget.value(), self.f_W.widget.value(), self.f_H.widget.value()),
                    cell=(self.f_pl.widget.value(), self.f_pw.widget.value(), self.f_ph.widget.value()),
                    t=self.f_t.widget.value(), slot_w=self.f_slot.widget.value(),
                    sep_t=self.f_sep.widget.value(), pads=self.f_pads.seg.value())

    def _price(self):
        return dict(code=self.f_mat.flute.value(), allow=self.f_allow.widget.value(),
                    labor=self.f_labor.widget.value(), qty=self.f_qty.widget.value())

    def refresh(self):
        a = self._args()
        t = a["t"]
        ok_slot = a["slot_w"] >= t - 1e-9
        plans = {}
        for v in (1, 2):
            try:
                p, rows, d = backend.grid_plan(**a, version=v, price=self._price())
                plans[v] = (p, rows, d, None)
            except (Exception, SystemExit) as e:
                plans[v] = (None, None, None, str(e))
        groups = []
        if plans[1][1]:
            groups.append(("V1 长对长 · 明细", plans[1][1]))
        cmp_rows = []
        for v in (1, 2):
            _p, _rows, d, err = plans[v]
            tag = "V1 长对长" if v == 1 else "V2 长对宽"
            if d is None:
                cmp_rows.append((tag, err))
                continue
            cmp_rows += [(f"{tag} · 格数 长×短", f"{d['n_l']} × {d['n_w']}"),
                         (f"{tag} · 层数 / 收容数", f"{d['layers']} / {d['capacity']}"),
                         (f"{tag} · 长刀卡/层", f"{d['cards_long']} 张（总 {d['cards_long_total']}）"),
                         (f"{tag} · 短刀卡/层", f"{d['cards_short']} 张（总 {d['cards_short_total']}）"),
                         (f"{tag} · 边距 长/短", f"{d['margin_l']:g} / {d['margin_w']:g}"),
                         (f"{tag} · 堆叠 ≤ 内高", f"{d['H_stack']:g} ≤ {a['container'][2]:g}")]
            if d.get("price"):
                cmp_rows.append((f"{tag} · 每套", f"¥ {d['price']['per_set']:.2f}"))
        groups.append(("方案对比", cmp_rows))
        errs = [plans[1][3], plans[2][3]]
        groups.append(("校验", [("开槽宽 ≥ 刀卡厚",
                                 f"{a['slot_w']:g} ≥ {t:g} {'✓' if ok_slot else '✗ 会干涉'}")] +
                                ([("错误", e) for e in errs if e] or [("状态", "OK")])))
        self.table.set_groups(groups)
        self.btn_gen.setEnabled(ok_slot)
        self.busy.info("；".join(x for x in errs if x) if any(errs) else
                       ("参数就绪" if ok_slot else "开槽宽不足"))

    def sig(self):
        a = self._args()
        return (a["container"], a["cell"], a["t"], a["slot_w"], a["sep_t"], a["pads"],
                self.f_ver.seg.value(), self._price(), self.f_scale.value())

    def generate(self, outdir, prefix):
        a = self._args()
        ver = self.f_ver.seg.value()
        vers = [1, 2] if ver == "12" else [int(ver)]
        files, rows = [], []
        for v in vers:
            pre = f"{prefix}-V{v}" if len(vers) > 1 else prefix
            r = backend.run_grid(a["container"], a["cell"], a["t"], outdir, prefix=pre,
                                 slot_w=a["slot_w"], sep_t=a["sep_t"], pads=a["pads"],
                                 version=v, frame=self.frame(), scale=self.f_scale.value(),
                                 price=self._price())
            files += r.files
            rows = r.rows
        if not files:
            raise ValueError("未选择任何导出方案")
        return backend.Result(files, rows)


# ================================================================ 瓦楞纸箱
BOX_META = {
    "0201": dict(label="0201 开槽箱（RSC）", parts=[("body", "纸板楞型")]),
    "0310": dict(label="0310 围框+两盖", parts=[("sleeve", "围框楞型"), ("cap_top", "上盖楞型"),
                                              ("cap_bottom", "下盖楞型")]),
    "0312": dict(label="0312 底箱+天盖", parts=[("base", "底箱楞型"), ("lid", "天盖楞型")]),
}
PARAM_DEFS = [("glue_w", "接舌宽"), ("flap_gain", "外摇盖加放"), ("flap_reduce", "内摇盖折减"),
              ("slot_w", "开槽宽"), ("gap", "盖/围框间隙"), ("cover_depth", "天盖罩深")]


class BoxPage(BasePage):
    title = "瓦楞纸箱"
    subtitle = ("选箱型与楞型 → 填外尺寸或内尺寸；自动给内 / 制造 / 外三口径 + 展开尺寸 + 面积数量 + "
                "报价（飞书口径，单价来自隔板表），工艺参数限标准区间。")
    preview_name = "图纸-展开图+轴测图_A3"
    temp_key = "box"

    def build_form(self):
        c = self.card("箱型与尺寸")
        g = RowGrid(2)
        self.f_box = seg_field("箱型", [(k, v["label"]) for k, v in BOX_META.items()],
                               "0201", on_change=self.on_box_changed)
        self.f_mode = seg_field("尺寸口径", [("outer", "外尺寸"), ("inner", "内尺寸")],
                                "outer", on_change=self._touched)
        self.f_L = num_field("长 L（mm）", 400.0, 10, 20000, 10, 1, on_change=self._touched)
        self.f_W = num_field("宽 W（mm）", 300.0, 10, 20000, 10, 1, on_change=self._touched)
        self.f_H = num_field("高 H（mm）", 200.0, 10, 20000, 10, 1, on_change=self._touched)
        g.add(self.f_box, span=True)
        g.add(self.f_mode, span=True)
        g.add(self.f_L)
        g.add(self.f_W)
        g.add(self.f_H)
        g.next_row()
        c.add(g)

        c2 = self.card("楞型 / 材料（单选按钮；单价来自飞书「隔板」表）")
        g2 = RowGrid(1)
        self.flute_rows = {}
        all_parts = []
        for bx in BOX_META.values():
            for key, label in bx["parts"]:
                if key not in [k for k, _ in all_parts]:
                    all_parts.append((key, label))
        for key, label in all_parts:
            r = flute_field(label, flute_options(), "BC", on_change=self.on_flute_changed)
            self.flute_rows[key] = r
            g2.add(r)
        c2.add(g2)
        self.f_link = check_field("上下盖同款同楞", True, on_change=self.on_flute_changed)
        c2.add(self.f_link)

        c3 = self.card("工艺参数（标准区间内可改）")
        g3 = RowGrid(2)
        self.p_rows = {}
        for key, label in PARAM_DEFS:
            r = num_field(label, 45.0, 0, 200, 1, 1, on_change=self._touched)
            self.p_rows[key] = r
            g3.add(r)
        c3.add(g3)

        c4 = self.card("报价（飞书口径：面积×单价+人工费）")
        g4 = RowGrid(2)
        self.f_allow_mode = seg_field("边料余量 A", [("auto", "按楞型默认"), ("manual", "手动")],
                                      "auto", on_change=self.on_flute_changed)
        self.f_allow = num_field("A 值（mm）", 20.0, 0, 100, 1, 1, on_change=self._touched)
        self.f_labor = num_field("人工费/套（元）", 0.0, 0, 9999, 0.1, 2,
                                 on_change=self._touched)
        self.f_qty = num_field("套数（套）", 1.0, 1, 100000, 1, 0, on_change=self._touched)
        g4.add(self.f_allow_mode)
        g4.add(self.f_allow)
        g4.add(self.f_labor)
        g4.add(self.f_qty)
        c4.add(g4)

        c5 = self.card("图纸比例")
        g5 = RowGrid(1)
        g5.add(self.scale_field())
        c5.add(g5)
        self.form.addStretch(1)
        self.on_box_changed()

    # ---------------- 联动 ----------------
    def _box(self):
        return self.f_box.seg.value()

    def on_box_changed(self, *_):
        box = self._box()
        parts = [k for k, _ in BOX_META[box]["parts"]]
        for key, r in self.flute_rows.items():
            r.setVisible(key in parts)
        self.f_link.setVisible(box == "0310")
        for key, r in self.p_rows.items():
            if key == "gap":
                r.setVisible(box in ("0310", "0312"))
            elif key == "cover_depth":
                r.setVisible(box == "0312")
            elif key in ("flap_gain", "flap_reduce", "slot_w"):
                r.setVisible(box in ("0201", "0312"))
            else:
                r.setVisible(True)
        self._sync_params()
        self.refresh()
        self._sync_export_hint()

    def on_flute_changed(self, *_):
        self._sync_params()
        self.refresh()
        self._sync_export_hint()

    def _flutes(self):
        box = self._box()
        out = {}
        for key, _ in BOX_META[box]["parts"]:
            out[key] = self.flute_rows[key].flute.value()
        if box == "0310" and self.f_link.widget.isChecked():
            out["cap_bottom"] = out["cap_top"]
        return out

    def _sync_params(self):
        box = self._box()
        fl = self._flutes()
        primary = "cap_top" if box == "0310" else ("lid" if box == "0312" else "body")
        code = fl.get(primary, "BC")
        d = backend.flute_defaults(code, box)
        r = backend.ranges_of(code, box)
        for key, row in self.p_rows.items():
            if key == "cover_depth":
                row.widget.setRange(10.0, max(20.0, self.f_H.widget.value()))
                row.set_hint("罩深 = 天盖墙高；建议 ≈ 0.45×H，且 ≤ 底箱制造高")
                continue
            if key not in d:
                continue
            lo, hi = (r.get(key) if isinstance(r.get(key), tuple) else (0.0, 10000.0))
            if key == "gap":
                lo, hi = (r.get("gap" if box == "0310" else "box_gap") or (1.0, 3.0))
            cur = row.widget.value()
            row.widget.setRange(lo, hi)
            if not (lo - 1e-9 <= cur <= hi + 1e-9):
                row.widget.setValue(d[key])
            row.set_hint(f"标准区间 {lo:g}–{hi:g} mm（{r.get('src', 'GB/T 6543 + 行业实践')}）")
        if self.f_allow_mode.seg.value() == "auto":
            self.f_allow.widget.setValue(price_lib.allow_default(code))
            self.f_allow.widget.setEnabled(False)
        else:
            self.f_allow.widget.setEnabled(True)
        if box == "0310" and self.f_link.widget.isChecked():
            cb = self.flute_rows["cap_bottom"].flute
            cb.set_value(self.flute_rows["cap_top"].flute.value())
            cb.setEnabled(False)
        elif box == "0310":
            self.flute_rows["cap_bottom"].flute.setEnabled(True)

    # ---------------- 计算 ----------------
    def _params(self):
        out = {}
        for key, row in self.p_rows.items():
            if row.isVisible():
                out[key] = row.widget.value()
        return out

    def _price(self):
        allow = {}
        if self.f_allow_mode.seg.value() == "manual":
            v = self.f_allow.widget.value()
            for k in ("body", "sleeve", "cap_top", "cap_bottom", "base", "lid"):
                allow[k] = v
        return dict(allow=allow or None, labor=self.f_labor.widget.value(),
                    qty=self.f_qty.widget.value())

    def _plan(self):
        return backend.box_plan(self._box(),
                                (self.f_L.widget.value(), self.f_W.widget.value(),
                                 self.f_H.widget.value()),
                                mode=self.f_mode.seg.value(), flutes=self._flutes(),
                                params=self._params(), price=self._price())

    def refresh(self):
        try:
            plan = self._plan()
        except (Exception, SystemExit) as e:
            self.table.set_rows([("参数错误", str(e))])
            self.btn_gen.setEnabled(False)
            self.busy.err(str(e))
            return
        p = plan["p"]
        box = self._box()
        dims = [("口径", "外尺寸输入" if self.f_mode.seg.value() == "outer" else "内尺寸输入")]
        dims += backend.box_dim_rows(box, p)
        price_rows = [r for r in plan["rows"] if r[0].startswith("—") or "·" in r[0]]
        price_keys = {r[0] for r in price_rows}
        core_rows = [r for r in plan["rows"] if r[0] not in price_keys]
        self.table.set_groups([("尺寸链", dims),
                               ("展开与工艺", core_rows),
                               ("报价（飞书口径）", price_rows)])
        self.btn_gen.setEnabled(True)
        self.busy.info("参数就绪")

    def sig(self):
        return (self._box(),
                (self.f_L.widget.value(), self.f_W.widget.value(), self.f_H.widget.value()),
                self.f_mode.seg.value(), self._flutes(), self._params(), self._price(),
                self.f_scale.value())

    def generate(self, outdir, prefix):
        plan = self._plan()
        return backend.box_export(self._box(), plan, outdir, prefix=prefix,
                                  frame=self.frame(), scale=self.f_scale.value())
