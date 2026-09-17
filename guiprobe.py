# -*- coding: utf-8 -*-
"""guiprobe.py — 冻结包内 GUI 层全流程自检（写日志文件，避免 windowed 版 stdout 丢失）。

用：PackagingDesigner.exe --guiprobe D:\\path\\probe.txt（必须 .txt：.log 会被 DGS 透明加密）
逐页执行：设值 → on_generate → 等 worker → on_export，每步用 try/except 记录真实异常与 traceback。
"""
import os
import time
import traceback


def _log(fh, msg):
    fh.write(msg + "\n")
    fh.flush()


def run(logpath, root_dir=None):
    out = open(logpath, "w", encoding="utf-8")
    _log(out, f"== guiprobe start {time.strftime('%Y-%m-%d %H:%M:%S')} ==")
    _log(out, f"frozen={getattr(__import__('sys'), 'frozen', False)} exe={os.sys.executable}")
    _log(out, f"sys.path head={os.sys.path[:6]}")

    try:
        from PySide6.QtWidgets import QApplication
        import theme
        import app as main_app
    except Exception:
        _log(out, "!! 导入阶段失败:\n" + traceback.format_exc())
        out.close()
        return 2

    app = QApplication.instance() or QApplication([])
    app.setStyleSheet(theme.qss())
    try:
        win = main_app.MainWindow()
    except Exception:
        _log(out, "!! MainWindow 构造失败:\n" + traceback.format_exc())
        out.close()
        return 2
    win.resize(1320, 840)
    win.show()
    app.processEvents()

    base = root_dir or os.path.join(os.path.dirname(os.path.abspath(logpath)), "guiprobe_out")
    os.makedirs(base, exist_ok=True)

    cases = [("片材", 0), ("仿形垫块", 1), ("网格刀卡", 2), ("瓦楞纸箱", 3)]
    fails = 0
    for name, idx in cases:
        _log(out, f"\n--- {name} (page {idx}) ---")
        try:
            win.group.button(idx).setChecked(True)
            win.stack.setCurrentIndex(idx)
            app.processEvents()
            pg = win.pages[idx]
            _log(out, f"  刷新后：生成按钮={pg.btn_gen.isEnabled()} 状态={pg.busy.status.text()!r} "
                      f"摘要行={pg.table.rowCount()}")
        except Exception:
            fails += 1
            _log(out, "  !! 切页/刷新失败:\n" + traceback.format_exc())
            continue
        d = os.path.join(base, name)
        os.makedirs(d, exist_ok=True)
        try:
            pg.out_edit.setText(d)
            pg.prefix_edit.setText("probe")
            t0 = time.time()
            pg.on_generate()
            _log(out, "  on_generate() 返回，worker="
                      f"{'运行中' if (pg._worker and pg._worker.isRunning()) else '未运行'}")
            while pg._worker is not None and pg._worker.isRunning():
                app.processEvents()
                time.sleep(0.05)
                if time.time() - t0 > 600:
                    raise TimeoutError("worker 超时 600s")
            app.processEvents()
            _log(out, f"  生成完成 {time.time()-t0:.1f}s：文件 {len(pg._gen_files)} 个；"
                      f"状态={pg.busy.status.text()!r}")
            for f in pg._gen_files[:3]:
                _log(out, f"     · {os.path.basename(f)}")
            pg.on_export()
            app.processEvents()
            n = len([x for x in os.listdir(d) if os.path.isfile(os.path.join(d, x))])
            _log(out, f"  导出后目录文件数={n}；状态={pg.busy.status.text()!r}")
            if len(pg._gen_files) == 0 or n == 0:
                fails += 1
                _log(out, "  ✗ 判定失败：生成或导出文件数为 0")
            else:
                _log(out, "  ✓ 通过")
        except Exception:
            fails += 1
            _log(out, "  !! 生成/导出阶段异常:\n" + traceback.format_exc())
            if pg._worker is not None:
                _log(out, f"     worker.isRunning={pg._worker.isRunning()}")
    _log(out, f"\n== guiprobe 结束：失败 {fails}/{len(cases)} ==")
    out.close()
    return 1 if fails else 0
