#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Stáhne výkaz FIN 2-12 M (Plnění rozpočtu ÚSC) z MONITORu Státní pokladny
za roky 2013-2025, vytáhne řádky obce Střelice (IČO 00282618) z detailního
výkazu FINM201 (příjmy/výdaje podle paragrafů a položek) a sestaví jeden
čistý "long" dataset s dekódovanými číselníky (paragraf, položka).
"""
import sys, os, io, csv, zipfile, subprocess
import xml.etree.ElementTree as ET
from datetime import date

sys.stdout.reconfigure(encoding="utf-8")

ICO = "00282618"
YEARS = list(range(2013, 2026))          # 2013..2025 (roční stav, období 12)
BASE = "https://monitor.statnipokladna.gov.cz"
RAW = "data/raw/FinM"
OUT = "data"
os.makedirs(RAW, exist_ok=True)

def dl(url, dest):
    if os.path.exists(dest) and os.path.getsize(dest) > 1000:
        return True
    print(f"  stahuji {url}")
    r = subprocess.run(["curl", "-s", "-f", "-m", "300", "-A", "research/1.0",
                        "-o", dest, url])
    ok = r.returncode == 0 and os.path.exists(dest) and os.path.getsize(dest) > 1000
    if not ok:
        print(f"  !! selhalo: {url}")
    return ok

# ---- číselníky ----------------------------------------------------------
def load_codelist(path, code_field):
    """vrátí list záznamů (dict) s parsovanými start/end daty"""
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
PAR = load_codelist("data/ciselniky/paragraf.xml", "paragraf")

def lookup(recs, code, year, fields):
    ref = date(year, 12, 31)
    cands = [r for r in recs if r["_code"] == code]
    hit = next((r for r in cands if r["_start"] <= ref <= r["_end"]), None)
    if hit is None and cands:
        hit = cands[-1]
    return {f: (hit.get(f, "") if hit else "") for f in fields}

# ---- hlavní průchod -----------------------------------------------------
rows = []
for y in YEARS:
    url = f"{BASE}/data/extrakty/csv/FinM/{y}_12_Data_CSUIS_FINM.zip"
    zp = f"{RAW}/{y}_12_FINM.zip"
    if not dl(url, zp):
        continue
    try:
        z = zipfile.ZipFile(zp)
    except zipfile.BadZipFile:
        print(f"  !! poškozený zip {zp}"); continue
    member = next((n for n in z.namelist() if "FINM201" in n.upper()), None)
    if not member:
        print(f"  !! FINM201 nenalezen v {zp}"); continue
    cnt = 0
    with z.open(member) as f:
        txt = io.TextIOWrapper(f, encoding="utf-8", errors="replace")
        r = csv.reader(txt, delimiter=";")
        next(r, None)  # header
        for c in r:
            if len(c) < 13 or c[4] != ICO:
                continue
            cnt += 1
            ci_type, par, pol = c[7], c[8], c[9]
            schv = c[10].strip(); uprav = c[11].strip(); skut = c[12].strip()
            pinfo = lookup(POL, pol, y, ["nazev", "druh", "trida", "seskupeni", "podseskupeni"])
            ainfo = lookup(PAR, par, y, ["nazev", "skupina", "oddil"])
            rows.append({
                "rok": y,
                "ico": ICO,
                "ci_type": ci_type,
                "paragraf": par,
                "paragraf_nazev": ainfo["nazev"],
                "par_skupina": ainfo["skupina"],
                "par_oddil": ainfo["oddil"],
                "polozka": pol,
                "polozka_nazev": pinfo["nazev"],
                "druh": pinfo["druh"],
                "trida": pinfo["trida"],
                "seskupeni": pinfo["seskupeni"],
                "podseskupeni": pinfo["podseskupeni"],
                "schvaleny_rozpocet": schv,
                "upraveny_rozpocet": uprav,
                "skutecnost": skut,
            })
    print(f"  {y}: {cnt} radku Strelice")

# ---- zápis --------------------------------------------------------------
cols = ["rok", "ico", "ci_type", "paragraf", "paragraf_nazev", "par_skupina",
        "par_oddil", "polozka", "polozka_nazev", "druh", "trida", "seskupeni",
        "podseskupeni", "schvaleny_rozpocet", "upraveny_rozpocet", "skutecnost"]
outpath = f"{OUT}/strelice_finm201_2013_2025.csv"
with open(outpath, "w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=cols, delimiter=";")
    w.writeheader()
    w.writerows(rows)
print(f"\nHOTOVO: {len(rows)} radku -> {outpath}")
