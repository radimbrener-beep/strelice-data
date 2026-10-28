#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Seznam položek pro upozornění → push/feed.json (spouští deploy.yml před nahráním).

Položky: jednání rady a zastupitelstva (z datasetů), nově vypsané zakázky (profil
zadavatele, data/profil_zakazky.json) a ručně ohlášené novinky portálu (data/push_novinky.json). Server (push/send.php) oznámí jen ty, které ještě neoznámil
a jsou novější než stav při zapnutí upozornění — viz push/lib/Send.php.

Novinka portálu = záznam v data/push_novinky.json:
    {"id": "volby-2026", "title": "…", "body": "…", "url": "/volby.html", "date": "2026-10-24"}
"""
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "push", "feed.json")
PER_TOPIC = 30


def load(path, default):
    p = os.path.join(HERE, path)
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else default


def meetings(dataset, shrnuti_path, topic, label, url):
    data = load(dataset, [])
    shrnuti = load(shrnuti_path, {})
    out = []
    for m in sorted(data, key=lambda m: m["datum"], reverse=True)[:PER_TOPIC]:
        c = m["cislo_zasedani"]
        body = shrnuti.get(str(c)) or f"Zápis z jednání: {len(m.get('body', []))} usnesení."
        out.append({
            "id": f"{topic}-{c}", "topic": topic,
            "title": f"{label} č. {c} · {m['datum_text']}",
            "body": body if len(body) <= 240 else body[:237].rsplit(" ", 1)[0] + "…",
            "url": url.format(c=c), "date": m["datum"],
        })
    return out


def tenders():
    """Nově vypsané zakázky z profilu zadavatele (data/profil_zakazky.json)."""
    out = []
    for z in load("data/profil_zakazky.json", {"zakazky": []})["zakazky"][:PER_TOPIC]:
        info = [z["druh"].capitalize()] if z.get("druh") else []
        if z.get("predpokladana_hodnota"):
            info.append(f"předpokládaná hodnota {z['predpokladana_hodnota']:,} Kč".replace(",", " "))
        if z.get("lhuta"):
            d, _, t = z["lhuta"].partition("T")
            y, m, dd = d.split("-")
            info.append(f"nabídky do {int(dd)}. {int(m)}. {y}" + (f" {t}" if t else ""))
        out.append({"id": "zakazka-" + z["id"], "topic": "zakazky",
                    "title": "Nová zakázka obce: " + z["nazev"],
                    "body": " · ".join(info) or "Obec vypsala novou zakázku na profilu zadavatele.",
                    "url": "/zakazky.html#vypsane", "date": z["datum"]})
    return out


def main():
    items = (meetings("dataset_RO.json", "data/shrnuti/ro.json", "rada", "Rada obce", "/zapisy.html?ro={c}")
             + meetings("dataset_ZO.json", "data/shrnuti/zo.json", "zastupitelstvo", "Zastupitelstvo", "/zastupitelstvo.html?zo={c}"))
    for n in load("data/push_novinky.json", []):
        items.append({"id": "portal-" + n["id"], "topic": "portal", "title": n["title"], "body": n.get("body", ""),
                      "url": n.get("url", "/"), "date": n["date"]})
    items += tenders()
    items.sort(key=lambda i: i["date"], reverse=True)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=1)
    by = {}
    for i in items:
        by[i["topic"]] = by.get(i["topic"], 0) + 1
    print(f"HOTOVO: push/feed.json — {len(items)} položek {by}, nejnovější: {items[0]['title'] if items else '—'}")


if __name__ == "__main__":
    main()
