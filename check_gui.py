# -*- coding: utf-8 -*-
"""GUI 端到端自检（offscreen）：四页各跑一次真实生成，验证线程、导出命名与状态回填。"""
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


def wait(app, page, timeout=600):
    t0 = time.time()
    while page._worker is not None and page._worker.isRunning():
        app.processEvents()
        time.sleep(0.05)
        if time.time() - t0 > timeout:
            raise TimeoutError("worker 超时")
    app.processEvents()


def main():
    app = QApplication([])
    app.setStyleSheet(theme.qss())
    w = main_app.MainWindow()
    os.makedirs(OUT, exist_ok=True)
    report = []

    # 1) 片材
    pg = w.pages[0]
    pg.out_edit.setText(os.path.join(OUT, "sheet"))
    pg.prefix_edit.setText("立板")
    pg.f_L.widget.setValue(400); pg.f_W.widget.setValue(300); pg.f_H.widget.setValue(15)
    pg.f_mat.widget.setText("EPE")
    pg.generate.__self__.refresh()
    print("sheet rows:", pg.table.rowCount(), "| btn enabled:", pg.btn.isEnabled())
    pg.on_generate()
    wait(app, pg)
    report.append(("片材", len(pg._files), pg.busy.status.text()[:40]))

    # 2) 仿形垫块（指定左侧边距 20）
    pg = w.pages[1]
    pg.out_edit.setText(os.path.join(OUT, "block"))
    pg.prefix_edit.setText("垫块")
    pg.f_L.widget.setValue(1000); pg.f_W.widget.setValue(100); pg.f_H.widget.setValue(100)
    pg.f_sl.widget.setValue(50); pg.f_sw.widget.setValue(70); pg.f_sh.widget.setValue(50)
    pg.f_gap.widget.setValue(40)
    pg.f_margin_mode.widget.setCurrentIndex(1)
    pg.f_ml.widget.setValue(20)
    pg.refresh()
    print("block rows:", pg.table.rowCount(), "| 左端边距可用:", pg.f_ml.widget.isEnabled())
    pg.on_generate()
    wait(app, pg)
    report.append(("仿形垫块", len(pg._files), pg.busy.status.text()[:40]))

    # 3) 网格刀卡（V1+V2 都导）
    pg = w.pages[2]
    pg.out_edit.setText(os.path.join(OUT, "grid"))
    pg.prefix_edit.setText("网格")
    pg.f_L.widget.setValue(580); pg.f_W.widget.setValue(380); pg.f_H.widget.setValue(380)
    pg.f_pl.widget.setValue(65); pg.f_pw.widget.setValue(38); pg.f_ph.widget.setValue(85)
    pg.f_t.widget.setValue(5); pg.f_slot.widget.setValue(7); pg.f_sep.widget.setValue(5)
    pg.refresh()
    print("grid cmp rows:", pg.cmp.rowCount())
    # 开槽宽 < 板厚 → 应阻断
    pg.f_slot.widget.setValue(3)
    pg.refresh()
    blocked = not pg.btn.isEnabled()
    pg.f_slot.widget.setValue(7)
    pg.refresh()
    print("grid slot< t blocked:", blocked, "| btn:", pg.btn.isEnabled())
    pg.on_generate()
    wait(app, pg)
    report.append(("网格刀卡 V1+V2", len(pg._files), pg.busy.status.text()[:40]))

    # 4) 纸箱：0201 / 0310(三楞) / 0312
    pg = w.pages[3]
    for box, tag in (("0201", "0201"), ("0310", "0310"), ("0312", "0312")):
        pg.out_edit.setText(os.path.join(OUT, tag))
        pg.prefix_edit.setText(tag)
        i = pg.f_box.widget.findData(box)
        pg.f_box.widget.setCurrentIndex(i)
        pg.on_box_changed()
        if box == "0310":
            pg.flute_rows["sleeve"].widget.setCurrentIndex(pg.flute_rows["sleeve"].widget.findData("ABC"))
            pg.flute_rows["cap_top"].widget.setCurrentIndex(pg.flute_rows["cap_top"].widget.findData("BC-HS"))
            pg.f_link_caps.widget.setChecked(False)      # 三楞：上 ABC / 下 BC-HS 之外再放开
            pg.on_flute_changed()
            pg.flute_rows["cap_bottom"].widget.setCurrentIndex(
                pg.flute_rows["cap_bottom"].widget.findData("BC"))
            pg.refresh()
        if box == "0312":
            pg.f_mode.widget.setCurrentIndex(1)          # 内尺寸输入
            pg.f_L.widget.setValue(380); pg.f_W.widget.setValue(280); pg.f_H.widget.setValue(180)
            pg.refresh()
        print(f"{tag} plan rows:", pg.table.rowCount(), "| btn:", pg.btn.isEnabled())
        if not pg.btn.isEnabled():
            report.append((tag, 0, "被阻断: " + pg.busy.status.text()[:40]))
            continue
        pg.on_generate()
        wait(app, pg)
        report.append((tag, len(pg._files), pg.busy.status.text()[:40]))

    print("\n=== GUI 端到端 ===")
    for name, n, msg in report:
        print(f"  {name:14s} {n:3d} files  {msg}")
    bad = [r for r in report if r[1] == 0]
    print("RESULT:", "FAIL" if bad else "PASS")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
