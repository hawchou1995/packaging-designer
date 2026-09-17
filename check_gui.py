# -*- coding: utf-8 -*-
"""GUI 端到端自检 v1.0.1（offscreen）：四页各跑「生成 → 导出」，验证线程、两段流程、命名与价格。"""
import importlib.util
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "ui"))

from PySide6.QtWidgets import QApplication           # noqa: E402

import theme                                          # noqa: E402

spec = importlib.util.spec_from_file_location("main_app", os.path.join(HERE, "app.py"))
main_app = importlib.util.module_from_spec(spec)
spec.loader.exec_module(main_app)

OUT = os.path.join(HERE, "_guitest")


def wait(app, page, timeout=900):
    t0 = time.time()
    while page._worker is not None and page._worker.isRunning():
        app.processEvents()
        time.sleep(0.05)
        if time.time() - t0 > timeout:
            raise TimeoutError("worker 超时")
    app.processEvents()
    page._sync_export_hint()


def run_case(app, page, outdir, prefix, tag, report):
    os.makedirs(outdir, exist_ok=True)
    page.out_edit.setText(outdir)
    page.prefix_edit.setText(prefix)
    page.on_generate()
    wait(app, page)
    n_gen = len(page._gen_files)
    page.on_export()
    app.processEvents()
    n_out = len([f for f in os.listdir(outdir) if os.path.isfile(os.path.join(outdir, f))])
    report.append((tag, n_gen, n_out, page.busy.status.text()[:44]))
    return n_gen, n_out


def main():
    app = QApplication([])
    app.setStyleSheet(theme.qss())
    w = main_app.MainWindow()
    os.makedirs(OUT, exist_ok=True)
    report = []

    # 1) 片材
    pg = w.pages[0]
    pg.f_L.widget.setValue(400); pg.f_W.widget.setValue(300); pg.f_H.widget.setValue(15)
    pg.f_mat.widget.setText("EPE")
    pg.refresh()
    run_case(app, pg, os.path.join(OUT, "sheet"), "立板", "片材", report)

    # 2) 仿形垫块（指定左侧边距 20）
    pg = w.pages[1]
    pg.f_L.widget.setValue(1000); pg.f_W.widget.setValue(100); pg.f_H.widget.setValue(100)
    pg.f_sl.widget.setValue(50); pg.f_sw.widget.setValue(70); pg.f_sh.widget.setValue(50)
    pg.f_gap.widget.setValue(40)
    pg.f_mm.seg.set_value("left"); pg._touched()
    pg.f_ml.widget.setValue(20); pg.refresh()
    print("block 左端边距可用:", pg.f_ml.widget.isEnabled())
    run_case(app, pg, os.path.join(OUT, "block"), "垫块", "仿形垫块", report)

    # 3) 网格刀卡（V1+V2；含报价）
    pg = w.pages[2]
    pg.f_L.widget.setValue(580); pg.f_W.widget.setValue(380); pg.f_H.widget.setValue(380)
    pg.f_pl.widget.setValue(65); pg.f_pw.widget.setValue(38); pg.f_ph.widget.setValue(85)
    pg.f_t.widget.setValue(5); pg.f_slot.widget.setValue(7); pg.f_sep.widget.setValue(5)
    pg.f_mat.flute.set_value("BC-K"); pg.refresh()
    pairs = [(pg.table.item(i, 0).text() if pg.table.item(i, 0) else "",
              pg.table.item(i, 1).text() if pg.table.item(i, 1) else "")
             for i in range(pg.table.rowCount())]
    print("grid 报价行:", [r for r in pairs if "每套" in r[0]][:2])
    print("grid 内衬高/每格高控件存在:", hasattr(pg, "f_H"), hasattr(pg, "f_ph"),
          "| 值:", pg.f_H.widget.value(), pg.f_ph.widget.value())
    pg.f_slot.widget.setValue(3); pg.refresh()
    blocked = not pg.btn_gen.isEnabled()
    pg.f_slot.widget.setValue(7); pg.refresh()
    print("grid 开槽宽<板厚 阻断:", blocked, "| 恢复后按钮:", pg.btn_gen.isEnabled())
    run_case(app, pg, os.path.join(OUT, "grid"), "网格", "网格刀卡 V1+V2", report)

    # 4) 纸箱：0201 / 0310(三楞) / 0312(内尺寸 + 手动比例)
    pg = w.pages[3]
    for box, tag in (("0201", "0201"), ("0310", "0310"), ("0312", "0312")):
        pg.f_box.seg.set_value(box); pg.on_box_changed()
        if box == "0310":
            pg.f_link.widget.setChecked(False); pg.on_flute_changed()
            pg.flute_rows["sleeve"].flute.set_value("ABC")
            pg.flute_rows["cap_top"].flute.set_value("ABC"); pg.on_flute_changed()
            pg.flute_rows["cap_bottom"].flute.set_value("BC-K"); pg.refresh()
        if box == "0312":
            pg.f_mode.seg.set_value("inner"); pg._touched()
            pg.f_L.widget.setValue(380); pg.f_W.widget.setValue(280); pg.f_H.widget.setValue(180)
            pg.f_scale.chk_auto.setChecked(False); pg.f_scale.sp.setValue(8.0)
            pg.refresh()
        print(f"{tag} 摘要行数:", pg.table.rowCount(), "| 生成按钮:", pg.btn_gen.isEnabled())
        if not pg.btn_gen.isEnabled():
            report.append((tag, 0, 0, "被阻断: " + pg.busy.status.text()[:40]))
            continue
        run_case(app, pg, os.path.join(OUT, tag), tag, tag, report)

    print("\n=== GUI 端到端（生成 → 导出）===")
    bad = 0
    for tag, n_gen, n_out, msg in report:
        ok = n_gen > 0 and n_out == n_gen
        bad += 0 if ok else 1
        print(f"  {'✓' if ok else '✗'} {tag:14s} 生成 {n_gen:3d} → 导出 {n_out:3d}  {msg}")
    print("RESULT:", "PASS" if not bad else f"FAIL {bad}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
