"""Ilustrace obcí značky „jak se máme" (SVG): kopce, Střelice s kostelem, Ostopovice
se školou, cesta mezi nimi, okna, hvězdy a měsíc.

Používá ji FB grafika (build_infografika_jaksemame.py, formát 680×360, noční barvy
napevno) i rozcestník jaksemame.cz (build_jaksemame.py): `wide=True` protáhne kopce
a oblohu do stran, `themed=True` místo barev vypíše CSS třídy `sk-*` — stránka pak
ve scene_css() přepíná denní (světlý režim) a noční (tmavý režim) paletu.
"""
import random

AMBER = "#f4b547"

# noční paleta (FB grafika i tmavý režim webu)
NIGHT = {
    "star": "#e4eeec", "moon": "#e4eeec", "hill1": "#183842", "hill2": "#132e37",
    "road": "#2b4d57", "dash": AMBER, "trunk": "#1c3a44", "tree": "#1f4a4f",
    "house": "#21444f", "roof": "#2e5a67", "win": "#2c5562", "lit": AMBER,
    "tower": "#27505c", "spire": "#33626f", "pole": "#4b7c88", "flag": AMBER,
}
# denní paleta (světlý režim webu): pastelové kopce, světlé domy, slunce
DAY = {
    "star": "transparent", "moon": "#f4c561", "hill1": "#cfe4df", "hill2": "#b7d5ce",
    "road": "#e8eeec", "dash": "#e6a93a", "trunk": "#7e9d93", "tree": "#93c2ac",
    "house": "#f7faf9", "roof": "#6fa7ad", "win": "#a9cfd6", "lit": "#efa42a",
    "tower": "#eef4f2", "spire": "#4f8f95", "pole": "#58696e", "flag": "#efa42a",
}
BG_HILL = NIGHT["hill2"]  # spodní okraj noční ilustrace (navazuje patička)


def _css_palette(pal):
    rules = []
    for k, v in pal.items():
        prop = "stroke" if k in ("road", "dash", "pole") else "fill"
        rules.append(f".sk-{k}{{{prop}:{v}}}")
    return "".join(rules)


# CSS pro `themed=True`: světlý režim = den, tmavý režim = noc
def scene_css(dark_selector='html[data-theme="dark"]'):
    """CSS pro `themed=True`: výchozí denní paleta, pod `dark_selector` noční."""
    night = "".join(f"{dark_selector} {r}}}" for r in _css_palette(NIGHT).split("}") if r)
    return _css_palette(DAY) + night


class _Paint:
    """Barvy buď napevno (FB grafika), nebo jako CSS třídy (web)."""

    def __init__(self, themed):
        self.themed = themed

    def fill(self, key):
        return f'class="sk-{key}"' if self.themed else f'fill="{NIGHT[key]}"'

    def stroke(self, key):
        return f'class="sk-{key}"' if self.themed else f'stroke="{NIGHT[key]}"'


def house(x, base, w, h, rng, p, lit=0.45):
    """Domek se sedlovou střechou a okny (část rozsvícená jantarem)."""
    r = h * 0.55
    s = (f'<rect x="{x}" y="{base - h}" width="{w}" height="{h}" {p.fill("house")}/>'
         f'<polygon points="{x - 4},{base - h} {x + w / 2},{base - h - r} {x + w + 4},{base - h}" {p.fill("roof")}/>')
    cols = max(1, int(w // 16))
    gap = (w - cols * 7) / (cols + 1)
    for c in range(cols):
        wx = x + gap + c * (7 + gap)
        key = "lit" if rng.random() < lit else "win"
        s += f'<rect x="{wx:.1f}" y="{base - h * 0.62:.1f}" width="7" height="9" rx="1.5" {p.fill(key)}/>'
    return s


def village(cx, base, rng, p, church=False, school=False, n=7):
    s, x = "", cx - n * 15
    for i in range(n):
        w = rng.choice([30, 34, 38, 44])
        h = rng.choice([26, 30, 34])
        if church and i == n // 2:          # kostel se špičatou věží (Střelice)
            s += f'<rect x="{x}" y="{base - 62}" width="20" height="62" {p.fill("tower")}/>'
            s += f'<polygon points="{x - 2},{base - 62} {x + 10},{base - 104} {x + 22},{base - 62}" {p.fill("spire")}/>'
            s += f'<rect x="{x + 7}" y="{base - 50}" width="6" height="10" rx="3" {p.fill("lit")}/>'
            x += 26
        if school and i == 1:               # škola s praporkem (Ostopovice — nová škola)
            s += f'<rect x="{x}" y="{base - 40}" width="62" height="40" {p.fill("tower")}/>'
            s += f'<polygon points="{x - 4},{base - 40} {x + 31},{base - 58} {x + 66},{base - 40}" {p.fill("spire")}/>'
            for k in range(4):
                s += (f'<rect x="{x + 8 + k * 13}" y="{base - 28}" width="8" height="10" rx="1.5" '
                      f'{p.fill("lit" if k % 2 == 0 else "win")}/>')
            s += f'<line x1="{x + 31}" y1="{base - 58}" x2="{x + 31}" y2="{base - 80}" {p.stroke("pole")} stroke-width="2"/>'
            s += f'<polygon points="{x + 31},{base - 80} {x + 46},{base - 75} {x + 31},{base - 70}" {p.fill("flag")}/>'
            x += 70
        s += house(x, base, w, h, rng, p)
        x += w + rng.choice([6, 9, 12])
    return s


def trees(xs, base, rng, p):
    s = ""
    for x in xs:
        r = rng.choice([11, 13, 15])
        s += f'<rect x="{x - 2}" y="{base - 14}" width="4" height="14" {p.fill("trunk")}/>'
        s += f'<circle cx="{x}" cy="{base - 14 - r * 0.8}" r="{r}" {p.fill("tree")}/>'
    return s


def scene(wide=False, preserve="xMidYMax meet", themed=False):
    """SVG scény. Základ má viewBox 680×360; `wide` ho rozšíří na -300…980."""
    p = _Paint(themed)
    rng = random.Random(7)
    x0, x1 = (-300, 980) if wide else (0, 680)
    s = (f'<svg viewBox="{x0} 0 {x1 - x0} 360" xmlns="http://www.w3.org/2000/svg" '
         f'preserveAspectRatio="{preserve}" aria-hidden="true">')
    for _ in range(26):
        s += (f'<circle cx="{rng.uniform(20, 660):.0f}" cy="{rng.uniform(8, 120):.0f}" r="{rng.choice([1, 1.2, 1.6])}" '
              f'{p.fill("star")} opacity="{rng.uniform(.25, .6):.2f}"/>')
    s += f'<circle cx="590" cy="44" r="15" {p.fill("moon")} opacity=".9"/>'
    if wide:                                # hvězdy i do bočních pruhů
        side = random.Random(11)
        for _ in range(26):
            cx = side.choice([side.uniform(-290, 10), side.uniform(670, 970)])
            s += (f'<circle cx="{cx:.0f}" cy="{side.uniform(8, 150):.0f}" r="{side.choice([1, 1.2, 1.6])}" '
                  f'{p.fill("star")} opacity="{side.uniform(.25, .6):.2f}"/>')
    s += '<g transform="translate(0 60)">'
    if wide:
        s += ('<path d="M-300 185 C -200 175, -80 165, 0 170 C 140 120, 260 150, 360 135 S 560 110, 680 150 '
              f'C 780 170, 880 160, 980 172 L980 300 L-300 300Z" {p.fill("hill1")}/>')
        s += ('<path d="M-300 232 C -180 222, -60 230, 0 225 C 160 190, 330 215, 440 200 S 600 185, 680 205 '
              f'C 800 222, 900 214, 980 220 L980 300 L-300 300Z" {p.fill("hill2")}/>')
    else:
        s += f'<path d="M0 170 C 140 120, 260 150, 360 135 S 560 110, 680 150 L680 300 L0 300Z" {p.fill("hill1")}/>'
        s += f'<path d="M0 225 C 160 190, 330 215, 440 200 S 600 185, 680 205 L680 300 L0 300Z" {p.fill("hill2")}/>'
    # cesta mezi obcemi
    s += f'<path d="M150 300 C 250 250, 400 250, 520 230" {p.stroke("road")} stroke-width="16" fill="none" stroke-linecap="round"/>'
    s += (f'<path d="M150 300 C 250 250, 400 250, 520 230" {p.stroke("dash")} stroke-opacity=".55" stroke-width="2" '
          'stroke-dasharray="10 10" fill="none"/>')
    s += trees([40, 66, 262, 300, 420, 640], 214, rng, p)
    if wide:
        s += trees([-240, -205, -120, 740, 790, 900], 222, random.Random(5), p)
    s += village(170, 218, rng, p, church=True, n=6)      # Střelice
    s += village(540, 200, rng, p, school=True, n=4)      # Ostopovice
    s += '</g></svg>'
    return s
