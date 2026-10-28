# -*- coding: utf-8 -*-
"""Data Střelic pro MCP server jaksemame.cz/mcp → mcp/strelice.sqlite (viz mcp_export.py).

Čte totéž co stránky portálu: datasety RO/ZO, přepisy diskuzí, shrnutí, rozpočet
z MONITORu a data vložená do investice.html a zakazky.html (běží až po jejich buildu)."""
import csv
import glob
import json
import os
import sys

import mcp_export as mx
import zastupitele as zs

OUT = "mcp/strelice.sqlite"


def embedded(path):
    """DATA vložená do vygenerované stránky (`const D=<json>`)."""
    s = open(path, encoding="utf-8").read()
    i = s.index("const D=") + len("const D=")
    return json.JSONDecoder().raw_decode(s, i)[0]


def load(path, default=None):
    return json.load(open(path, encoding="utf-8")) if os.path.exists(path) else default


def counts(b):
    h = b.get("hlasovani")
    return list(h) if isinstance(h, list) and len(h) == 3 else None


def named_votes(z, present):
    """Jmenovitá hlasování ze zápisu přiřazená k usnesením: hlasy jdou ve stejném pořadí,
    takže stačí posouvat ukazatel a párovat podle počtů pro/proti/zdržel."""
    vs = (zs.override_votes(z["cislo_zasedani"], present) if z["cislo_zasedani"] == 27
          else zs.votes(z, present)) or []
    out, j = {}, 0
    for i, b in enumerate(z["body"]):
        c = counts(b)
        if not c:
            continue
        for k in range(j, min(j + 4, len(vs))):
            if list(vs[k]["cnt"]) == c:
                v = vs[k]
                h = {o: "pro" for o in v["pro"]}
                h.update({o: "proti" for o in v["proti"]})
                h.update({o: "zdrzel" for o in v["zdrzel"]})
                for o in present:
                    h.setdefault(o, "nehlasoval")
                out[i] = h
                j = k + 1
                break
    return out


def main():
    inv = embedded("investice.html")
    ex = mx.Export(OUT, "strelice", "Střelice", "https://strelice.jaksemame.cz",
                   kod_obce="583910", ico="00282618", obyvatel=inv.get("pop"), okres="Brno-venkov",
                   sekce=["jednani_zo", "jednani_ro", "prepisy", "hlasovani", "rozpocet", "investice",
                          "zakazky", "vyberova_rizeni", "dotace"],
                   poznamky={
                       "jednani_ro": "Rada obce jedná neveřejně; zápisy obsahují jen rozhodnutí, ne diskuzi. "
                                     "Rada se podle zápisu shodla jednomyslně, není-li uvedeno jinak.",
                       "prepisy": "Přepisy diskuzí jsou z videozáznamů zastupitelstva, převedené do spisovné "
                                  "češtiny a zkrácené; nejsou doslovné. Občané jsou anonymní.",
                       "castky": "Částky u usnesení jsou automaticky vytažené z textu zápisu; u důležitých "
                                 "rozhodnutí je ověř v PDF.",
                       "zakazky": "Zakázky = usnesení RO a ZO s firmou a částkou. Dodatky se nepočítají jako "
                                  "nové zakázky, ale jejich částky jsou v součtech.",
                       "vyberova_rizeni": "Výběrová řízení z profilu zadavatele obce (E-zakázky): kdo podal nabídku, "
                                          "za kolik a kdo vyhrál. Ceny bez DPH, jak je obec zapsala na profil; "
                                          "stav obec na profilu nevede, je odvozený (zadáno = je vybraná firma). "
                                          "Menší zakázky zadané napřímo na profilu nejsou.",
                       "rozpocet": "Rozpočet z MONITORu MF (výkaz FIN 2-12 M, konsolidovaný); rok 2026 je "
                                   "průběžný stav k uvedenému měsíci.",
                       "autor": "Portál provozuje občan Střelic, který je zároveň zastupitelem (Radim Brener).",
                   })

    for k, jmeno, funkce in zs.MEMBERS:
        od, do = zs.TERM.get(k, (None, None))
        ex.osoba(k, jmeno, funkce, od, None if do == 999 else do)

    video = load("video_casy.json", {})
    zo_texty = {}  # číslo ZO → texty usnesení (k nim se váží přepisy)
    for organ, fn, shr in (("ZO", "dataset_ZO.json", "data/shrnuti/zo.json"),
                           ("RO", "dataset_RO.json", "data/shrnuti/ro.json")):
        shrnuti = load(shr, {})
        for z in json.load(open(fn, encoding="utf-8")):
            n = z["cislo_zasedani"]
            jid = f"{organ}-{n}"
            pres, omluv, hl = [], [], {}
            if organ == "ZO":
                pres, _ = zs.attendance(z)
                omluv = [zs.FULL[k] for k in zs.KEYS if zs.is_member(k, n) and k not in pres]
                hl = named_votes(z, pres)
                zo_texty[n] = [b["text"] for b in z["body"]]
            ex.jednani(jid, organ, cislo=n, rok=z["rok"], datum=z["datum"],
                       nazev=f"{n}. zasedání {'zastupitelstva' if organ == 'ZO' else 'rady'} obce Střelice",
                       url_pdf=z["url"], video=(video.get(str(n)) or {}).get("vid") if organ == "ZO" else None,
                       shrnuti=shrnuti.get(str(n)), pritomno=z.get("pritomno") or (len(pres) or None),
                       omluveni=omluv or None, pocet_usneseni=len(z["body"]))
            for i, b in enumerate(z["body"]):
                c = counts(b) or [None] * 3
                ex.usneseni(jid, i + 1, b["text"], hlasy=hl.get(i), kategorie=b.get("kategorie"),
                            tema=b.get("tema"), castka=mx.num(b.get("castka")),
                            pro=c[0], proti=c[1], zdrzel=c[2])

    for f in sorted(glob.glob("prepisy/[0-9]*.json"), key=lambda p: int(os.path.basename(p)[:-5])):
        p = json.load(open(f, encoding="utf-8"))
        n = p["cislo_zasedani"]
        texty = zo_texty.get(n, [])
        poradi = 0
        for b in p["body"]:
            # index = pořadí usnesení v zápisu (od 0), ke kterému diskuze patří — ne číslo bodu programu
            i = b["index"]
            nazev = mx.clean(texty[i]) if 0 <= i < len(texty) else None
            if nazev and len(nazev) > 110:
                nazev = nazev[:110].rsplit(" ", 1)[0] + "…"
            for t in b["turns"]:
                poradi += 1
                who = t["who"]
                ex.promluva(f"ZO-{n}", poradi, who, t["text"], bod=i + 1, bod_nazev=nazev,
                            role=t.get("role"), osoba=zs.SPEAKER.get(who) if t.get("role") != "o" else None,
                            cas=b.get("start"))

    for fn in ("data/strelice_finm201_2013_2025.csv", "data/strelice_fin_2026.csv"):
        for r in csv.DictReader(open(fn, encoding="utf-8-sig"), delimiter=";"):
            ob = r.get("obdobi") or "12"
            ex.rozpocet(rok=int(r["rok"]), obdobi=f'{r["rok"]}-{int(ob):02d}', granularita="polozka",
                        strana="prijmy" if r["druh"] == "Příjmy" else "vydaje", druh=r["trida"],
                        oblast=r["par_oddil"] if r["druh"] == "Výdaje" else None,
                        paragraf=r["paragraf"], paragraf_nazev=r["paragraf_nazev"],
                        polozka=r["polozka"], polozka_nazev=r["polozka_nazev"],
                        schvaleny=mx.num(r["schvaleny_rozpocet"]), upraveny=mx.num(r["upraveny_rozpocet"]),
                        skutecnost=mx.num(r["skutecnost"]))

    for rok, kap, vyd in zip(inv["years"], inv["kap"], inv["vyd"]):
        ex.kapitalove(rok, kap, vyd)
    # akce: [datum, částka, orgán, číslo jednání, text, url, zhotovitel, skupina, …]
    for a in inv["akce"]:
        ex.akce(a[4], datum=a[0], rok=int(a[0][:4]), castka=a[1], organ=a[2], jednani_id=f"{a[2]}-{a[3]}",
                skupina=a[7], zhotovitel=a[6] or None, url=a[5], zdroj="usnesení RO/ZO")

    # zakázky: [rok, firma, částka, datum, orgán, číslo jednání, url, text, dodatek]
    for r in embedded("zakazky.html")["rows"]:
        ex.zakazka(r[7], datum=r[3], rok=r[0], dodavatel=r[1], castka=r[2], organ=r[4],
                   jednani_id=f"{r[4]}-{r[5]}", dodatek=1 if r[8] else 0, url=r[6])

    # výběrová řízení z profilu zadavatele (scripts/fetch_profil_zakazky.py)
    for z in json.load(open("data/profil_zakazky.json", encoding="utf-8"))["zakazky"]:
        ex.rizeni(z["id"], z["nazev"], datum=z["datum"], rok=int(z["datum"][:4]), druh=z["druh"], postup="výjimka" if z["maly_rozsah"] else None, stav=z["stav"],
                  predpokladana_hodnota=z["predpokladana_hodnota"], lhuta=z["lhuta"] or None,
                  dodavatel=z["dodavatel"] or None, dodavatel_ico=z["dodavatel_ico"] or None, cena=z["cena"], url=z["url"],
                  nabidky=[dict(n, vybrana=bool(z["dodavatel_ico"]) and n["ico"] == z["dodavatel_ico"]) for n in z["nabidky"]])

    for r in csv.DictReader(open("data/dotace_strelice.csv", encoding="utf-8-sig"), delimiter=";"):
        ex.dotace(r["prijemce"], r["ucel"], rok=int(r["rok"]), castka=mx.num(r["castka"]),
                  url="https://strelice.jaksemame.cz/dotace.html?prijemce=" + r["prijemce"].replace(" ", "+"))

    meta = ex.close()
    print(OUT, {k: v for k, v in meta.items() if k.startswith("pocet_")})


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
