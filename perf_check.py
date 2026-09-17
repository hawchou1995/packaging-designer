# -*- coding: utf-8 -*-
"""验证 1.0.3 的两条新能力：分阶段进度回调 + 「只出图纸」快路径（含耗时对比）。"""
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "core"))

import backend                       # noqa: E402

OUT = os.path.join(HERE, "_perf2")
MSGS = []


def pg(m):
    MSGS.append(m)
    print("   [进度]", m)


def main():
    t0 = time.time()
    r = backend.run_grid((580, 380, 380), (65, 38, 85), 5.0, os.path.join(OUT, "only_v1"),
                         prefix="T", slot_w=7.0, version=1, progress=pg, full=False)
    t_only = time.time() - t0
    t0 = time.time()
    r2 = backend.run_grid((580, 380, 380), (65, 38, 85), 5.0, os.path.join(OUT, "full_v1"),
                          prefix="T", slot_w=7.0, version=1, progress=None, full=True)
    t_full = time.time() - t0
    print(f"\n只出图纸 V1：{t_only:.1f}s / {len(r.files)} 文件"
          f"　全套 V1：{t_full:.1f}s / {len(r2.files)} 文件"
          f"　省 {t_full - t_only:.1f}s（{(1 - t_only / t_full) * 100:.0f}%）")

    # 纸箱快路径
    t0 = time.time()
    rb = backend.run_box("0310", (400, 300, 200), os.path.join(OUT, "box_only"), prefix="T",
                         flutes=dict(sleeve="ABC", cap_top="ABC", cap_bottom="BC-K"),
                         progress=pg, full=False)
    t_bo = time.time() - t0
    print(f"纸箱 0310 只出图纸：{t_bo:.1f}s / {len(rb.files)} 文件")


if __name__ == "__main__":
    main()
