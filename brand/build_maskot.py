#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Maskot portálu (robůtek s hlavou-grafem) → maskot/01-…10-*.svg.

Předloha je maskot/maskot.svg (dodaná grafika). Tělo, hlava, anténa a obličej se tu
skládají z jejích přesných tvarů a souřadnic; varianty mění jen ruce, výraz obličeje
(oči na třech sloupcích) a přidávají rekvizity. Barvy výhradně z palety značky,
flat, průhledné pozadí. Spuštění: python brand/build_maskot.py
"""
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "maskot"
INK, PET, AMB, PAP, SOFT, WH = "#142F3A", "#1D6B73", "#EFA42A", "#F2F5F4", "#8FD0D4", "#FFFFFF"

# --- díly předlohy (souřadnice beze změny) ---
SHADOW = f'<ellipse cx="204" cy="370" rx="96" ry="11" fill="{SOFT}" opacity=".22"/>'
LEGS = (f'<path d="M171 324v30M231 324v30" stroke="{INK}" stroke-width="16" stroke-linecap="round"/>'
        f'<rect x="146" y="348" width="51" height="24" rx="12" fill="{PET}" stroke="{INK}" stroke-width="5"/>'
        f'<rect x="206" y="348" width="51" height="24" rx="12" fill="{PET}" stroke="{INK}" stroke-width="5"/>')
BODY = (f'<rect x="149" y="222" width="109" height="119" rx="39" fill="{INK}"/>'
        f'<rect x="157" y="229" width="94" height="103" rx="32" fill="{WH}"/>'
        f'<circle cx="205" cy="280" r="16" fill="{PET}"/><circle cx="205" cy="280" r="8" fill="{AMB}"/>')
ANTENNA = (f'<rect x="134" y="66" width="24" height="40" rx="8" fill="{INK}"/>'
           f'<rect x="174" y="48" width="26" height="58" rx="9" fill="{PET}"/>'
           f'<rect x="215" y="29" width="29" height="77" rx="10" fill="{AMB}"/>')
HEAD = (f'<rect x="79" y="89" width="251" height="157" rx="49" fill="{INK}"/>'
        f'<rect x="93" y="101" width="223" height="129" rx="38" fill="{WH}"/>')
BARS = (f'<rect x="130" y="172" width="38" height="41" rx="9" fill="{INK}"/>'
        f'<rect x="175" y="151" width="38" height="62" rx="9" fill="{PET}"/>'
        f'<rect x="220" y="126" width="41" height="87" rx="9" fill="{AMB}"/>')
EARS = f'<circle cx="84" cy="168" r="8" fill="{PET}"/><circle cx="326" cy="168" r="8" fill="{PET}"/>'
WAVES = (f'<g fill="none" stroke="{AMB}" stroke-width="7" stroke-linecap="round">'
         '<path d="M332 142l9-14M345 160l20-3M325 127l-2-17"/></g>')

# středy očí na sloupcích (z oblouků předlohy)
EYES = [(149, 193), (194, 184), (240.5, 172)]


def face(expr):
    """Oči na třech sloupcích grafu. Výrazy: happy (předloha), open, look, think, wow, confused."""
    g = f'<g fill="none" stroke="{WH}" stroke-width="4.7" stroke-linecap="round">'
    if expr == "happy":
        return BARS + g + '<path d="M140 191q9 15 18 0"/><path d="M185 182q9 15 18 0"/><path d="M231.5 170q9 15 18 0"/></g>'
    if expr == "open":
        return BARS + "".join(f'<circle cx="{x}" cy="{y}" r="6" fill="{WH}"/>' for x, y in EYES)
    if expr == "look":                      # dívá se doprava (ukazuje na něco)
        return BARS + "".join(f'<circle cx="{x + 5}" cy="{y - 2}" r="6" fill="{WH}"/>' for x, y in EYES)
    if expr == "lookl":                     # dívá se doleva
        return BARS + "".join(f'<circle cx="{x - 5}" cy="{y - 2}" r="6" fill="{WH}"/>' for x, y in EYES)
    if expr == "think":                     # oči nahoru doprava + rovná „pusa" pod nimi
        return (BARS + "".join(f'<circle cx="{x + 4}" cy="{y - 6}" r="5.5" fill="{WH}"/>' for x, y in EYES)
                + g + "".join(f'<path d="M{x - 6} {y + 9}h12"/>' for x, y in EYES) + '</g>')
    if expr == "wow":
        return BARS + g + "".join(f'<circle cx="{x}" cy="{y}" r="7"/>' for x, y in EYES) + '</g>'
    if expr == "confused":                  # každé oko jinak
        (x1, y1), (x2, y2), (x3, y3) = EYES
        return (BARS + f'<circle cx="{x1}" cy="{y1}" r="5" fill="{WH}"/>' + g
                + f'<path d="M{x2 - 8} {y2}h16"/><circle cx="{x3}" cy="{y3}" r="7.5"/></g>')
    raise ValueError(expr)


def arm(d):
    """Paže jako v předloze: tmavý obrys + světle tyrkysová výplň."""
    return (f'<path d="{d}" fill="none" stroke="{INK}" stroke-width="28" stroke-linecap="round"/>'
            f'<path d="{d}" fill="none" stroke="{SOFT}" stroke-width="17" stroke-linecap="round"/>')


def fist(x, y, tx, ty):
    return f'<circle cx="{x}" cy="{y}" r="19" fill="{PET}"/><circle cx="{tx}" cy="{ty}" r="10" fill="{PET}"/>'


def pointer(x, y, fx, fy):
    """Ruka s nataženým prstem směrem (fx, fy)."""
    return (f'<path d="M{x} {y}L{fx} {fy}" stroke="{PET}" stroke-width="13" stroke-linecap="round"/>'
            f'<circle cx="{x}" cy="{y}" r="18" fill="{PET}"/>')


# ruce
L_DOWN = arm("M154 265Q118.5 279 103 319") + fist(103, 319, 91, 307)
R_WAVE = (arm("M257 265Q293.5 229 310 219")
          + f'<rect x="293" y="201" width="34" height="37" rx="15" fill="{PET}" stroke="{INK}" stroke-width="4"/>'
          + f'<rect x="319" y="194" width="11" height="19" rx="5" fill="{PET}"/>')
R_POINT = arm("M257 265Q298 262 334 240") + pointer(334, 240, 362, 226)
L_POINT = arm("M154 265Q113 262 77 240") + pointer(77, 240, 49, 226)
# držení předmětu před tělem: paže zvlášť (za tělem), dlaně až přes předmět
L_HOLD_ARM, R_HOLD_ARM = arm("M154 268Q126 280 137 300"), arm("M257 268Q285 280 273 300")
HOLD_HANDS = f'<circle cx="137" cy="300" r="15" fill="{PET}"/><circle cx="273" cy="300" r="15" fill="{PET}"/>'


def board(x, y, w, h, inner):
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="16" fill="{WH}" stroke="{INK}" stroke-width="7"/>'
            + inner)


def bar_chart(x, y, w, h, vals, colors):
    """Sloupcový graf v obdélníku (x, y, w, h), hodnoty 0–1."""
    n = len(vals)
    gap = w * 0.12
    bw = (w - gap * (n + 1)) / n
    s = f'<path d="M{x} {y + h}h{w}" stroke="{INK}" stroke-width="5" stroke-linecap="round"/>'
    for i, (v, c) in enumerate(zip(vals, colors)):
        bh = h * v
        s += (f'<rect x="{x + gap + i * (bw + gap):.1f}" y="{y + h - bh:.1f}" width="{bw:.1f}" height="{bh:.1f}" '
              f'rx="5" fill="{c}"/>')
    return s


def pin(x, y, s=1.0):
    """Jantarový špendlík s hrotem v bodě (x, y)."""
    return (f'<g transform="translate({x} {y}) scale({s})"><path d="M0 0C-6-12-17-20-17-33a17 17 0 0 1 34 0C17-20 6-12 0 0Z" '
            f'fill="{AMB}" stroke="{INK}" stroke-width="4" stroke-linejoin="round"/>'
            f'<circle cx="0" cy="-33" r="6.5" fill="{WH}"/></g>')


def mini_map(x, y, w, h, pin_at=None):
    """Plánek: papír, silnice, park, domky; volitelný špendlík."""
    s = (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="14" fill="{PAP}" stroke="{INK}" stroke-width="6"/>'
         f'<path d="M{x + w * .58} {y + 6}C{x + w * .5} {y + h * .4},{x + w * .66} {y + h * .6},{x + w * .54} {y + h - 6}" '
         f'fill="none" stroke="{WH}" stroke-width="{max(8, w * .07):.0f}" stroke-linecap="round"/>'
         f'<path d="M{x + 6} {y + h * .62}C{x + w * .35} {y + h * .55},{x + w * .7} {y + h * .7},{x + w - 6} {y + h * .6}" '
         f'fill="none" stroke="{WH}" stroke-width="{max(7, w * .06):.0f}" stroke-linecap="round"/>'
         f'<ellipse cx="{x + w * .25}" cy="{y + h * .3}" rx="{w * .14}" ry="{h * .14}" fill="{SOFT}"/>'
         f'<rect x="{x + w * .72}" y="{y + h * .16}" width="{w * .14}" height="{h * .14}" rx="3" fill="{PET}"/>'
         f'<rect x="{x + w * .14}" y="{y + h * .74}" width="{w * .14}" height="{h * .12}" rx="3" fill="{PET}"/>')
    if pin_at:
        s += pin(*pin_at)
    return s


def svg(content, vb="0 0 400 400", label="Maskot Jak se máme"):
    x, y, w, h = vb.split()
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="{vb}" role="img" '
            f'aria-label="{label}">{content}</svg>\n')


def robot(expr="happy", arms_back="", front="", hands="", extra=""):
    """Celý robot ve stejném pořadí vrstev jako předloha; `front` = rekvizita před tělem."""
    return (SHADOW + LEGS + arms_back + BODY + ANTENNA + HEAD + face(expr) + EARS + front + hands + extra)


def question(x, y, s=1.0):
    return (f'<g transform="translate({x} {y}) scale({s})" fill="none" stroke="{AMB}" stroke-width="9" stroke-linecap="round">'
            '<path d="M-12-14a12 12 0 1 1 18 10c-5 3-6 5-6 11"/></g>'
            f'<circle cx="{x}" cy="{y + 22 * s}" r="{5 * s}" fill="{AMB}"/>')


def build():
    v = {}
    # 1 uvítání = předloha
    v["01-uvitani"] = svg(robot("happy", L_DOWN + R_WAVE, extra=WAVES), label="Robot mává a vítá")

    # 2 rozpočet: ukazuje na sloupcový graf vpravo
    chart = board(372, 140, 150, 140, bar_chart(390, 165, 114, 92, [.38, .55, .48, .82], [INK, PET, PET, AMB]))
    v["02-rozpocet"] = svg(robot("look", L_DOWN + R_POINT, extra=chart), "0 0 540 400", "Robot ukazuje na graf")

    # 3 moje ulice: drží plánek s označeným místem
    mp = mini_map(132, 248, 146, 92, pin_at=(214, 300))
    v["03-moje-ulice"] = svg(robot("happy", L_HOLD_ARM + R_HOLD_ARM, front=mp, hands=HOLD_HANDS),
                             label="Robot drží mapu s označeným místem")

    # 4 žádné výsledky: zamyšlený s lupou
    lupa = (arm("M257 265Q306 262 336 236")
            + f'<path d="M336 236L362 196" stroke="{INK}" stroke-width="11" stroke-linecap="round"/>'
            + f'<circle cx="336" cy="236" r="18" fill="{PET}"/>'
            + f'<circle cx="378" cy="166" r="30" fill="{WH}" stroke="{INK}" stroke-width="8"/>'
            + f'<path d="M362 156a18 18 0 0 1 16-11" fill="none" stroke="{SOFT}" stroke-width="6" stroke-linecap="round"/>')
    dots = "".join(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{AMB}"/>' for x, y, r in [(60, 120, 6), (44, 98, 8), (24, 70, 10)])
    v["04-zadne-vysledky"] = svg(robot("think", L_DOWN + lupa, extra=dots), "0 0 430 400", "Zamyšlený robot s lupou")

    # 5 hlasování: dokument s výsledky (pro / proti / zdržel se jako proužky)
    doc = (f'<rect x="138" y="240" width="134" height="104" rx="10" fill="{WH}" stroke="{INK}" stroke-width="6"/>'
           f'<path d="M156 258h62" stroke="{INK}" stroke-width="6" stroke-linecap="round"/>'
           f'<path d="M154 281l6 6 11-12" fill="none" stroke="{PET}" stroke-width="5" stroke-linecap="round" stroke-linejoin="round"/>'
           f'<rect x="180" y="276" width="74" height="10" rx="5" fill="{PET}"/>'
           f'<path d="M155 300l12 12M167 300l-12 12" stroke="{INK}" stroke-width="5" stroke-linecap="round"/>'
           f'<rect x="180" y="301" width="26" height="10" rx="5" fill="{INK}"/>'
           f'<circle cx="161" cy="330" r="6" fill="none" stroke="{AMB}" stroke-width="5"/>'
           f'<rect x="180" y="325" width="14" height="10" rx="5" fill="{AMB}"/>')
    v["05-hlasovani"] = svg(robot("open", L_HOLD_ARM + R_HOLD_ARM, front=doc, hands=HOLD_HANDS),
                            label="Robot drží dokument s výsledky hlasování")

    # 6 investice: ukazuje na místo v mapě
    mapa = mini_map(372, 128, 156, 150, pin_at=(452, 214))
    v["06-investice"] = svg(robot("look", L_DOWN + R_POINT, extra=mapa), "0 0 540 400", "Robot ukazuje na investici v mapě")

    # 7 srovnání obcí: dva grafy po stranách, robot ukazuje oběma rukama
    left = board(14, 140, 140, 130, bar_chart(30, 162, 108, 86, [.45, .6, .72], [INK, PET, AMB]))
    right = board(526, 140, 140, 130, bar_chart(542, 162, 108, 86, [.62, .5, .4], [INK, PET, AMB]))
    shift = '<g transform="translate(136 0)">' + robot("open", L_POINT + R_POINT) + '</g>'
    v["07-srovnani-obci"] = svg(left + right + shift, "0 0 680 400", "Robot vysvětluje srovnání dvou grafů")

    # 8 upozornění: drží obálku
    env = (f'<rect x="140" y="250" width="130" height="86" rx="10" fill="{WH}" stroke="{INK}" stroke-width="6"/>'
           f'<path d="M144 256l61 42 61-42" fill="none" stroke="{INK}" stroke-width="6" stroke-linejoin="round" stroke-linecap="round"/>'
           f'<circle cx="266" cy="252" r="15" fill="{AMB}" stroke="{INK}" stroke-width="5"/>')
    v["08-upozorneni"] = svg(robot("happy", L_HOLD_ARM + R_HOLD_ARM, front=env, hands=HOLD_HANDS),
                             label="Robot drží obálku")

    # 9 404: zmatený, drží mapu nakřivo a drbe se na hlavě
    scratch = arm("M154 262Q98 262 94 212") + fist(94, 212, 104, 198)
    holdmap = (arm("M257 268Q296 290 318 296")
               + f'<g transform="rotate(14 362 300)">{mini_map(318, 252, 96, 92)}</g>'
               + f'<circle cx="318" cy="296" r="18" fill="{PET}"/>')
    v["09-404"] = svg(robot("confused", scratch + holdmap, extra=question(40, 70, 1.4)), "0 0 420 400",
                      "Zmatený robot s mapou")

    # 10 hlava pro malé nápovědy
    v["10-hlava-mini"] = svg(ANTENNA + HEAD + face("happy") + EARS, "68 22 274 232", "Robot Jak se máme")
    return v


def main():
    OUT.mkdir(exist_ok=True)
    for name, s in build().items():
        (OUT / f"{name}.svg").write_text(s, encoding="utf-8")
    print(f"HOTOVO: {len(build())} SVG v {OUT.name}/")


if __name__ == "__main__":
    main()
