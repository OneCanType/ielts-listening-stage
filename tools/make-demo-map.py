#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成演示用的公园示意图（自绘，无版权问题）。

输出：tools/demo-map.webp
用法：python3 tools/make-demo-map.py

地图不追求写实，只要求：一眼看懂方位、六个字母标记清晰、打印成 PDF 也不糊。
"""

import os
from PIL import Image, ImageDraw, ImageFont

W, H = 900, 620
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "demo-map.webp")

PARK = (56, 52, 844, 566)
GREEN = (242, 248, 238)
GREEN_LINE = (122, 154, 106)
PATH = (233, 228, 216)
PATH_LINE = (214, 206, 190)
WATER = (207, 230, 245)
WATER_LINE = (143, 184, 207)
BUILD = (244, 201, 139)
BUILD_LINE = (176, 122, 60)
SAND = (246, 227, 168)
GREY = (217, 221, 226)
ROSE = (232, 180, 190)
INK = (74, 82, 90)
LETTER = (192, 57, 43)


def font(size, bold=True):
    path = "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else \
           "/System/Library/Fonts/Supplemental/Arial.ttf"
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()


def rrect(d, box, r, fill, outline, width=3):
    d.rounded_rectangle(box, radius=r, fill=fill, outline=outline, width=width)


def label(d, x, y, text, size=13, color=INK, anchor="mm"):
    d.text((x, y), text, font=font(size, False), fill=color, anchor=anchor)


def marker(d, x, y, ch):
    r = 19
    d.ellipse((x - r, y - r, x + r, y + r), fill=LETTER, outline=(255, 255, 255), width=2)
    d.text((x, y + 1), ch, font=font(21), fill=(255, 255, 255), anchor="mm")


def main():
    im = Image.new("RGB", (W, H), (255, 255, 255))
    d = ImageDraw.Draw(im)

    # 公园边界
    rrect(d, PARK, 18, GREEN, GREEN_LINE, 4)
    label(d, 450, 34, "GREENWAY PARK", 15, (96, 120, 84))

    # 主路（十字）
    d.line((70, 330, 830, 330), fill=PATH_LINE, width=34)
    d.line((70, 330, 830, 330), fill=PATH, width=28)
    d.line((455, 66, 455, 552), fill=PATH_LINE, width=34)
    d.line((455, 66, 455, 552), fill=PATH, width=28)

    # 湖 + 桥
    d.ellipse((120, 372, 330, 520), fill=WATER, outline=WATER_LINE, width=3)
    label(d, 200, 455, "LAKE", 12, (92, 140, 168))
    d.line((330, 440, 395, 360), fill=PATH_LINE, width=26)
    d.line((330, 440, 395, 360), fill=PATH, width=20)
    bridge = [(338, 430), (362, 448), (384, 404), (360, 386)]
    d.polygon(bridge, fill=(185, 138, 94), outline=(140, 100, 64))
    label(d, 392, 448, "bridge", 11, (120, 90, 64))

    # 咖啡厅（A）
    rrect(d, (92, 214, 196, 290), 8, BUILD, BUILD_LINE)
    d.polygon([(88, 214), (200, 214), (188, 192), (100, 192)], fill=(206, 120, 92))
    label(d, 144, 256, "CAFÉ", 14, (120, 78, 42))
    marker(d, 74, 190, "A")

    # 游乐场（F）
    rrect(d, (104, 96, 232, 190), 10, SAND, (208, 176, 96))
    for cx, cy in [(128, 122), (168, 118), (206, 132), (140, 158), (190, 166)]:
        d.ellipse((cx - 7, cy - 7, cx + 7, cy + 7), fill=(226, 150, 120))
    label(d, 168, 78, "PLAYGROUND", 12, (150, 118, 58))
    marker(d, 252, 96, "F")

    # 玫瑰园（B）
    rrect(d, (500, 96, 640, 190), 10, (232, 244, 224), (140, 176, 120))
    for cx, cy in [(524, 120), (556, 146), (592, 118), (616, 158), (540, 172), (612, 188)]:
        d.ellipse((cx - 6, cy - 6, cx + 6, cy + 6), fill=ROSE)
    label(d, 570, 205, "ROSE GARDEN", 12, (128, 156, 108))
    marker(d, 664, 108, "B")

    # 喷泉（C）
    d.ellipse((410, 285, 500, 375), fill=WATER, outline=WATER_LINE, width=3)
    d.ellipse((438, 313, 472, 347), fill=(255, 255, 255), outline=WATER_LINE, width=2)
    d.ellipse((449, 324, 461, 336), fill=(150, 196, 220))
    label(d, 455, 396, "FOUNTAIN", 11, (92, 140, 168))
    marker(d, 455, 258, "C")

    # 雕像（D）
    d.rectangle((646, 314, 674, 334), fill=(196, 200, 206), outline=(150, 156, 164))
    d.ellipse((652, 292, 668, 310), fill=(140, 146, 154))
    label(d, 660, 352, "statue", 11, INK)
    marker(d, 660, 270, "D")

    # 停车场（E）
    rrect(d, (676, 386, 788, 472), 6, GREY, (170, 176, 184))
    d.text((732, 429), "P", font=font(34), fill=(110, 118, 128), anchor="mm")
    label(d, 732, 490, "CAR PARK", 12, (120, 126, 134))
    marker(d, 812, 470, "E")

    # 门
    d.rectangle((438, 560, 472, 578), fill=(255, 255, 255), outline=GREEN_LINE, width=3)
    label(d, 455, 596, "MAIN ENTRANCE", 12, (110, 130, 96))
    d.rectangle((836, 314, 852, 348), fill=(255, 255, 255), outline=GREEN_LINE, width=3)
    label(d, 792, 288, "EAST GATE", 12, (110, 130, 96))

    im.save(OUT, "WEBP", quality=90, method=6)
    print("saved", OUT, os.path.getsize(OUT) // 1024, "KB")


if __name__ == "__main__":
    main()
