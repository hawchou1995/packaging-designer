# -*- coding: utf-8 -*-
"""GUI 端到端自检 v1.0.1（offscreen）：四页各跑「生成 → 导出」，验证线程、两段流程、命名与价格。"""
import importlib.util
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "ui"))

from PySide6.QtWidgets import QApplication, QLineEdit, QTabWidget, QWidget   # noqa: E402

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
    # 不变量（比“数量相等”更强）：每个生成件都要有一个**内容一致**的导出副本；
    # 目标被占用时允许落到「xxx (2).pdf」这类编号名上，但不能丢件。
    import hashlib

    def _h(p):
        with open(p, "rb") as fh:
            return hashlib.sha256(fh.read()).hexdigest()

    out_files = [os.path.join(outdir, f) for f in os.listdir(outdir)
                 if os.path.isfile(os.path.join(outdir, f))]
    out_hashes = {}
    for p in out_files:
        try:
            out_hashes.setdefault(_h(p), []).append(os.path.basename(p))
        except OSError:
            pass
    missing = [os.path.basename(g) for g in page._gen_files if _h(g) not in out_hashes]
    err = page.busy.status.text()
    ok = n_gen > 0 and not missing and "失败" not in err
    detail = err[:44] if ok else (f"缺件 {missing[:2]}" if missing else err[:44])
    report.append((tag, n_gen, len(out_files), detail, ok, len(missing)))
    return n_gen, len(out_files)


# -*- guard -*-
def _iso_guard(base_dir):
    """离线测试护栏：把 Settings 指到临时 INI，禁止写用户真实注册表设置。"""
    import os as _os
    from PySide6.QtCore import QSettings as _QS
    import settings as _st
    ini = _os.path.join(base_dir, "_settings.ini")

    def _init(self):
        self.q = _QS(ini, _QS.IniFormat)
        for k, v in _st.DEFAULTS.items():
            setattr(self, k, self.q.value(k, v))
        self.open_after = str(self.open_after).lower() in ("true", "1")

    _st.Settings.__init__ = _init


def main():
    _iso_guard(os.path.dirname(os.path.abspath(__file__)))   # 护栏：不碰用户真实设置
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
            report.append((tag, 0, 0, "被阻断: " + pg.busy.status.text()[:40], False, 0))
            continue
        run_case(app, pg, os.path.join(OUT, tag), tag, tag, report)

    # 6) 对话框冒烟（v1.0.14 新增）：设置/关于 + 图框字段这两处此前**零自动化覆盖**，
    #    所以「容器 QWidget 被循环变量顶掉 → 连坐 QFormLayout 被析构 → already deleted」
    #    从 v1.0.0 存活到 v1.0.13。以后构造不成功 / 返回错对象 / 保存不回写，这里直接红。
    print("\n=== 对话框冒烟（设置/关于 + 图框字段）===")
    import dialogs as dl

    dlg_checks = []

    def _ck(name, ok, detail=""):
        dlg_checks.append(bool(ok))
        print(f"  {'✓' if ok else '✗'} {name}" + (f"  {detail}" if detail else ""))
        return bool(ok)

    keep = (w.settings.outdir, w.settings.prefix, w.settings.dwg_no, w.settings.proofed)
    try:
        sd = dl.SettingsDialog(w.settings, w)
        _ck("SettingsDialog 构造", True)
    except Exception as e:                      # 历史故障：RuntimeError QFormLayout already deleted
        sd = None
        _ck("SettingsDialog 构造", False, f"{type(e).__name__}: {e}")
    if sd is not None:
        page = sd._settings_page
        _ck("设置页是 QWidget（不是被循环变量顶掉的行编辑框）",
            isinstance(page, QWidget) and not isinstance(page, QLineEdit), type(page).__name__)
        need = ("out", "prefix", "company", "author", "dwg_name", "dwg_no", "dwg_version",
                "dwg_material", "designed", "drawn", "proofed", "checked", "process",
                "standard", "approved", "date")
        have = [k for k in need if isinstance(getattr(sd, "e_" + k, None), QLineEdit)]
        _ck("设置页字段齐（16 项输入框，与 on_save 的 key 一致）",
            len(have) == len(need), f"{len(have)}/{len(need)}")
        tabs = sd.findChild(QTabWidget)
        ok_tab = False
        if tabs is not None and tabs.count() == 2:
            try:
                for i in (0, 1):
                    tabs.setCurrentIndex(i)
                    app.processEvents()
                ok_tab = True
            except Exception as e:
                ok_tab = False
                _ck("设置/关于 两个 tab 切换", False, f"{type(e).__name__}: {e}")
        else:
            _ck("设置/关于 两个 tab 存在", False, f"count={getattr(tabs, 'count', lambda: None)()}")
        _ck("设置/关于 两个 tab 切换", ok_tab)
        _ck("设置 tab 内容 = _settings_tab 的容器（不是被顶掉的行编辑框）",
            tabs is not None and tabs.count() == 2 and tabs.widget(0) is sd._settings_page,
            type(tabs.widget(0)).__name__ if (tabs is not None and tabs.count()) else "n/a")
        sd.e_out.setText(os.path.join(OUT, "outdir_smoke"))
        sd.e_prefix.setText("SMOKE")
        sd.e_dwg_no.setText("SMOKE-1")
        sd.on_save()
        _ck("保存写回设置（含图样栏字段）",
            w.settings.prefix == "SMOKE" and w.settings.dwg_no == "SMOKE-1",
            f"prefix={w.settings.prefix!r} dwg_no={w.settings.dwg_no!r}")
        sd.e_out.setText(keep[0])
        sd.e_prefix.setText(keep[1])
        sd.e_dwg_no.setText(keep[2])
        sd.on_save()                            # 收尾复原，别污染后续

    try:
        fd = dl.FrameDialog(w.settings)
        _ck("FrameDialog 构造 + 字段齐（14 项）",
            len(fd.edits) == 14 and all(k in fd.edits for k, _ in dl.FrameDialog.FIELDS))
        fd.edits["proofed"].setText("校对人")
        fd.on_save()
        _ck("FrameDialog 保存生效", w.settings.proofed == "校对人")
        fd.edits["proofed"].setText(keep[3])
        fd.on_save()
    except Exception as e:
        _ck("FrameDialog 构造/保存", False, f"{type(e).__name__}: {e}")

    bad_dlg = sum(1 for ok in dlg_checks if not ok)
    print(f"  对话框冒烟：{len(dlg_checks) - bad_dlg}/{len(dlg_checks)} 通过")

    print("\n=== GUI 端到端（生成 → 导出）===")
    bad = 0
    for tag, n_gen, n_out, msg, ok, _miss in report:
        bad += 0 if ok else 1
        print(f"  {'✓' if ok else '✗'} {tag:14s} 生成 {n_gen:3d} → 导出 {n_out:3d}  {msg}")
    print("RESULT:", "PASS" if not bad and not bad_dlg else f"FAIL {bad + bad_dlg}")
    return 1 if (bad or bad_dlg) else 0


if __name__ == "__main__":
    sys.exit(main())
