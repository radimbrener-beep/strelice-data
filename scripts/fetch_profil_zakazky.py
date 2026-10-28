#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stáhne veřejné zakázky vypsané obcí Střelice z profilu zadavatele na E-zakázkách
a uloží je do data/profil_zakazky.json (sekce Vypsané zakázky na stránce Zakázky).

Zdroj: XML export profilu ve formátu MMR (vz-z-profilu-zadavatele v100) — název,
druh, nabídky (firma + cena), vybraný dodavatel a smluvní cena, dokumenty.
Předpokládanou hodnotu a lhůtu pro nabídky XML nemá → doplní se z HTML detailu
zakázky. Detail se stahuje jen pro nové a dosud probíhající zakázky (ostatní se berou
z minulého běhu).

Stav na profilu obec neaktualizuje (vše je „zahájen"), proto se odvozuje:
zadáno (je vybraný dodavatel) / zrušeno (dokument o zrušení) / probíhá (běží lhůta
nebo čeká na výběr) / bez výsledku (starší, výsledek na profilu chybí).

    python scripts/fetch_profil_zakazky.py
"""
import html
import json
import os
import re
import sys
import time
import urllib.request
import xml.etree.ElementTree as ET
from datetime import date, datetime

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "profil_zakazky.json")
PROFIL = "https://www.e-zakazky.cz/Profil-Zadavatele/c62ff3fd-035b-4804-850e-f63264638ee2"
OD = "01012019"
H = {"User-Agent": "Mozilla/5.0 (compatible; StrelicePortalBot/1.0)"}
# zakázka bez výsledku na profilu se po této době po konci lhůty nepovažuje za probíhající
CEKANI_DNU = 120


def get(url):
    req = urllib.request.Request(url, headers=H)
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def tag(e):
    return e.tag.split("}")[1]


def find(e, name):
    return [x for x in e.iter() if tag(x) == name]


def txt(e, name):
    x = find(e, name)
    return (x[0].text or "").strip() if x else ""


def num(s):
    try:
        v = float(s)
    except (TypeError, ValueError):
        return None
    return round(v) if v else None


def firma(subjekt):
    """Název firmy bez adresy sídla („IMOS Brno, a.s. sídlem Olomoucká…")."""
    n = re.sub(r"\s+", " ", txt(subjekt, "nazev_subjektu"))
    n = re.split(r",?\s+(?:sídlem|se sídlem|IČO?:?)\s", n)[0]
    n = re.split(r",\s+(?=[^,]*\d)", n)[0]   # „…, Nebovidská 12/39, 664 47 Střelice"
    return n.strip(" ,")


def ico(subjekt):
    return re.sub(r"\D", "", txt(subjekt, "ico"))


def detail(zid):
    """Předpokládaná hodnota a lhůta pro nabídky z HTML detailu zakázky."""
    s = get(f"{PROFIL}/Zakazka/{zid}").decode("utf-8", "ignore")

    def pole(label):
        m = re.search(r"<th>\s*" + label + r"\s*:?\s*</th>\s*<td>(.*?)</td>", s, re.S)
        return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", m.group(1)))).strip() if m else ""

    hod = pole("Předpokl&#225;dan&#225; hodnota VZ")
    hod = num(re.sub(r"[^\d,]", "", hod).replace(",", ".")) if hod else None
    konec = pole("Konec lhůty pro pod&#225;n&#237; nab&#237;dek")
    m = re.match(r"(\d\d)\.(\d\d)\.(\d{4})(?:\s+(\d\d:\d\d))?", konec)
    lhuta = f"{m.group(3)}-{m.group(2)}-{m.group(1)}" + (f"T{m.group(4)}" if m and m.group(4) else "") if m else ""
    return {"predpokladana_hodnota": hod, "lhuta": lhuta}


def stav(z, dnes):
    if z["dodavatel"]:
        return "zadáno"
    if z["zruseno"]:
        return "zrušeno"
    konec = date.fromisoformat((z.get("lhuta") or z["datum"])[:10])
    return "probíhá" if (dnes - konec).days <= CEKANI_DNU else "bez výsledku"


def main():
    old = {}
    if os.path.exists(OUT):
        old = {z["id"]: z for z in json.load(open(OUT, encoding="utf-8"))["zakazky"]}

    dnes = date.today()
    root = ET.fromstring(get(f"{PROFIL}/XMLdataVZ?od={OD}&do={dnes:%d%m%Y}"))
    out = []
    for zk in (c for c in root if tag(c) == "zakazka"):
        zid = txt(zk, "id_objektu")
        for cast in find(zk, "cast_zakazky"):
            nazev = txt(cast, "nazev_casti_vz") or txt(zk, "nazev_vz")
            nazev = re.sub(r"\s+", " ", nazev).strip(" „“\"")
            nabidky = [{"firma": firma(u), "ico": ico(u),
                        "cena": num(txt(u, "nabidkova_cena_bez_dph")),
                        "vyloucen": txt(u, "ucastnik_vyloucen") == "1" or txt(u, "ucastnik_odstoupil") == "1"}
                       for u in find(cast, "ucastnik")]
            vyb = find(cast, "vybrany_dodavatel")
            dok = [{"typ": txt(d, "jiny_dokument_nazev") or txt(d, "typ_dokumentu"),
                    "cas": txt(d, "cas_vlozeni_na_profil")[:10]} for d in find(cast, "dokument")]
            cena = num(txt(vyb[0], "smluvni_cena_bez_DPH")) if vyb else None
            if vyb and not cena:   # smluvní cenu obec často nevyplní → vítězná nabídka
                cena = next((n["cena"] for n in nabidky if n["ico"] and n["ico"] == ico(vyb[0])), None)
            z = {
                "id": zid if len(find(zk, "cast_zakazky")) == 1 else f"{zid}/{len([o for o in out if o['id'].startswith(zid)]) + 1}",
                "url": f"{PROFIL}/Zakazka/{zid}",
                "nazev": nazev,
                "druh": txt(cast, "druh_casti_vz") or txt(zk, "druh_vz"),
                "maly_rozsah": txt(cast, "druh_zadavaciho_postupu") == "výjimka",
                "datum": txt(cast, "datum_uverejneni")[:10],
                "nabidky": nabidky,
                "dodavatel": firma(vyb[0]) if vyb else "",
                "dodavatel_ico": ico(vyb[0]) if vyb else "",
                "cena": cena,
                "zruseno": any(re.search(r"zrušen", d["typ"], re.I) for d in dok),
                "smlouva": any(d["typ"] == "smlouva" for d in dok),
                "posledni_dokument": max((d["cas"] for d in dok), default=""),
            }
            prev = old.get(z["id"])
            # lhůta se může prodloužit jen u běžící zakázky — ostatní detaily se nemění
            if prev and "lhuta" in prev and prev.get("stav") != "probíhá":
                z.update(predpokladana_hodnota=prev.get("predpokladana_hodnota"), lhuta=prev.get("lhuta"))
            else:
                try:
                    z.update(detail(zid))
                    time.sleep(0.3)
                except Exception as e:   # výpadek detailu nevadí, zkusí se příště
                    print(f"  detail {zid} nedostupný: {e}")
                    z.update(predpokladana_hodnota=(prev or {}).get("predpokladana_hodnota"),
                             lhuta=(prev or {}).get("lhuta", ""))
            z["stav"] = stav(z, dnes)
            out.append(z)

    out.sort(key=lambda z: z["datum"], reverse=True)
    nove = [z for z in out if z["id"] not in old]
    json.dump({"profil": PROFIL, "zakazky": out}, open(OUT, "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(f"HOTOVO: {len(out)} zakázek z profilu zadavatele, nových {len(nove)}")
    for z in nove:
        print(f"  NOVÁ: {z['datum']} {z['nazev']}")


if __name__ == "__main__":
    main()
