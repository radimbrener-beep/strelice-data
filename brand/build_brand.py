"""Generátor značky „jak se máme" — logo (SVG, text převedený na křivky) + favikony.

    python brand/build_brand.py

Výstup: brand/logo/*.svg, brand/favicon/*, brand/preview.html.
Novou obec stačí přidat do OBCE (název v 5. pádě = oslovení).
"""
import io
import json
import math
from pathlib import Path

import uharfbuzz as hb
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer
from PIL import Image, ImageDraw

ROOT = Path(__file__).parent
FONT = ROOT / "_src" / "BricolageGrotesque.ttf"
AXES = {"opsz": 96, "wght": 760, "wdth": 100}
TRACK = -35  # letter-spacing v jednotkách fontu (UPM 1000) = -0.035em
SPACE_TRACK = 15  # mezera mezi slovy se nezužuje, naopak lehce rozšiřuje

# (slug subdomény, oslovení v 5. pádě)
OBCE = [("strelice", "Střelice"), ("ostopovice", "Ostopovice")]

LIGHT = dict(ink="#142F3A", obec="#1D6B73", amber="#EFA42A", muted="#58696E", bg="#F2F5F4")
DARK = dict(ink="#E4EEEC", obec="#8FD0D4", amber="#F4B547", muted="#8FA4A7", bg="#0D191E")

# ---------------------------------------------------------------- symbol
# Geometrie ve viewBoxu 64×64 (stejná jako v návrhu CI).
BUBBLE = ("M18 4H46A14 14 0 0 1 60 18V36A14 14 0 0 1 46 50H29L13 61L18.5 50H18"
          "A14 14 0 0 1 4 36V18A14 14 0 0 1 18 4Z")
BARS = [(15, 30, 8.5, 12), (27.75, 23, 8.5, 19), (40.5, 14, 8.5, 28)]  # x, y, w, h
BAR_R = 2
SYM_BOX = (4, 4, 60, 61)  # vizuální bbox symbolu


def rr(x, y, w, h, r):
    """Zaoblený obdélník jako podcesta (opačný směr než bublina → díra i při nonzero)."""
    return (f"M{x+r:g} {y:g}A{r} {r} 0 0 0 {x:g} {y+r:g}V{y+h-r:g}A{r} {r} 0 0 0 {x+r:g} {y+h:g}"
            f"H{x+w-r:g}A{r} {r} 0 0 0 {x+w:g} {y+h-r:g}V{y+r:g}A{r} {r} 0 0 0 {x+w-r:g} {y:g}Z")


def symbol_paths(c, mono=False):
    """Bublina s vyříznutými sloupci; nejvyšší sloupec jantarový (v mono také vyříznutý)."""
    holes = BARS if mono else BARS[:2]
    d = BUBBLE + "".join(rr(*b, BAR_R) for b in holes)
    out = f'<path fill="{c["ink"]}" fill-rule="evenodd" d="{d}"/>'
    if not mono:
        out += f'<path fill="{c["amber"]}" d="{rr(*BARS[2], BAR_R)}"/>'
    return out


# ---------------------------------------------------------------- písmo
_var = TTFont(FONT)
_inst = instancer.instantiateVariableFont(TTFont(FONT), AXES)
_gs = _inst.getGlyphSet()
UPM = _inst["head"].unitsPerEm
XH = _inst["OS/2"].sxHeight

_hbface = hb.Face(FONT.read_bytes())
_hbfont = hb.Font(_hbface)
_hbfont.set_variations(AXES)


def shape(text):
    buf = hb.Buffer()
    buf.add_str(text)
    buf.guess_segment_properties()
    hb.shape(_hbfont, buf, {"kern": True, "liga": True})
    names = _inst.getGlyphOrder()
    return [(names[i.codepoint], p.x_advance, p.x_offset, p.y_offset)
            for i, p in zip(buf.glyph_infos, buf.glyph_positions)]


def run_paths(text, x0):
    """Vrátí [(glyph, path_d, x)], novou pozici x a bbox. Souřadnice: y nahoru (font)."""
    out, x = [], x0
    bb = [math.inf, math.inf, -math.inf, -math.inf]
    for name, adv, dx, dy in shape(text):
        pen = SVGPathPen(_gs, ntos=lambda v: f"{round(v):d}")
        _gs[name].draw(TransformPen(pen, (1, 0, 0, -1, x + dx, -dy)))  # y dolů
        bp = BoundsPen(_gs)
        _gs[name].draw(bp)
        if bp.bounds:
            a, b, c, d = bp.bounds
            bb = [min(bb[0], a + x + dx), min(bb[1], -d - dy), max(bb[2], c + x + dx), max(bb[3], -b - dy)]
        out.append((name, pen.getCommands(), x))
        x += adv + (SPACE_TRACK if name == "space" else TRACK)
    return out, x - TRACK, bb


def glyph_bounds(name):
    bp = BoundsPen(_gs)
    _gs[name].draw(bp)
    return bp.bounds


# ---------------------------------------------------------------- wordmark
def accent(ax):
    """Jantarová čárka nad „a" — rostoucí tah (náhrada diakritiky á)."""
    x0, _, x1, _ = glyph_bounds("a")
    L, T, ang = 0.33 * UPM, 0.115 * UPM, 30
    cx = ax + x0 + 0.30 * (x1 - x0)          # levý střed tahu
    cy = -(XH + 0.135 * UPM)                  # y dolů
    return (f'<rect x="{cx:.1f}" y="{cy - T/2:.1f}" width="{L:.1f}" height="{T:.1f}" rx="{T*0.5:.1f}" '
            f'transform="rotate(-{ang} {cx:.1f} {cy:.1f})"'), (cx, cy, L, T, ang)


def accent_bbox(cx, cy, L, T, ang):
    a = math.radians(ang)
    pts = []
    for px, py in [(0, -T/2), (L, -T/2), (L, T/2), (0, T/2)]:
        pts.append((cx + px * math.cos(a) + py * math.sin(a), cy - px * math.sin(a) + py * math.cos(a)))
    xs, ys = zip(*pts)
    return [min(xs), min(ys), max(xs), max(ys)]


def union(*bbs):
    bbs = [b for b in bbs if b and b[0] != math.inf]
    return [min(b[0] for b in bbs), min(b[1] for b in bbs), max(b[2] for b in bbs), max(b[3] for b in bbs)]


def wordmark(c, x0=0, y0=0, obec=None, stacked=False):
    """SVG skupina wordmarku s účařím v (x0, y0). Vrací (svg, bbox)."""
    parts, bbs = [], []

    def put(text, x, y, fill):
        g, xe, bb = run_paths(text, x)
        d = "".join(p for _, p, _ in g)
        parts.append(f'<path fill="{fill}" transform="translate(0 {y:g})" d="{d}"/>')
        bbs.append([bb[0], bb[1] + y, bb[2], bb[3] + y])
        return g, xe

    g, x = put("jak se mame" + ("," if obec else ""), x0, y0, c["ink"])
    a_x = [gx for name, _, gx in g if name == "a"][-1]  # „a" v „máme"
    rect, geo = accent(a_x)
    parts.append(f'<g transform="translate(0 {y0:g})">{rect} fill="{c["amber"]}"/></g>')
    ab = accent_bbox(*geo)
    bbs.append([ab[0], ab[1] + y0, ab[2], ab[3] + y0])
    if obec:
        if stacked:
            _, x = put(obec, x0, y0 + 1.08 * UPM, c["obec"])
            put("?", x - TRACK, y0 + 1.08 * UPM, c["muted"])
        else:
            _, x = put(" " + obec, x, y0, c["obec"])
            put("?", x - TRACK, y0, c["muted"])
    return "".join(parts), union(*bbs)


# ---------------------------------------------------------------- lockupy
SYM_K = 1.42 * UPM / 64  # symbol ~1.42 em vysoký (viewBox 64)
GAP = 0.30 * UPM


def lockup(c, obec=None, stacked=False, symbol=True, mono=False):
    cc = dict(c)
    if mono:
        cc.update(obec=c["ink"], muted=c["ink"], amber=c["ink"])
    sym_svg, sym_bb = "", None
    tx = 0
    if symbol:
        k = SYM_K * (1.55 if stacked else 1)
        # vertikálně: střed těla bubliny (y=27) na optický střed textu
        mid = -XH * 0.55 if not stacked else 0.54 * UPM - XH * 0.5
        sy = mid - 27 * k
        sym_svg = f'<g transform="translate({-SYM_BOX[0]*k:.1f} {sy:.1f}) scale({k:.4f})">{symbol_paths(cc, mono)}</g>'
        sym_bb = [0, sy + SYM_BOX[1] * k, (SYM_BOX[2] - SYM_BOX[0]) * k, sy + SYM_BOX[3] * k]
        tx = sym_bb[2] + GAP
    wm_svg, wm_bb = wordmark(cc, tx, 0, obec, stacked)
    bb = union(sym_bb, wm_bb)
    pad = 0.06 * UPM
    vb = (bb[0] - pad, bb[1] - pad, bb[2] - bb[0] + 2 * pad, bb[3] - bb[1] + 2 * pad)
    return svg_doc(vb, sym_svg + wm_svg, title(obec))


def title(obec):
    return f"Jak se máme, {obec}?" if obec else "Jak se máme"


def svg_doc(vb, body, ttl, extra=""):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{vb[0]:.1f} {vb[1]:.1f} {vb[2]:.1f} {vb[3]:.1f}" '
            f'role="img" aria-label="{ttl}"><title>{ttl}</title>{extra}{body}</svg>\n')


def symbol_doc(c, mono=False, pad=2):
    x0, y0, x1, y1 = SYM_BOX
    vb = (x0 - pad, y0 - pad, x1 - x0 + 2 * pad, y1 - y0 + 2 * pad)
    return svg_doc(vb, symbol_paths(c, mono), "Jak se máme")


# ---------------------------------------------------------------- rastr (favikony)
SS = 8  # supersampling


def render_symbol(size, c, bg=None, scale=0.84, radius=0.0):
    """PNG symbolu: čtverec size×size, symbol zabírá `scale` strany, volitelně podklad."""
    S = size * SS
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    if bg:
        ImageDraw.Draw(img).rounded_rectangle([0, 0, S - 1, S - 1], radius=int(radius * S), fill=bg)
    x0, y0, x1, y1 = SYM_BOX
    k = scale * S / max(x1 - x0, y1 - y0)
    ox = (S - (x1 - x0) * k) / 2 - x0 * k
    oy = (S - (y1 - y0) * k) / 2 - y0 * k
    T = lambda x, y: (ox + x * k, oy + y * k)  # noqa: E731
    m = Image.new("L", (S, S), 0)
    d = ImageDraw.Draw(m)
    d.rounded_rectangle([*T(4, 4), *T(60, 50)], radius=14 * k, fill=255)
    d.polygon([T(31, 44), T(29, 50), T(13, 61), T(18.5, 50), T(17, 44)], fill=255)
    for (x, y, w, h) in BARS[:2]:
        d.rounded_rectangle([*T(x, y), *T(x + w, y + h)], radius=BAR_R * k, fill=0)
    img.paste(Image.new("RGBA", (S, S), c["ink"]), (0, 0), m)
    a = Image.new("L", (S, S), 0)
    x, y, w, h = BARS[2]
    ImageDraw.Draw(a).rounded_rectangle([*T(x, y), *T(x + w, y + h)], radius=BAR_R * k, fill=255)
    img.paste(Image.new("RGBA", (S, S), c["amber"]), (0, 0), a)
    return img.resize((size, size), Image.LANCZOS)


# Ručně hintovaná 16px favikona (# = inkoust, A = jantar, . = průhledné).
PIX16 = """
................
..############..
.##############.
.#########AA###.
.#########AA###.
.######..#AA###.
.######..#AA###.
.###..#..#AA###.
.###..#..#AA###.
.###..#..#AA###.
.##############.
..############..
....###.........
...##...........
...#............
................
"""


def render_pix16(c):
    img = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    col = {"#": c["ink"], "A": c["amber"]}
    for y, row in enumerate(PIX16.strip().splitlines()):
        for x, ch in enumerate(row):
            if ch in col:
                img.putpixel((x, y), Image.new("RGBA", (1, 1), col[ch]).getpixel((0, 0)))
    return img


def favicon_svg():
    x0, y0, x1, y1 = SYM_BOX
    vb = (x0 - 1, y0 - 1.5, x1 - x0 + 2, y1 - y0 + 3)
    style = (f'<style>.b{{fill:{LIGHT["ink"]}}}.h{{fill:{LIGHT["amber"]}}}'
             f'@media (prefers-color-scheme:dark){{.b{{fill:{DARK["ink"]}}}.h{{fill:{DARK["amber"]}}}}}</style>')
    d = BUBBLE + "".join(rr(*b, BAR_R) for b in BARS[:2])
    body = f'<path class="b" fill-rule="evenodd" d="{d}"/><path class="h" d="{rr(*BARS[2], BAR_R)}"/>'
    return svg_doc(vb, body, "Jak se máme", style)


# ---------------------------------------------------------------- build
def main():
    logo, fav = ROOT / "logo", ROOT / "favicon"
    logo.mkdir(exist_ok=True)
    fav.mkdir(exist_ok=True)
    files = {}

    files["jaksemame-symbol.svg"] = symbol_doc(LIGHT)
    files["jaksemame-symbol-inverse.svg"] = symbol_doc(DARK)
    files["jaksemame-symbol-mono-black.svg"] = symbol_doc(dict(LIGHT, ink="#000000"), mono=True)
    files["jaksemame-symbol-mono-white.svg"] = symbol_doc(dict(LIGHT, ink="#FFFFFF"), mono=True)
    files["jaksemame-logo.svg"] = lockup(LIGHT)
    files["jaksemame-logo-inverse.svg"] = lockup(DARK)
    files["jaksemame-logo-mono-black.svg"] = lockup(dict(LIGHT, ink="#000000"), mono=True)
    files["jaksemame-logo-mono-white.svg"] = lockup(dict(LIGHT, ink="#FFFFFF"), mono=True)
    files["jaksemame-wordmark.svg"] = lockup(LIGHT, symbol=False)
    for slug, name in OBCE:
        files[f"{slug}-logo.svg"] = lockup(LIGHT, name)
        files[f"{slug}-logo-inverse.svg"] = lockup(DARK, name)
        files[f"{slug}-logo-stacked.svg"] = lockup(LIGHT, name, stacked=True)
        files[f"{slug}-logo-stacked-inverse.svg"] = lockup(DARK, name, stacked=True)
    for fn, s in files.items():
        (logo / fn).write_text(s, encoding="utf-8")

    # webové varianty pro hlavičku portálu: barvy přes CSS třídy (přepínají se s tématem stránky)
    web = logo / "web"
    web.mkdir(exist_ok=True)
    WEB = dict(ink="#000001", obec="#000002", amber="#000003", muted="#000004")
    cls = {"#000001": "lg-i", "#000002": "lg-o", "#000003": "lg-a", "#000004": "lg-q"}

    def webify(svg):
        for col, c in cls.items():
            svg = svg.replace(f'fill="{col}"', f'class="{c}"')
        return svg.split("<title>")[0] + svg.split("</title>")[1]  # bez <title>, popisek nese odkaz

    (web / "jaksemame-header.svg").write_text(webify(lockup(WEB)), encoding="utf-8")
    (web / "symbol.svg").write_text(webify(symbol_doc(WEB)), encoding="utf-8")
    for slug, name in OBCE:
        (web / f"{slug}-header.svg").write_text(webify(lockup(WEB, name)), encoding="utf-8")

    (fav / "favicon.svg").write_text(favicon_svg(), encoding="utf-8")
    sizes = {n: render_symbol(n, LIGHT, scale=0.96) for n in (32, 48)}
    sizes[16] = render_pix16(LIGHT)
    sizes[16].save(fav / "favicon-16.png")
    sizes[32].save(fav / "favicon-32.png")
    sizes[48].save(fav / "favicon.ico", sizes=[(16, 16), (32, 32), (48, 48)],
                   append_images=[sizes[16], sizes[32]])
    render_symbol(180, DARK, bg=LIGHT["ink"], scale=0.62).save(fav / "apple-touch-icon.png")
    render_symbol(192, DARK, bg=LIGHT["ink"], scale=0.62, radius=0.22).save(fav / "icon-192.png")
    render_symbol(512, DARK, bg=LIGHT["ink"], scale=0.62, radius=0.22).save(fav / "icon-512.png")
    render_symbol(512, DARK, bg=LIGHT["ink"], scale=0.50).save(fav / "icon-maskable-512.png")
    (fav / "site.webmanifest").write_text(json.dumps({
        "name": "Jak se máme", "short_name": "Jak se máme",
        "icons": [
            {"src": "/icon-192.png", "sizes": "192x192", "type": "image/png"},
            {"src": "/icon-512.png", "sizes": "512x512", "type": "image/png"},
            {"src": "/icon-maskable-512.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable"},
        ],
        "theme_color": LIGHT["ink"], "background_color": LIGHT["bg"], "display": "browser",
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    write_preview(sorted(files), sorted(p.name for p in fav.iterdir()))
    print(f"{len(files)} SVG v brand/logo, favikony v brand/favicon, náhled brand/preview.html")


def write_preview(svgs, favs):
    def tile(fn):
        dark = "inverse" in fn or "white" in fn
        return (f'<figure class="{"d" if dark else "l"}"><img src="logo/{fn}" alt="{fn}">'
                f'<figcaption>{fn}</figcaption></figure>')
    fav_imgs = "".join(
        f'<figure class="l"><img src="favicon/{f}" alt="{f}" style="height:64px;width:auto;image-rendering:pixelated">'
        f'<figcaption>{f}</figcaption></figure>' for f in favs if f.endswith((".png", ".svg")))
    big16 = ('<figure class="l"><img src="favicon/favicon-16.png" style="width:128px;height:128px;'
             'image-rendering:pixelated" alt=""><figcaption>favicon-16 · zvětšeno 8×</figcaption></figure>'
             '<figure class="l"><img src="favicon/favicon-32.png" style="width:128px;height:128px;'
             'image-rendering:pixelated" alt=""><figcaption>favicon-32 · zvětšeno 4×</figcaption></figure>')
    html = f"""<!doctype html><meta charset="utf-8"><title>Jak se máme – soubory značky</title>
<style>body{{font:14px system-ui;margin:0;padding:24px;background:#E7ECEA;color:#142F3A}}
.g{{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:12px;margin-bottom:28px}}
figure{{margin:0;border-radius:10px;padding:22px;display:flex;flex-direction:column;gap:10px;align-items:center;justify-content:center}}
.l{{background:#fff}}.d{{background:#0D191E;color:#8FA4A7}}img{{max-width:100%;height:64px}}
figcaption{{font:12px ui-monospace,monospace}}</style>
<h2>Logo</h2><div class="g">{"".join(tile(f) for f in svgs)}</div>
<h2>Favikony</h2><div class="g">{big16}{fav_imgs}</div>"""
    (ROOT / "preview.html").write_text(html, encoding="utf-8")


if __name__ == "__main__":
    main()
