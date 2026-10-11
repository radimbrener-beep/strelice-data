#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stáhne výsledky komunálních voleb 2026 (9.–10. 10. 2026) pro Střelice z otevřených
dat aplikace volby.gov.cz a uloží je do data/volby/strelice_kv2026.json.

Zdroj: https://volby.gov.cz/appdata/kv2026/20261009/… (JSON, který používá oficiální
aplikace ČSÚ). Surové odpovědi se ukládají do data/volby/kv2026_raw/ pro kontrolu.

    python scripts/fetch_kv2026.py
"""
import json
import os
import re
import sys
import unicodedata
import urllib.request

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import zastupitele  # noqa: E402  (skutečné složení zastupitelstva 2022–26 vč. náhradníků)
BASE = "https://volby.gov.cz/appdata/kv2026/20261009"
OKRES, OBEC = 6203, 583910          # Brno-venkov, Střelice
RAW = os.path.join(ROOT, "data", "volby", "kv2026_raw")
OUT = os.path.join(ROOT, "data", "volby", "strelice_kv2026.json")
PREV = os.path.join(ROOT, "data", "volby", "strelice_volby.json")   # komunální 2022

PRE_TITLES = {"Ing.", "Mgr.", "MUDr.", "MVDr.", "JUDr.", "PhDr.", "RNDr.", "Bc.", "BcA.", "MgA.", "doc.",
              "prof.", "PaedDr.", "PharmDr.", "ThDr.", "Ing.arch.", "akad.", "arch."}   # „Ing. arch." = dva tokeny


def get(path):
    req = urllib.request.Request(f"{BASE}/{path}", headers={"User-Agent": "jaksemame-strelice/1.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        data = json.loads(r.read().decode("utf-8-sig"))
    os.makedirs(RAW, exist_ok=True)
    with open(os.path.join(RAW, path.replace("/", "_")), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    return data


def split_name(raw):
    """„Vašulín Jakub Ing." → („Ing. Jakub Vašulín", „jakub vasulin") — tituly před/za jméno."""
    parts = raw.split()
    words = [p for p in parts if not p.endswith(".") and p not in ("Ph.D.", "MBA", "CSc.", "DiS.")]
    pre = [p for p in parts if p in PRE_TITLES]
    post = [p for p in parts if p.endswith(".") and p not in PRE_TITLES]
    surname, given = words[0], " ".join(words[1:])
    display = " ".join(pre + [given, surname]) + (", " + " ".join(post) if post else "")
    return display, key(given + " " + surname)


def key(s):
    s = s.replace(",", " ")                                           # „Dobšíková, Ph.D."
    s = re.sub(r"\b[\w.]+\.(?=\s|$)", " ", s)                       # tituly pryč
    s = unicodedata.normalize("NFD", s).encode("ascii", "ignore").decode().lower()
    return " ".join(sorted(s.split()))


def main():
    vys = get(f"vysled/{OKRES}/{OBEC}.json")
    jms = get(f"jmsez/{OKRES}/{OBEC}.json")
    uc = get(f"ucast/obec/{OKRES}/{OBEC}.json")
    okrsky = get(f"navig/okrsky/{OKRES}/{OBEC}.json")["okrsky"]
    ok_res = {o: get(f"vysled/okrsek/{OKRES}/{OBEC}_{o}.json") for o in okrsky}
    for kind in ("zastup", "kand"):
        get(f"prehl/{kind}/vekPohl/obec/{OKRES}/{OBEC}.json")
    get(f"prehl/zastup/nstrana/obec/{OKRES}/{OBEC}.json")

    p = vys["prehled"]           # [mandáty, …, voliči, obálky, účast %, 0, odevzdané, platné obálky, % platných, platné hlasy]
    prev = json.load(open(PREV, encoding="utf-8"))["komunalni"]
    # pokračuje = byl/a členem zastupitelstva v období 2022–26 (vč. náhradníků, kteří nastoupili během období)
    term_keys = {key(m[1]) for m in zastupitele.MEMBERS}

    strany = []
    for c, nazev, hlasy, pct, *_rest in vys["vysledky"]:
        mand = _rest[3]          # [kandidátů, platné hlasy celkem, %, mandáty, % mandátů, zvoleno]
        strany.append({
            "c": c, "nazev": nazev, "hlasy": hlasy, "pct": pct, "mandaty": mand,
            "hranice": vys["hranice"].get(str(c)),                       # 110 % průměru na kandidáta
            "podily": [round(v, 2) for _, v in vys["podilyHlasu"][str(c)]],
            "kandidatu": len(vys["hlasy"][str(c)]),
        })

    kandidati = []
    for c, info in jms["platni"].items():
        for r in info["seznam"]:
            poradi, jmeno, vek, navrh, prisl, povolani, bydliste, hlasy, pct, por2, zvolen = r
            disp, k = split_name(jmeno)
            kandidati.append({
                "strana": int(c), "poradi": poradi, "jmeno": disp, "vek": vek, "hlasy": hlasy, "pct": pct,
                "zvolen": zvolen, "poradi_vysl": por2,          # pořadí zvolení / pořadí náhradníka
                "navrh": navrh, "prislusnost": "bez politické příslušnosti" if prisl == "BEZPP" else prisl,
                "povolani": povolani, "zena": bool(re.search(r"(ová|á)$", jmeno.split()[0])),
                "pokracuje": zvolen and k in term_keys,
                "okrsky": [next(h[3] for h in ok_res[o]["hlasy"][c] if h[0] == poradi) for o in okrsky],
            })

    okrs = []
    for o in okrsky:
        r = ok_res[o]
        u = next(x for x in uc["okrsky"] if x[0] == o)
        okrs.append({"c": o, "volici": u[1], "obalky": u[2], "ucast": u[3], "platne_hlasy": u[8],
                     "strany": {str(s[0]): [s[2], s[3]] for s in r["vysledky"]}})

    out = {
        "rok": 2026, "datum": "9.–10. 10. 2026", "obec": vys["obecNazev"], "generovano": vys["generovano"],
        "zdroj": f"{BASE}/vysled/{OKRES}/{OBEC}.json",
        "mandaty": p[0],
        "ucast": {"volici": p[5], "obalky": p[6], "pct": p[7], "odevzdane": p[9], "platne_obalky": p[10],
                  "pct_platnych": p[11], "platne_hlasy": p[12]},
        "strany": strany, "kandidati": kandidati, "okrsky": okrs,
        "prev": {"rok": prev["rok"], "ucast": prev["ucast"], "strany": prev["strany"],
                 "zastupitele": prev["zastupitele"]},
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    zv = [k for k in kandidati if k["zvolen"]]
    print(f"HOTOVO: {OUT} — {len(strany)} stran, {len(kandidati)} kandidátů, zvoleno {len(zv)}, "
          f"pokračují z 2022–26 {sum(k['pokracuje'] for k in zv)}, žen zvoleno {sum(k['zena'] for k in zv)}, účast {p[7]} %")


if __name__ == "__main__":
    main()
