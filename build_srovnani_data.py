#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Extrahuje data pro sekci Srovnání: hospodaření Střelic a sousedních obcí
z celostátních extraktů MONITORu (FIN 2-12 M + Rozvaha) a počty obyvatel
z ČSÚ demografie okresu Brno-venkov. Výstup: data/srovnani_obce.json.

Metriky per obec × rok (skutečnost, Kč):
  prijmy, vydaje, saldo, kap (kapitálové výdaje), dan (daňové příjmy),
  ucty (stav na bankovních účtech k 31.12., FINM204),
  dluh (úvěry+dluhopisy+NFV+směnky dle fiskálního pravidla, Rozvaha),
  majetek (aktiva netto, Rozvaha), pop (obyvatel k 1. 1., ČSÚ)."""
import sys, io, csv, json, zipfile, os
from datetime import date
import xml.etree.ElementTree as ET

sys.stdout.reconfigure(encoding="utf-8")

YEARS = list(range(2013, 2026))
OBCE = {  # IČO -> název (ARES, právní forma 801, okres Brno-venkov)
    "00282618": "Střelice",
    "00282723": "Troubsko",
    "00282294": "Ostopovice",
    "00488232": "Omice",
    "00487520": "Radostice",
    "00488305": "Silůvky",
    "00282278": "Ořechov",
    "00282120": "Moravany",
    "00282952": "Želešice",
    "00282405": "Prštice",
}
# syntetické účty tvořící "dluh" dle pravidel rozpočtové odpovědnosti
# (úvěry, dluhopisy, návratné finanční výpomoci, směnky; zákon č. 23/2017 Sb.)
DLUH_SU = {"281", "282", "283", "289", "322", "326", "451", "452", "453", "457", "459"}

def num(s):
    s = (s or "").strip()
    if not s:
        return 0.0
    neg = s.endswith("-")
    try:
        v = float(s.rstrip("-"))
    except ValueError:
        return 0.0
    return -v if neg else v

# ---- třída položky (Daňové příjmy / Kapitálové výdaje ...) z číselníku ----
def load_codelist(path, code_field):
    recs = []
    for rec in list(ET.parse(path).getroot()):
        d = {ch.tag: (ch.text or "").strip() for ch in rec}
        def pd(s, default):
            try:
                y, m, dd = s.split("-"); return date(int(y), int(m), int(dd))
            except Exception:
                return default
        d["_start"] = pd(d.get("start_date", ""), date(1900, 1, 1))
        d["_end"] = pd(d.get("end_date", ""), date(9999, 12, 31))
        d["_code"] = d.get(code_field, "")
        recs.append(d)
    return recs

POL = load_codelist("data/ciselniky/polozka.xml", "polozka")
TRIDA = {}   # (polozka, rok) se nemění tak často — cache dle (kód, rok)
def trida(pol_code, year):
    key = (pol_code, year)
    if key not in TRIDA:
        ref = date(year, 12, 31)
        cands = [r for r in POL if r["_code"] == pol_code]
        hit = next((r for r in cands if r["_start"] <= ref <= r["_end"]), cands[-1] if cands else None)
        TRIDA[key] = (hit or {}).get("trida", "")
    return TRIDA[key]

PRIJ = {"Daňové příjmy", "Nedaňové příjmy", "Kapitálové příjmy", "Přijaté transfery"}
VYD = {"Běžné výdaje", "Kapitálové výdaje"}

# ---- obyvatelé z ČSÚ demografie okresu (Stav 1. 1.) ----
import openpyxl
pop = {}   # (nazev, rok) -> obyvatel
wb = openpyxl.load_workbook("data/skolstvi/cz0643_demografie.xlsx", read_only=True, data_only=True)
ws = wb["CZ0643"]
names = set(OBCE.values())
for row in ws.iter_rows(min_row=2, values_only=True):
    try:
        rok, nazev, stav = int(row[0]), str(row[2]).strip(), row[4]
    except (TypeError, ValueError):
        continue
    if nazev in names and stav is not None:
        pop[(nazev, rok)] = int(stav)
wb.close()
pop_max_rok = max(r for (_, r) in pop)
print(f"obyvatelé: {len(pop)} záznamů, do roku {pop_max_rok}")

# ---- hlavní průchod ----
out = {ico: {"nazev": nm, "roky": {}} for ico, nm in OBCE.items()}

for y in YEARS:
    zp = f"data/raw/FinM/{y}_12_FINM.zip"
    if not os.path.exists(zp):
        print(f"  !! chybí {zp}"); continue
    z = zipfile.ZipFile(zp)
    agg = {ico: {"prijmy": 0.0, "vydaje": 0.0, "kap": 0.0, "dan": 0.0, "ucty": 0.0,
                 "dluh": 0.0, "majetek": 0.0} for ico in OBCE}

    m201 = next(n for n in z.namelist() if "FINM201" in n.upper())
    with z.open(m201) as f:
        r = csv.reader(io.TextIOWrapper(f, encoding="utf-8", errors="replace"), delimiter=";")
        next(r, None)
        for c in r:
            if len(c) < 13 or c[4] not in OBCE:
                continue
            t = trida(c[9], y)
            skut = num(c[12])
            a = agg[c[4]]
            if t in PRIJ:
                a["prijmy"] += skut
                if t == "Daňové příjmy":
                    a["dan"] += skut
            elif t in VYD:
                a["vydaje"] += skut
                if t == "Kapitálové výdaje":
                    a["kap"] += skut

    m204 = next((n for n in z.namelist() if "FINM204" in n.upper()), None)
    if m204:
        with z.open(m204) as f:
            r = csv.reader(io.TextIOWrapper(f, encoding="utf-8", errors="replace"), delimiter=";")
            next(r, None)
            for c in r:
                if len(c) >= 11 and c[4] in OBCE:
                    agg[c[4]]["ucty"] += num(c[9])       # ZU_AKTZ = stav ke konci období

    rz = f"data/raw/Rozvaha/{y}_12_ROZV.zip"
    if os.path.exists(rz):
        zr = zipfile.ZipFile(rz)
        for member in zr.namelist():
            with zr.open(member) as f:
                r = csv.reader(io.TextIOWrapper(f, encoding="utf-8", errors="replace"), delimiter=";")
                next(r, None)
                for c in r:
                    if len(c) < 14 or c[4] not in OBCE:
                        continue
                    su, polvyk = c[9], c[8]
                    if su in DLUH_SU:
                        agg[c[4]]["dluh"] += num(c[12])   # pasiva: běžné období netto
                    elif polvyk == "A." and su == "-":
                        agg[c[4]]["majetek"] += num(c[12])  # aktiva celkem netto
    else:
        print(f"  !! chybí {rz} (dluh/majetek {y} = N/A)")

    for ico, a in agg.items():
        nm = OBCE[ico]
        a["saldo"] = a["prijmy"] - a["vydaje"]
        a["pop"] = pop.get((nm, y)) or pop.get((nm, pop_max_rok))
        out[ico]["roky"][y] = {k: round(v) for k, v in a.items()}
    print(f"  {y}: hotovo")

os.makedirs("data", exist_ok=True)
with open("data/srovnani_obce.json", "w", encoding="utf-8") as f:
    json.dump({"years": YEARS, "obce": out}, f, ensure_ascii=False, indent=1)
print("HOTOVO -> data/srovnani_obce.json")
