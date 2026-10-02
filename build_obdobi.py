#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Sestaví obdobi.html — „Volební období 2022–2026 v datech":
(A) bilance období: hospodaření, největší akce, rozhodnutí, dodavatelé, dotace,
    časová osa klíčových rozhodnutí;
(B) aktivita zastupitelů: docházka, jmenovité hlasování, role v jednání,
    vystoupení v diskuzi (zastupitele.py).

Nestrannost: jen fakta z veřejných zdrojů, žádné hodnocení ani pořadí „nejlepších".
Spouštět PO build_investice.py a build_zakazky.py (čte data vložená do jejich HTML)."""
import sys, json, csv, os
from collections import defaultdict, Counter
import portal_common as pc
import zastupitele

sys.stdout.reconfigure(encoding="utf-8")
CHARTJS = open("data/vendor/chart.umd.js", encoding="utf-8").read()


def embedded(path):
    s = open(path, encoding="utf-8").read()
    i = s.index("const D=") + len("const D=")
    return json.JSONDecoder().raw_decode(s[i:])[0]


def num(s):
    try: return round(float((s or "").strip()))
    except ValueError: return 0


def mil(v):
    return f"{v/1e6:.1f}".replace(".", ",")


ro = json.load(open("dataset_RO.json", encoding="utf-8"))
zo = json.load(open("dataset_ZO.json", encoding="utf-8"))
Y0, Y1 = 2022, 2026

# --- hospodaření po letech (2022–2025 skutečnost, 2026 upravený rozpočet + stav k pololetí) ---
fin = list(csv.DictReader(open("data/strelice_finm201_2013_2025.csv", encoding="utf-8-sig"), delimiter=";"))
hosp = []
for y in range(Y0, 2026):
    rr = [r for r in fin if int(r["rok"]) == y]
    hosp.append({"y": y, "pr": sum(num(r["skutecnost"]) for r in rr if r["druh"] == "Příjmy"),
                 "vy": sum(num(r["skutecnost"]) for r in rr if r["druh"] == "Výdaje"),
                 "kap": sum(num(r["skutecnost"]) for r in rr if r["trida"] == "Kapitálové výdaje"), "plan": False})
f26 = "data/strelice_fin_2026.csv"
mon26 = None
if os.path.exists(f26):
    rr = list(csv.DictReader(open(f26, encoding="utf-8-sig"), delimiter=";"))
    mon26 = int(rr[0]["obdobi"])
    hosp.append({"y": 2026, "pr": sum(num(r["upraveny_rozpocet"]) for r in rr if r["druh"] == "Příjmy"),
                 "vy": sum(num(r["upraveny_rozpocet"]) for r in rr if r["druh"] == "Výdaje"),
                 "kap": sum(num(r["upraveny_rozpocet"]) for r in rr if r["trida"] == "Kapitálové výdaje"),
                 "kap_s": sum(num(r["skutecnost"]) for r in rr if r["trida"] == "Kapitálové výdaje"), "plan": True})
kap_done = sum(h["kap"] for h in hosp if not h["plan"])
pr_done = sum(h["pr"] for h in hosp if not h["plan"])
vy_done = sum(h["vy"] for h in hosp if not h["plan"])

# --- největší akce období (data stránky Investice) ---
inv = embedded("investice.html")
akce = [a for a in inv["akce"] if a[0] and a[0][:4] >= str(Y0)]
# srozumitelné názvy největších akcí (text usnesení je dlouhý a obsahuje iniciály osob)
import re
AKCE_LBL = [
    (r"Novostavba MŠ Střelice – stavební", "Stavba nové mateřské školy"),
    (r"SATOV s\.r\.o\.", "Koupě prostor obchodního domu (od SATOV s.r.o.)"),
    (r"jednotku č\. 630/4 byt|manželi .{0,20}úschov|úschově mezi obcí Střelice a manžel", "Koupě bytu v obchodním domě"),
    (r"Oprava chodníku ul\. Ant\. Smutného", "Oprava chodníku Ant. Smutného a části Na Hrázi"),
    (r"rekonstrukce ulice Školní", "Rekonstrukce ulice Školní"),
    (r"půdní vestavba budovy ZUŠ", "Stavební úpravy a půdní vestavba budovy ZUŠ"),
    (r"Oprava chodníku nám\. Svobody", "Oprava chodníků nám. Svobody a Brněnská"),
    (r"budova pošty", "Koupě budovy pošty s pozemkem"),
    (r"Polní cesta C20", "Polní cesta C20"),
    (r"gastrovybavení pro novou kuchyň", "Vybavení kuchyně nové MŠ"),
    (r"Komunikace ul\. Vršovická", "Komunikace v ulici Vršovické"),
    (r"Výstavba FVE", "Fotovoltaické elektrárny na obecních budovách"),
    (r"Protierozní opatření", "Protierozní opatření v lese"),
    (r"výtahu a výtahové šachty", "Výtah ke zdravotnímu středisku"),
]
# financování ČOV (podíl obce) je v bilanci zvlášť; neschválené a pověření radou nejsou akce
AKCE_SKIP = re.compile(r"stavby ČOV|Rozšíření ČOV|podílu na realizaci stavby|neschválilo|pověřilo radu obce dokončením|Nabídku Úřadu pro zastupování", re.I)
def akce_lbl(t):
    for rx, l in AKCE_LBL:
        if re.search(rx, t):
            return l
    t = re.sub(r"^(Zastupitelstvo obce Střelice |Zastupitelstvo obce )?(schválilo |Schvaluje )?", "", t)
    t = re.sub(r"\b[A-ZŠČŘŽ]\. [A-ZŠČŘŽ]\.", "…", t)   # iniciály fyzických osob
    return t[:120].rsplit(" ", 1)[0] + "…"
seen = set()
top_akce = []
for a in sorted(akce, key=lambda a: -a[1]):
    if AKCE_SKIP.search(a[4]):
        continue
    l = akce_lbl(a[4])
    if l in seen and l != "Koupě bytu v obchodním domě":
        continue
    seen.add(l)
    top_akce.append(a + [l])
    if len(top_akce) == 12:
        break

# --- dodavatelé a dotace ---
zak = embedded("zakazky.html")
firms = defaultdict(lambda: [0, 0])
for r in zak["rows"]:
    firms[r[1]][0] += r[2]
    firms[r[1]][1] += 0 if r[8] else 1
top_firms = sorted(firms.items(), key=lambda x: -x[1][0])[:8]
dot_y, dot_r = Counter(), Counter()
for r in csv.DictReader(open("data/dotace_strelice.csv", encoding="utf-8-sig"), delimiter=";"):
    try: v = int(r["castka"])
    except ValueError: continue
    dot_y[int(r["rok"])] += v
    dot_r[r["prijemce"].strip()] += v
top_dot = dot_r.most_common(6)

# --- rozhodnutí podle témat (RO + ZO) ---
tema_c = Counter()
for src in (ro, zo):
    for m in src:
        for b in m["body"]:
            t = b.get("tema") or "Ostatní"
            if t != "Jednání a formality":
                tema_c[t] += 1

# --- časová osa (ručně vybrané milníky ze shrnutí zasedání; jen fakta) ---
TIMELINE = [
    ("2022-10-19", 1, "Ustavující zasedání", "Zastupitelstvo zvolilo starostou Jiřího Vašulína a místostarostou Josefa Tichého, dále tři další členy rady obce."),
    ("2023-05-11", 5, "Koupě obchodního domu", "Obec koupila prostory obchodního domu SATOV (15,85 mil. Kč) a byt v témže domě (8,5 mil. Kč); v roce 2026 přikoupila další byt (9,99 mil. Kč)."),
    ("2023-06-22", 7, "Nová mateřská škola", "Zadána stavba nové budovy MŠ za 27,2 mil. Kč bez DPH (MATYÁŠ s.r.o.); stavba byla podpořena dotací MMR 28,8 mil. Kč."),
    ("2023-12-14", 10, "Program rozvoje obce", "Schválen Program rozvoje obce na roky 2024–2030 a zřízena Základní umělecká škola."),
    ("2024-02-29", 11, "Chodníky v centru", "Zadána oprava chodníků na náměstí Svobody a v Brněnské ulici za 6,3 mil. Kč a obnova plochy koupaliště."),
    ("2024-04-25", 12, "ZUŠ a plánovací smlouva", "Zadána půdní vestavba budovy ZUŠ (7,6 mil. Kč); plánovací smlouva s developerem Win plus (příspěvek obci 4 mil. Kč)."),
    ("2024-06-20", 13, "Memorandum o čistírně", "Schváleno memorandum o rozšíření čistírny odpadních vod na 6 500 ekvivalentních obyvatel."),
    ("2024-07-29", 14, "Fotovoltaika", "Vybrán dodavatel fotovoltaických elektráren na obecních budovách; dotace SFŽP 2,3 mil. Kč přijata v roce 2025."),
    ("2025-02-27", 18, "Ulice Školní", "Zadána rekonstrukce ulice Školní za 7,7 mil. Kč bez DPH."),
    ("2025-08-29", 21, "650 let obce", "Slavnostní zasedání k 650. výročí založení obce, ocenění bývalých starostů a zastupitelů."),
    ("2026-02-26", 26, "Financování čistírny (ČOV)", "Schváleno financování rozšíření ČOV: stavba 188,9 mil. Kč, podíl obce 130,8 mil. Kč, převážně z úvěru České spořitelny. Obec si tak bere první úvěr za dobu pokrytou daty (od roku 2013)."),
    ("2026-06-23", 28, "Budova pošty", "Obec koupila budovu pošty s pozemkem za 5,37 mil. Kč; od 1. 9. 2026 provozuje Poštu Partner."),
    ("2026-09-17", 29, "Nový územní plán", "Zastupitelstvo vydalo nový územní plán obce (11:1, jeden se zdržel), který nahradil plán z roku 2009."),
]

# --- aktivita zastupitelů ---
Z = zastupitele.build()
n_meet = len(zo)
n_ro = len(ro)
n_zo_items = sum(len(m["b"]) for m in embedded("zastupitelstvo.html")["meet"])   # stejně jako sekce Zastupitelstvo (vč. doplnění ZO 27)
n_ro_items = sum(len(m["body"]) for m in ro)

# vystoupení v diskuzi po zastupitelích: [zo, datum, text bodu, čas ve videu, video id, [texty]]
import glob
_zmeet = {m["n"]: m for m in embedded("zastupitelstvo.html")["meet"]}
SP = defaultdict(list)
for _f in sorted(glob.glob("prepisy/[0-9]*.json"), key=lambda x: int(os.path.basename(x)[:-5])):
    _j = json.load(open(_f, encoding="utf-8"))
    _n = _j["cislo_zasedani"]; _m = _zmeet.get(_n)
    if not _m:
        continue
    for _b in _j["body"]:
        _by = defaultdict(list)
        for _t in _b["turns"]:
            if _t.get("role") in ("s", "z"):
                _k = zastupitele.SPEAKER.get(_t["who"])
                if _k:
                    _by[_k].append(_t["text"])
        _it = _m["b"][_b["index"]] if _b["index"] < len(_m["b"]) else None
        _bt = (_it[4] if _it else "").replace("Zastupitelstvo obce Střelice ", "").replace("Zastupitelstvo ", "")
        for _k, _tx in _by.items():
            SP[_k].append([_n, _m["d"], _bt[:220], _b.get("start") or 0, _m.get("v") or _j.get("vid"), _tx])

DATA = {"sp": SP, "hosp": hosp, "mon26": mon26, "Z": Z, "tema": tema_c.most_common(),
        "dotY": sorted(dot_y.items())}
data_json = json.dumps(DATA, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")


def esc(s):
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def short(t, n=170):
    t = t.replace("Zastupitelstvo obce Střelice ", "").replace("Zastupitelstvo obce ", "")
    return t if len(t) <= n else t[:n].rsplit(" ", 1)[0] + "…"


akce_rows = "".join(
    f'<tr><td class="num">{mil(a[1])}</td><td><b>{esc(a[-1])}</b>'
    f'{"<br><small>" + esc(a[6]) + "</small>" if a[6] else ""}</td>'
    f'<td class="nw">{a[0][8:10].lstrip("0")}. {a[0][5:7].lstrip("0")}. {a[0][:4]}</td>'
    f'<td class="nw"><a href="{"zastupitelstvo.html?zo=" if a[2] == "ZO" else "zapisy.html?ro="}{a[3]}">{a[2]} {a[3]}</a></td></tr>'
    for a in top_akce)
firm_rows = "".join(f'<tr><td><a href="zakazky.html?firma={esc(f)}">{esc(f)}</a></td><td class="num">{c}</td><td class="num">{mil(v)}</td></tr>'
                    for f, (v, c) in top_firms)
dot_rows = "".join(f'<tr><td><a href="dotace.html?prijemce={esc(p)}">{esc(p)}</a></td><td class="num">{mil(v)}</td></tr>'
                   for p, v in top_dot)
tl_html = "".join(
    f'<div class="tl"><div class="tld">{d[8:10].lstrip("0")}. {d[5:7].lstrip("0")}. {d[:4]}</div>'
    f'<div class="tlb"><b>{esc(t)}</b><p>{esc(x)}</p><a href="zastupitelstvo.html?zo={n}">ZO {n} →</a></div></div>'
    for d, n, t, x in TIMELINE)

unan = Z["n_unanimous"] / Z["n_votes"] * 100
body = f'''<header class="hero">
  <h1>Volební období 2022–2026 v datech</h1>
  <p>Co zastupitelstvo a rada obce za čtyři roky rozhodly, kolik obec vybrala, utratila a proinvestovala, a jak se jednotliví zastupitelé účastnili jednání. Jen fakta z veřejných zdrojů — bez hodnocení.</p>
  <div class="chips"><span class="chip">říjen 2022 – září 2026</span><span class="chip">zdroje: zápisy RO a ZO · MONITOR SP · přepisy záznamů ZO</span></div>
  <nav class="jump"><a href="#bilance">Bilance období</a><a href="#osa">Časová osa</a><a href="#zastupitele">Zastupitelé</a></nav>
</header>

<div class="cards">
  <div class="kpi"><div class="lab">Zasedání zastupitelstva</div><div class="val">{n_meet}</div><div class="delta" style="color:var(--muted)">{n_zo_items} usnesení</div></div>
  <div class="kpi" style="--bar:#3b82f6"><div class="lab">Jednání rady obce</div><div class="val">{n_ro}</div><div class="delta" style="color:var(--muted)">{n_ro_items} bodů</div></div>
  <div class="kpi" style="--bar:#16a34a"><div class="lab">Jednomyslná hlasování ZO</div><div class="val">{unan:.0f} %</div><div class="delta" style="color:var(--muted)">{Z["n_unanimous"]} z {Z["n_votes"]} věcných hlasování</div></div>
  <div class="kpi" style="--bar:var(--amber)"><div class="lab">Investice 2022–2025</div><div class="val">{mil(kap_done)} <span style="font-size:14px;color:var(--muted)">mil. Kč</span></div><div class="delta" style="color:var(--muted)">kapitálové výdaje, skutečnost</div></div>
  <div class="kpi" style="--bar:#db2777"><div class="lab">Dotace spolkům 2022–2026</div><div class="val">{mil(sum(dot_y.values()))} <span style="font-size:14px;color:var(--muted)">mil. Kč</span></div><div class="delta" style="color:var(--muted)">{len(dot_r)} příjemců</div></div>
</div>

<section id="bilance">
  <div class="sec-h"><h2>Hospodaření obce v období</h2><span class="hint">mil. Kč · 2022–2025 skutečnost, 2026 upravený rozpočet</span></div>
  <div class="panel">
    <div class="chartbox"><canvas id="hospCh"></canvas></div>
    <p class="note">V letech 2022–2025 obec vybrala celkem <b>{mil(pr_done)} mil. Kč</b> a utratila <b>{mil(vy_done)} mil. Kč</b>, z toho <b>{mil(kap_done)} mil. Kč</b> na investice.
    Do konce roku 2025 obec <b>neměla žádný úvěr</b>; na rozšíření čistírny odpadních vod schválilo zastupitelstvo v únoru 2026 úvěr u České spořitelny.
    Rok 2026 je zobrazen podle upraveného rozpočtu (plán){f", skutečně zaplacené investice k {mon26}. měsíci činily {mil(hosp[-1]['kap_s'])} mil. Kč" if mon26 else ""}. Detail v sekci <a href="rozpocet.html">Rozpočet</a>.</p>
  </div>
</section>

<section>
  <div class="sec-h"><h2>Největší akce období</h2><span class="hint">investice, stavby a nákupy majetku podle částky v usnesení · mil. Kč</span></div>
  <div class="panel tblp"><table class="t"><thead><tr><th class="num">mil. Kč</th><th>Akce</th><th>Datum</th><th>Zdroj</th></tr></thead><tbody>{akce_rows}</tbody></table>
  <p class="note">Částka = cena uvedená v usnesení (u staveb obvykle bez DPH). Financování rozšíření ČOV (podíl obce 130,8 mil. Kč, hlavně úvěrem) je uvedeno v časové ose. Další akce a mapa v sekci <a href="investice.html">Investice</a>.</p></div>
</section>

<section>
  <div class="grid2">
    <div><div class="sec-h"><h2>O čem se rozhodovalo</h2><span class="hint">body RO + ZO podle tématu</span></div>
      <div class="panel"><div class="chartbox sm"><canvas id="temaCh"></canvas></div>
      <p class="note">Bez formálních bodů (program, ověřovatelé, zprávy o činnosti). Témata přiřazena automaticky podle textu.</p></div></div>
    <div><div class="sec-h"><h2>Komu obec nejvíc platila</h2><span class="hint">dodavatelé 2022–2026</span></div>
      <div class="panel tblp"><table class="t"><thead><tr><th>Firma</th><th class="num">zakázek</th><th class="num">mil. Kč</th></tr></thead><tbody>{firm_rows}</tbody></table>
      <div class="sec-h" style="margin:18px 0 8px"><h2 style="font-size:16px">Největší příjemci dotací</h2></div>
      <table class="t"><thead><tr><th>Příjemce</th><th class="num">mil. Kč</th></tr></thead><tbody>{dot_rows}</tbody></table></div></div>
  </div>
</section>

<section id="osa">
  <div class="sec-h"><h2>Časová osa klíčových rozhodnutí</h2><span class="hint">výběr největších a dlouhodobých rozhodnutí zastupitelstva</span></div>
  <div class="panel"><div class="tlw">{tl_html}</div>
  <p class="note">Výběr podle výše částky a dlouhodobého dopadu. Všechna rozhodnutí se shrnutím najdete v sekcích <a href="zastupitelstvo.html">Zastupitelstvo</a> a <a href="zapisy.html">Rada obce</a>.</p></div>
</section>

<section id="zastupitele">
  <div class="sec-h"><h2>Zastupitelé: účast a aktivita</h2><span class="hint">{n_meet} zasedání · {Z["n_votes"]} věcných hlasování · přepisy {len(Z["sp_meetings"])} zasedání se záznamem</span></div>
  <div class="panel expl">
    <p><b>Co tabulka ukazuje.</b> <b>Účast</b> = na kolika zasedáních byl zastupitel přítomen (ze zasedání během svého mandátu).
    <b>Hlasování</b> = jak hlasoval ve věcných hlasováních, když byl přítomen (bez volby ověřovatelů a komisí, kde se zvolený obvykle zdrží).
    <b>Proti / zdržel se</b> = kolikrát v těchto hlasováních hlasoval proti nebo se zdržel.
    <b>Diskuze</b> = ke kolika bodům jednání zastupitel v rozpravě promluvil / kolikrát celkem vystoupil, podle přepisů videozáznamů ({len(Z["sp_meetings"])} z {n_meet} zasedání má záznam); starosta jednání řídí a předkládá většinu bodů, proto má vystoupení nejvíc.</p>
    <p style="margin-top:8px"><b>Tip:</b> klikněte na <b>jméno zastupitele</b> — ukáže se přehled, k čemu v diskuzi vystoupil: po zasedáních a bodech, s textem vystoupení a odkazem ▶ na přesný čas ve videozáznamu. Klik na počet <b>„proti / zdržel se"</b> ukáže seznam konkrétních hlasování.</p>
    <p class="note" style="margin-top:6px">Aktivita zastupitele se neodráží jen v číslech — velká část práce probíhá ve výborech, komisích a mimo zasedání.</p>
  </div>
  <div class="panel tblp" style="margin-top:14px"><div class="tscroll"><table class="t zt" id="zt"><thead></thead><tbody>{pc.skel_tr(10, 6)}</tbody></table></div></div>
</section>

<section>
  <div class="sec-h"><h2>Docházka po zasedáních</h2><span class="hint">● přítomen · ○ omluven · prázdné = nebyl členem</span></div>
  <div class="panel tblp"><div class="tscroll"><table class="att" id="att"></table></div></div>
</section>

<section>
  <div class="sec-h"><h2>Nejednomyslná hlasování</h2><span class="hint">{Z["n_contested"]} věcných hlasování, kde někdo hlasoval proti nebo se zdržel</span></div>
  <div class="panel tblp"><table class="t"><thead><tr><th>Zasedání</th><th>Usnesení</th><th class="num">pro : proti : zdržel</th><th>Proti / zdržel se</th></tr></thead><tbody id="cont"></tbody></table></div>
</section>

<div class="modal" id="modal" hidden><div class="modal-bd" id="modalBd"></div>
  <div class="modal-card"><div class="modal-h"><b id="modalT"></b><button class="iconbtn" id="modalX" aria-label="Zavřít">✕</button></div>
  <div class="modal-c" id="modalC"></div></div></div>'''

CSS = '''<style>
.jump{display:flex;gap:8px;flex-wrap:wrap;margin-top:14px}
.jump a{font-size:13px;padding:6px 13px;border-radius:10px;background:var(--accent-soft);color:var(--accent);text-decoration:none;font-weight:600}
.t{width:100%;border-collapse:collapse;font-size:13.5px}
.t th{text-align:left;font-size:12px;color:var(--muted);font-weight:600;padding:8px 10px;border-bottom:1px solid var(--line);white-space:nowrap}
.t td{padding:9px 10px;border-bottom:1px solid var(--line);vertical-align:top}
.t tr:last-child td{border-bottom:0}
.t td small{color:var(--muted)}
.t a{color:var(--accent);text-decoration:none}
.num{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
.nw{white-space:nowrap}
.tblp{padding:10px 12px;overflow-x:auto}
@media(max-width:560px){.t{font-size:12.5px}.t td,.t th{padding:7px 6px}}
.tscroll{overflow-x:auto}
.zt td{vertical-align:middle}
.zt .nm b{display:block}.zt .nm small{color:var(--muted)}
.bar{display:inline-block;height:7px;border-radius:4px;background:var(--accent);vertical-align:middle;margin-right:6px}
.vs{display:flex;height:9px;border-radius:5px;overflow:hidden;min-width:110px;background:var(--inset)}
.vs i{display:block;height:100%}
.lnk{color:var(--accent);cursor:pointer;text-decoration:underline dotted}
.att{border-collapse:separate;border-spacing:2px;font-size:12px}
.att th{font-weight:600;color:var(--muted);padding:2px 4px;white-space:nowrap}
.att th.v{writing-mode:vertical-rl;transform:rotate(180deg);font-weight:500;font-size:11px;height:64px}
.att td{text-align:center;width:22px;height:20px;border-radius:4px}
.att td.p{background:var(--pos);color:#fff}.att td.o{background:var(--inset);color:var(--neg);font-weight:700}
.att td.nm{text-align:left;width:auto;white-space:nowrap;padding-right:8px}
.att td.sum{width:auto;padding-left:8px;color:var(--muted);white-space:nowrap}
.tlw{position:relative;margin-left:8px;border-left:2px solid var(--line);padding-left:18px}
.tl{position:relative;display:grid;grid-template-columns:100px 1fr;gap:12px;padding:8px 0}
.tl::before{content:"";position:absolute;left:-25px;top:14px;width:10px;height:10px;border-radius:50%;background:var(--accent)}
.tld{font-size:12.5px;color:var(--muted);font-variant-numeric:tabular-nums;padding-top:2px}
.tlb p{margin:3px 0 4px;color:var(--muted);font-size:13.5px;line-height:1.5}
.tlb a{font-size:12px;color:var(--accent);text-decoration:none}
.note a{color:var(--accent)}
.expl p{margin:0;font-size:13.5px;line-height:1.6;color:var(--text)}
@media(max-width:560px){.tl{grid-template-columns:1fr;gap:2px}}
.modal[hidden]{display:none}.modal{position:fixed;inset:0;z-index:100;display:grid;place-items:center}
.modal-bd{position:absolute;inset:0;background:rgba(2,8,20,.55)}
.modal-card{position:relative;background:var(--surface);border:1px solid var(--line);border-radius:14px;width:min(760px,94vw);max-height:84vh;display:flex;flex-direction:column;box-shadow:var(--shadow-h)}
.modal-h{display:flex;justify-content:space-between;align-items:center;gap:10px;padding:14px 18px;border-bottom:1px solid var(--line)}
.modal-c{padding:8px 18px 16px;overflow:auto;font-size:13.5px}
.modal-c .it{padding:10px 0;border-bottom:1px solid var(--line)}
.modal-c .it small{color:var(--muted)}
.modal-c .it small a{color:var(--accent);text-decoration:none;white-space:nowrap}
.modal-c blockquote{margin:6px 0 0;padding:6px 10px;border-left:3px solid var(--accent);background:var(--inset);border-radius:0 8px 8px 0;line-height:1.55}
.sph{margin:14px 0 2px;font-weight:650;font-size:13px;color:var(--text)}
.sph a{font-weight:500;font-size:12px;color:var(--accent);text-decoration:none;margin-left:6px}
.spnote{font-size:12px;color:var(--faint);margin:8px 0 4px;line-height:1.5}
.spsum{margin:4px 0 0;font-size:13px}
.zt .nm b.lnk{text-decoration:underline dotted;text-underline-offset:3px}
</style>'''

JS = '<script>' + CHARTJS + '''</script>
<script>
const D=DATA_JSON, Z=D.Z, M=Z.members;
/*TEMAJS*/
const nf=new Intl.NumberFormat('cs-CZ');
const esc=s=>String(s==null?'':s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const mil=v=>(v/1e6).toLocaleString('cs-CZ',{maximumFractionDigits:1});
const FULL={};M.forEach(m=>FULL[m.key]=m.name);
let charts={};
function mk(id,cfg){if(charts[id])charts[id].destroy();charts[id]=new Chart(document.getElementById(id),cfg);}
function axis(){return {grid:{color:cssv('--line')},ticks:{color:cssv('--muted')}};}
function drawCharts(){
  const H=D.hosp;
  mk('hospCh',{type:'bar',data:{labels:H.map(h=>h.y+(h.plan?' (plán)':'')),datasets:[
    {label:'Příjmy',data:H.map(h=>h.pr/1e6),backgroundColor:H.map(h=>h.plan?'rgba(127,183,164,.38)':'#7fb7a4')},
    {label:'Výdaje celkem',data:H.map(h=>h.vy/1e6),backgroundColor:H.map(h=>h.plan?'rgba(224,168,120,.38)':'#e0a878')},
    {label:'z toho investice',data:H.map(h=>h.kap/1e6),backgroundColor:H.map(h=>h.plan?'rgba(169,155,209,.38)':'#a99bd1')}]},
    options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{labels:{color:cssv('--muted')}},
      tooltip:{callbacks:{label:c=>c.dataset.label+': '+c.parsed.y.toLocaleString('cs-CZ',{maximumFractionDigits:1})+' mil. Kč'}}},
      scales:{x:axis(),y:Object.assign(axis(),{beginAtZero:true})}}});
  const T=D.tema;
  mk('temaCh',{type:'bar',data:{labels:T.map(t=>t[0]),datasets:[{data:T.map(t=>t[1]),backgroundColor:T.map(t=>temaRGB(t[0])),borderRadius:4}]},
    options:{indexAxis:'y',responsive:true,maintainAspectRatio:false,plugins:{legend:{display:false}},
      scales:{x:axis(),y:Object.assign(axis(),{grid:{display:false}})}}});
}
// --- tabulka zastupitelů (řaditelná) ---
const COLS=[
  ['name','Zastupitel',m=>`<div class="nm"><b class="lnk" data-sp="${esc(m.key)}" title="Přehled vystoupení v diskuzi">${esc(m.name)}</b><small>${esc(m.funkce)}</small></div>`,m=>surKey(m)],
  ['ucast','Účast',m=>`<span class="bar" style="width:${Math.round(m.pritomen/m.mozno*60)}px"></span>${m.pritomen}/${m.mozno} <small style="color:var(--muted)">(${Math.round(m.pritomen/m.mozno*100)} %)</small>`,m=>m.pritomen/m.mozno],
  ['hl','Hlasování (věcná)',m=>{const t=m.hl_mozno||1;return `<div class="vs" title="pro ${m.pro} · proti ${m.proti} · zdržel se ${m.zdrzel}"><i style="width:${m.pro/t*100}%;background:#22c55e"></i><i style="width:${m.proti/t*100}%;background:#ef4444"></i><i style="width:${m.zdrzel/t*100}%;background:#eab308"></i></div><small style="color:var(--muted)">${m.hl_mozno} hlasování · pro ${m.pro}</small>`;},m=>m.pro/(m.hl_mozno||1)],
  ['odl','Proti / zdržel se',m=>(m.proti+m.zdrzel)?`<span class="lnk" data-k="${esc(m.key)}">${m.proti} / ${m.zdrzel}</span>`:'0 / 0',m=>m.proti+m.zdrzel],
  ['sp','Diskuze: bodů / vystoupení',m=>m.sp_turns?`${m.sp_body} / ${m.sp_turns} <small style="color:var(--muted)">(${nf.format(m.sp_words)} slov)</small>`:'—',m=>m.sp_turns],
];
// řazení jmen podle příjmení (česká abeceda), při shodě podle jména
const surKey=m=>{const p=m.name.split(' ');return p[p.length-1]+' '+p.slice(0,-1).join(' ');};
const BY_SUR=M.slice().sort((a,b)=>surKey(a).localeCompare(surKey(b),'cs'));
let sortK='name', sortD=1;
function ztable(){
  const c=COLS.find(c=>c[0]===sortK), rows=M.slice().sort((a,b)=>{const x=c[3](a),y=c[3](b);
    return (typeof x==='string'?x.localeCompare(y,'cs'):(x<y?-1:x>y?1:0))*sortD;});
  document.querySelector('#zt thead').innerHTML='<tr>'+COLS.map(c=>`<th class="thsort" data-k="${c[0]}">${c[1]}<span class="ar">${sortK===c[0]?(sortD>0?'▲':'▼'):'↕'}</span></th>`).join('')+'</tr>';
  document.querySelector('#zt tbody').innerHTML=rows.map(m=>'<tr>'+COLS.map(c=>`<td>${c[2](m)}</td>`).join('')+'</tr>').join('');
  document.querySelectorAll('#zt .thsort').forEach(th=>th.onclick=()=>{if(sortK===th.dataset.k)sortD=-sortD;else{sortK=th.dataset.k;sortD=th.dataset.k==='name'?1:-1;}ztable();});
  document.querySelectorAll('#zt .lnk[data-k]').forEach(a=>a.onclick=()=>odlisne(a.dataset.k));
  document.querySelectorAll('#zt .lnk[data-sp]').forEach(a=>a.onclick=()=>vystoupeni(a.dataset.sp));
}
function odlisne(k){
  const m=M.find(x=>x.key===k);
  document.getElementById('modalT').textContent=m.name+' — hlasování proti / zdržení se';
  document.getElementById('modalC').innerHTML=m.odlisne.map(o=>`<div class="it"><small>ZO ${o.zo} · ${esc(o.datum)} · <b>${esc(o.jak)}</b> · výsledek ${o.cnt.join(' : ')}</small><div>${esc(o.text.replace(/^[\\uf0b7•\\s]+/,''))}</div><a href="zastupitelstvo.html?zo=${o.zo}" style="font-size:12px;color:var(--accent)">zasedání ZO ${o.zo} →</a></div>`).join('');
  document.getElementById('modal').hidden=false;
}
function fdIso(iso){const p=iso.split('-');return (+p[2])+'. '+(+p[1])+'. '+p[0];}
function fmtT(t){t=Math.round(t);const h=Math.floor(t/3600),m=Math.floor(t%3600/60),s=t%60;return (h?h+':'+String(m).padStart(2,'0'):m)+':'+String(s).padStart(2,'0');}
function vystoupeni(k){
  const m=M.find(x=>x.key===k), L=D.sp[k]||[];
  document.getElementById('modalT').textContent=m.name+' — vystoupení v diskuzi';
  const cov=`<p class="spnote">Podle přepisů záznamů ${Z.sp_meetings.length} zasedání (ZO ${Z.sp_meetings.join(', ')}). Zasedání bez záznamu zde nejsou. Přepis je redakčně upravený z automatických titulků — rozhoduje záznam.</p>`;
  if(!L.length){document.getElementById('modalC').innerHTML=cov+'<div class="it">V přepisech zasedání se záznamem není zaznamenáno žádné vystoupení v diskuzi.</div>';
    document.getElementById('modal').hidden=false;return;}
  const zs=[...new Set(L.map(x=>x[0]))];
  let h=cov+`<p class="spsum"><b>${L.length}</b> ${L.length===1?'bod':(L.length<5?'body':'bodů')} na <b>${zs.length}</b> zasedáních · ${nf.format(L.reduce((a,x)=>a+x[5].length,0))} vystoupení</p>`;
  let last=null;
  // zasedání od nejnovějšího, body v rámci zasedání v pořadí jednání
  const ord=zs.slice().reverse();
  for(const x of ord.flatMap(z=>L.filter(y=>y[0]===z))){
    if(x[0]!==last){h+=`<div class="sph">ZO ${x[0]} · ${fdIso(x[1])} <a href="zastupitelstvo.html?zo=${x[0]}">zasedání →</a></div>`;last=x[0];}
    const yt=x[4]&&x[3]?` <a href="https://youtu.be/${x[4]}?t=${x[3]}" target="_blank" rel="noopener">▶ ${fmtT(x[3])}</a>`:'';
    h+=`<div class="it"><small><b>Bod:</b> ${esc(x[2]||'—')}${yt}</small>`+x[5].map(t=>`<blockquote>${esc(t)}</blockquote>`).join('')+'</div>';
  }
  document.getElementById('modalC').innerHTML=h;
  document.getElementById('modal').hidden=false;
  document.getElementById('modalC').scrollTop=0;
}
['modalX','modalBd'].forEach(id=>document.getElementById(id).onclick=()=>document.getElementById('modal').hidden=true);
document.addEventListener('keydown',e=>{if(e.key==='Escape')document.getElementById('modal').hidden=true;});
// --- docházka ---
(function(){
  const MT=Z.meetings;
  let h='<tr><th></th>'+MT.map(t=>`<th class="v" title="${esc(t.datum)}">ZO ${t.zo}</th>`).join('')+'<th></th></tr>';
  for(const m of BY_SUR){
    h+=`<tr><td class="nm">${esc(m.name)}</td>`+MT.map(t=>{
      if(t.pritomni.includes(m.key))return `<td class="p" title="ZO ${t.zo} · ${esc(t.datum)} · přítomen">●</td>`;
      if(t.omluveni.includes(m.key))return `<td class="o" title="ZO ${t.zo} · ${esc(t.datum)} · omluven">○</td>`;
      return '<td></td>';}).join('')+`<td class="sum">${m.pritomen}/${m.mozno}</td></tr>`;
  }
  document.getElementById('att').innerHTML=h;
})();
// --- nejednomyslná hlasování ---
document.getElementById('cont').innerHTML=Z.contested.slice().reverse().map(v=>`<tr><td class="nw"><a href="zastupitelstvo.html?zo=${v.zo}">ZO ${v.zo}</a><br><small>${esc(v.datum)}</small></td>`+
  `<td>${esc(v.text.replace(/^[\\uf0b7•\\s]+/,'').slice(0,260))}${v.text.length>260?'…':''}</td><td class="num">${v.cnt.join(' : ')}</td>`+
  `<td><small>${v.proti.length?'<b>proti:</b> '+v.proti.map(k=>esc(FULL[k])).join(', '):''}${v.proti.length&&v.zdrzel.length?'<br>':''}${v.zdrzel.length?'<b>zdržel se:</b> '+v.zdrzel.map(k=>esc(FULL[k])).join(', '):''}</small></td></tr>`).join('');
ztable(); drawCharts(); bindTheme(drawCharts);
</script>'''.replace("DATA_JSON", data_json).replace("/*TEMAJS*/", pc.TEMA_JS)

html = pc.page("Bilance", "Volební období 2022–2026 — Jak žijí Střelice", body, head_scripts=CSS, body_scripts=JS)
open("obdobi.html", "w", encoding="utf-8").write(html)
print(f"HOTOVO: obdobi.html ({len(html)//1024} kB) — {len(Z['members'])} zastupitelů, {Z['n_contested']} sporných hlasování")
