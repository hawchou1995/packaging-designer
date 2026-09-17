# -*- coding: utf-8 -*-
"""pages.py — 四个模块页（片材 / 仿形垫块 / 网格刀卡 / 瓦楞纸箱）。

统一结构：左列参数（标签在输入之上）+ 右列即时计算与预览 + 底部导出栏（目录/前缀/生成）。
所有重型生成都在后台线程里跑，主线程只做即时计算（纯数学，毫秒级）。
"""
import os
import traceback

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (QFileDialog, QGridLayout, QHBoxLayout, QLabel, QLineEdit,
                               QPushButton, QScrollArea, QSizePolicy, QSplitter,
                               QVBoxLayout, QWidget)

import backend
import theme
from widgets import (BusyBar, Card, FileList, PreviewPane, ResultTable, TwoColForm,
                     check_field, choice_field, int_field, num_field, open_path, text_field)


class GenWorker(QThread):
    done = Signal(object)
    fail = Signal(str)

    def __init__(self, fn, parent=None):
        super().__init__(parent)
        self.fn = fn

    def run(self):
        try:
            self.done.emit(self.fn())
        except (Exception, SystemExit) as e:      # 核心模块用 SystemExit 报参数错误
            msg = str(e) or e.__class__.__name__
            self.fail.emit(msg)


class BasePage(QWidget):
    title = ""
    subtitle = ""
    preview_name = None            # 主图纸 PNG 的“属性后缀”，用于预览

    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        self._worker = None
        self._files = []
        self._outdir = settings.outdir

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 14, 16, 12)
        root.setSpacing(10)

        head = QVBoxLayout()
        head.setSpacing(2)
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
        # 左：参数
        left = QScrollArea()
        left.setWidgetResizable(True)
        lw = QWidget()
        self.form = QVBoxLayout(lw)
        self.form.setContentsMargins(0, 0, 8, 0)
        self.form.setSpacing(10)
        left.setWidget(lw)
        left.setMinimumWidth(360)
        # 右：计算 + 预览
        right = QWidget()
        rv = QVBoxLayout(right)
        rv.setContentsMargins(0, 0, 0, 0)
        rv.setSpacing(10)
        self.res_card = Card("计算摘要")
        self.table = ResultTable()
        self.res_card.add(self.table)
        rv.addWidget(self.res_card, 2)
        self.prev_card = Card("图纸预览")
        self.preview = PreviewPane()
        self.prev_card.add(self.preview)
        rv.addWidget(self.prev_card, 3)
        split.addWidget(left)
        split.addWidget(right)
        split.setStretchFactor(0, 4)
        split.setStretchFactor(1, 5)
        root.addWidget(split, 1)

        # 底部：导出
        exp = Card("导出")
        g = QGridLayout()
        g.setHorizontalSpacing(10)
        g.setVerticalSpacing(4)
        self.out_edit = QLineEdit(settings.outdir)
        browse = QPushButton("浏览…")
        browse.clicked.connect(self.on_browse)
        out_box = QWidget()
        oh = QHBoxLayout(out_box)
        oh.setContentsMargins(0, 0, 0, 0)
        oh.setSpacing(6)
        oh.addWidget(self.out_edit, 1)
        oh.addWidget(browse, 0)
        self.prefix_edit = QLineEdit(settings.prefix)
        self.prefix_edit.setPlaceholderText("例：XG盖板 或 客户简称")
        g.addWidget(self._lab("输出目录（全部文件写入此目录）"), 0, 0, 1, 2)
        g.addWidget(self._lab("文件名前缀（每个文件自动加属性后缀）"), 0, 2)
        g.addWidget(out_box, 1, 0, 1, 2)
        g.addWidget(self.prefix_edit, 1, 2)
        self.btn = QPushButton("生成并导出")
        self.btn.setObjectName("Primary")
        self.btn.clicked.connect(self.on_generate)
        self.btn.setMinimumWidth(120)
        g.addWidget(self.btn, 2, 2)
        self.busy = BusyBar()
        g.addWidget(self.busy, 2, 0, 1, 2)
        g.setColumnStretch(0, 1)
        g.setColumnStretch(1, 1)
        exp.body().addLayout(g)

        frow = QHBoxLayout()
        frow.setSpacing(8)
        self.file_list = FileList()
        self.file_list.setFixedHeight(92)
        frow.addWidget(self.file_list, 1)
        btns = QVBoxLayout()
        btns.setSpacing(6)
        b_open_dir = QPushButton("打开目录")
        b_open_dir.clicked.connect(lambda: open_path(self._outdir))
        b_open_dwg = QPushButton("打开图纸")
        b_open_dwg.clicked.connect(self.on_open_main)
        btns.addWidget(b_open_dir)
        btns.addWidget(b_open_dwg)
        btns.addStretch(1)
        frow.addLayout(btns)
        exp.body().addLayout(frow)
        root.addWidget(exp, 0)

        self.build_form()
        self.refresh()

    # ---------------- 工具 ----------------
    @staticmethod
    def _lab(text):
        lab = QLabel(text)
        lab.setObjectName("FieldLabel")
        return lab

    def card(self, title):
        c = Card(title)
        self.form.addWidget(c)
        return c

    def stretch(self):
        self.form.addStretch(1)

    # ---------------- 子类接口 ----------------
    def build_form(self):
        raise NotImplementedError

    def refresh(self):
        """即时计算（子类实现）。"""

    def generate(self):
        raise NotImplementedError

    # ---------------- 交互 ----------------
    def on_browse(self):
        d = QFileDialog.getExistingDirectory(self, "选择输出目录", self.out_edit.text() or
                                             os.path.expanduser("~"))
        if d:
            self.out_edit.setText(d)

    def on_open_main(self):
        if not self._files:
            self.busy.info("尚未生成文件")
            return
        main = None
        if self.preview_name:
            for f in self._files:
                if f.endswith(self.preview_name + ".pdf"):
                    main = f
                    break
        if main is None:
            for f in self._files:
                if f.endswith(".pdf"):
                    main = f
                    break
        if main is None:
            for f in self._files:
                if f.endswith(".png"):
                    main = f
                    break
        if not open_path(main or self._files[0]):
            self.busy.err("文件不存在（可能已被移动）")

    def on_generate(self):
        if self._worker is not None and self._worker.isRunning():
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
        self._outdir = outdir
        self.btn.setEnabled(False)
        self.busy.busy("正在生成图纸与模型…（含 OCC 建模，约数秒）")
        self._worker = GenWorker(self.generate, self)
        self._worker.done.connect(self.on_done)
        self._worker.fail.connect(self.on_fail)
        self._worker.start()

    def on_done(self, result):
        self.btn.setEnabled(True)
        files = result.files if hasattr(result, "files") else list(result)
        self._files = files
        self.file_list.set_files(files)
        names = [os.path.basename(f) for f in files]
        self.busy.ok(f"已生成 {len(files)} 个文件到 {self._outdir}")
        if hasattr(result, "rows") and result.rows:
            self.table.set_rows(result.rows)
        png = None
        for f in files:
            if f.endswith(".png") and (self.preview_name is None or self.preview_name in f):
                png = f
                break
        if png is None:
            for f in files:
                if f.endswith(".png"):
                    png = f
                    break
        self.preview.show_image(png)
        self.after_done(result)
        if self.settings.open_after:
            open_path(self._outdir)

    def after_done(self, result):
        """子类可选：生成后补齐界面状态。"""

    def on_fail(self, msg):
        self.btn.setEnabled(True)
        self.busy.err(f"生成失败：{msg}")
        traceback.print_exc()

    def prefix(self):
        return self.prefix_edit.text().strip() or self.settings.prefix

    def frame(self):
        return self.settings.frame()


# ================================================================ 片材
class SheetPage(BasePage):
    title = "片材"
    subtitle = "输入长 / 宽 / 厚，输出第一角三视图 + 等轴测图 + 1:1 DXF 轮廓 + STEP/STL 数模 + 参数表（A3 图框）。"
    preview_name = "图纸-三视图+轴测图_A3"

    def build_form(self):
        c = self.card("尺寸")
        g = TwoColForm()
        self.f_name = text_field("名称", "片材", on_change=self.refresh)
        self.f_mat = text_field("材料（可空）", "", placeholder="EPE / EVA / 蜂窝纸板", on_change=self.refresh)
        g.add(self.f_name, 0)
        g.add(self.f_mat, 1)
        g.next_row()
        self.f_L = num_field("长 L", 400.0, 1, 20000, 10, 1, on_change=self.refresh)
        self.f_W = num_field("宽 W", 300.0, 1, 20000, 10, 1, on_change=self.refresh)
        g.add(self.f_L, 0)
        g.add(self.f_W, 1)
        g.next_row()
        self.f_H = num_field("厚 T", 15.0, 0.5, 500, 1, 1, on_change=self.refresh)
        g.add(self.f_H, 0)
        c.add(g)
        info = QLabel("说明：薄板按 1:1 轮廓出图；比例与图幅自动选择，单位 mm。")
        info.setObjectName("FieldHint")
        info.setWordWrap(True)
        c.add(info)
        self.stretch()

    def refresh(self):
        try:
            from sheet_core import Params, report
            p = Params(L=self.f_L.widget.value(), W=self.f_W.widget.value(), H=self.f_H.widget.value(),
                       name=self.f_name.widget.text() or "片材", material=self.f_mat.widget.text())
            errs, rows = report(p)
            self.table.set_rows(rows)
            self.btn.setEnabled(not errs)
            self.busy.info("；".join(errs) if errs else "参数就绪")
        except (Exception, SystemExit) as e:
            self.table.set_rows([("参数错误", str(e))])
            self.btn.setEnabled(False)

    def generate(self):
        return backend.run_sheet(self.f_L.widget.value(), self.f_W.widget.value(),
                                 self.f_H.widget.value(), self._outdir, prefix=self.prefix(),
                                 name=self.f_name.widget.text() or "片材",
                                 material=self.f_mat.widget.text(), frame=self.frame())


# ================================================================ 仿形垫块
class BlockPage(BasePage):
    title = "仿形垫块"
    subtitle = "输入垫块外形、槽尺寸与间距；边距可两端均分或指定一侧，另一侧自动。输出三视图 + 轴测图 + DXF + STEP/STL + 参数表。"
    preview_name = "图纸-三视图+轴测图_A3"

    def build_form(self):
        c = self.card("垫块与开槽")
        g = TwoColForm()
        self.f_L = num_field("垫块长 L", 1000.0, 10, 20000, 10, 1, on_change=self.refresh)
        self.f_W = num_field("垫块宽 W", 100.0, 5, 5000, 5, 1, on_change=self.refresh)
        g.add(self.f_L, 0)
        g.add(self.f_W, 1)
        g.next_row()
        self.f_H = num_field("垫块高 H", 100.0, 5, 2000, 5, 1, on_change=self.refresh)
        self.f_gap = num_field("槽间距", 40.0, 0, 2000, 5, 1, on_change=self.refresh)
        g.add(self.f_H, 0)
        g.add(self.f_gap, 1)
        g.next_row()
        self.f_sl = num_field("槽长（沿块长）", 50.0, 1, 20000, 5, 1, on_change=self.refresh)
        self.f_sw = num_field("槽宽（沿块宽）", 70.0, 1, 5000, 5, 1, on_change=self.refresh)
        g.add(self.f_sl, 0)
        g.add(self.f_sw, 1)
        g.next_row()
        self.f_sh = num_field("槽深（自顶面）", 50.0, 1, 2000, 5, 1, on_change=self.refresh)
        c.add(g)

        c2 = self.card("边距与开口")
        g2 = TwoColForm()
        self.f_margin_mode = choice_field("边距方式", [("even", "两端均分（左=右）"), ("left", "指定左侧，右侧自动")],
                                          "even", on_change=self.refresh)
        g2.add_wide(self.f_margin_mode)
        self.f_ml = num_field("左端边距", 20.0, 0, 5000, 5, 1,
                              hint="仅在「指定左侧」时生效", on_change=self.refresh)
        g2.add(self.f_ml, 0)
        self.f_side = choice_field("单边贯穿开口侧", [("front", "前侧（长-宽 视图下方）"), ("back", "后侧")],
                                   "front", on_change=self.refresh)
        g2.add(self.f_side, 1)
        c2.add(g2)
        self.f_name = text_field("名称", "仿形块", on_change=self.refresh)
        self.f_mat = text_field("材料（可空）", "", placeholder="EPE / EVA 等", on_change=self.refresh)
        c2.add(self.f_name)
        c2.add(self.f_mat)
        hint = QLabel("槽宽 = 垫块宽 → 全贯穿；否则单边贯穿（默认前侧），对侧保留墙厚。")
        hint.setObjectName("FieldHint")
        hint.setWordWrap(True)
        c2.add(hint)
        self.stretch()

    def refresh(self):
        try:
            from block_core import Params, report
            mode = self.f_margin_mode.widget.currentData()
            ml = self.f_ml.widget.value() if mode == "left" else None
            p = Params(L=self.f_L.widget.value(), W=self.f_W.widget.value(), H=self.f_H.widget.value(),
                       sl=self.f_sl.widget.value(), sw=self.f_sw.widget.value(),
                       sh=self.f_sh.widget.value(), gap=self.f_gap.widget.value(),
                       margin_left=ml, open_side=self.f_side.widget.currentData(),
                       name=self.f_name.widget.text() or "仿形块", material=self.f_mat.widget.text())
            errs, rows, d = report(p)
            self.table.set_rows(rows)
            self.f_ml.widget.setEnabled(mode == "left")
            self.btn.setEnabled(not errs)
            self.busy.info("；".join(errs) if errs else "参数就绪")
        except (Exception, SystemExit) as e:
            self.table.set_rows([("参数错误", str(e))])
            self.btn.setEnabled(False)

    def generate(self):
        mode = self.f_margin_mode.widget.currentData()
        return backend.run_block(self.f_L.widget.value(), self.f_W.widget.value(),
                                 self.f_H.widget.value(), self.f_sl.widget.value(),
                                 self.f_sw.widget.value(), self.f_sh.widget.value(),
                                 self.f_gap.widget.value(), self._outdir, prefix=self.prefix(),
                                 margin_left=(self.f_ml.widget.value() if mode == "left" else None),
                                 open_side=self.f_side.widget.currentData(),
                                 name=self.f_name.widget.text() or "仿形块",
                                 material=self.f_mat.widget.text(), frame=self.frame())


# ================================================================ 网格刀卡
class GridPage(BasePage):
    title = "网格刀卡"
    subtitle = "输入内衬外尺寸（= 容器内尺寸）、每格尺寸与刀卡厚度；自动算出两种排布（V1 长对长 / V2 长对宽）的格数、层数、收容数与刀卡片数，可只导一种或两种都导。"
    preview_name = "图纸-网格俯视+刀卡侧视+轴测图_A3"

    def build_form(self):
        c = self.card("容器与格子")
        g = TwoColForm()
        self.f_L = num_field("内衬外长（容器内长）", 580.0, 20, 20000, 10, 1, on_change=self.refresh)
        self.f_W = num_field("内衬外宽（容器内宽）", 380.0, 20, 20000, 10, 1, on_change=self.refresh)
        g.add(self.f_L, 0)
        g.add(self.f_W, 1)
        g.next_row()
        self.f_H = num_field("内衬高（容器内高）", 380.0, 20, 20000, 10, 1, on_change=self.refresh)
        c.add(g)
        g2 = TwoColForm()
        self.f_pl = num_field("每格长（产品+缓冲）", 65.0, 1, 5000, 1, 1, on_change=self.refresh)
        self.f_pw = num_field("每格宽（产品+缓冲）", 38.0, 1, 5000, 1, 1, on_change=self.refresh)
        g2.add(self.f_pl, 0)
        g2.add(self.f_pw, 1)
        g2.next_row()
        self.f_ph = num_field("每格高（产品+缓冲）", 85.0, 1, 5000, 5, 1, on_change=self.refresh)
        c.add(g2)

        c3 = self.card("纸板与隔板")
        g3 = TwoColForm()
        self.f_t = num_field("刀卡厚度 t", 5.0, 1, 20, 0.5, 1, on_change=self.refresh)
        self.f_slot = num_field("开槽宽度", 7.0, 1, 30, 0.5, 1, on_change=self.refresh)
        g3.add(self.f_t, 0)
        g3.add(self.f_slot, 1)
        g3.next_row()
        self.f_sep = num_field("隔板厚度", 5.0, 1, 30, 0.5, 1,
                               hint="0 或与刀卡同厚时按同厚计", on_change=self.refresh)
        self.f_pads = choice_field("顶 / 底隔板", [("both", "底部 + 顶部"), ("bottom", "仅底部"),
                                                   ("top", "仅顶部"), ("none", "无（层间隔板恒有）")],
                                  "both", on_change=self.refresh)
        g3.add(self.f_sep, 0)
        g3.add(self.f_pads, 1)
        c3.add(g3)
        self.slot_hint = QLabel("")
        self.slot_hint.setObjectName("FieldHint")
        self.slot_hint.setWordWrap(True)
        c3.add(self.slot_hint)

        c4 = self.card("导出方案（可多选）")
        self.chk1 = check_field("V1 长对长（内衬长向 = 产品长）", True, on_change=self.refresh)
        self.chk2 = check_field("V2 长对宽（内衬长向 = 产品宽）", True, on_change=self.refresh)
        c4.add(self.chk1)
        c4.add(self.chk2)
        note = QLabel("两种都导出时，文件名自动带 -V1 / -V2 后缀区分。")
        note.setObjectName("FieldHint")
        note.setWordWrap(True)
        c4.add(note)

        c5 = self.card("方案对比")
        self.cmp = ResultTable()
        self.cmp.setMinimumHeight(150)
        c5.add(self.cmp)
        self.stretch()

    def _args(self):
        return dict(container=(self.f_L.widget.value(), self.f_W.widget.value(), self.f_H.widget.value()),
                    cell=(self.f_pl.widget.value(), self.f_pw.widget.value(), self.f_ph.widget.value()),
                    t=self.f_t.widget.value(), slot_w=self.f_slot.widget.value(),
                    sep_t=self.f_sep.widget.value(), pads=self.f_pads.widget.currentData())

    def refresh(self):
        a = self._args()
        t = a["t"]
        ok_slot = a["slot_w"] >= t - 1e-9
        self.slot_hint.setText(
            f"开槽宽须 ≥ 刀卡厚 t={t:g} mm（当前 {a['slot_w']:g} mm）："
            + ("可以装配，单边间隙 %.1f mm" % (a["slot_w"] - t) if ok_slot else "会干涉，请加大开槽宽"))
        plans = {}
        for v in (1, 2):
            try:
                p, rows, d = backend.grid_plan(**a, version=v)
                plans[v] = (rows, d, None)
            except (Exception, SystemExit) as e:
                plans[v] = (None, None, str(e))
        cmp_rows = []
        for v in (1, 2):
            rows, d, err = plans[v]
            tag = "V1 长对长" if v == 1 else "V2 长对宽"
            if rows is None:
                cmp_rows += [(f"{tag} · 状态", err)]
                continue
            cmp_rows += [(f"{tag} · 格数（长×短）", f"{d['n_l']} × {d['n_w']}"),
                         (f"{tag} · 层数 / 收容数", f"{d['layers']} / {d['capacity']}"),
                         (f"{tag} · 长刀卡（每层×层=总）",
                          f"{d['cards_long']} × {d['layers']} = {d['cards_long_total']}"),
                         (f"{tag} · 短刀卡（每层×层=总）",
                          f"{d['cards_short']} × {d['layers']} = {d['cards_short_total']}"),
                         (f"{tag} · 边距（长/短）", f"{d['margin_l']:g} / {d['margin_w']:g}"),
                         (f"{tag} · 堆叠高 ≤ 内高", f"{d['H_stack']:g} ≤ {a['container'][2]:g}")]
        self.cmp.set_rows(cmp_rows)
        # 主结果表显示选中的第一个方案明细
        rows1 = plans[1][0]
        self.table.set_rows(rows1 if rows1 else [("提示", "参数不满足：见下方方案对比")])
        errs = [plans[1][2], plans[2][2]]
        self.btn.setEnabled(ok_slot and any(r is None for r in errs))
        self.busy.info("；".join(x for x in errs if x) if any(errs) else
                       ("参数就绪" if ok_slot else "开槽宽不足"))

    def generate(self):
        a = self._args()
        both = self.chk1.widget.isChecked() and self.chk2.widget.isChecked()
        files, rows = [], []
        for v, chk in ((1, self.chk1), (2, self.chk2)):
            if not chk.widget.isChecked():
                continue
            pre = (self.prefix() + (f"-V{v}" if both else "")) if self.prefix() else (f"V{v}" if both else "")
            r = backend.run_grid(a["container"], a["cell"], a["t"], self._outdir, prefix=pre,
                                 slot_w=a["slot_w"], sep_t=a["sep_t"], pads=a["pads"],
                                 version=v, frame=self.frame())
            files += r.files
            rows = r.rows
        if not files:
            raise ValueError("未选择任何导出方案")
        res = backend.Result(files, rows)
        return res


# ================================================================ 瓦楞纸箱
BOX_META = {
    "0201": dict(label="FEFCO 0201 · 标准开槽箱（RSC，上下一片式）",
                 parts=[("body", "纸板楞型")]),
    "0310": dict(label="FEFCO 0310 · 围框 + 两盖（端对端双盖）",
                 parts=[("sleeve", "围框楞型"), ("cap_top", "上盖楞型"), ("cap_bottom", "下盖楞型")]),
    "0312": dict(label="FEFCO 0312 · 底箱 + 平顶天盖（罩盖）",
                 parts=[("base", "底箱楞型"), ("lid", "天盖楞型")]),
}


class BoxPage(BasePage):
    title = "瓦楞纸箱"
    subtitle = "选箱型与楞型，输入外尺寸或内尺寸；图框自动填内 / 制造 / 外三口径，其余参数按楞型取标准区间默认值（可改，超范围阻断）。"
    preview_name = "图纸-展开图+轴测图_A3"

    def build_form(self):
        c = self.card("箱型与尺寸")
        g = TwoColForm()
        self.f_box = choice_field("箱型", [(k, v["label"]) for k, v in BOX_META.items()],
                                  "0201", on_change=self.on_box_changed)
        g.add_wide(self.f_box)
        self.f_mode = choice_field("尺寸输入口径", [("outer", "外尺寸（组装外形）"), ("inner", "内尺寸（内腔）")],
                                   "outer", on_change=self.refresh)
        g.add_wide(self.f_mode)
        self.f_L = num_field("长 L", 400.0, 10, 20000, 10, 1, on_change=self.refresh)
        self.f_W = num_field("宽 W", 300.0, 10, 20000, 10, 1, on_change=self.refresh)
        self.f_H = num_field("高 H", 200.0, 10, 20000, 10, 1, on_change=self.refresh)
        g.add(self.f_L, 0)
        g.add(self.f_W, 1)
        g.next_row()
        g.add(self.f_H, 0)
        c.add(g)
        self.dim_note = QLabel("")
        self.dim_note.setObjectName("FieldHint")
        self.dim_note.setWordWrap(True)
        c.add(self.dim_note)

        c2 = self.card("楞型（材料来自飞书包材表 + GB/T 6544）")
        g2 = TwoColForm()
        self.flute_rows = {}
        all_parts = []
        for bx, m in BOX_META.items():
            for key, label in m["parts"]:
                if key not in [k for k, _ in all_parts]:
                    all_parts.append((key, label))
        for key, label in all_parts:
            r = choice_field(label, backend.flute_choices(), "BC", on_change=self.on_flute_changed)
            self.flute_rows[key] = r
            g2.add_wide(r)
        c2.add(g2)
        self.f_link_caps = check_field("上下盖同款同楞", True, on_change=self.on_flute_changed)
        c2.add(self.f_link_caps)
        hint = QLabel("不同楞型板厚不同：0310 围框外尺寸按较厚盖板计算，两盖展开图各出一张。")
        hint.setObjectName("FieldHint")
        hint.setWordWrap(True)
        c2.add(hint)

        c3 = self.card("工艺参数（标准区间内可改）")
        g3 = TwoColForm()
        self.p_rows = {}
        for key, label in (("glue_w", "接舌宽"), ("flap_gain", "外摇盖加放"),
                           ("flap_reduce", "内摇盖折减"), ("slot_w", "开槽宽"),
                           ("gap", "盖 / 围框单边间隙"), ("cover_depth", "天盖罩深")):
            r = num_field(label, 45.0, 0, 200, 1, 1, hint="", on_change=self.refresh)
            self.p_rows[key] = r
            g3.add(r, (len(self.p_rows) - 1) % 2)
            if len(self.p_rows) % 2 == 0:
                g3.next_row()
        c3.add(g3)
        self.stretch()
        self.on_box_changed()

    # ---------------- 楞型 / 箱型联动 ----------------
    def _box(self):
        return self.f_box.widget.currentData()

    def on_box_changed(self):
        box = self._box()
        parts = BOX_META[box]["parts"]
        for key, r in self.flute_rows.items():
            r.setVisible(any(key == k for k, _ in parts))
        self.f_link_caps.setVisible(box == "0310")
        for key, r in self.p_rows.items():
            if key in ("gap",):
                r.setVisible(box in ("0310", "0312"))
            elif key == "cover_depth":
                r.setVisible(box == "0312")
            elif key in ("flap_gain", "flap_reduce", "slot_w"):
                r.setVisible(box in ("0201", "0312"))
            else:
                r.setVisible(True)
        self._sync_params()
        self.refresh()

    def on_flute_changed(self):
        self._sync_params()
        self.refresh()

    def _flutes(self):
        box = self._box()
        out = {}
        for key, _ in BOX_META[box]["parts"]:
            out[key] = self.flute_rows[key].widget.currentData()
        if box == "0310" and self.f_link_caps.widget.isChecked():
            out["cap_bottom"] = out["cap_top"]
        return out

    def _sync_params(self):
        """按各楞型默认值刷新工艺参数（保留用户已改动且仍在区间内的值）。"""
        box = self._box()
        fl = self._flutes()
        primary = "cap_top" if box == "0310" else ("lid" if box == "0312" else "body")
        code = fl.get(primary, "BC")
        d = backend.flute_defaults(code, box)
        r = backend.ranges_of(code, box)
        for key, row in self.p_rows.items():
            if key == "cover_depth":
                row.widget.setRange(10.0, 10000.0)
                msg = "罩深（天盖墙高）；建议 ≈ 0.45×H，且 ≤ 底箱制造高"
                row.set_hint(msg)
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
        if box == "0312":
            self.p_rows["cover_depth"].widget.setRange(10.0, max(20.0, self.f_H.widget.value()))
        # 下盖楞型随上盖
        if box == "0310" and self.f_link_caps.widget.isChecked():
            cb = self.flute_rows["cap_bottom"].widget
            i = cb.findData(self.flute_rows["cap_top"].widget.currentData())
            if i >= 0:
                cb.setCurrentIndex(i)
            self.flute_rows["cap_bottom"].widget.setEnabled(False)
        elif box == "0310":
            self.flute_rows["cap_bottom"].widget.setEnabled(True)

    # ---------------- 即时计算 ----------------
    def _args(self):
        box = self._box()
        fl = self._flutes()
        params = {}
        for key, row in self.p_rows.items():
            if row.isVisible():
                params[key] = row.widget.value()
        return dict(box=box, dims=(self.f_L.widget.value(), self.f_W.widget.value(), self.f_H.widget.value()),
                    mode=self.f_mode.widget.currentData(), flutes=fl, params=params)

    def refresh(self):
        a = self._args()
        try:
            plan = backend.box_plan(a["box"], a["dims"], mode=a["mode"], flutes=a["flutes"],
                                    params=a["params"])
        except (Exception, SystemExit) as e:
            self.table.set_rows([("参数错误", str(e))])
            self.btn.setEnabled(False)
            self.busy.err(str(e))
            return
        rows = []
        rows += [(f"口径（{ '外尺寸输入' if a['mode'] == 'outer' else '内尺寸输入'}）", "")]
        rows += backend.box_dim_rows(a["box"], plan["p"])
        rows += [("", "")]
        rows += plan["rows"]
        self.table.set_rows(rows)
        self.btn.setEnabled(True)
        self.dim_note.setText("尺寸链：内 = 外 − 2t（L/W/H 同口径）· 制造 = 外 − t；"
                              "0310 围框高 = 外高 − 上盖 t − 下盖 t；0312 内高 = 外高 − 2×底箱 t。")
        self.busy.info("参数就绪")

    def generate(self):
        a = self._args()
        plan = backend.box_plan(a["box"], a["dims"], mode=a["mode"], flutes=a["flutes"], params=a["params"])
        return backend.box_export(a["box"], plan, self._outdir, prefix=self.prefix(), frame=self.frame())
