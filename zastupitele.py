#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Aktivita zastupitelů 2022–2026 — docházka, jmenovité hlasování, role v jednání
a vystoupení v diskuzi (z přepisů videozáznamů).

Zdroj: dataset_ZO.json (raw_text výpisů usnesení: „Přítomno: … Omluveni: …",
hlasovací bloky „Pro – N (jména) Proti – N (jména) Zdržel se – N (jména)";
jednomyslné hlasování „(všichni přítomní)" nebo bez jmen = všichni přítomní),
zo_votes_override.json (ZO 27 — nečitelný sken, přetisk ze zpravodaje),
prepisy/N.json (vystoupení v diskuzi; jen zasedání se záznamem).

Výstup: funkce build() → dict pro stránku (build_obdobi.py). Spuštěno samostatně
vypíše kontrolní přehled."""
import json, re, glob, os, unicodedata

ROOT = os.path.dirname(os.path.abspath(__file__))

# Členové zastupitelstva 2022–2026 (plná jména bez titulů; klíč = krátké jméno
# používané ve výpisech hlasování). Klíma rezignoval po ZO 22, od ZO 23 náhradník Smištík.
MEMBERS = [
    # key,            jméno,                 funkce
    ("Vašulín",     "Jiří Vašulín",        "starosta · rada obce"),
    ("Tichý",       "Josef Tichý",         "místostarosta · rada obce"),
    ("Zoubková",    "Petra Zoubková",      "rada obce"),
    ("A. Liška",    "Alois Liška",         "rada obce"),
    ("Dvořák",      "David Dvořák",        "rada obce"),
    ("Bartoňová",   "Eva Bartoňová",       "předsedkyně kontrolního výboru"),
    ("V. Liška",    "Vojtěch Liška",       "předseda finančního výboru"),
    ("Brener",      "Radim Brener",        ""),
    ("Dlapka",      "Jan Dlapka",          ""),
    ("Fialová",     "Helena Fialová",      ""),
    ("Hloušková",   "Zuzana Hloušková",    ""),
    ("Klíma",       "Martin Klíma",        "do 9/2025 (ZO 1–22)"),
    ("Pernikář",    "Jan Pernikář",        ""),
    ("Rozsíval",    "Petr Rozsíval",       ""),
    ("Smištík",     "Radovan Smištík",     "od 10/2025 (ZO 23–) · náhradník"),
    ("Ströbinger",  "Robert Ströbinger",   ""),
]
KEYS = [m[0] for m in MEMBERS]
FULL = {m[0]: m[1] for m in MEMBERS}
# mandát (čísla zasedání, kdy byl členem)
TERM = {"Klíma": (1, 22), "Smištík": (23, 999)}
# zasedání, kde někdo přišel později / slib složil během jednání → u prvních
# hlasování „všichni přítomní" nebyl (počet hlasujících je o 1 nižší)
LATE = {23: "Smištík", 25: "Hloušková"}

# mluvčí v přepisech → klíč člena
SPEAKER = {"Starosta": "Vašulín", "Místostarosta": "Tichý", "pan Smištík": "Smištík",
           "pan Liška": None}  # „pan Liška" nejde rozlišit (Alois/Vojtěch) → vynecháno
for k, full in FULL.items():
    SPEAKER.setdefault(full, k)


def _fold(s):
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn").lower()


def is_member(k, n):
    a, b = TERM.get(k, (1, 999))
    return a <= n <= b


def names_in(txt):
    """Z textu (výpis jmen v závorce / v seznamu přítomných) vrátí klíče členů."""
    t = re.sub(r"\s+", " ", txt)
    out = []
    for k in KEYS:
        if k in ("A. Liška", "V. Liška"):
            first = "Alois" if k == "A. Liška" else "Vojtěch"
            if re.search(re.escape(k), t) or re.search(first + r"\s+Lišk", t):
                out.append(k)
        elif re.search(re.escape(k.split()[-1]) + r"(?!\w)", t) or re.search(re.escape(FULL[k]), t):
            out.append(k)
    return out


def attendance(z):
    """→ (přítomní, omluvení) jako seznamy klíčů."""
    t = z["raw_text"]
    n = z["cislo_zasedani"]
    members = [k for k in KEYS if is_member(k, n)]
    m = re.search(r"Přítomn\w*:?(.*?)(?=Omluven||•|Zastupitelstvo|Za ověřovatel)", t, re.S)
    if not m:  # ZO 1 (ustavující — slib složili všichni) a ZO 27 (sken; přetisk: 15 přítomných)
        return members, []
    pres = [k for k in names_in(m.group(1)) if k in members]
    if z.get("pritomno") and len(pres) != z["pritomno"]:
        print(f"  ! ZO {n}: přítomno {z['pritomno']}, rozpoznáno {len(pres)}")
    return pres, [k for k in members if k not in pres]


VOTE = re.compile(
    r"Pro\s*[–\-:]?\s*(\d+)\s*(\([^)]*\))?\s*Proti\s*[–\-:]?\s*(\d+)\s*(\([^)]*\))?\s*"
    r"Zdržel\w*\s+se\s*[–\-:]?\s*(\d+)\s*(\([^)]*\))?", re.S)
PROCEDURAL = re.compile(r"ověřovatel|návrhov\w* komis|program jednání|program dnešního", re.I)


def votes(z, present):
    """Hlasování zasedání → seznam {text, proc, pro, proti, zdrzel} (klíče členů)."""
    n = z["cislo_zasedani"]
    t = z["raw_text"]
    out = []
    last = 0
    for i, m in enumerate(VOTE.finditer(t)):
        ctx = t[last:m.start()]
        last = m.end()
        text = re.sub(r"\s+", " ", ctx).strip()[-400:]
        cnt = [int(m.group(1)), int(m.group(3)), int(m.group(5))]
        proti = names_in(m.group(4) or "") if cnt[1] else []
        zdr = names_in(m.group(6) or "") if cnt[2] else []
        grp = m.group(2) or ""
        if cnt[0] and grp and "všichni" not in grp:
            pro = names_in(grp)
        else:
            pro = [k for k in present if k not in proti and k not in zdr]
            if n in LATE and len(pro) == cnt[0] + 1 and LATE[n] in pro:
                pro.remove(LATE[n])
        out.append({"text": text, "proc": bool(PROCEDURAL.search(text) or re.match(r"a\s+pan", text)),
                    "pro": pro, "proti": proti, "zdrzel": zdr, "cnt": cnt})
    return out


def override_votes(n, present):
    ov = json.load(open(os.path.join(ROOT, "zo_votes_override.json"), encoding="utf-8")).get(str(n))
    if not ov:
        return None
    ds = json.load(open(os.path.join(ROOT, "dataset_ZO.json"), encoding="utf-8"))
    z = next(x for x in ds if x["cislo_zasedani"] == n)
    out = []
    for b in z["body"]:
        if not b.get("hlasovani"):
            continue
        it = next((i for i in ov.get("items", []) if i["match"] in b["text"]), None)
        if it and it.get("names"):
            pro, proti, zdr = ([k for k in names_in(", ".join(g))] for g in it["names"])
        else:
            pro, proti, zdr = list(present), [], []
        out.append({"text": b["text"][:400], "proc": bool(PROCEDURAL.search(b["text"])),
                    "pro": pro, "proti": proti, "zdrzel": zdr, "cnt": b["hlasovani"]})
    return out


def speaking():
    """Vystoupení v diskuzi z přepisů: {klíč: {turns, words, body, zasedani}}."""
    res = {k: {"turns": 0, "words": 0, "body": 0, "zasedani": 0} for k in KEYS}
    meetings = []
    for f in sorted(glob.glob(os.path.join(ROOT, "prepisy", "[0-9]*.json"))):
        j = json.load(open(f, encoding="utf-8"))
        meetings.append(j["cislo_zasedani"])
        seen_m = set()
        for b in j["body"]:
            seen_b = set()
            for tr in b["turns"]:
                if tr.get("role") not in ("s", "z"):
                    continue  # občané, návrhová komise (čtení usnesení)
                k = SPEAKER.get(tr["who"])
                if not k:
                    continue
                res[k]["turns"] += 1
                res[k]["words"] += len(tr["text"].split())
                seen_b.add(k)
            for k in seen_b:
                res[k]["body"] += 1
            seen_m |= seen_b
        for k in seen_m:
            res[k]["zasedani"] += 1
    return res, sorted(meetings)


def _stem(k):
    last = FULL[k].split()[-1]
    return last[:-1] if last[-1] in "aáeý" else last


def who_named(txt):
    """Kdo je jmenován ve větě typu „zvolilo pana Petra Rozsívala / paní Evu Bartoňovou"."""
    out = []
    for k in KEYS:
        st = _stem(k)
        if k in ("A. Liška", "V. Liška"):
            if re.search(("Alois" if k == "A. Liška" else "Vojtěch") + r"\w*\s+Lišk", txt):
                out.append(k)
        elif re.search(re.escape(st) + r"\w*", txt):
            out.append(k)
    return out


def roles(z, vs):
    """Volba ověřovatelů zápisu a návrhové komise → {'over': [...], 'komise': [...]}."""
    out = {"over": [], "komise": []}
    if z["cislo_zasedani"] == 1:
        t = re.sub(r"\s+", " ", z["raw_text"])
        m = re.search(r"ověřovatele zápisu(.*?)do návrhové komise(.*?)\.", t)
        if m:
            out["over"], out["komise"] = who_named(m.group(1)), who_named(m.group(2))
        return out
    mode = None
    for v in vs:
        t = v["text"]
        tail = re.split(r"[•]", t)[-1]
        if re.search(r"ověřovatel", tail, re.I):
            mode = "over"
        elif re.search(r"návrhov\w* komis", tail, re.I):
            mode = "komise"
        elif not re.match(r"a\s+pan", t):
            mode = None
            continue
        if mode:
            for k in who_named(tail):
                if k not in out[mode]:
                    out[mode].append(k)
    return out


def build():
    ds = json.load(open(os.path.join(ROOT, "dataset_ZO.json"), encoding="utf-8"))
    per = {k: {"key": k, "name": FULL[k], "funkce": dict((m[0], m[2]) for m in MEMBERS)[k],
               "mozno": 0, "pritomen": 0, "omluven": 0,
               "hl_mozno": 0, "pro": 0, "proti": 0, "zdrzel": 0, "nehlasoval": 0,
               "over": 0, "komise": 0, "odlisne": []} for k in KEYS}
    meetings = []
    all_votes = []
    for z in ds:
        n = z["cislo_zasedani"]
        pres, exc = attendance(z)
        members = [k for k in KEYS if is_member(k, n)]
        vs = override_votes(n, pres) if n == 27 else votes(z, pres)
        vs = vs or []
        for k in members:
            per[k]["mozno"] += 1
            if k in pres:
                per[k]["pritomen"] += 1
            else:
                per[k]["omluven"] += 1
        r = roles(z, vs)
        for k in r["over"]:
            per[k]["over"] += 1
        for k in r["komise"]:
            per[k]["komise"] += 1
        for v in vs:
            v["zo"] = n
            v["datum"] = z["datum_text"]
            all_votes.append(v)
            if v["proc"]:
                continue
            for k in pres:
                per[k]["hl_mozno"] += 1
                if k in v["pro"]:
                    per[k]["pro"] += 1
                elif k in v["proti"]:
                    per[k]["proti"] += 1
                elif k in v["zdrzel"]:
                    per[k]["zdrzel"] += 1
                else:
                    per[k]["nehlasoval"] += 1
            if v["proti"] or v["zdrzel"]:
                for k in v["proti"] + v["zdrzel"]:
                    per[k]["odlisne"].append({"zo": n, "datum": z["datum_text"],
                                              "jak": "proti" if k in v["proti"] else "zdržel se",
                                              "text": v["text"], "cnt": v["cnt"]})
        meetings.append({"zo": n, "datum": z["datum_text"], "iso": z["datum"],
                         "pritomni": pres, "omluveni": [k for k in members if k not in pres]})
    sp, sp_meet = speaking()
    for k in KEYS:
        per[k].update({"sp_" + a: b for a, b in sp[k].items()})
    # podobnost hlasování: jen nejednomyslná věcná hlasování, dvojice přítomné obě
    contested = [v for v in all_votes if not v["proc"] and (v["proti"] or v["zdrzel"])]
    def how(k, v):
        return "pro" if k in v["pro"] else "proti" if k in v["proti"] else "zdr" if k in v["zdrzel"] else None
    sim = {}
    for a in KEYS:
        for b in KEYS:
            both = [v for v in contested if how(a, v) and how(b, v)]
            same = sum(1 for v in both if how(a, v) == how(b, v))
            sim[a + "|" + b] = [same, len(both)]
    subst = [v for v in all_votes if not v["proc"]]
    return {"members": [per[k] for k in KEYS], "meetings": meetings,
            "n_votes": len(subst), "n_contested": len(contested),
            "n_unanimous": sum(1 for v in subst if not (v["proti"] or v["zdrzel"])),
            "contested": [{"zo": v["zo"], "datum": v["datum"], "text": v["text"], "cnt": v["cnt"],
                           "proti": v["proti"], "zdrzel": v["zdrzel"]} for v in contested],
            "sim": sim, "sp_meetings": sp_meet}


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    d = build()
    print("věcných hlasování", d["n_votes"], "jednomyslně", d["n_unanimous"], "sporných", d["n_contested"])
    for m in d["members"]:
        print(f'{m["name"]:18} účast {m["pritomen"]:2}/{m["mozno"]:2}  pro {m["pro"]:3} proti {m["proti"]:2} zdr {m["zdrzel"]:2} '
              f'neh {m["nehlasoval"]:2}/{m["hl_mozno"]:3}  ověř {m["over"]:2} kom {m["komise"]:2}  '
              f'řeč: {m["sp_turns"]:3} vyst / {m["sp_body"]:2} bodů / {m["sp_words"]:5} slov')
    for mt in d["meetings"]:
        print(mt["zo"], len(mt["pritomni"]), "omluv:", mt["omluveni"])
