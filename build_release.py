# -*- coding: utf-8 -*-
"""build_release.py — 打包 + **产物校验**（v1.0.7 新增，堵「能启动却没 Qt 插件」这类静默失败）

教训：PyInstaller 在内存紧张时，取 Qt 信息的子进程会被系统杀掉（exit 0xC0000417），
      于是 PySide6 插件目录没被收集，包能生成、装完一启动就 "no Qt platform plugin"。
      必须在**打包后立刻校验关键文件**，缺了就报错，不允许进入安装/发布环节。

用法：python build_release.py <dist目录名>  例：python build_release.py dist107
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PYI = r"D:/Tools/venvs/fefco0210/Scripts/pyinstaller.exe"
VENV_PY = r"D:/Tools/venvs/fefco0210/Scripts/python.exe"

# 缺任何一个都说明收集不完整（按 dist106 实际内容为基准）
REQUIRED = [
    "PackagingDesigner.exe",
    "_internal/PySide6/Qt6Core.dll",
    "_internal/PySide6/Qt6Widgets.dll",
    "_internal/PySide6/Qt6Gui.dll",
    "_internal/PySide6/plugins/platforms/qwindows.dll",
    "_internal/PySide6/plugins/platforms/qoffscreen.dll",
    "_internal/PySide6/plugins/styles/qmodernwindowsstyle.dll",
    "_internal/PySide6/plugins/imageformats/qico.dll",
    "_internal/PySide6/plugins/imageformats/qsvg.dll",
    "_internal/matplotlib/mpl-data/fonts/ttf",
    "_internal/ezdxf",
]


def verify(dist_dir):
    root = os.path.join(HERE, dist_dir, "PackagingDesigner")
    if not os.path.isdir(root):
        print(f"  ✗ 产物目录不存在：{root}")
        return False
    print(f"  产物目录：{root}")
    miss = []
    for rel in REQUIRED:
        p = os.path.join(root, *rel.split("/"))
        if not os.path.exists(p):
            miss.append(rel)
    n_plugins = len(os.listdir(os.path.join(root, "_internal", "PySide6", "plugins"))) \
        if os.path.isdir(os.path.join(root, "_internal", "PySide6", "plugins")) else 0
    n_files = sum(len(f) for _r, _d, f in os.walk(root))
    print(f"  文件总数 {n_files} · 插件类目 {n_plugins}")
    if miss:
        print("  ✗ 缺少关键文件：")
        for m in miss:
            print(f"      · {m}")
        return False
    print("  ✓ 关键文件齐全（含 Qt 平台插件 qwindows/qoffscreen）")
    return True


def main():
    dist = sys.argv[1] if len(sys.argv) > 1 else "dist107"
    print(f"=== 打包 {dist} ===")
    r = subprocess.run([PYI, "--noconfirm", "--clean",
                        "--distpath", os.path.join(HERE, dist),
                        "--workpath", os.path.join(HERE, "build_" + dist),
                        os.path.join(HERE, "packaging-designer.spec")],
                       cwd=HERE, capture_output=True, text=True)
    print(f"  pyinstaller exit={r.returncode}")
    log = os.path.join(HERE, f"_pyi_{dist}.log")
    with open(log, "w", encoding="utf-8") as fh:
        fh.write(r.stdout + "\n" + r.stderr)
    if "failed to obtain Qt library info" in (r.stdout + r.stderr):
        print("  ⚠ 日志出现「failed to obtain Qt library info」→ Qt 收集不完整，需要重打")
    if r.returncode != 0:
        print("  ✗ 打包失败，详见", log)
        return 1
    print(f"  日志：{log}")
    if not verify(dist):
        return 1
    print("\n=== 冻结包后端自检 ===")
    exe = os.path.join(HERE, dist, "PackagingDesigner", "PackagingDesigner.exe")
    out = os.path.join(HERE, f"_{dist}_selftest")
    env = dict(os.environ, QT_QPA_PLATFORM="offscreen")
    rr = subprocess.run([exe, "--selftest", out], cwd=HERE, capture_output=True,
                        text=True, env=env)
    tail = [l for l in (rr.stdout + rr.stderr).splitlines()
            if l.startswith(("sheet", "block", "grid", "0201", "0310", "0312", "SELFTEST"))]
    print("  " + " | ".join(tail[-7:]))
    ok = "SELFTEST OK" in rr.stdout
    print("  结果:", "PASS" if ok else f"FAIL（exit={rr.returncode}）")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
