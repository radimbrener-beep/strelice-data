#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Rychlý přehled trendů z konsolidovaného datasetu Střelice (FIN 2-12 M)."""
import sys, csv
from collections import defaultdict
sys.stdout.reconfigure(encoding="utf-8")

PATH = "data/strelice_finm201_2013_2025.csv"

def num(s):
    s = (s or "").strip()
    try: return float(s)
    except: return 0.0

rows = list(csv.DictReader(open(PATH, encoding="utf-8-sig"), delimiter=";"))
years = sorted({int(r["rok"]) for r in rows})

# agregace skutečnosti dle druhu a roku
by_druh = defaultdict(lambda: defaultdict(float))
by_trida = defaultdict(lambda: defaultdict(float))   # (druh,trida) -> rok -> skut
for r in rows:
    y = int(r["rok"]); sk = num(r["skutecnost"]); druh = r["druh"] or "?"
    by_druh[druh][y] += sk
    by_trida[(druh, r["trida"] or "?")][y] += sk

def mil(x): return f"{x/1e6:8.1f}"

print("=== SKUTEČNOST dle druhu (mil. Kč) ===")
print("rok        ", "  ".join(f"{y}" for y in years))
for druh in ["Příjmy", "Výdaje", "Financování"]:
    print(f"{druh:12}", " ".join(mil(by_druh[druh][y]) for y in years))
print(f"{'SALDO P-V':12}", " ".join(mil(by_druh['Příjmy'][y]-by_druh['Výdaje'][y]) for y in years))

print("\n=== PŘÍJMY dle třídy (mil. Kč) ===")
for (druh, trida), d in sorted(by_trida.items()):
    if druh != "Příjmy": continue
    print(f"{trida:28}", " ".join(mil(d[y]) for y in years))

print("\n=== VÝDAJE dle třídy (mil. Kč) ===")
for (druh, trida), d in sorted(by_trida.items()):
    if druh != "Výdaje": continue
    print(f"{trida:28}", " ".join(mil(d[y]) for y in years))

# Top výdajové oddíly v posledním roce
ly = years[-1]
odd = defaultdict(float)
for r in rows:
    if int(r["rok"]) == ly and r["druh"] == "Výdaje":
        odd[r["par_oddil"] or "(neuvedeno)"] += num(r["skutecnost"])
print(f"\n=== TOP 12 výdajových oddílů (paragraf) {ly} (mil. Kč) ===")
for k, v in sorted(odd.items(), key=lambda x: -x[1])[:12]:
    print(f"  {v/1e6:7.1f}  {k}")

print(f"\nřádků celkem: {len(rows)}, roky: {years[0]}–{years[-1]}")
