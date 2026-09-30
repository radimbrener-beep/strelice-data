#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Přepočítá téma (pole `tema`) všech usnesení RO i ZO podle aktuálních pravidel
v temata.py — bez nového parsování PDF. Použít po úpravě vzorů v temata.py,
pak přegenerovat stránky (build_zapisy.py, build_zastupitelstvo.py, …)."""
import csv, json, os, sys
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import temata  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")
for js, cs in (("dataset_RO.json", "dataset_RO_body.csv"), ("dataset_ZO.json", "dataset_ZO_body.csv")):
    p = os.path.join(ROOT, js)
    d = json.load(open(p, encoding="utf-8"))
    changed = Counter()
    for m in d:
        for b in m["body"]:
            t = temata.classify(b["text"])
            if b.get("tema") != t:
                changed[(b.get("tema"), t)] += 1
                b["tema"] = t
    json.dump(d, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    # CSV: přepsat sloupec tema podle textu
    cp = os.path.join(ROOT, cs)
    if os.path.exists(cp):
        rows = list(csv.reader(open(cp, encoding="utf-8-sig"), delimiter=";"))
        h = rows[0]
        if "tema" in h and "text" in h:
            ti, xi = h.index("tema"), h.index("text")
            for r in rows[1:]:
                if len(r) > max(ti, xi):
                    r[ti] = temata.classify(r[xi])
            with open(cp, "w", encoding="utf-8-sig", newline="") as f:
                csv.writer(f, delimiter=";").writerows(rows)
    print(js, "změněno", sum(changed.values()))
    print("  ", Counter(b["tema"] for m in d for b in m["body"]).most_common())
