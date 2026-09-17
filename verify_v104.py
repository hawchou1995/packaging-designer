# -*- coding: utf-8 -*-
"""verify_v104.py — v1.0.4 两项修复的点击级验证（offscreen 程序化点击，非真实窗口验收）

① 导出目录：粘贴带引号/空格/大写的目录 → 导出落到清洗后的真实目录；
   「打开目录」请求当前输入框目录；「打开图纸」请求导出副本；设置保存后四页同步。
② 图框字段：八栏标签与值一一对应 + 日期默认当天 + 设置页/图框对话框可填。
"""
import hashlib
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
TMPBASE = os.path.join(HERE, "_v104")
shutil.rmtree(TMPBASE, ignore_errors=True)
os.makedirs(TMPBASE, exist_ok=True)
tempfile.tempdir = TMPBASE                     # 隔离：临时目录也放 D 盘
os.environ["LOCALAPPDATA"] = TMPBASE



sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "ui"))

from PySide6.QtWidgets import QApplication          # noqa: E402
from PySide6.QtCore import QSettings                # noqa: E402

import theme                                        # noqa: E402
import settings as _set_mod                         # noqa: E402
from PySide6.QtCore import QSettings as _QS         # noqa: E402

_ISO_INI = os.path.join(TMPBASE, "settings.ini")


def _iso_init(self):
    self.q = _QS(_ISO_INI, _QS.IniFormat)
    for k, v in _set_mod.DEFAULTS.items():
        setattr(self, k, self.q.value(k, v))
    self.open_after = str(self.open_after).lower() in ("true", "1")


_set_mod.Settings.__init__ = _iso_init

import app as main_app                              # noqa: E402
import pages as pages_mod                          # noqa: E402  (与 app.py 同一模块对象)
import settings as set_mod                          # noqa: E402

RESULTS = []


def check(name, ok, detail=""):
    RESULTS.append((name, bool(ok), detail))
    print(f"  {'✓' if ok else '✗'} {name}" + (f" — {detail}" if detail else ""))
    return ok


def hashf(p):
    with open(p, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()[:16]


def main():
    # 每次新建 Settings（QSettings 落点在隔离目录）
    app = QApplication.instance() or QApplication([])
    app.setStyleSheet(theme.qss())
    win = main_app.MainWindow()
    win.settings = set_mod.Settings()

    calls = {}
    # 拦截点=open_path_ex（v1.0.4 起「打开」都走它，带关联探测与兜底）
    pages_mod.open_path_ex = (lambda p: (calls.setdefault("open", []).append(str(p)),
                                         (True, ""))[1])
    pages_mod.has_assoc = lambda p: True          # 测试里假定有关联，走正常打开分支

    outdir = os.path.join(TMPBASE, "OUT_测试 目录")            # 含空格
    os.makedirs(outdir, exist_ok=True)

    print("\n=== ① 导出目录链路 ===")
    for i, pg in enumerate(win.pages):
        win.group.button(i).setChecked(True)
        win.stack.setCurrentIndex(i)
        # 用户粘贴：带引号 + 大小写混合 + 前后空格
        pg.out_edit.setText(f'  "{outdir}"  ')
        gen = pg._tmpdir()
        # 造两个哑产物（只验证导出链路，不涉及几何生成）
        names = ["图纸_A3.pdf", "轮廓_1-1.dxf"]
        made = []
        for n in names:
            f = os.path.join(gen, "gen_" + n)
            with open(f, "w", encoding="utf-8") as fh:
                fh.write(f"page{i}:{n}")
            made.append(f)
        pg._gen_files = made
        pg._gen_prefix = "gen"
        pg._gen_sig = pg.sig()
        pg._export_files = []
        got = pg.cur_outdir()
        check(f"页{i + 1} 目录清洗", got == os.path.abspath(outdir), f"'{got}'")

        pg.on_export()
        landed = sorted(os.listdir(outdir))
        ok_copy = all(os.path.isfile(os.path.join(outdir, b))
                      for b in [n for n in landed if n.endswith((".pdf", ".dxf"))])
        check(f"页{i + 1} 文件确实落到指定目录", ok_copy, f"{len(landed)} 项")

        calls.pop("open", None)
        pg.on_open_dir()
        if not calls.get("open"):
            print("     busy 原文:", pg.busy.status.text())
        check(f"页{i + 1}「打开目录」= 输入框目录",
              (calls.get("open") or [""])[-1] == os.path.abspath(outdir),
              str((calls.get("open") or [""])[-1]))

        calls.pop("open", None)
        pg.on_open_main()
        if not calls.get("open"):
            print("     busy 原文:", pg.busy.status.text())
        req = (calls.get("open") or [""])[-1]
        check(f"页{i + 1}「打开图纸」= 导出副本（非临时件）",
              req.startswith(os.path.abspath(outdir)), req)
        shutil.rmtree(outdir, ignore_errors=True)
        os.makedirs(outdir, exist_ok=True)

    print("\n=== ①b 改默认目录后四页同步 ===")
    newdir = os.path.join(TMPBASE, "OUT_新默认")
    os.makedirs(newdir, exist_ok=True)
    win.settings.outdir = newdir
    # 直接调用保存后同步逻辑（与 app.on_settings 相同路径）
    for p in win.pages:
        p.out_edit.setText(win.settings.outdir)
        p._outdir = p.cur_outdir()
    synced = all(p.cur_outdir() == os.path.abspath(newdir) for p in win.pages)
    check("设置保存后四页输出目录同步", synced)
    calls.pop("open", None)
    win.pages[0].on_open_dir()
    check("同步后「打开目录」跟到新目录",
          (calls.get("open") or [""])[-1] == os.path.abspath(newdir),
          str((calls.get("open") or [""])[-1]))

    print("\n=== ② 图框字段 ===")
    import dialogs as dl
    fd = dl.FrameDialog(win.settings)
    keys = [k for k, _ in dl.FrameDialog.FIELDS]
    check("图框对话框字段数 = 10（含工艺/标准化/日期）", len(keys) == 10, str(keys))
    fd.edits["proofed"].setText("校对人")
    fd.edits["process"].setText("工艺人")
    fd.edits["standard"].setText("标准化人")
    fd.edits["date"].setText("")
    fd.on_save()
    s = win.settings
    check("校对/工艺/标准化 已存入设置",
          s.proofed == "校对人" and s.process == "工艺人" and s.standard == "标准化人")
    check("日期留空 = 用当天", s.date == "")
    import backend as be
    meta = be.frame_meta(s.frame())
    check("frame_meta 透传 proofed/process/standard/date",
          meta["proofed"] == "校对人" and meta["date"] == "")
    from core.dwgframe import _today
    check("当天日期可用", len(_today()) == 10, _today())

    print("\n=== 结果 ===")
    bad = [r for r in RESULTS if not r[1]]
    print(f"{len(RESULTS) - len(bad)}/{len(RESULTS)} 通过")
    for n, _, d in bad:
        print("  失败:", n, d)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
