#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Průběžné plnění rozpočtu obce Střelice v aktuálním roce (2026).

Od roku 2026 publikuje MONITOR FIN 2-12 M v novém extraktu `FinM2026`
(nová rozpočtová skladba; soubor FINM01_UJ = příjmy/výdaje za účetní jednotky).
Skript najde nejnovější dostupný měsíc, vytáhne řádky Střelic (IČO 00282618),
dekóduje paragraf/položku a uloží `data/strelice_fin_2026.csv` (stejné sloupce
jako roční dataset 2013–2025 + sloupec `obdobi`).

Použití: python build_fin2026.py   (stáhne ~25 MB zip do data/raw/FinM2026/)
"""
import sys, os, io, csv, zipfile, subprocess, json
import xml.etree.ElementTree as ET
from datetime import date

sys.stdout.reconfigure(encoding="utf-8")
ICO = "00282618"
YEAR = 2026
BASE = "https://monitor.statnipokladna.gov.cz/data/extrakty/csv/FinM2026"
RAW = "data/raw/FinM2026"
OUT = "data/strelice_fin_2026.csv"
os.makedirs(RAW, exist_ok=True)


def dl(url, dest):
    if os.path.exists(dest) and os.path.getsize(dest) > 1000:
        return True
    r = subprocess.run(["curl", "-s", "-f", "-m", "600", "-A", "research/1.0", "-o", dest, url])
    ok = r.returncode == 0 and os.path.exists(dest) and os.path.getsize(dest) > 1000
    if not ok and os.path.exists(dest):
        os.remove(dest)
    return ok


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


def lookup(recs, code, fields):
    ref = date(YEAR, 6, 30)
    cands = [r for r in recs if r["_code"] == code]
    hit = next((r for r in cands if r["_start"] <= ref <= r["_end"]), None) or (cands[-1] if cands else None)
    return {f: (hit.get(f, "") if hit else "") for f in fields}


# číselníky: aktuální verze (obsahuje položky nové skladby 2026)
for f in ("polozka", "paragraf"):
    p = f"data/ciselniky/{f}.xml"
    subprocess.run(["curl", "-s", "-f", "-m", "120", "-A", "research/1.0", "-o", p + ".new",
                    f"https://monitor.statnipokladna.gov.cz/data/xml/{f}.xml"])
    if os.path.exists(p + ".new") and os.path.getsize(p + ".new") > 100000:
        os.replace(p + ".new", p)
    elif os.path.exists(p + ".new"):
        os.remove(p + ".new")
POL = load_codelist("data/ciselniky/polozka.xml", "polozka")
PAR = load_codelist("data/ciselniky/paragraf.xml", "paragraf")

# nejnovější dostupný měsíc
zp = month = None
for m in range(12, 0, -1):
    cand = f"{RAW}/{YEAR}_{m:02d}_FINM{YEAR}.zip"
    if dl(f"{BASE}/{YEAR}_{m:02d}_Data_CSUIS_FINM{YEAR}.zip", cand):
        zp, month = cand, m
        break
if not zp:
    sys.exit("Žádný extrakt FinM2026 není dostupný.")
print(f"extrakt {YEAR}/{month:02d}: {zp}")

z = zipfile.ZipFile(zp)
member = next(n for n in z.namelist() if n.upper().startswith("FINM01_UJ"))
rows = []
with z.open(member) as f:
    r = csv.reader(io.TextIOWrapper(f, encoding="utf-8", errors="replace"), delimiter=";")
    next(r, None)
    # sloupce: 0 výkaz, 1 tabulka, 2 období, 3 účetní jednotka, 4 IČO, 5 kraj, 6 NUTS,
    # 7 typ položky, 8 paragraf, 9 položka, 10 ÚZ, 11 prostor. jedn., 12 nástroj,
    # 13 mimoř. událost, 14 partner, 15 schválený, 16 po změnách, 17 skutečnost
    agg = {}
    for c in r:
        if len(c) < 18 or c[4] != ICO:
            continue   # c[14] = partner (protistrana transferu, např. vlastní škola) — ponechat
        key = (c[7], c[8], c[9])
        a = agg.setdefault(key, [0.0, 0.0, 0.0])
        for i, col in enumerate((15, 16, 17)):
            try:
                a[i] += float(c[col].strip() or 0)
            except ValueError:
                pass
for (ci, par, pol), (schv, upr, skut) in sorted(agg.items()):
    if not (schv or upr or skut):
        continue
    pi = lookup(POL, pol, ["nazev", "druh", "trida", "seskupeni", "podseskupeni"])
    ai = lookup(PAR, par, ["nazev", "skupina", "oddil"])
    rows.append({"rok": YEAR, "obdobi": month, "ico": ICO, "ci_type": ci, "paragraf": par,
                 "paragraf_nazev": ai["nazev"], "par_skupina": ai["skupina"], "par_oddil": ai["oddil"],
                 "polozka": pol, "polozka_nazev": pi["nazev"], "druh": pi["druh"], "trida": pi["trida"],
                 "seskupeni": pi["seskupeni"], "podseskupeni": pi["podseskupeni"],
                 "schvaleny_rozpocet": f"{schv:.2f}", "upraveny_rozpocet": f"{upr:.2f}",
                 "skutecnost": f"{skut:.2f}"})
unk = sum(1 for r in rows if not r["trida"])
cols = list(rows[0].keys())
with open(OUT, "w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=cols, delimiter=";")
    w.writeheader()
    w.writerows(rows)
print(f"{len(rows)} řádků → {OUT} (nedekódováno: {unk})")
