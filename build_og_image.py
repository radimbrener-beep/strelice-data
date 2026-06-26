#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Vygeneruje sdílecí obrázek og-image.png (1200×630) pro náhled odkazu na FB ap.
Tmavé pozadí v barvách portálu, logo terč+šíp, název a adresa. Plochý soubor
v kořeni (deploy ho kopíruje stejně jako HTML)."""
import sys
from PIL import Image, ImageDraw, ImageFont
sys.stdout.reconfigure(encoding="utf-8")

W, H = 1200, 630
BG = (11, 17, 32)        # --bg2 #0b1120
SURF = (18, 26, 44)      # --surface
TEXT = (232, 237, 246)   # --text
MUTED = (147, 161, 184)  # --muted
ACCENT = (111, 160, 208)  # --accent #6fa0d0
LINE = (31, 42, 64)


def font(size, bold=False):
    cands = ([r"C:\Windows\Fonts\segoeuib.ttf", r"C:\Windows\Fonts\arialbd.ttf"] if bold
             else [r"C:\Windows\Fonts\segoeui.ttf", r"C:\Windows\Fonts\arial.ttf"])
    cands += ["DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"]
    for p in cands:
        try:
            return ImageFont.truetype(p, size)
        except OSError:
            continue
    return ImageFont.load_default()


def center(draw, y, text, fnt, fill, letter=0):
    w = draw.textlength(text, font=fnt)
    draw.text(((W - w) / 2, y), text, font=fnt, fill=fill)


img = Image.new("RGB", (W, H), BG)
d = ImageDraw.Draw(img)

# jemný rám a spodní akcentní linka
d.rectangle([0, 0, W - 1, H - 1], outline=LINE, width=2)
d.rectangle([0, H - 8, W, H], fill=ACCENT)

# --- logo: terč + šíp (vycentrované nahoře) ---
cx, cy = W // 2, 150
for r, wdt in ((74, 9), (50, 9), (27, 9)):
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=ACCENT, width=wdt)
d.ellipse([cx - 9, cy - 9, cx + 9, cy + 9], fill=ACCENT)
# šíp mířící do středu (z pravého horního rohu)
d.line([(cx + 120, cy - 120), (cx + 14, cy - 14)], fill=TEXT, width=9)
# hrot šípu
d.polygon([(cx + 6, cy - 6), (cx + 40, cy - 16), (cx + 16, cy - 40)], fill=TEXT)
# opeření šípu
d.line([(cx + 120, cy - 120), (cx + 104, cy - 150)], fill=TEXT, width=8)
d.line([(cx + 120, cy - 120), (cx + 150, cy - 104)], fill=TEXT, width=8)

# --- texty ---
center(d, 268, "Jak žijí Střelice", font(96, bold=True), TEXT)
center(d, 388, "Otevřená data obce Střelice u Brna", font(38), MUTED)
center(d, 452, "rozpočet · investice · dotace · zastupitelstvo · školství", font(31), ACCENT)

# adresa v patičce (na akcentním pruhu prostor nad ním)
center(d, 540, "jakzijistrelice.cz", font(40, bold=True), TEXT)

img.save("og-image.png", optimize=True)
import os
print(f"HOTOVO: og-image.png ({W}×{H}, {os.path.getsize('og-image.png')} B)")
