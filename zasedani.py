# -*- coding: utf-8 -*-
"""Klíč zasedání ZO a jednání RO napříč volebními obdobími.

Obec čísluje zasedání v každém volebním období znovu od 1 (ustavující zasedání
2026–2030 bylo 6. 11. 2026). Portál proto zasedání nepoznává jen podle čísla:

  * období 2022–2026 (první, které portál má) si nechává holé číslo: „29“
    → staré odkazy zastupitelstvo.html?zo=29, id upozornění „zastupitelstvo-29“,
    MCP „ZO-29“, prepisy/29.json, řádky map.txt i klíče shrnutí platí dál;
  * každé další období má klíč „<rok začátku>-<číslo>“: „2026-1“
    (stejný tvar jako portál Ostopovic, MCP id „ZO-2026-1“).

Období se bere z pole `obdobi` záznamu (zapisuje ho scripts/update_portal.py podle
podstránky webu obce), u starších záznamů bez něj z data zasedání."""

LEGACY = "2022-2026"
# den ustavujícího zasedání = začátek období (první jednání rady bývá o pár dní později)
ZACATKY = {"2022-2026": "2022-10-19", "2026-2030": "2026-11-06"}


def obdobi(m):
    """Volební období záznamu datasetu („2022-2026“)."""
    if m.get("obdobi"):
        return m["obdobi"]
    d = m.get("datum") or ""
    o = LEGACY
    for ob, zac in sorted(ZACATKY.items(), key=lambda x: x[1]):
        if d >= zac:
            o = ob
    return o


def key_for(cislo, ob):
    return str(cislo) if ob == LEGACY else f"{ob[:4]}-{cislo}"


def key(m):
    """Klíč zasedání: „29“ (2022–2026), „2026-1“ (další období)."""
    return key_for(m["cislo_zasedani"], obdobi(m))


def parse_key(k):
    """„29“ → ("2022-2026", 29); „2026-1“ → ("2026-2030", 1)."""
    k = str(k)
    if "-" in k:
        y, c = k.split("-", 1)
        return f"{y}-{int(y) + 4}", int(c)
    return LEGACY, int(k)


def key_sort(k):
    """Řazení klíčů chronologicky (období, číslo)."""
    return parse_key(k)


def sort_key(m):
    return (obdobi(m), m["cislo_zasedani"])


def rozsah(ob):
    """(od, do) data jednání období: do = začátek dalšího známého období (None = trvá)."""
    zac = ZACATKY.get(ob) or f"{ob[:4]}-10-01"
    dals = sorted(d for d in ZACATKY.values() if d > zac)
    return zac, (dals[0] if dals else None)


def v_obdobi(datum, ob):
    od, do = rozsah(ob)
    return bool(datum) and datum >= od and (do is None or datum < do)


def label(ob):
    """„2022-2026“ → „2022–2026“."""
    return ob.replace("-", "–")


def obdobi_text(obd):
    """Do věty: „z volebního období 2022–2026“ / „z volebních období 2022–2026 a 2026–2030“."""
    obd = [label(o) for o in sorted(obd)]
    if len(obd) == 1:
        return f"z volebního období {obd[0]}"
    return "z volebních období " + ", ".join(obd[:-1]) + " a " + obd[-1]


def nazev(m, organ="ZO"):
    """Krátký popisek pro texty: „ZO 29“, „ZO 1 (2026–2030)“."""
    ob = obdobi(m)
    s = f"{organ} {m['cislo_zasedani']}"
    return s if ob == LEGACY else f"{s} ({label(ob)})"
