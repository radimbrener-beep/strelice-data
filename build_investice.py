#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generuje sekci portálu 'Investice — co se staví' (investice.html).
Kapitálové výdaje obce z FIN 2-12 M (vývoj v čase, podle oblasti) propojené
s konkrétními investičními rozhodnutími z usnesení Rady obce a Zastupitelstva
(téma Stavby/investice a Doprava, s uvedenou částkou)."""
import sys, csv, json, re, os
from datetime import date
import portal_common as pc
sys.stdout.reconfigure(encoding="utf-8")

CHARTJS = open("data/vendor/chart.umd.js", encoding="utf-8").read()
LEAFLET_JS = open("data/vendor/leaflet.js", encoding="utf-8").read()
LEAFLET_CSS = open("data/vendor/leaflet.css", encoding="utf-8").read()
FIN = "data/strelice_finm201_2013_2025.csv"
POP = 3258  # obyvatel (2023) pro přepočet na obyvatele

def num(s):
    try: return round(float((s or "").strip()))
    except: return 0

rows = list(csv.DictReader(open(FIN, encoding="utf-8-sig"), delimiter=";"))
years = sorted({int(r["rok"]) for r in rows})
PRIJ = {"Daňové příjmy", "Nedaňové příjmy", "Kapitálové příjmy", "Přijaté transfery"}
VYD  = {"Běžné výdaje", "Kapitálové výdaje"}

# --- kapitálové výdaje a celkové výdaje po letech (skutečnost) ---
kap_by_year, vyd_by_year = {}, {}
for y in years:
    rr = [r for r in rows if int(r["rok"]) == y]
    kap_by_year[y] = sum(num(r["skutecnost"]) for r in rr if r["trida"] == "Kapitálové výdaje")
    vyd_by_year[y] = sum(num(r["skutecnost"]) for r in rr if r["trida"] in VYD)

recent5 = set(y for y in years if y >= max(years) - 4)

# --- rozpad roku pro modal (největší rozpočtové položky) ---
def _agg(yset, keyfn):
    a = {}
    for r in rows:
        if r["trida"] == "Kapitálové výdaje" and int(r["rok"]) in yset:
            k = keyfn(r)
            if k:
                a[k] = a.get(k, 0) + num(r["skutecnost"])
    return sorted(([k, v] for k, v in a.items() if v > 0), key=lambda x: -x[1])

# rozpad jednoho roku: největší rozpočtové položky (paragrafy)
year_detail = {}
for y in years:
    year_detail[y] = {
        "par": _agg({y}, lambda r: r["paragraf_nazev"] or r["paragraf"])[:10],
        "tot": kap_by_year[y],
    }

# --- konkrétní investiční akce z usnesení RO + ZO ---
# Téma Pozemky/majetek/bydlení zahrnuto celé (≥100k) — pořízení pozemků i
# nemovitostí je investice (je i v kapitálových výdajích).
THEMES = {"Stavby, investice a územní rozvoj", "Doprava a sítě",
          "Pozemky, majetek a bydlení"}
MIN_AKCE = 100_000   # práh: investiční akce, ne drobné nákupy
ro = json.load(open("dataset_RO.json", encoding="utf-8"))
zo = json.load(open("dataset_ZO.json", encoding="utf-8"))

# časy v záznamu jednání (jen ZO mají video): {číslo_ZO: {text_usnesení: čas_s}}, {číslo_ZO: video_id}
VCAS = json.load(open("video_casy.json", encoding="utf-8")) if os.path.exists("video_casy.json") else {}
zo_text_time, zo_vid = {}, {}
for _m in zo:
    _c = _m.get("cislo_zasedani")
    _vc = VCAS.get(str(_c))
    if not _vc:
        continue
    zo_vid[_c] = _vc.get("vid")
    _bt = _vc.get("bodytimes") or {}
    zo_text_time[_c] = {b["text"]: _bt[str(ix)] for ix, b in enumerate(_m["body"]) if str(ix) in _bt}


# zjevné ne-investice (i když spadají do tématu): pojištění, dluhy, nájmy
_NONINVEST = re.compile(r"pojist|uznání dluhu|splátkov|náj(?:em|mu)", re.IGNORECASE)


def is_invest(b):
    if not (b.get("castka") and b["castka"] >= MIN_AKCE and b.get("tema") in THEMES):
        return False
    return not _NONINVEST.search(b["text"])


akce = []
for src, mid in (("RO", ro), ("ZO", zo)):
    for m in mid:
        for b in m["body"]:
            if is_invest(b):
                akce.append([m.get("datum") or "", b["castka"], src,
                             m.get("cislo_zasedani"), b["text"], m.get("url") or ""])


def _date(iso):
    try:
        return date.fromisoformat(iso)
    except (ValueError, TypeError):
        return None


_PARC = re.compile(r"p\.?\s*č\.?\s*(\d+(?:/\d+)?)", re.IGNORECASE)


def _parcels(text):
    """Čísla parcel v textu — identita pozemkové akce (různé parcely se stejnou
    částkou jsou různé akce; tatáž parcela napříč fázemi je jedna akce)."""
    return set(_PARC.findall(text))


_KEEP_STRONG = re.compile(r"kupní smlouv|nákup|koup|smlouvu o dílo", re.IGNORECASE)


def _score(it):
    """Která z duplicit nejlépe reprezentuje akci (pro zobrazení)."""
    t = it[4]
    s = 2 if it[2] == "ZO" else 0                       # ZO = závazné schválení
    if _KEEP_STRONG.search(t):
        s += 3
    elif re.search(r"schvál", t, re.IGNORECASE):
        s += 1
    if re.search(r"na vědomí|vzal", t, re.IGNORECASE):
        s -= 3                                          # "bere na vědomí" = slabý záznam
    if re.search(r"úschov", t, re.IGNORECASE):
        s -= 1                                          # smlouva o úschově = vedlejší k nákupu
    return s


def dedup_projects(items):
    """Tentýž projekt/akvizice se ve feedu investic objeví jen JEDNOU. Dvě položky
    se shodnou částkou splývají, jsou-li: a) z téhož jednání (např. kupní smlouva +
    smlouva o úschově), b) z různých zdrojů (RO vyhodnocení ↔ ZO schválení) v okně
    90 dnů, nebo c) velká specifická částka ≥ 4 mil (tatáž stavba/nemovitost napříč
    časem). Ponechá se nejvýstižnější záznam (_score). Různé projekty s náhodně
    shodnou menší částkou z různých jednání zůstanou oba."""
    kept = []
    for it in sorted(items, key=lambda x: x[0]):
        idx = None
        for i, k in enumerate(kept):
            if k[1] != it[1]:                          # různá částka = různá akce
                continue
            same_meeting = (k[2] == it[2] and k[3] == it[3])
            d1, d2 = _date(k[0]), _date(it[0])
            close = bool(d1 and d2 and abs((d1 - d2).days) <= 90)
            share_parcel = bool(_parcels(k[4]) & _parcels(it[4]))
            if same_meeting or (k[2] != it[2] and close) or share_parcel or it[1] >= 4_000_000:
                idx = i
                break
        if idx is None:
            kept.append(it)
        elif _score(it) > _score(kept[idx]):
            kept[idx] = it
    return kept


akce = dedup_projects(akce)
akce.sort(key=lambda x: -x[1])
akce_years = sorted({int(a[0][:4]) for a in akce if a[0]}, reverse=True)

# --- zhotovitel / firma u každé akce (sloupec ve feedu) ---
# název firmy se bere AŽ ZA konektorem (společností/firmou) — tím se vynechají
# advokátní/dotační kanceláře (zprostředkovatelé "kanceláří"); cena patří vítězi.
_CONN = r"(?:[Ss]polečnost[íi]|[Ff]irm[ouy])\s+"
_FORM = r"(?:spol\.\s*s\.?\s*r\.?\s*o\.?|s\.\s*r\.\s*o\.?|a\.\s*s\.|v\.\s*o\.\s*s\.)"
_FIRM = re.compile(_CONN + r"([A-ZÁ-Ž0-9][\wáčďéěíňóřšťúůýž.&-]*(?:[ -][\wáčďéěíňóřšťúůýž0-9.&/-]+){0,4}?)\s*,?\s*" + _FORM)
_FIRM_DROP = re.compile(r"kancelář|advokát|dota[cč]", re.IGNORECASE)
# u KOUPĚ nemovitosti je uvedená firma PRODÁVAJÍCÍ, ne zhotovitel → nezobrazovat
_REALTY_BUY = re.compile(r"kupní smlouv|nákup|koup", re.IGNORECASE)
_REALTY = re.compile(r"budov|pozem|nemovit|jednotk|komerčn", re.IGNORECASE)


def _firm(text):
    if _REALTY_BUY.search(text) and _REALTY.search(text):
        return ""                                     # koupě nemovitosti — firma je prodávající
    for m in _FIRM.finditer(text):
        core = re.sub(r"\s*\d+/20\d\d/[A-Za-z]?\d+\s*", " ", m.group(1))   # vložené ID usnesení
        core = re.sub(r"\s*-\s*", "-", core)                               # sjednotit pomlčku
        core = re.sub(r"\s+", " ", core).strip(" ,.-").replace("POOR", "PORR")
        if len(core) >= 2 and not _FIRM_DROP.search(core):
            return core
    return ""


# --- tematická skupina akce (pořadí ROZHODUJE, první shoda vyhrává) ---
SKUPINY = [
    ("Energie", r"FVE|fotovolt|elektrárn|solárn|úspor\w*\s+energi|obnoviteln|tepeln\w*\s+čerpadl|energetick|elektrorozvaděč"),
    ("Voda", r"vodovod|kanalizac|\bČOV\b|odpadní\s+vod|dešťov|retenč|vodohospo"),
    ("Chodníky", r"chodník|přecház|přechod|lávk"),
    ("Komunikace", r"silnic|komunikac|cyklo|polní\s+cest|\bcest[ay]\b|rekonstrukc\w*\s+ul|parkov|zastávk|čekárn|autobus|\bmost\b|úvoz|dopravn|obrubník|značen"),
    ("Budovy", r"budov|nemovit|jednotk|nebytov|bytov|komerčn|obchodní\s+dům|SATOV|mateřsk|\bMŠ\b|\bZŠ\b|\bZUŠ\b|škol|zbrojnic|hasič|pošt|stavebn|vestavb|přístavb|novostavb|výtah|rekonstrukc|oprav|úprav|DPS|sociál|kabin|zázemí|střech"),
    ("Pozemky", r"pozem|parcel"),
    ("Prostranství", r"osvětlen|veřejn\w*\s+zele|\bzeleň|hřbitov|pohřeb|hřišt|sport|koupališt|mobiliář|kontejner|\bodpad|vzhled\s+obc|\bpark\b"),
    ("Ostatní", r"projektov|studie|dokumentac|výběrov|technick\w*\s+dozor|právní|příspěv|dotac|úschov"),
]
_SKUP = [(n, re.compile(kw, re.IGNORECASE)) for n, kw in SKUPINY]


def _skupina(text):
    for name, rx in _SKUP:
        if rx.search(text):
            return name
    return "Ostatní"


for a in akce:
    a.append(_firm(a[4]))        # index 6 = zhotovitel (název firmy, jinak "")
    a.append(_skupina(a[4]))     # index 7 = tematická skupina
    # index 8 = čas v záznamu (s) a index 9 = video id (jen ZO se záznamem a napárovaným bodem)
    a.append(zo_text_time.get(a[3], {}).get(a[4]) if a[2] == "ZO" else None)
    a.append(zo_vid.get(a[3], "") if a[2] == "ZO" else "")

# --- KPI ---
last = max(years)
kap_last = kap_by_year[last]
sum5 = sum(kap_by_year[y] for y in recent5)
share_last = round(kap_last / vyd_by_year[last] * 100) if vyd_by_year[last] else 0
rec_year = max(years, key=lambda y: kap_by_year[y])   # rok s nejvyššími investicemi
rec_val = kap_by_year[rec_year]
total_all = sum(kap_by_year.values())

try:                                  # parcela -> [lat, lon] (k.ú. Střelice u Brna)
    parcely_geo = json.load(open("data/parcely_geo.json", encoding="utf-8"))
except FileNotFoundError:
    parcely_geo = {}

def _load_geo(path):
    try:
        return json.load(open(path, encoding="utf-8"))
    except FileNotFoundError:
        return {}

ulice_geo = _load_geo("data/ulice_geo.json")   # název ulice -> [lat, lon] (OSM)
mista_geo = _load_geo("data/mista_geo.json")   # klíč místa (zs, ms, ou...) -> [lat, lon]
akce_geo = _load_geo("data/akce_geo.json") or []   # ruční opravy: podřetězec textu akce -> [lat, lon]

DATA = {
    "years": years,
    "kap": [kap_by_year[y] for y in years],
    "vyd": [vyd_by_year[y] for y in years],
    "yearDetail": year_detail,
    "akce": akce,
    "akceYears": akce_years,
    "pgeo": parcely_geo,
    "ugeo": ulice_geo,
    "mgeo": mista_geo,
    "ageo": akce_geo,
    "pop": POP,
    "minAkce": MIN_AKCE,
}
data_json = json.dumps(DATA, ensure_ascii=False, separators=(",", ":"))

def mil(v): return f"{v/1e6:.1f}".replace(".", ",")

body = f'''<header class="hero">
  <h1>Investice obce <span style="font-size:17px;font-weight:500;color:var(--muted)">· co se staví a opravuje</span></h1>
  <p>Kolik obec Střelice investuje do svého majetku — silnic a chodníků, školy a školky, budov a veřejných prostor — a které konkrétní stavby a zakázky za tím stojí. Kapitálové výdaje {years[0]}–{years[-1]} propojené s rozhodnutími rady a zastupitelstva.</p>
  <div class="chips"><span class="chip">zdroj: MONITOR Státní pokladny (FIN 2-12 M)</span><span class="chip">akce z usnesení RO a ZO</span><span class="chip">skutečné výdaje</span></div>
</header>

<div class="cards">
  <div class="kpi" style="--bar:var(--c0)"><div class="lab">Investice {last}</div><div class="val">{mil(kap_last)} mil</div><div class="delta" style="color:var(--muted)">kapitálové výdaje · {share_last} % všech výdajů</div></div>
  <div class="kpi" style="--bar:var(--c1)"><div class="lab">Za posledních 5 let</div><div class="val">{mil(sum5)} mil</div><div class="delta" style="color:var(--muted)">{min(recent5)}–{max(recent5)} · {(sum5/1e6/POP*1000):.0f} tis. Kč / obyvatele</div></div>
  <div class="kpi" style="--bar:var(--c3)"><div class="lab">Rekordní rok {rec_year}</div><div class="val">{mil(rec_val)} mil</div><div class="delta" style="color:var(--muted)">nejvíc investic za {len(years)} let</div></div>
  <div class="kpi" style="--bar:var(--c4)"><div class="lab">Celkem od {years[0]}</div><div class="val">{mil(total_all)} mil</div><div class="delta" style="color:var(--muted)">souhrn investic za {len(years)} let</div></div>
</div>

<section>
  <div class="sec-h"><h2>Vývoj investic v čase</h2><span class="hint">kapitálové výdaje · mil. Kč · klikni na rok pro detail</span></div>
  <div class="panel">
    <div class="chartbox sm"><canvas id="yearChart"></canvas></div>
    <p class="note">Po letech stabilních investic (~15–20 mil Kč ročně) přišly rekordní roky <b>2023</b> a <b>2024</b> — přístavba mateřské školy, rekonstrukce ulic a chodníků a další velké stavby. Kapitálové (investiční) výdaje jdou na pořízení a zhodnocení majetku obce, na rozdíl od běžných provozních výdajů.</p>
  </div>
</section>

<section>
  <div class="sec-h"><h2>Mapa investic</h2><span class="hint">kde se stavělo a opravovalo · klikni na bod</span></div>
  <div class="ctrls">
    <span class="lbl">Rok</span><span class="seg" id="mapYrSeg"></span>
  </div>
  <div class="panel" style="padding:10px">
    <div id="map"></div>
    <div class="legend" id="mapLeg" style="margin:10px 8px 4px"></div>
    <p class="note" style="margin:6px 8px 4px">Poloha akce se určuje automaticky — z čísla parcely v usnesení, názvu ulice nebo známého místa (škola, úřad, hřbitov…). Velikost bodu odpovídá částce. <span id="mapMiss"></span> Mapové podklady © přispěvatelé <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener" style="color:var(--accent)">OpenStreetMap</a> (vyžadují připojení k internetu).</p>
  </div>
</section>

<section>
  <div class="sec-h"><h2>Konkrétní akce a rozhodnutí</h2><span class="hint">z usnesení rady a zastupitelstva · od {MIN_AKCE//1000} tis. Kč výše</span></div>
  <div class="ctrls">
    <span class="lbl">Rok</span><span class="seg" id="yrSeg"></span>
    <span class="lbl" style="margin-left:8px">Skupina</span><select id="skupSel" class="oblsel"></select>
    <span class="lbl" style="margin-left:8px">Řadit</span><span class="seg" id="sortSeg"><button class="on" data-k="amount">Podle částky</button><button data-k="date">Podle data</button></span>
    <button class="dlbtn" id="dlAkce" style="margin-left:auto" title="Stáhnout aktuální výběr akcí jako CSV">⬇ Stáhnout CSV</button>
  </div>
  <div class="panel">
    <div class="tablewrap"><table id="tbl"><thead><tr><th>Datum</th><th>Skupina</th><th>Investiční akce</th><th>Zhotovitel</th><th class="r">Částka</th><th>Zdroj</th></tr></thead><tbody id="tbody"></tbody></table></div>
    <p class="note">Akce s uvedenou částkou z usnesení Rady obce (RO) a Zastupitelstva (ZO) — typicky smlouvy o dílo, vyhodnocení veřejných zakázek a dodatky. Tatáž stavba se může objevit dvakrát (rada vyhodnotí zakázku → zastupitelstvo schválí smlouvu). Částka je orientační, vychází z textu usnesení. Plné znění a kontext najdete v sekcích <a href="zapisy.html" style="color:var(--accent)">Rada obce</a> a <a href="zastupitelstvo.html" style="color:var(--accent)">Zastupitelstvo</a>.</p>
  </div>
</section>

<div class="modal" id="modal" hidden><div class="modal-bd" id="modalBd"></div>
  <div class="modal-card"><div class="modal-h"><b id="modalT"></b><button class="iconbtn" id="modalX" aria-label="Zavřít">✕</button></div>
  <div class="modal-c" id="modalC"></div></div></div>'''

scripts = '<style>' + '''
#tbl{width:100%;border-collapse:collapse;font-size:13.5px}
#tbl thead th{text-align:left;color:var(--muted);font-weight:600;font-size:11.5px;letter-spacing:.02em;
  padding:8px 14px 8px 0;border-bottom:1px solid var(--line)}
#tbl thead th.r{text-align:right}
#tbl tbody td{padding:11px 14px 11px 0;border-bottom:1px solid var(--line);vertical-align:top}
#tbl td.r{text-align:right;white-space:nowrap;font-variant-numeric:tabular-nums;font-weight:600}
#tbl td.dt{white-space:nowrap;color:var(--muted);font-size:12.5px}
.zsrc{display:inline-block;font-size:11.5px;padding:2px 8px;border-radius:999px;background:var(--inset);color:var(--muted);text-decoration:none;border:1px solid var(--line);white-space:nowrap}
.zsrc:hover{color:var(--accent);border-color:var(--accent)}
.srccell{display:flex;flex-direction:column;gap:4px;align-items:flex-start}
.zsrc.vid{color:var(--accent);font-weight:600;font-variant-numeric:tabular-nums}
.zsrc.vid:hover{background:var(--accent-soft);border-color:var(--accent)}
.tablewrap{overflow-x:auto}
.morebtn{margin:14px auto 0;display:block;background:var(--inset);border:1px solid var(--line);color:var(--text);
  font:inherit;font-size:13px;font-weight:500;padding:9px 20px;border-radius:10px;cursor:pointer;transition:.16s}
.morebtn:hover{border-color:var(--accent);color:var(--accent)}
.parc{color:var(--accent);text-decoration:none;border-bottom:1px dashed var(--accent);
  white-space:nowrap;font-variant-numeric:tabular-nums;cursor:pointer}
.parc:hover{background:var(--accent-soft);border-bottom-style:solid}
#tbl td.firmac{font-size:12.5px;min-width:120px}
.firma{font-weight:500}
.nofirm{color:var(--faint)}
#tbl td.skupc{white-space:nowrap}
.skup{display:inline-block;font-size:11px;padding:3px 9px 3px 8px;border-radius:999px;
  background:var(--inset);color:var(--text);border-left:3px solid var(--sc);white-space:nowrap}
.oblsel{font:inherit;font-size:13px;padding:6px 10px;border-radius:9px;border:1px solid var(--line);
  background:var(--surface);color:var(--text);cursor:pointer;max-width:280px}
.oblsel:hover{border-color:var(--accent)}
#map{height:460px;border-radius:12px;z-index:1}
/* ztlumený podklad — barevné body akcí na něm lépe vyniknou
   (filtr patří na .leaflet-tile-pane: leaflet.css má .leaflet-tile{filter:inherit}) */
.leaflet-tile-pane{filter:grayscale(.92) contrast(.92) brightness(1.04)}
/* !important: Leaflet si na kontejner píše position:relative inline stylem */
body.map-full #map{position:fixed!important;inset:0;height:auto;z-index:250;border-radius:0}
.mapfull-btn{display:block;width:34px;height:34px;background:var(--surface);color:var(--text);
  border:2px solid rgba(0,0,0,.25);border-radius:4px;cursor:pointer;font-size:17px;line-height:30px;padding:0;text-align:center}
.mapfull-btn:hover{background:var(--inset)}
html[data-theme="dark"] .leaflet-tile-pane{filter:grayscale(.5) brightness(.6) invert(1) contrast(3.2) hue-rotate(200deg) saturate(.1) brightness(.75)}
html[data-theme="dark"] .leaflet-container{background:#0d1424}
.leaflet-container{font-family:inherit}
.leaflet-popup-content-wrapper,.leaflet-popup-tip{background:var(--surface);color:var(--text);box-shadow:var(--shadow-h)}
.leaflet-popup-content{font-size:12.5px;line-height:1.5;margin:12px 14px;max-width:270px}
.mpop .amt{font-size:14px;font-weight:680;font-variant-numeric:tabular-nums}
.mpop .dt{color:var(--muted);font-size:11.5px}
.mpop p{margin:6px 0}
@media(max-width:640px){#map{height:340px}}
@media(max-width:640px){
  .tablewrap{overflow:visible}
  #tbl thead{display:none}
  #tbl,#tbl tbody{display:block}
  #tbl tbody tr{display:block;padding:12px 4px;border-bottom:1px solid var(--line)}
  #tbl tbody td{display:block;padding:2px 0;border:none;text-align:left}
  #tbl td.dt,#tbl td.skupc{display:inline-block;vertical-align:middle}
  #tbl td.dt{font-size:11.5px;margin-bottom:0}
  #tbl td.skupc{margin-left:6px}
  #tbl tbody td:nth-child(3){margin:5px 0}
  #tbl td.firmac,#tbl td.r{display:inline-block;vertical-align:middle}
  #tbl td.r{margin-left:8px}
  #tbl tbody td:nth-child(6){margin-top:4px}
}
</style>
<style>''' + LEAFLET_CSS + '''</style>
<script>''' + CHARTJS + '''</script>
<script>''' + LEAFLET_JS + '''</script>
<script>
const D=DATA_JSON;
const nf=new Intl.NumberFormat('cs-CZ');
const charts={};
function axis(){return {grid:{color:isDark()?'#1f2a40':'#eef2f7'},ticks:{color:cssv('--muted')}};}
function mk(id,cfg){if(charts[id])charts[id].destroy();charts[id]=new Chart(document.getElementById(id),cfg);}
function mil(v){return (v/1e6).toLocaleString('cs-CZ',{minimumFractionDigits:1,maximumFractionDigits:1})+' mil';}
function castka(v){return v>=1e6?mil(v)+' Kč':nf.format(Math.round(v/1000))+' tis. Kč';}

// ---- proklik parcelních čísel a čísel budov (č. p.) do katastrální mapy ----
const PGEO=D.pgeo||{};
const PARC_RE=/((?:p(?:arc)?\\.?\\s*č\\.?|parcel\\w*\\s*č\\.?)\\s*)(\\d{1,5}(?:\\/\\d{1,4})?)/gi;
const CP_RE=/(č\\.?\\s*p\\.?\\s*)(\\d{1,4})\\b/gi;
const ONP_RE=/na pozemku\\s+(?:parc|p)\\.?\\s*č\\.?\\s*(\\d{1,5}(?:\\/\\d{1,4})?)/i;
// jiné k.ú. než Střelice — souřadnice nemáme, nelinkujeme
const OTHER_KU=/k\\.?\\s*ú\\.?\\s*(Troubsk|Ostopovic|Omic|Radostic|Popůvk|Heršpic|Tetčic|Nebovid|Rosic|Žebětín|Bosonoh|Modřic|Želešic|Šlapanic)/i;
function _esc(s){return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');}
function _kat(g,label,title){
  const u='https://www.ikatastr.cz/#kde='+g[0]+','+g[1]+',18&mapa=zakladni&vrstvy=parcelybudovy&info='+g[0]+','+g[1];
  return '<a class="parc" href="'+u+'" target="_blank" rel="noopener" onclick="event.stopPropagation()" title="'+title+'">'+label+'</a>';
}
function linkifyMap(text){
  let html=_esc(text);
  if(OTHER_KU.test(text)) return html;
  // souřadnice budovy = parcela, na které stojí (jinak první geokódovaná v textu)
  let bg=null;
  const onp=text.match(ONP_RE);
  if(onp && PGEO[onp[1]]) bg=PGEO[onp[1]];
  if(!bg) for(const mm of text.matchAll(PARC_RE)){ if(PGEO[mm[2]]){bg=PGEO[mm[2]];break;} }
  html=html.replace(PARC_RE,(m,pre,num)=>{const g=PGEO[num];
    return g?pre+_kat(g,num,'Parcela č. '+num+' v katastrální mapě (k.ú. Střelice u Brna)'):m;});
  if(bg) html=html.replace(CP_RE,(m,pre,num)=>pre+_kat(bg,num,'Budova č. p. '+num+' v katastrální mapě'));
  return html;
}

function yearChart(){
  const lab=D.years, val=D.kap.map(v=>+(v/1e6).toFixed(2));
  mk('yearChart',{type:'bar',data:{labels:lab,datasets:[{label:'Kapitálové výdaje',data:val,
    backgroundColor:lab.map(y=>y>=2023?cssv('--c3'):cssv('--c0')),borderRadius:5}]},
    options:{responsive:true,maintainAspectRatio:false,animation:{duration:500},
      onClick:(e,a,ch)=>{const el=ch.getElementsAtEventForMode(e,'nearest',{intersect:false},true)[0];if(el)yearModal(D.years[el.index]);},
      onHover:(e,els)=>{if(e.native)e.native.target.style.cursor=els.length?'pointer':'default';},
      plugins:{legend:{display:false},tooltip:{callbacks:{label:c=>'Investice '+c.label+': '+mil(c.parsed.y*1e6)+' Kč · klikni pro detail'}}},
      scales:{x:axis(),y:Object.assign(axis(),{ticks:{color:cssv('--muted'),callback:v=>v+' mil'}})}}});
}


// --- feed konkrétních akcí ---
let curYear='vse', curSkup='', sortK='amount', shown=12;
const PAGE=12;
// Matcher oblasti pro filtr akcí ve feedu (odvozeno z názvu oddílu rozpočtu).
// ci = kmeny case-insensitive; cs = ZKRATKY jen velkými (MŠ/ZŠ/ČOV) — jinak by
// "ZŠ" chytlo "roZŠíření", "ČOV" chytlo "léČOVání" apod.
// barvy skupin (index do palety --c0..--c7)
const SKUP_COLOR={'Energie':3,'Voda':6,'Chodníky':0,'Komunikace':5,
  'Budovy':1,'Pozemky':2,'Prostranství':9,'Ostatní':8};
function skupCount(name){return D.akce.filter(x=>x[7]===name).length;}
function filtered(){
  let a=D.akce.slice();
  if(curYear!=='vse') a=a.filter(x=>x[0].slice(0,4)===curYear);
  if(curSkup) a=a.filter(x=>x[7]===curSkup);
  a.sort(sortK==='amount'?(p,q)=>q[1]-p[1]:(p,q)=>(q[0]||'').localeCompare(p[0]||''));
  return a;
}
function fmtDate(iso){if(!iso)return '—';const p=iso.split('-');return p[2]+'. '+(+p[1])+'. '+p[0];}
function fmtT(s){return Math.floor(s/60)+':'+String(s%60).padStart(2,'0');}
function renderTbl(){
  const a=filtered(), slice=a.slice(0,shown);
  document.getElementById('tbody').innerHTML=slice.map(x=>{
    const secUrl=(x[2]==='ZO'?'zastupitelstvo.html?zo=':'zapisy.html?ro=')+x[3];
    const secTit=x[2]==='ZO'?'Zobrazit usnesení tohoto zasedání v sekci Zastupitelstvo':'Zobrazit usnesení tohoto jednání v sekci Rada obce';
    let srcParts=[`<a class="zsrc" href="${secUrl}" title="${secTit}">${x[2]} č.&nbsp;${x[3]}</a>`];
    if(x[5]) srcParts.push(`<a class="zsrc" href="${x[5]}" target="_blank" rel="noopener" title="Originální zápis (PDF)">PDF&nbsp;&#8599;</a>`);
    if(x[8]&&x[9]) srcParts.push(`<a class="zsrc vid" href="https://youtu.be/${x[9]}?t=${x[8]}" target="_blank" rel="noopener" title="Skočit na projednávání bodu v záznamu jednání">&#9654;&nbsp;${fmtT(x[8])}</a>`);
    const src=`<div class="srccell">${srcParts.join('')}</div>`;
    const firma=x[6]?`<span class="firma">${x[6]}</span>`:'<span class="nofirm">—</span>';
    const sk=`<span class="skup" style="--sc:var(--c${SKUP_COLOR[x[7]]??8})">${x[7]}</span>`;
    return `<tr><td class="dt">${fmtDate(x[0])}</td><td class="skupc">${sk}</td><td>${linkifyMap(x[4])}</td><td class="firmac">${firma}</td><td class="r">${castka(x[1])}</td><td>${src}</td></tr>`;
  }).join('');
  const wrap=document.getElementById('moreWrap');
  wrap.innerHTML = a.length>shown ? `<button class="morebtn" id="more">Zobrazit další (${a.length-shown})</button>` : '';
  const mb=document.getElementById('more'); if(mb) mb.onclick=()=>{shown+=PAGE;renderTbl();};
}
function setYear(y){
  curYear=y; shown=PAGE;
  document.querySelectorAll('#yrSeg button').forEach(x=>x.classList.toggle('on',x.dataset.y===y));
  renderTbl();
}
function buildYrSeg(){
  const seg=document.getElementById('yrSeg');
  seg.innerHTML='<button class="on" data-y="vse">Vše</button>'+D.akceYears.map(y=>`<button data-y="${y}">${y}</button>`).join('');
  seg.querySelectorAll('button').forEach(b=>b.onclick=()=>setYear(b.dataset.y));
}
function buildSkupSel(){
  const sel=document.getElementById('skupSel'); if(!sel)return;
  const names=[...new Set(D.akce.map(x=>x[7]))].map(nm=>({nm,c:skupCount(nm)})).sort((a,b)=>b.c-a.c);
  sel.innerHTML='<option value="">Všechny skupiny</option>'+names.map(o=>`<option value="${o.nm}">${o.nm} (${o.c})</option>`).join('');
  sel.value=curSkup;
  sel.onchange=()=>setSkup(sel.value);
}
function setSkup(name){
  curSkup=name; shown=PAGE;
  const sel=document.getElementById('skupSel'); if(sel)sel.value=name;
  renderTbl();
}

// --- detailní modal (klik na graf) ---
const modal=document.getElementById('modal');
function openModal(title,html){document.getElementById('modalT').textContent=title;document.getElementById('modalC').innerHTML=html;modal.hidden=false;}
function closeModal(){modal.hidden=true;}
function mtab(arr,totLab,tot){
  let h='<table class="mtab"><tbody>';
  h+=arr.map(x=>`<tr><td>${x[0]}</td><td><b>${castka(x[1])}</b></td></tr>`).join('');
  if(tot!=null)h+=`<tr class="total"><td>${totLab}</td><td>${castka(tot)}</td></tr>`;
  return h+'</tbody></table>';
}
function yearModal(y){
  const d=D.yearDetail[y]; if(!d)return;
  let h=`<p class="note" style="margin:2px 0 12px">Největší investiční (kapitálové) výdaje obce v roce ${y} podle rozpočtových položek (paragrafů).</p>`;
  h+=mtab(d.par,null,null);
  if(D.akceYears.includes(+y))
    h+=`<button class="morebtn" id="goAkce" style="margin-top:16px">Zobrazit konkrétní akce z roku ${y} →</button>`;
  openModal('Investice '+y+' — '+castka(d.tot),h);
  const g=document.getElementById('goAkce');
  if(g)g.onclick=()=>{closeModal();setYear(''+y);document.getElementById('tbl').scrollIntoView({behavior:'smooth',block:'center'});};
}
// ---- mapa investic ----
const MGEO=D.mgeo||{}, UGEO=D.ugeo||{};
// pozor: JS \\b nefunguje po znacích s diakritikou ("Školní\\b" nikdy nematchne)
// -> hranice slova řešíme unicode lookaround (?<!\\p{L}) ... (?!\\p{L}) s flagem 'u'
const MISTA_RX=[
  [/mateřsk|(?<!\\p{L})MŠ(?!\\p{L})/u,'ms'],[/základní škol|(?<!\\p{L})ZŠ(?!\\p{L})/u,'zs'],
  [/(?<!\\p{L})ZUŠ(?!\\p{L})|uměleck/u,'zus'],
  [/obecní(?:ho)?\\s+úřad|radnic/,'ou'],[/hřbitov|pohřeb/,'hrbitov'],[/koupališt/,'koupaliste'],
  [/sokolovn/,'sokolovna'],[/pečovatel|(?<!\\p{L})DPS(?!\\p{L})/u,'dps'],
  [/KESI/,'kesi'],[/hasič|zbrojnic/i,'hasici'],
  [/u Trnků/i,'trnky'],[/nádraž/i,'nadrazi'],
  [/(?<!\\p{L})ČOV(?!\\p{L})|čistírn/u,'cov'],[/kostel/,'kostel'],
  [/Lotrůvk/,'lotruvka'],[/Bobrav/,'bobrava'],[/Březeč/,'brezeci']];  // liniové stavby -> střed trasy
const GEN_RX=[[/škol/,'zs']];   // obecné "škola/školou" až jako poslední záchrana (až po ulicích)
const _rxesc=s=>s.replace(/[.*+?^${}()|[\\]\\\\]/g,'\\\\$&');
const UL_RX=Object.keys(UGEO).map(nm=>{
  // skloňování názvů ulic: Brněnská -> Brněnské/Brněnskou, Školní -> Školního/Školním
  let rx;
  if(nm==='Nová ulice') rx='(Nová ulice|Nové ulici|ulic\\\\w* Nová|ul\\\\. Nová)';
  else if(/á$/.test(nm)) rx=_rxesc(nm.slice(0,-1))+'(á|é|ou)(?!\\\\p{L})';
  else if(/í$/.test(nm)) rx=_rxesc(nm)+'(ho|mu|m|ch)?(?!\\\\p{L})';
  else rx=_rxesc(nm)+'(?!\\\\p{L})';
  return [new RegExp(rx,'u'),nm];
});
const OD_RX=/obchodn\\p{L}*\\s+d[oů]m\\p{L}*|SATOV/iu;   // obchodní dům = vždy budova SATOV
function geoOf(text){
  // ruční opravy mají přednost přede vším (data/akce_geo.json):
  // {match, geo:[lat,lon]} = pevné souřadnice; {match, misto:"zs"} = odkaz na místo
  for(const o of (D.ageo||[])){if(text.includes(o.match)){
    const g=o.geo||(o.misto&&MGEO[o.misto]); if(g)return g; break;}}
  if(OTHER_KU.test(text))return null;
  // obchodní dům SATOV má přednost i před parcelami (smlouvy k němu
  // často uvádějí čísla okolních pozemků, bod by uskočil vedle)
  if(OD_RX.test(text)&&MGEO.od)return MGEO.od;
  const onp=text.match(ONP_RE); if(onp&&PGEO[onp[1]])return PGEO[onp[1]];
  for(const mm of text.matchAll(PARC_RE)){const g=PGEO[mm[2]];if(g)return g;}
  // konkrétní budova/místo (MŠ, ZŠ, ČOV…) je přesnější než střed ulice
  for(const [rx,k] of MISTA_RX){if(rx.test(text)&&MGEO[k])return MGEO[k];}
  for(const [rx,nm] of UL_RX){if(rx.test(text))return UGEO[nm];}
  for(const [rx,k] of GEN_RX){if(rx.test(text)&&MGEO[k])return MGEO[k];}
  // fallback: akce bez místa (nákupy, dokumentace, příspěvky, akce po celé obci)
  // se zobrazí u obecního úřadu s poznámkou v popupu
  return MGEO.ou?{f:MGEO.ou}:null;
}
let map=null,mapLayer=null,mapYear='vse';
function renderMap(){
  if(typeof L==='undefined'||!document.getElementById('map'))return;
  if(!map){
    map=L.map('map',{scrollWheelZoom:false});
    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',
      {maxZoom:19,attribution:'&copy; přispěvatelé OpenStreetMap'}).addTo(map);
    map.setView([49.1525,16.4965],15);
    // tlačítko zvětšení na celou obrazovku (Esc = zpět)
    const FullCtl=L.Control.extend({options:{position:'topleft'},onAdd(){
      const b=L.DomUtil.create('button','mapfull-btn');
      b.innerHTML='⛶';b.title='Zvětšit mapu na celou obrazovku';
      L.DomEvent.on(b,'click',e=>{L.DomEvent.stop(e);toggleMapFull();});
      return b;}});
    map.addControl(new FullCtl());
  }
  if(mapLayer)mapLayer.remove();
  mapLayer=L.layerGroup().addTo(map);
  let placed=0,missed=0,fallback=0;const pts=[],skupSeen=new Set();
  // mírný rozptyl bodů na témže místě, ať se nepřekrývají úplně
  const seen={};
  D.akce.forEach(x=>{
    if(mapYear!=='vse'&&x[0].slice(0,4)!==mapYear)return;
    let g=geoOf(x[4]), fb=false;
    if(g&&g.f){g=g.f;fb=true;fallback++;}
    if(!g){missed++;return;}
    placed++;skupSeen.add(x[7]);
    // překrývající se body rozestoupit po malém kruhu (~10 m), ať jdou rozkliknout
    const key=g[0]+','+g[1], n=(seen[key]=(seen[key]||0)+1);
    const lat=g[0]+(n>1?Math.cos(n*2.4)*0.00009:0), lon=g[1]+(n>1?Math.sin(n*2.4)*0.00013:0);
    const clr=cssv('--c'+(SKUP_COLOR[x[7]]??8));
    const r=Math.min(24,5+Math.sqrt(x[1]/1e6)*3.4);
    const secUrl=(x[2]==='ZO'?'zastupitelstvo.html?zo=':'zapisy.html?ro=')+x[3];
    const txt=_esc(x[4].length>190?x[4].slice(0,187)+'…':x[4]);
    const pop=`<div class="mpop"><div class="dt">${fmtDate(x[0])} · ${x[7]}${x[6]?' · '+_esc(x[6]):''}</div>
      <p>${txt}</p><div class="amt">${castka(x[1])}</div>
      ${fb?'<div class="dt">📌 akce bez konkrétního místa — zobrazena u obecního úřadu</div>':''}
      <p><a href="${secUrl}" style="color:var(--accent)">${x[2]} č. ${x[3]} →</a>${x[5]?` · <a href="${x[5]}" target="_blank" rel="noopener" style="color:var(--accent)">PDF ↗</a>`:''}</p></div>`;
    L.circleMarker([lat,lon],{radius:r,color:clr,weight:1.6,fillColor:clr,fillOpacity:fb?.22:.5,dashArray:fb?'4 4':null})
      .bindPopup(pop).addTo(mapLayer);
    pts.push([lat,lon]);
  });
  if(pts.length)map.fitBounds(pts,{padding:[28,28],maxZoom:16});
  document.getElementById('mapLeg').innerHTML=[...skupSeen].sort()
    .map(nm=>`<span><i class="sw" style="background:${cssv('--c'+(SKUP_COLOR[nm]??8))}"></i>${nm}</span>`).join('');
  document.getElementById('mapMiss').textContent = fallback
    ? `${fallback} akcí bez konkrétního místa (nákupy, dokumentace, příspěvky…) je zobrazeno čárkovaně u obecního úřadu.` : '';
}
function toggleMapFull(){
  const on=document.body.classList.toggle('map-full');
  const b=document.querySelector('.mapfull-btn');
  if(b){b.innerHTML=on?'✕':'⛶';b.title=on?'Zavřít celoobrazovkovou mapu (Esc)':'Zvětšit mapu na celou obrazovku';}
  map.options.scrollWheelZoom=on;   // na celé obrazovce dává zoom kolečkem smysl
  if(on)map.scrollWheelZoom.enable();else map.scrollWheelZoom.disable();
  setTimeout(()=>map.invalidateSize(),80);
}
document.addEventListener('keydown',e=>{
  if(e.key==='Escape'&&document.body.classList.contains('map-full'))toggleMapFull();});
function buildMapYrSeg(){
  const seg=document.getElementById('mapYrSeg'); if(!seg)return;
  seg.innerHTML='<button class="on" data-y="vse">Vše</button>'+D.akceYears.map(y=>`<button data-y="${y}">${y}</button>`).join('');
  seg.querySelectorAll('button').forEach(b=>b.onclick=()=>{
    seg.querySelectorAll('button').forEach(x=>x.classList.toggle('on',x===b));
    mapYear=b.dataset.y;renderMap();});
}

function redraw(){yearChart();renderMap();}
document.getElementById('dlAkce').onclick=()=>{
  dlCSV('strelice_investicni_akce.csv',
    ['datum','skupina','akce','zhotovitel','castka_kc','zdroj','zasedani','pdf_url'],
    filtered().map(x=>[x[0],x[7],x[4],x[6],x[1],x[2],x[3],x[5]]));};
buildYrSeg();
document.querySelectorAll('#sortSeg button').forEach(b=>b.onclick=()=>{document.querySelectorAll('#sortSeg button').forEach(x=>x.classList.remove('on'));b.classList.add('on');sortK=b.dataset.k;shown=PAGE;renderTbl();});
document.getElementById('modalX').onclick=closeModal;
document.getElementById('modalBd').onclick=closeModal;
document.addEventListener('keydown',e=>{if(e.key==='Escape')closeModal();});
yearChart();buildSkupSel();renderTbl();buildMapYrSeg();renderMap();
bindTheme(redraw);
window.addEventListener('load',()=>{Object.values(charts).forEach(c=>{try{c.resize();}catch(e){}});});
</script>'''.replace("DATA_JSON", data_json)

# vložit kontejner pro tlačítko "více" za tabulku
body = body.replace('</table></div>\n    <p class="note">Akce', '</table></div>\n    <div id="moreWrap"></div>\n    <p class="note">Akce')

html = pc.page("Investice", "Investice — Jak žijí Střelice", body, body_scripts=scripts)
open("investice.html", "w", encoding="utf-8").write(html)
print(f"HOTOVO: investice.html — {len(years)} let, {len(akce)} akcí")
