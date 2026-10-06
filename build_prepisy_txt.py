#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Sestaví jeden textový soubor 'prepisy-zo.txt' s PLNÝMI přepisy diskuze
všech zasedání zastupitelstva (ze záznamů). Nasazuje se jako statický soubor
→ dostupný přímo na https://strelice.jaksemame.cz/prepisy-zo.txt (neuvedený,
odnikud neodkazovaný). UTF-8 s BOM, ať se diakritika správně zobrazí i při
otevření přímo v prohlížeči / Poznámkovém bloku."""
import sys, json, glob, os, datetime
sys.stdout.reconfigure(encoding="utf-8")

zo = {m["cislo_zasedani"]: m for m in json.load(open("dataset_ZO.json", encoding="utf-8"))}

def fmt_d(iso):
    p = (iso or "").split("-")
    return f"{int(p[2])}. {int(p[1])}. {p[0]}" if len(p) == 3 else (iso or "")

def mmss(s):
    s = int(s or 0)
    return f"{s // 60}:{s % 60:02d}"

SEP = "─" * 60
DISCLAIMER = ("Redakčně upravený přepis z automatických titulků videozáznamu — orientační, "
              "NENÍ doslovný ani úřední záznam. Závazné je usnesení a originální zápis.\n"
              "Zastupitelé jsou uvedeni jménem, občané z pléna anonymizováni.")

def build_text(cislo, pj):
    m = zo.get(cislo, {})
    body_ds = m.get("body", [])
    vid = pj.get("vid")
    L = ["PŘEPIS JEDNÁNÍ ZASTUPITELSTVA OBCE STŘELICE",
         f"{cislo}. zasedání — {fmt_d(m.get('datum',''))}"]
    if vid:
        L.append(f"Videozáznam: https://youtu.be/{vid}")
    L += ["", DISCLAIMER, ""]
    for b in pj.get("body", []):
        idx = b.get("index")
        ds = body_ds[idx] if isinstance(idx, int) and idx < len(body_ds) else {}
        kat = (ds.get("kategorie") or "").upper()
        usn = ds.get("text") or ""
        head = f"Bod {idx}"
        if b.get("start") is not None:
            head += f"  [{mmss(b['start'])}]"
        if kat:
            head += f"  — {kat}"
        L += [SEP, head]
        if usn:
            L.append(f"Usnesení: {usn}")
        L.append("")
        for t in b.get("turns", []):
            L.append(f"  {t.get('who','').strip()}: {t.get('text','').strip()}")
        L.append("")
    L += [SEP, "Zdroj: videozáznam obce (YouTube @tvstreliceubrna) + ověřená data portálu strelice.jaksemame.cz."]
    return "\n".join(L)

meetings = []
for fp in glob.glob("prepisy/*.json"):
    base = os.path.basename(fp)
    if base.startswith("_"):
        continue
    pj = json.load(open(fp, encoding="utf-8"))
    c = pj.get("cislo_zasedani")
    if c is None:
        continue
    meetings.append((c, build_text(c, pj), sum(len(b.get("turns", [])) for b in pj.get("body", []))))
meetings.sort(key=lambda x: x[0])

today = datetime.date.today()
head = ("PŘEPISY JEDNÁNÍ ZASTUPITELSTVA OBCE STŘELICE\n"
        f"Staženo ze strelice.jaksemame.cz · {today.day}. {today.month}. {today.year}\n"
        f"Obsahuje {len(meetings)} zasedání se záznamem. Orientační přepisy z videozáznamů, "
        "redakčně upravené — nejsou úředním záznamem.\n\n\n")
joined = ("\n\n\n" + "=" * 60 + "\n\n\n").join(t for _, t, _ in meetings)
out = head + joined + "\n"

open("prepisy-zo.txt", "w", encoding="utf-8-sig").write(out)
total_turns = sum(n for _, _, n in meetings)
print(f"HOTOVO: prepisy-zo.txt — {len(meetings)} zasedání, {total_turns} replik, {len(out)//1024} kB")
