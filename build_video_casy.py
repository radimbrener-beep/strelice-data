#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Z YouTube auto-titulků záznamů zasedání ZO sestaví časové kotvy bodů jednání.

Pro každé zasedání, které má na kanálu @tvstreliceubrna záznam:
 - načte stažené české auto-titulky (data/video/caps/cap_<id>.cs-orig.vtt),
 - detekuje přechody na body jednání ("(k) bod(u) (číslo) X"),
 - vybere monotónní páteř (nejdelší rostoucí posloupnost čísel bodů v čase),
   čímž odfiltruje úvodní rekapitulaci programu i ojedinělé přeřeky,
 - každý přechod napáruje na text usnesení daného zasedání (kvůli čistému
   popisku) podle překryvu slov; jinak použije přepsaná slova předsedajícího,
 - výstup: video_casy.json { "<čísloZO>": {vid, dur, has_caps, chapters:[...]} }.

Zasedání s videem bez titulků (starší) dostanou jen odkaz na celé video.
Mapa číslo->video se bere z data/video/map.txt (řádky: "<číslo> <videoId>").
"""
import sys, os, re, json, bisect, unicodedata
sys.stdout.reconfigure(encoding="utf-8")

CAPS = "data/video/caps"
MAP = "data/video/map.txt"

CARD = {'jedna':1,'jeden':1,'dva':2,'dve':2,'tri':3,'ctyri':4,'pet':5,'sest':6,'sedm':7,
        'osm':8,'devet':9,'deset':10,'jedenact':11,'dvanact':12,'trinact':13,'ctrnact':14,
        'patnact':15,'sestnact':16,'sedmnact':17,'osmnact':18,'devatenact':19,'dvacet':20,
        'dvacetjedna':21,'dvacetdva':22,'dvacettri':23,'dvacetctyri':24,'dvacetpet':25}
# druhy usnesení, které ZAČÍNAJÍ nový bod programu (na rozdíl od navazujících)
PRIMARY = {'schvaluje','neschvaluje','bere na vědomí','souhlasí','nesouhlasí','volí',
           'rozhodlo','projednalo','stanovuje','vydává','zřizuje','ukládá'}
SECONDARY = {'pověřuje'}  # navazuje na předchozí bod


def strip(s):
    return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn').lower()


def parse_vtt(path):
    txt = open(path, encoding="utf-8").read()
    tok = re.findall(r'<(\d{2}):(\d{2}):(\d{2})\.(\d{3})><c>([^<]*)</c>', txt)
    W = []
    for h, m, s, ms, w in tok:
        t = int(h)*3600 + int(m)*60 + int(s) + int(ms)/1000
        w = w.strip()
        if w:
            W.append((t, w))
    return W


# přechod: "(k) bod(u) (číslo) <num|slovo>", tolerantní k tečkám/čárkám
PAT = re.compile(r'\b(?:k )?bod[uy]?\b[.,\s]*(?:cislo[.,\s]*|c[.,\s]*)?(\d{1,2}|[a-z]+)')


def detect(W):
    text = ""; offs = []; tms = []
    for t, w in W:
        offs.append(len(text)); tms.append(t); text += w + " "
    nt = strip(text)
    timeat = lambda p: tms[max(0, bisect.bisect_right(offs, p) - 1)]
    hits = []
    for m in PAT.finditer(nt):
        tokn = m.group(1)
        n = int(tokn) if tokn.isdigit() else CARD.get(tokn)
        if n and 1 <= n <= 26:
            snip = re.sub(r'\s+', ' ', text[m.start():m.start()+110]).strip()
            hits.append((round(timeat(m.start())), n, snip))
    return hits, (round(tms[-1]) if tms else 0)


def monotone_spine(hits):
    """Nejdelší (časově i číslem bodu) rostoucí posloupnost. Vstup hits je v čase."""
    hits = sorted(hits, key=lambda h: (h[0], h[1]))
    vals = [h[1] for h in hits]
    n = len(vals)
    if not n:
        return []
    # LIS s rekonstrukcí (strictly increasing); preferuj delší, pak menší časy
    best = [1]*n; prev = [-1]*n
    for i in range(n):
        for j in range(i):
            if vals[j] < vals[i] and best[j]+1 > best[i]:
                best[i] = best[j]+1; prev[i] = j
    end = max(range(n), key=lambda i: (best[i], -i))
    seq = []
    while end != -1:
        seq.append(hits[end]); end = prev[end]
    return seq[::-1]


# pevné popisky pro standardní procedurální body (číslování je napříč ZO stejné)
FIXED = {1: "Zahájení", 2: "Schválení programu", 3: "Volba ověřovatelů a návrhové komise"}
# slova, která se v párování neberou jako rozlišovací (jsou všudypřítomná/procedurální)
STOP = {'obce', 'strelice', 'zastupitelstvo', 'zastupitelstva', 'schvaluje', 'schvalilo',
        'schvalit', 'bere', 'vedomi', 'poveruje', 'poverilo', 'navrh', 'navrhu', 'tento',
        'tato', 'toto', 'bude', 'byla', 'bylo', 'mezi', 'podle', 'ktera', 'ktere', 'ktery',
        'jako', 'take', 'vyse', 'dalsi', 'prosim', 'pana', 'pani', 'mistostarostu',
        'mistostarostku', 'starostu', 'bodu', 'cislo', 'rok', 'roce', 'roku', 'vam', 'nam'}


def toks(s):
    return set(t for t in re.findall(r'[a-z0-9]{4,}', strip(s)) if t not in STOP)


def clean_usn_label(text, maxlen=82):
    """Krátký popisek z textu usnesení: odstraň úvodní 'Zastupitelstvo … schvaluje' apod."""
    # OCR artefakty: kódy usnesení "N/RRRR/ZNN" a koncové odkazy "Bod N."
    t = re.sub(r'\s*\d+/20\d\d/Z\d+', '', text)
    t = re.sub(r'(?:\s*Bod\s*\d*\.?)+\s*$', '', t).rstrip(' .,')
    # koncový podpis/místo/datum ze zápisu ("Střelice, 29. dubna 2026. Josef Tichý …")
    t = re.sub(r'\s*Střelice,\s*\d+\.\s*\w+\s*20\d\d\..*$', '', t).rstrip(' .,')
    t = re.sub(r'^\s*Zastupitelstvo( obce)?( Střelice)?\s*', '', t)
    for verb in ['bere bez připomínek na vědomí', 'vzalo bez připomínek na vědomí',
                 'bere na vědomí', 'vzalo na vědomí', 'neschvaluje', 'neschválilo',
                 'schvaluje', 'schválilo', 'nesouhlasilo s', 'nesouhlasilo',
                 'souhlasí s', 'souhlasilo s', 'souhlasí', 'souhlasilo',
                 'pověřuje', 'pověřilo', 'volí', 'zvolilo', 'rozhodlo', 'rozhodla',
                 'projednalo', 'stanovuje', 'stanovilo', 'vydává', 'vydalo',
                 'zřizuje', 'zřídilo', 'ukládá', 'uložilo', 'vzalo']:
        if t.lower().startswith(verb):
            t = t[len(verb):]; break
    t = re.sub(r'^[\s:;.)–-]*\d*[\s:;.)–-]+', ' ', t)  # zbytky typu ": 1)"
    t = re.sub(r'\s+', ' ', t).strip(' .,–-')
    if len(t) > maxlen:
        t = t[:maxlen].rsplit(' ', 1)[0] + '…'
    return t and (t[0].upper() + t[1:])


def build_groups(body):
    """Seskup usnesení do bodů programu: navazující 'pověřuje' patří k předchozímu bodu.
    Procedurální usnesení (schválení programu, volba ověřovatelů) se vynechají —
    nejsou to věcné body programu a kazila by zarovnání."""
    groups = []
    for b in body:
        s = strip(b["text"])
        if 'program jednani' in s or 'overovatel' in s or 'navrhove komis' in s:
            continue
        if b["kategorie"] in ('pověřuje', 'ukládá') and groups:
            groups[-1]["txt"] += " " + b["text"]
        else:
            groups.append({"label": clean_usn_label(b["text"]), "txt": b["text"]})
    for g in groups:
        g["toks"] = toks(g["txt"])
    return groups
# výplňková slova/fráze, které z přepisu vyhodíme ze začátku i konce popisku
FILLER = re.compile(
    r'\b(?:a (?:to|tím) je|tím je|to je|a poprosím|poprosím|poprosil bych|pana|paní|'
    r'místostarostu?u?|místostarostku|starostu?u?|starostku|večer\.?|vám|nám|'
    r'předkládáme(?: vám| nám)?|předkládám|v materiálu(?: číslo)?(?: \w+)?|'
    r'materiálu(?: číslo)?(?: \w+)?|jako (?:první|druhý|další)|tady|nyní|teď|tedy)\b',
    re.I)


def clean_snippet_label(snip, bod=None, maxlen=72):
    """Popisek z přepisu: odřízni 'k bodu číslo X', výplňková slova a uřízni na frázi."""
    if bod in FIXED:
        return FIXED[bod]
    sl = strip(snip)
    for key, lab in (('rozprava', 'Rozprava'), ('ruzne', 'Různé'), ('zaver', 'Závěr a poděkování')):
        if key in sl:
            return lab
    t = re.sub(r'^\s*(?:k\s+)?bod[uy]?\b[.,\s]*(?:číslo|čislo|c\.?)?[.,\s]*\S+', '', snip, flags=re.I)
    # uřízni na hranici věty (první tečka mimo zkratky/čísla) ať nepřeteče do dalšího tématu
    t = re.sub(r'^[.,\s]+', '', t)
    # odstraň výplňková slova opakovaně ze začátku
    for _ in range(6):
        t2 = FILLER.sub('', t, count=1).strip(' .,–-')
        if t2 == t:
            break
        t = t2
    t = re.sub(r'\s+', ' ', t).strip(' .,–-')
    if len(t) > maxlen:
        t = t[:maxlen].rsplit(' ', 1)[0] + '…'
    if t:
        t = t[0].upper() + t[1:]
    return t


def locate_group(gtoks, wtok, wt, lo, hi, win=34, thr=2):
    """Najdi nejranější okno v čase (lo,hi), kde se sejdou ≥thr rozlišovacích slov
    bodu; vrať čas prvního shodného slova (= zhruba začátek projednávání bodu)."""
    if len(gtoks) < thr or lo is None or hi is None or hi <= lo:
        return None
    n = len(wtok)
    i_lo = bisect.bisect_left(wt, lo)
    i_hi = bisect.bisect_right(wt, hi)
    for i in range(i_lo, max(i_lo, i_hi)):
        if len(set(wtok[i:i + win]) & gtoks) >= thr:
            for j in range(i, min(n, i + win)):
                if wtok[j] in gtoks:
                    return wt[j]
    return None


def build_chapters(W, groups):
    """Sestaví kapitoly: zakotví detekované 'bod číslo X', zbývající body programu
    doplní lokalizací podle rozlišovacích slov mezi sousedními kotvami."""
    hits, dur = detect(W)
    spine = monotone_spine(hits)
    wtok = [strip(w) for _, w in W]
    wt = [t for t, _ in W]
    # textová osa pro vyhledávání frází (procedurální body)
    text = ""; offs = []; tms = []
    for t, w in W:
        offs.append(len(text)); tms.append(t); text += w + " "
    ntext = strip(text)

    def first_time(keys, lo, hi):
        best = None
        for k in keys:
            i = ntext.find(k)
            while i != -1:
                ti = tms[max(0, bisect.bisect_right(offs, i) - 1)]
                if (lo is None or ti >= lo) and (hi is None or ti <= hi):
                    if best is None or ti < best:
                        best = ti
                    break
                i = ntext.find(k, i + 1)
        return best

    # rozlišovací slova bodů: vyřaď slova společná více bodům (dotace, smlouvu, pozemku…)
    df = {}
    for g in groups:
        for tk in g["toks"]:
            df[tk] = df.get(tk, 0) + 1
    common = {tk for tk, c in df.items() if c >= 3}
    loc_toks = [g["toks"] - common for g in groups]

    chapters = []         # procedurální a útržkové (mimo body programu)
    g_time = {}           # index bodu programu -> (čas, čísloBodu z kotvy)
    ptr = 0
    for t, n, snip in spine:
        if n in FIXED:
            chapters.append({"t": t, "bod": n, "label": FIXED[n], "src": "fix"})
            continue
        stoks = toks(snip)
        best_i, best_sc = -1, 0
        for i in range(ptr, min(len(groups), ptr + 6)):
            sc = len(stoks & groups[i]["toks"])
            if sc > best_sc:
                best_sc, best_i = sc, i
        if best_i >= 0 and best_sc >= 2:
            g_time[best_i] = (t, n); ptr = best_i + 1
        else:
            chapters.append({"t": t, "bod": n, "src": "snip",
                             "label": clean_snippet_label(snip, bod=n) or f"Bod {n}"})

    anchored = {gi: tv[0] for gi, tv in g_time.items()}
    first = min(anchored) if anchored else None
    earliest = min(anchored.values()) if anchored else dur

    # procedurální body 1–3: vezmi z detekce, jinak dohledej podle klíčových slov
    proc = {c["bod"]: c["t"] for c in chapters if c["src"] == "fix"}
    ov = proc.get(3) or first_time(["overovatel"], 0, earliest)
    prog = proc.get(2) or first_time(["zmenu programu", "doplneni programu",
                                      "doplneni ci zmenu", "program dnesniho", "schvaleni programu"], 0, ov)
    zah = proc.get(1) or first_time(["zahajuji", "vsechny pritomne", "mile divaky",
                                     "mili divaci", "usnaseni schopn", "pritomno vsech"], 0, prog or ov)
    for b, tt in ((1, zah), (2, prog), (3, ov)):
        if b not in proc and tt is not None:
            chapters.append({"t": round(tt), "bod": b, "label": FIXED[b], "src": "fix"})
            proc[b] = round(tt)
    disc_start = ov or prog or zah or 0

    last_t = 0
    for gi in range(len(groups)):
        if gi in anchored:
            chapters.append({"t": anchored[gi], "bod": g_time[gi][1],
                             "label": groups[gi]["label"], "src": "prog"})
            last_t = anchored[gi]; continue
        if first is not None and gi < first:
            if disc_start <= 0:
                continue  # neznáme konec rekapitulace → raději nevyplňovat
            lo, hi = max(last_t, disc_start), anchored[first]
        else:
            lo = last_t
            hi = min([anchored[a] for a in anchored if a > gi], default=dur)
        t = locate_group(loc_toks[gi], wtok, wt, lo + 1, hi - 1)
        if t and t > last_t:
            a = max([x for x in anchored if x < gi], default=None)
            b = min([x for x in anchored if x > gi], default=None)
            ba = g_time[a][1] if a is not None else None
            bb = g_time[b][1] if b is not None else None
            bodN = None
            if ba and bb and (b - a) == (bb - ba):
                bodN = ba + (gi - a)
            elif bb and (bb - (b - gi)) >= 1:
                bodN = bb - (b - gi)
            elif ba:
                bodN = ba + (gi - a)
            chapters.append({"t": round(t), "bod": bodN, "label": groups[gi]["label"],
                             "src": "fill"})
            last_t = t
    chapters.sort(key=lambda c: c["t"])

    # útržkové (snip) kapitoly z přeslechnutého „bod číslo X" často jen duplikují
    # programovou kapitolu poblíž — takové zahodíme
    prog_t = [c["t"] for c in chapters if c["src"] in ("prog", "fill", "fix")]
    chapters = [c for c in chapters
                if c["src"] != "snip" or all(abs(c["t"] - p) > 22 for p in prog_t)]

    # čísla bodů MUSÍ jít vzestupně: ponech nejdelší striktně rostoucí posloupnost,
    # u ostatních číslo skryj (zobrazí se jen čas + téma)
    idx = [i for i, c in enumerate(chapters) if c.get("bod")]
    vals = [chapters[i]["bod"] for i in idx]
    nb = len(vals)
    if nb:
        best = [1] * nb; prv = [-1] * nb
        for i in range(nb):
            for j in range(i):
                if vals[j] < vals[i] and best[j] + 1 > best[i]:
                    best[i] = best[j] + 1; prv[i] = j
        e = max(range(nb), key=lambda i: best[i])
        keep = set()
        while e != -1:
            keep.add(idx[e]); e = prv[e]
        for i, c in enumerate(chapters):
            if c.get("bod") and i not in keep:
                c["bod"] = None
    return chapters, dur


def main():
    src = json.load(open("dataset_ZO.json", encoding="utf-8"))
    by_cislo = {z["cislo_zasedani"]: z for z in src}
    themap = {}
    for ln in open(MAP, encoding="utf-8"):
        ln = ln.split()
        if len(ln) == 2:
            themap[int(ln[0])] = ln[1]

    out = {}
    report = []
    for cislo in sorted(themap, reverse=True):
        vid = themap[cislo]
        cap = os.path.join(CAPS, f"cap_{vid}.cs-orig.vtt")
        z = by_cislo.get(cislo)
        usn = [b["text"] for b in z["body"]] if z else []
        if not os.path.exists(cap):
            out[str(cislo)] = {"vid": vid, "dur": None, "has_caps": False, "chapters": []}
            report.append((cislo, vid, 0, 0, []))
            continue
        W = parse_vtt(cap)
        groups = build_groups(z["body"]) if z else []
        chapters, dur = build_chapters(W, groups)
        out[str(cislo)] = {"vid": vid, "dur": dur, "has_caps": True, "chapters": chapters}
        report.append((cislo, vid, dur, len(chapters), chapters))

    json.dump(out, open("video_casy.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # report pro kontrolu
    for cislo, vid, dur, nch, chapters in report:
        ds = f"{dur//60}:{dur%60:02d}" if dur else "—"
        nfill = sum(1 for c in chapters if c.get("src") == "fill")
        print(f"=== ZO {cislo} ({vid}) {ds} — {nch} kapitol (+{nfill} doplněno) ===")
        for c in chapters:
            tag = {"prog": "P", "fill": "+", "fix": "·", "snip": "≈"}.get(c.get("src"), "?")
            bod = f"bod{c['bod']:>2}" if c.get("bod") else "  –  "
            print(f"   {c['t']//60:>3}:{c['t']%60:02d} {bod} {tag} {c['label']}")
    print("\nHOTOVO: video_casy.json")


if __name__ == "__main__":
    main()
