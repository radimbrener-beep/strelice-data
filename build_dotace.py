#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stáhne veřejnoprávní smlouvy o poskytnutí dotace z webu obce Střelice
(sekce Hospodaření → Poskytnuté dotace, roky 2022–2026) a z textu každé
smlouvy vytáhne příjemce, výši dotace a účel."""
import re, sys, os, subprocess, csv, html
from urllib.parse import unquote
sys.stdout.reconfigure(encoding="utf-8")

BASE = "https://www.streliceubrna.cz"
YEARS = [2022, 2023, 2024, 2025, 2026]
rows = []

def recipient(fn):
    n = fn[:-4] if fn.lower().endswith(".pdf") else fn
    n = re.sub(r"^Veřejnoprávní smlouva o poskytnutí dotace z rozpočtu obce\s*-\s*", "", n)
    n = re.sub(r"\s*\d{4}.*$", "", n)          # odřízni rok a vše za ním (č.1, _0, doc…)
    return n.strip(" -_") or n

for y in YEARS:
    h = open(f"data/dotace2/page_{y}.html", encoding="utf-8", errors="replace").read()
    hrefs = [html.unescape(x) for x in dict.fromkeys(re.findall(r'href="([^"]+\.pdf)"', h, re.I))]
    os.makedirs(f"data/dotace2/pdf/{y}", exist_ok=True)
    for i, href in enumerate(hrefs):
        fn = unquote(href.split("/")[-1])
        out = f"data/dotace2/pdf/{y}/{i:02d}.pdf"
        url = href if href.startswith("http") else BASE + href
        if not (os.path.exists(out) and os.path.getsize(out) > 1500):
            subprocess.run(["curl", "-s", "-L", "-m", "60", "-A", "Mozilla/5.0", "-o", out, url])
        txt = subprocess.run(["pdftotext", "-enc", "UTF-8", out, "-"],
                             capture_output=True).stdout.decode("utf-8", "replace")
        t = re.sub(r"\s+", " ", txt)
        # výše dotace: "ve výši: 520 000,- Kč"
        amt = None
        ma = re.search(r"ve\s+výši:?\s*([\d][\d\s. ]*?)\s*,?\s*-?\s*K[čc]", t)
        if ma:
            d = re.sub(r"\D", "", ma.group(1)); amt = int(d) if d else None
        # účel: "...v žádosti : <účel>" až do dalšího článku smlouvy
        ucel = ""
        mu = re.search(r"v\s+žádosti\s*:?\s*(.{3,400})", t)
        if mu:
            u = re.split(r"\s*(?:\bčl\.\s*I|\b2\.\s|Poskytnut[ío]\s+dotace|Dotace je ve smyslu|Dotace je poskytována|Tato dotace)", mu.group(1))[0]
            ucel = re.sub(r"\s+", " ", u).strip(" :;,.-")[:180]
        rows.append({"rok": y, "prijemce": recipient(fn), "castka": amt, "ucel": ucel,
                     "textlen": len(txt), "soubor": fn})

# výpis + souhrny
rows.sort(key=lambda r: (r["rok"], -(r["castka"] or 0)))
cur = None
yt = {}
for r in rows:
    if r["rok"] != cur:
        cur = r["rok"]; print(f"\n================  {cur}  ================")
    print(f"  {str(r['castka']) if r['castka'] is not None else '   ?':>9} Kč | {r['prijemce'][:36]:36} | {r['ucel'][:46]}")
    yt[r["rok"]] = yt.get(r["rok"], 0) + (r["castka"] or 0)

print("\n=== SOUČTY PER ROK ===")
for y in YEARS:
    n = sum(1 for r in rows if r["rok"] == y)
    miss = sum(1 for r in rows if r["rok"] == y and r["castka"] is None)
    print(f"  {y}: {n} smluv, součet {yt.get(y,0):,} Kč".replace(",", " ") + (f"  (bez částky: {miss})" if miss else ""))

with open("data/dotace_strelice.csv", "w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["rok", "prijemce", "castka", "ucel", "soubor"], delimiter=";")
    w.writeheader()
    for r in rows: w.writerow({k: r[k] for k in ["rok", "prijemce", "castka", "ucel", "soubor"]})
print(f"\nuloženo: data/dotace_strelice.csv ({len(rows)} řádků)")
