# -*- coding: utf-8 -*-
"""生成应用图标：深青底 + 白色瓦楞纸箱展开图（dieline）符号。

输出：resources/app.ico（16/24/32/48/64/128/256）、resources/app_256.png、app_64.png
运行：python make_icon.py
"""
import os

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "resources")
BG = (15, 118, 110, 255)        # 深青 #0F766E（唯一强调色）
FG = (250, 250, 249, 255)
SS = 8                          # 8x 超采样后缩小，得到平滑描边


def _flute(d, px, lw):
    """瓦楞板断面符号：上下纸／面线 + 中间楞芯波浪线（小尺寸下仍清晰）。"""
    import math
    x0, x1 = px * 0.185, px * 0.815
    y_top, y_bot = px * 0.345, px * 0.655
    d.line([(x0, y_top), (x1, y_top)], fill=FG, width=lw)
    d.line([(x0, y_bot), (x1, y_bot)], fill=FG, width=lw)
    # 楞芯波浪
    amp = (y_bot - y_top) / 2.0 * 0.55
    ymid = (y_top + y_bot) / 2.0
    n = 64
    pts = []
    for i in range(n + 1):
        t = i / n
        pts.append((x0 + (x1 - x0) * t, ymid - amp * math.sin(t * 2 * math.pi * 3.0)))
    d.line(pts, fill=FG, width=lw, joint="curve")


def render(size):
    px = size * SS
    im = Image.new("RGBA", (px, px), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    pad = px * 0.055
    d.rounded_rectangle([pad, pad, px - pad, px - pad], radius=px * 0.19, fill=BG)
    lw = max(SS, int(px * 0.048))
    _flute(d, px, lw)
    return im.resize((size, size), Image.LANCZOS)


def main():
    os.makedirs(OUT, exist_ok=True)
    sizes = [16, 24, 32, 48, 64, 128, 256]
    imgs = [render(s) for s in sizes]
    ico = os.path.join(OUT, "app.ico")
    imgs[-1].save(ico, format="ICO", sizes=[(s, s) for s in sizes])
    imgs[-1].save(os.path.join(OUT, "app_256.png"))
    imgs[4].save(os.path.join(OUT, "app_64.png"))
    imgs[3].save(os.path.join(OUT, "app_48.png"))
    imgs[2].save(os.path.join(OUT, "app_32.png"))
    print("icon:", ico, os.path.getsize(ico), "bytes")
    for f in ("app_256.png", "app_64.png", "app_48.png", "app_32.png"):
        print(" ", f, os.path.getsize(os.path.join(OUT, f)))


if __name__ == "__main__":
    main()
