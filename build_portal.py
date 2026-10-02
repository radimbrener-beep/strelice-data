#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generuje rozcestník (index.html) a sekci Školství (skolstvi.html)
portálu obce Střelice. Sdílené prvky z portal_common.py."""
import sys, csv, json
import portal_common as pc
sys.stdout.reconfigure(encoding="utf-8")

CHARTJS = open("data/vendor/chart.umd.js", encoding="utf-8").read()

# ---- demografická data ČSÚ ----
def num(s):
    try: return int(float((s or "").strip()))
    except: return None
dem = []
for r in csv.DictReader(open("data/skolstvi/strelice_demografie.csv", encoding="utf-8-sig"), delimiter=";"):
    y = num(r["rok"])
    if y and y >= 2000:
        dem.append({"rok": y, "stav": num(r["stav"]), "nar": num(r["narozeni"]),
                    "zem": num(r["zemreli"]), "pri": num(r["pristehovali"]), "vys": num(r["vystehovali"])})
last = dem[-1]

# ================= INDEX (rozcestník) =================
tiles = [
    ("obdobi.html", "Bilance období 2022–2026", "bi", True,
     "Co zastupitelstvo a rada za čtyři roky rozhodly, kolik se proinvestovalo, časová osa klíčových rozhodnutí — a docházka, hlasování a vystoupení jednotlivých zastupitelů.",
     "Otevřít bilanci →", "nové"),
    ("hledat.html", "Hledat a Moje ulice", "hl", True,
     "Jedno hledání přes celý portál — usnesení, diskuze na zastupitelstvu, firmy, dotace i rozpočet. A přehled všeho, co se řešilo ve vaší ulici, na mapě.",
     "Hledat →", "nové"),
    ("rozpocet.html", "Rozpočet", "ti", True,
     "Příjmy, výdaje a saldo 2013–2025, tok peněz, struktura podle oblastí a položek, dotace přijaté i poskytnuté. Rozklikávací detail a slovníček pojmů.",
     "Otevřít rozpočet →", None),
    ("srovnani.html", "Srovnání se sousedy", "sr", True,
     "Jak si Střelice vedou vedle okolních obcí — příjmy, investice, dluh a rezervy na obyvatele. A karty finančního zdraví obce podle metodiky MF.",
     "Otevřít srovnání →", None),
    ("investice.html", "Investice", "in", True,
     "Co se v obci staví a opravuje — kapitálové výdaje v čase a podle oblasti, propojené s konkrétními zakázkami a smlouvami z usnesení rady a zastupitelstva.",
     "Otevřít investice →", None),
    ("zakazky.html", "Zakázky obce", "za", True,
     "Komu obec platí — firmy a jejich zakázky 2022–2026. Žebříček dodavatelů, kolik zakázek a za kolik získali, s rozklikem na jednotlivé smlouvy a usnesení.",
     "Otevřít zakázky →", None),
    ("dotace.html", "Komu obec přispívá", "do", True,
     "Dotace spolkům a organizacím 2022–2026 — kolik, komu a na co. Žebříček příjemců a vývoj objemu v čase.",
     "Otevřít dotace →", None),
    ("skolstvi.html", "Školství", "sk", True,
     "Demografický vývoj obce a poptávka po vzdělávání — mateřská a základní škola, ZUŠ, kapacity.",
     "Otevřít školství →", None),
    ("zapisy.html", "Rada obce", "ra", True,
     "Zápisy z jednání Rady obce 2022–2026 — u každého jednání krátké shrnutí, fulltextové hledání v usneseních, filtr podle roku a tématu, odkaz na originální PDF a u parcelních čísel proklik přímo do katastrální mapy.",
     "Procházet zápisy →", None),
    ("zastupitelstvo.html", "Zastupitelstvo", "zo", True,
     "Usnesení zastupitelstva 2022–2026 — shrnutí každého zasedání, výsledky hlasování, témata, výdaje, účast i prokliky parcel do katastru. U zasedání se záznamem na YouTube navíc proklik na přesný čas ve videu u jednotlivých bodů jednání.",
     "Procházet usnesení →", None),
    ("demografie.html", "Demografie", "de", True,
     "Jak Střelice rostou — počet obyvatel od roku 1971, narození a úmrtí, kolik lidí se přistěhovalo a odstěhovalo.",
     "Otevřít demografii →", "nové"),
    ("volby.html", "Volby", "vo", True,
     "Jak Střelice volí — složení zastupitelstva z komunálních voleb 2022, zvolení zastupitelé, sněmovní a prezidentské volby v obci.",
     "Otevřít volby →", "nové"),
]
# jednobarevné linkové ikony dlaždic (24×24, tah currentColor — barvu dává CSS .tile .ic)
TILE_ICONS = {
    "ti": '<ellipse cx="12" cy="6" rx="7" ry="3"/><path d="M5 6v6c0 1.7 3.1 3 7 3s7-1.3 7-3V6M5 12v6c0 1.7 3.1 3 7 3s7-1.3 7-3v-6"/>',
    "sr": '<path d="M12 4v16M7 20h10M5 7h14M5 7l-3 6a3 3 0 0 0 6 0zM19 7l-3 6a3 3 0 0 0 6 0z"/>',
    "in": '<path d="M3 21h18M5 21V11l5-3v13M10 21V4l9 4v13M14 11h2M14 15h2"/>',
    "za": '<path d="M6 3h12v18l-3-2-3 2-3-2-3 2zM9 8h6M9 12h6M9 16h3"/>',
    "sk": '<path d="M2 9l10-5 10 5-10 5zM6 11v5c0 1.5 2.7 3 6 3s6-1.5 6-3v-5M22 9v6"/>',
    "ra": '<rect x="5" y="4" width="14" height="17" rx="2"/><path d="M9 4V3h6v1M9 10h6M9 14h6M9 18h3"/>',
    "do": '<path d="M12 20s-7-4.4-7-10a4 4 0 0 1 7-2.6A4 4 0 0 1 19 10c0 5.6-7 10-7 10z"/>',
    "zo": '<path d="M3 10l9-6 9 6M5 10v8M9.5 10v8M14.5 10v8M19 10v8M3 21h18"/>',
    "pl": '<path d="M12 5v14M5 12h14"/>',
    "bi": '<path d="M4 20h16M7 16v-4M12 16V8M17 16V5"/>',
    "hl": '<circle cx="11" cy="11" r="6"/><path d="M20 20l-4.5-4.5"/>',
    "de": '<circle cx="9" cy="8" r="3"/><path d="M3 20c0-3.3 2.7-6 6-6s6 2.7 6 6M16 5.5a3 3 0 0 1 0 5.5M18 14.5c1.8.9 3 2.9 3 5.5"/>',
    "vo": '<path d="M4 12h16v8H4zM8 12V5h8v7M10 8.5l1.5 1.5L14 7.5"/>',
}
tile_html = ""
for href, name, ic, active, desc, go, badge in tiles:
    cls = "tile" + ("" if active else " soon")
    badge_html = f'<span class="badge">{badge}</span>' if badge else ""
    go_html = f'<span class="go">{go}</span>' if go else ""
    icon = '<svg viewBox="0 0 24 24" aria-hidden="true">' + TILE_ICONS.get(ic, TILE_ICONS["pl"]) + '</svg>'
    tile_html += f'''<a class="{cls}" href="{href}">{badge_html}
      <span class="ic">{icon}</span><h3>{name}</h3><p>{desc}</p>{go_html}</a>'''

# --- panel "Co je noveho" — naposledy pridane zapisy ze ZO a RO (automaticky z dat) ---
# Zobrazene datum = kdy se zapis objevil na portalu (published.json), ne datum zasedani.
# Backlog ma datum spusteni portalu; nove zapisy build orazitkuje dnem sestaveni.
import datetime
_PUB_PATH = "published.json"
try:
    _pub = json.load(open(_PUB_PATH, encoding="utf-8"))
except FileNotFoundError:
    _pub = {}
_pub.setdefault("ZO", {})
_pub.setdefault("RO", {})
_today = datetime.date.today().isoformat()
_dirty = False

def _fmt_d(iso):
    p = iso.split("-")
    return f"{int(p[2])}. {int(p[1])}. {p[0]}"

def _pubdate(grp, cislo):
    global _dirty
    k = str(cislo)
    if k not in _pub[grp]:
        _pub[grp][k] = _today
        _dirty = True
    return _pub[grp][k]

_feed = []
for _m in json.load(open("dataset_ZO.json", encoding="utf-8")):
    _c = _m["cislo_zasedani"]
    _feed.append((_pubdate("ZO", _c), _m["datum"], "Zastupitelstvo", "#e0a458",
                  f'Zápis z {_c}. zasedání zastupitelstva <span class="updmd">· zasedání {_fmt_d(_m["datum"])}</span>',
                  f'zastupitelstvo.html?zo={_c}'))
for _m in json.load(open("dataset_RO.json", encoding="utf-8")):
    _c = _m["cislo_zasedani"]
    _feed.append((_pubdate("RO", _c), _m["datum"], "Rada obce", "#85b7eb",
                  f'Zápis z {_c}. jednání rady obce <span class="updmd">· jednání {_fmt_d(_m["datum"])}</span>',
                  f'zapisy.html?ro={_c}'))
if _dirty:
    json.dump(_pub, open(_PUB_PATH, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
# jen nejnovejsi zaznam z kazde sekce (jeden ZO + jeden RO)
_best = {}
for _row in _feed:
    _s = _row[2]
    if _s not in _best or (_row[0], _row[1]) > (_best[_s][0], _best[_s][1]):
        _best[_s] = _row
# vysledne radky razeny podle data publikace (pri shode podle data zasedani), sestupne
_shown = sorted(_best.values(), key=lambda x: (x[0], x[1]), reverse=True)
updlist = "".join(
    f'<a class="updrow" href="{lnk}"><span class="upddate"><small>přidáno</small>{_fmt_d(pubd)}</span>'
    f'<span class="updsec"><i style="background:{col}"></i>{sec}</span>'
    f'<span class="updtxt">{txt}</span><span class="updarr">&#8594;</span></a>'
    for pubd, _md, sec, col, txt, lnk in _shown)
upd_panel = ('<section><div class="panel">'
             '<div class="sec-h" style="margin:0 0 8px"><h2 style="font-size:16px">Co je nového</h2>'
             '<span class="hint">poslední zápis z každé sekce · datum = kdy přibyl na portál</span></div>'
             f'<div class="updlist">{updlist}</div></div></section>')

UPD_CSS = '''<style>
.updlist{display:flex;flex-direction:column}
.updrow{display:flex;align-items:center;gap:12px;padding:10px 6px;border-radius:10px;text-decoration:none;color:var(--text);border-bottom:1px solid var(--line)}
.updlist .updrow:last-child{border-bottom:0}
.updrow:hover{background:var(--inset)}
.upddate{color:var(--muted);font-size:12.5px;min-width:88px;white-space:nowrap;font-variant-numeric:tabular-nums}
.updsec{display:inline-flex;align-items:center;font-size:11px;font-weight:600;color:var(--muted);background:var(--inset);border:1px solid var(--line);padding:2px 9px;border-radius:999px;white-space:nowrap}
.updsec i{width:8px;height:8px;border-radius:2px;display:inline-block;margin-right:6px}
.updtxt{font-size:13.5px;flex:1}
.updmd{color:var(--muted);font-size:12.5px}
.upddate small{display:block;font-size:10.5px;color:var(--faint);line-height:1.1}
.updarr{color:var(--faint);font-size:14px}
@media(max-width:560px){.updrow{flex-wrap:wrap;gap:6px 10px}.updtxt{flex-basis:100%;order:3;font-size:13px}.updarr{display:none}}
</style>'''

pop_fmt = f'{last["stav"]:,}'.replace(",", " ")

# --- poutač „období v číslech" s animovaným počítadlem (hero) ---
import os
def _emb(path):
    t = open(path, encoding="utf-8").read(); i = t.index("const D=") + 8
    return json.JSONDecoder().raw_decode(t[i:])[0]
_ro = json.load(open("dataset_RO.json", encoding="utf-8"))
_zo_n = len(json.load(open("dataset_ZO.json", encoding="utf-8")))
# počet usnesení ZO stejně jako sekce Zastupitelstvo (vč. doplnění nečitelného ZO 27)
_zo_b = (sum(len(m["b"]) for m in _emb("zastupitelstvo.html")["meet"]) if os.path.exists("zastupitelstvo.html")
         else sum(len(m["body"]) for m in json.load(open("dataset_ZO.json", encoding="utf-8"))))
_body = sum(len(m["body"]) for m in _ro) + _zo_b
_jed = len(_ro) + _zo_n
_fin = list(csv.DictReader(open("data/strelice_finm201_2013_2025.csv", encoding="utf-8-sig"), delimiter=";"))
_kap = sum(float(r["skutecnost"] or 0) for r in _fin if 2022 <= int(r["rok"]) <= 2025 and r["trida"] == "Kapitálové výdaje")
_dot = 0
for r in csv.DictReader(open("data/dotace_strelice.csv", encoding="utf-8-sig"), delimiter=";"):
    try: _dot += int(r["castka"])
    except ValueError: pass
def _cnt(v, dec=0):
    shown = (f"{v:,.{dec}f}").replace(",", " ").replace(".", ",")
    return f'<b class="cnt" data-v="{v:.{dec}f}" data-d="{dec}">{shown}</b>'
POUTAC = (f'<a class="poutac" href="obdobi.html"><span class="pt">Volební období 2022–2026 v číslech</span>'
          f'<span class="pl">Rada a zastupitelstvo projednaly {_cnt(_body)} bodů na {_cnt(_jed)} jednáních, '
          f'obec proinvestovala {_cnt(_kap/1e6, 1)} mil. Kč a spolkům přispěla {_cnt(_dot/1e6, 1)} mil. Kč.</span>'
          f'<span class="pg">Celá bilance období a aktivita zastupitelů →</span></a>')
POUTAC_CSS = """<style>
.poutac{display:block;margin:18px 0 0;padding:18px 22px;border-radius:var(--radius);text-decoration:none;color:var(--text);
  background:linear-gradient(135deg,var(--accent-soft),transparent 70%),var(--surface);border:1px solid var(--line);box-shadow:var(--shadow);transition:transform .2s,box-shadow .2s}
.poutac:hover{transform:translateY(-2px);box-shadow:var(--shadow-h)}
.poutac .pt{display:block;font-size:12px;font-weight:650;letter-spacing:.05em;text-transform:uppercase;color:var(--accent);margin-bottom:6px}
.poutac .pl{display:block;font-size:17px;line-height:1.6}
.poutac .cnt{font-size:22px;font-weight:720;color:var(--accent);font-variant-numeric:tabular-nums;letter-spacing:-.01em}
.poutac .pg{display:block;margin-top:8px;font-size:13px;color:var(--muted)}
@media(max-width:560px){.poutac .pl{font-size:15.5px}.poutac .cnt{font-size:19px}}
</style>"""
POUTAC_JS = r"""<script>
(function(){var els=document.querySelectorAll('.cnt');if(!els.length)return;
 var red=window.matchMedia&&matchMedia('(prefers-reduced-motion: reduce)').matches;
 function fmt(v,d){return v.toLocaleString('cs-CZ',{minimumFractionDigits:d,maximumFractionDigits:d});}
 function run(el){var t=+el.dataset.v,d=+el.dataset.d,t0=performance.now(),dur=1400;
   if(red){el.textContent=fmt(t,d);return;}
   (function step(now){var k=Math.min(1,(now-t0)/dur),e=1-Math.pow(1-k,3);el.textContent=fmt(t*e,d);
     if(k<1)requestAnimationFrame(step);else el.textContent=fmt(t,d);})(t0);
   setTimeout(function(){el.textContent=fmt(t,d);},dur+120);}
 if(!('IntersectionObserver' in window)){els.forEach(run);return;}
 var io=new IntersectionObserver(function(en){en.forEach(function(x){if(x.isIntersecting){run(x.target);io.unobserve(x.target);}});},{threshold:.4});
 els.forEach(function(el){io.observe(el);});   // v HTML jsou vždy skutečná čísla; animace jen když je poutač vidět})();
</script>"""
index_body = f'''<header class="hero">
  <h1>Jak žijí Střelice <span style="font-size:17px;font-weight:500;color:var(--muted)">· občanský datový portál</span></h1>
  <p>Datový portál obce Střelice (okres Brno-venkov) — jak obec hospodaří, roste a žije, srozumitelně v číslech. Hospodaření, školství a další oblasti přehledně a pro každého.</p>
  <div class="chips"><span class="chip">obec Střelice · IČO 00282618</span><span class="chip">≈ {pop_fmt} obyvatel</span><span class="chip">zdroje: MONITOR SP · ČSÚ · MŠMT · streliceubrna.cz</span></div>
  {POUTAC}
</header>
{upd_panel}
<section>
  <div class="tiles">{tile_html}</div>
</section>
<section>
  <div class="panel">
    <div class="sec-h" style="margin:0 0 6px"><h2 style="font-size:16px">O portálu</h2></div>
    <p style="color:var(--muted);font-size:13.5px;margin:0;line-height:1.6">Portál zpracovává <b>veřejná data</b> o obci do přehledných interaktivních vizualizací. Hodnoty pocházejí z oficiálních zdrojů (MONITOR Státní pokladny, Český statistický úřad, MŠMT) a z webu obce <a href="https://www.streliceubrna.cz" target="_blank" rel="noopener" style="color:var(--accent)">streliceubrna.cz</a> (zápisy rady a zastupitelstva, smlouvy o dotacích). Zdroj je u každé sekce uveden.</p>
    <p style="color:var(--muted);font-size:13.5px;margin:10px 0 0;line-height:1.6"><b>Kontakt:</b> Radim Brener · ''' + pc.MAIL_LINK + ''' — připomínky, náměty i upozornění na chyby vítány.</p>
  </div>
</section>'''

open("index.html", "w", encoding="utf-8").write(
    pc.page("Přehled", "Jak žijí Střelice — data obce", index_body, head_scripts=UPD_CSS + POUTAC_CSS,
            body_scripts='<script>bindTheme();</script>' + POUTAC_JS))

# ================= ŠKOLSTVÍ =================
DATA = {"obec": "Střelice", "dem": dem,
        "skoly": [
            {"nazev": "Mateřská škola", "stav": None, "kapacita": 186, "pozn": "kapacita navýšena 2024 o 56 míst (přístavba)", "izo": "IZO 107603900"},
            {"nazev": "Základní škola", "stav": 448, "kapacita": 500, "pozn": "448 žáků (2024/25), naplněnost 90 %", "izo": "IZO 102191212"},
            {"nazev": "ZUŠ Střelice", "stav": None, "kapacita": 250, "pozn": "obory hudební · taneční · výtvarný", "izo": "RED-IZO 691001707"},
        ],
        # počty žáků ZŠ z výročních zpráv školy (skolastrelice.cz, vz0506–vz2425); 2009/10 a 2012/13 vynechány (nečitelný součet)
        "zaciZS": [{"rok": "2005/06", "pocet": 312}, {"rok": "2006/07", "pocet": 312}, {"rok": "2007/08", "pocet": 283},
                   {"rok": "2008/09", "pocet": 273}, {"rok": "2010/11", "pocet": 286}, {"rok": "2011/12", "pocet": 286},
                   {"rok": "2013/14", "pocet": 315}, {"rok": "2014/15", "pocet": 308}, {"rok": "2015/16", "pocet": 319},
                   {"rok": "2016/17", "pocet": 329}, {"rok": "2017/18", "pocet": 312}, {"rok": "2018/19", "pocet": 337},
                   {"rok": "2019/20", "pocet": 405}, {"rok": "2020/21", "pocet": 424}, {"rok": "2021/22", "pocet": 437},
                   {"rok": "2022/23", "pocet": 451}, {"rok": "2023/24", "pocet": 444}, {"rok": "2024/25", "pocet": 448}],
        "kapacitaZS": 500,
        # MŠ — povolený počet dětí (kapacita, dlouhodobě naplněná) dle výročních zpráv; spolehlivé od 2013/14
        "zaciMS": [{"rok": "2013/14", "pocet": 109}, {"rok": "2014/15", "pocet": 109}, {"rok": "2015/16", "pocet": 109},
                   {"rok": "2016/17", "pocet": 109}, {"rok": "2017/18", "pocet": 109}, {"rok": "2018/19", "pocet": 102},
                   {"rok": "2019/20", "pocet": 102}, {"rok": "2020/21", "pocet": 130}, {"rok": "2021/22", "pocet": 130},
                   {"rok": "2022/23", "pocet": 130}, {"rok": "2023/24", "pocet": 130}, {"rok": "2024/25", "pocet": 186}],
        "zusKapacita": 250,
        # žáci ZŠ dle obce trvalého bydliště (výroční zpráva 2024/25)
        "bydliste": [["Střelice", 324], ["Omice", 40], ["Radostice", 28], ["Troubsko", 22], ["Popůvky", 6], ["ostatní obce", 28]]}
# počet tříd ZŠ (z tabulek výročních zpráv: 15 tříd 2014–2019, 18 od 2019/20) + průměr žáků/třídu
TRIDY = {"2014/15": 15, "2015/16": 15, "2016/17": 15, "2017/18": 15, "2018/19": 15,
         "2019/20": 18, "2020/21": 18, "2021/22": 18, "2022/23": 18, "2023/24": 18, "2024/25": 18}
_zs = {r["rok"]: r["pocet"] for r in DATA["zaciZS"]}
DATA["tridy"] = [{"rok": k, "t": v, "avg": round(_zs[k] / v, 1)} for k, v in TRIDY.items() if k in _zs]

data_json = json.dumps(DATA, ensure_ascii=False, separators=(",", ":"))

skol_body = '''<header class="hero">
  <h1>Školství ve Střelicích</h1>
  <p>Demografický vývoj obce jako ukazatel poptávky po místech ve školce a škole, a přehled školských zařízení.</p>
  <div class="chips"><span class="chip">ZŠ a MŠ Střelice</span><span class="chip">ZUŠ Střelice</span><span class="chip">zdroj: ČSÚ · MŠMT · rejstřík škol</span></div>
</header>

<div class="cards" id="kpis"></div>

<section>
  <div class="sec-h"><h2>Demografický vývoj obce</h2><span class="hint">ČSÚ · 2000–''' + str(last["rok"]) + ''' · klikni na sloupec pro detail</span></div>
  <div class="grid2">
    <div class="panel">
      <div class="ctrls"><span class="lbl">Ukazatel</span>
        <span class="seg" id="demSeg"><button class="on" data-k="stav">Počet obyvatel</button><button data-k="nar">Živě narození</button></span></div>
      <div class="chartbox"><canvas id="demChart"></canvas></div>
      <p class="note">Počet narozených dětí předznamenává poptávku po MŠ (s odstupem ~3 roky) a ZŠ (~6 let).</p>
    </div>
    <div class="panel">
      <div class="sec-h" style="margin:0 0 8px"><h2 style="font-size:16px">Přírůstek obyvatel</h2></div>
      <div class="legend"><span><i class="sw" style="background:var(--c1)"></i>přirozený (narození − úmrtí)</span><span><i class="sw" style="background:var(--c3)"></i>migrační (přistěhovalí − vystěhovalí)</span></div>
      <div class="chartbox"><canvas id="prirChart"></canvas></div>
      <p class="note">Růst obce je tažen hlavně migrací (stěhování za bydlením), méně přirozenou měnou.</p>
    </div>
  </div>
</section>

<section>
  <div class="sec-h"><h2>Školská zařízení, počty žáků a kapacity</h2><span class="hint">výroční zprávy škol · rejstřík MŠMT</span></div>
  <div class="cards" id="skoly"></div>
  <div class="grid2" style="margin-top:6px">
    <div class="panel">
      <div class="ctrls" style="margin-bottom:4px"><span class="lbl">Zařízení</span>
        <span class="seg" id="skSeg"><button class="on" data-k="zs">Základní škola</button><button data-k="ms">Mateřská škola</button></span></div>
      <div class="chartbox sm"><canvas id="enrollChart"></canvas></div>
      <p class="note" id="enrollNote"></p>
    </div>
    <div class="panel">
      <div class="sec-h" style="margin:0 0 8px"><h2 style="font-size:16px">Žáci ZŠ podle obce bydliště</h2><span class="hint">2024/25</span></div>
      <div class="chartbox sm"><canvas id="bydlChart"></canvas></div>
      <p class="note">Škola slouží i okolním obcím — ze Střelic je jen ~72 % žáků, zbytek dojíždí (Omice, Radostice, Troubsko…).</p>
    </div>
  </div>
  <div class="panel" style="margin-top:18px">
    <div class="sec-h" style="margin:0 0 8px"><h2 style="font-size:16px">Počet tříd a žáci na třídu (ZŠ)</h2></div>
    <div class="legend"><span><i class="sw" style="background:var(--c5)"></i>počet tříd</span><span><i class="sw" style="background:var(--c0)"></i>průměr žáků na třídu</span></div>
    <div class="chartbox sm"><canvas id="tridyChart"></canvas></div>
    <p class="note">S růstem školy přibyly třídy (15 → 18, tj. dva paralelní ročníky) a třídy se zaplnily — průměr stoupl z ~21 na ~25 žáků. Přibližné hodnoty z výročních zpráv (2014/15–2024/25).</p>
  </div>
  <div class="panel" style="margin-top:18px">
    <p class="note" style="margin:0;font-size:12.5px">Zdroj počtů žáků ZŠ: výroční zprávy školy (skolastrelice.cz), ročníky 2005/06–2024/25. Počty dětí v MŠ (skutečnost) a žáků ZUŠ podle oborů ve výročních zprávách nejsou jednotně uvedeny — lze doplnit daty přímo od školy či obce; u MŠ je zde uvedena kapacita. Provoz škol obec podporuje z rozpočtu — 2024: příspěvky 8,45 mil. Kč pro ZŠ a MŠ a 0,54 mil. Kč pro ZUŠ; přístavbu MŠ spolufinancovala dotace MMR 28,8 mil. Kč (viz sekce <a href="rozpocet.html" style="color:var(--accent)">Rozpočet</a> a <a href="rozpocet.html#ziskane" style="color:var(--accent)">Získané dotace</a>).</p>
  </div>
</section>

<div class="modal" id="modal" hidden><div class="modal-bd" id="modalBd"></div>
  <div class="modal-card"><div class="modal-h"><b id="modalT"></b><button class="iconbtn" id="modalX">✕</button></div>
  <div class="modal-c" id="modalC"></div></div></div>'''

skol_scripts = '<script>' + CHARTJS + '''</script>
<script>
const D=DATA_JSON, dem=D.dem, YRS=dem.map(d=>d.rok);
const nf=new Intl.NumberFormat('cs-CZ');
const charts={};
function axis(){return {grid:{color:cssv('--line')},ticks:{color:cssv('--muted')}};}
function mk(id,cfg){if(charts[id])charts[id].destroy();charts[id]=new Chart(document.getElementById(id),cfg);}

function kpis(){
  const L=dem[dem.length-1], F=dem.find(d=>d.rok>=2010)||dem[0];
  const grow=((L.stav-F.stav)/F.stav*100);
  const narAvg5=Math.round(dem.slice(-5).reduce((a,d)=>a+(d.nar||0),0)/5);
  const C=[
    ['Počet obyvatel '+L.rok, nf.format(L.stav), 'od '+F.rok+': '+(grow>=0?'+':'')+grow.toFixed(0)+' %','var(--c0)'],
    ['Živě narození '+L.rok, nf.format(L.nar), 'průměr 5 let: '+narAvg5,'var(--c1)'],
    ['Migrační přírůstek '+L.rok, (L.pri-L.vys>=0?'+':'')+nf.format(L.pri-L.vys), 'přistěhovalí − vystěhovalí','var(--c3)'],
    ['Školská zařízení', '3', 'MŠ · ZŠ · ZUŠ','var(--c4)'],
  ];
  document.getElementById('kpis').innerHTML=C.map(c=>`<div class="kpi" style="--bar:${c[3]}"><div class="lab">${c[0]}</div><div class="val">${c[1]}</div><div class="delta">${c[2]}</div></div>`).join('');
}
function skoly(){
  document.getElementById('skoly').innerHTML=D.skoly.map(s=>{
    const big=s.stav?nf.format(s.stav):'kap. '+nf.format(s.kapacita);
    const sub=s.stav?('z kapacity '+nf.format(s.kapacita)+' · '+Math.round(s.stav/s.kapacita*100)+' %'):s.pozn;
    return `<div class="kpi" style="--bar:var(--c6)"><div class="lab">${s.nazev} · ${s.izo}</div>
      <div class="val">${big}<span class="unit"> ${s.stav?'žáků':'míst'}</span></div>
      <div class="delta" style="color:var(--muted)">${sub}</div></div>`;}).join('');
}
let demKey='stav';
function demChart(){
  const isBirth=demKey==='nar';
  const data=dem.map(d=>d[demKey]);
  mk('demChart',{type:isBirth?'bar':'line',data:{labels:YRS,datasets:[{
    label:isBirth?'Živě narození':'Počet obyvatel',data,
    borderColor:cssv('--c0'),backgroundColor:isBirth?cssv('--c1'):'transparent',
    borderWidth:2.4,tension:.3,pointRadius:2,borderRadius:4,fill:false}]},
    options:{responsive:true,maintainAspectRatio:false,animation:{duration:500},
      onClick:(e,a,ch)=>{const el=ch.getElementsAtEventForMode(e,'nearest',{intersect:false},true)[0];if(el)detail(YRS[el.index]);},
      onHover:(e,els)=>{if(e.native)e.native.target.style.cursor=els.length?'pointer':'default';},
      plugins:{legend:{display:false},tooltip:{callbacks:{label:c=>c.dataset.label+': '+nf.format(c.parsed.y)}}},
      scales:{x:Object.assign(axis(),{ticks:{color:cssv('--muted'),autoSkip:true,maxRotation:40}}),y:axis()}}});
}
function prirChart(){
  const pr=dem.map(d=>(d.nar||0)-(d.zem||0)), mi=dem.map(d=>(d.pri||0)-(d.vys||0));
  mk('prirChart',{type:'bar',data:{labels:YRS,datasets:[
    {label:'přirozený',data:pr,backgroundColor:cssv('--c1'),borderRadius:3,stack:'s'},
    {label:'migrační',data:mi,backgroundColor:cssv('--c3'),borderRadius:3,stack:'s'}]},
    options:{responsive:true,maintainAspectRatio:false,animation:{duration:500},
      onClick:(e,a,ch)=>{const el=ch.getElementsAtEventForMode(e,'nearest',{intersect:false},true)[0];if(el)detail(YRS[el.index]);},
      onHover:(e,els)=>{if(e.native)e.native.target.style.cursor=els.length?'pointer':'default';},
      plugins:{legend:{display:false},tooltip:{callbacks:{label:c=>c.dataset.label+': '+(c.parsed.y>=0?'+':'')+nf.format(c.parsed.y)}}},
      scales:{x:Object.assign(axis(),{stacked:true,ticks:{color:cssv('--muted'),autoSkip:true,maxRotation:40}}),y:Object.assign(axis(),{stacked:true})}}});
}
function detail(rok){
  const d=dem.find(x=>x.rok===rok); if(!d)return;
  const pr=(d.nar||0)-(d.zem||0), mi=(d.pri||0)-(d.vys||0);
  const rows=[['Stav obyvatel k 1.1.',d.stav],['Živě narození',d.nar],['Zemřelí',d.zem],
    ['Přistěhovalí',d.pri],['Vystěhovalí',d.vys],['Přirozený přírůstek',(pr>=0?'+':'')+pr],['Migrační přírůstek',(mi>=0?'+':'')+mi],['Celkový přírůstek',((pr+mi)>=0?'+':'')+(pr+mi)]];
  document.getElementById('modalT').textContent='Demografie obce — '+rok;
  document.getElementById('modalC').innerHTML='<table class="mtab"><tbody>'+rows.map(r=>`<tr><td>${r[0]}</td><td><b>${nf.format(r[1])}</b></td></tr>`).join('')+'</tbody></table>';
  document.getElementById('modal').hidden=false;
}
let curCap=null;
const capLine={id:'capLine',afterDatasetsDraw(c){const cap=curCap;if(!cap)return;const y=c.scales.y;if(!y)return;
  const py=y.getPixelForValue(cap),a=c.chartArea,ctx=c.ctx;ctx.save();
  ctx.strokeStyle=cssv('--neg');ctx.setLineDash([5,4]);ctx.globalAlpha=.75;ctx.lineWidth=1.4;
  ctx.beginPath();ctx.moveTo(a.left,py);ctx.lineTo(a.right,py);ctx.stroke();
  ctx.setLineDash([]);ctx.globalAlpha=1;ctx.fillStyle=cssv('--neg');ctx.font='11px sans-serif';
  ctx.fillText('kapacita '+nf.format(cap),a.left+6,py-5);ctx.restore();}};
let skKind='zs';
const SK={
  zs:{label:'Žáci ZŠ',color:'--c0',series:'zaciZS',cap:D.kapacitaZS,min:250,
      note:'Základní škola: po letech ~280–330 žáků (2005–2018) prudký růst od roku 2019 na 448 (2024/25), blíží se kapacitě 500. Zdroj: výroční zprávy školy; roky 2009/10 a 2012/13 chybí (nečitelná data).'},
  ms:{label:'Děti MŠ',color:'--c1',series:'zaciMS',cap:null,min:80,
      note:'Mateřská škola: povolený počet dětí (kapacita), který je dlouhodobě naplněn (MŠ je plná). Navýšení přístavbou 2024 ze 130 na 186 míst. Zdroj: výroční zprávy (spolehlivé od 2013/14).'},
  zus:{label:'Kapacita ZUŠ',color:'--c4',series:null,cap:null,min:0,
      note:'ZUŠ: konkrétní počty žáků (ani podle oborů) nejsou veřejně dostupné — zobrazena pouze cílová kapacita 250 žáků. Lze doplnit daty přímo od školy.'}
};
function enrollChart(){
  const k=SK[skKind]; document.getElementById('enrollNote').textContent=k.note; curCap=k.cap;
  if(skKind==='zus'){
    mk('enrollChart',{type:'bar',data:{labels:['Cílová kapacita ZUŠ'],datasets:[{label:'Kapacita',data:[D.zusKapacita],backgroundColor:cssv('--c4'),borderRadius:8,barPercentage:.35}]},
      options:{responsive:true,maintainAspectRatio:false,animation:{duration:500},
        plugins:{legend:{display:false},tooltip:{callbacks:{label:c=>'Kapacita '+nf.format(c.parsed.y)+' žáků · počty nedostupné'}}},
        scales:{x:axis(),y:Object.assign(axis(),{suggestedMax:300,ticks:{color:cssv('--muted')}})}}});
    return;
  }
  const z=D[k.series],lab=z.map(x=>x.rok),val=z.map(x=>x.pocet);
  mk('enrollChart',{type:'line',plugins:[capLine],data:{labels:lab,datasets:[{label:k.label,data:val,
    borderColor:cssv(k.color),backgroundColor:'transparent',borderWidth:2.6,tension:.3,pointRadius:2.5,pointHoverRadius:5,fill:false}]},
    options:{responsive:true,maintainAspectRatio:false,animation:{duration:500},
      plugins:{legend:{display:false},tooltip:{callbacks:{label:c=>k.label+' '+c.label+': '+nf.format(c.parsed.y)+(k.cap?' (kap. '+nf.format(k.cap)+')':'')}}},
      scales:{x:Object.assign(axis(),{ticks:{color:cssv('--muted'),autoSkip:true,maxRotation:45}}),
        y:Object.assign(axis(),{suggestedMax:k.cap?Math.round(k.cap*1.05):undefined,suggestedMin:k.min,ticks:{color:cssv('--muted')}})}}});
}
function bydlChart(){
  const b=D.bydliste,lab=b.map(x=>x[0]),val=b.map(x=>x[1]);
  mk('bydlChart',{type:'bar',data:{labels:lab,datasets:[{label:'Žáci',data:val,backgroundColor:cssv('--c1'),borderRadius:5}]},
    options:{indexAxis:'y',responsive:true,maintainAspectRatio:false,animation:{duration:500},
      plugins:{legend:{display:false},tooltip:{callbacks:{label:c=>nf.format(c.parsed.x)+' žáků'}}},
      scales:{x:axis(),y:Object.assign(axis(),{ticks:{color:cssv('--muted')}})}}});
}
function tridyChart(){
  const t=D.tridy,lab=t.map(x=>x.rok);
  mk('tridyChart',{data:{labels:lab,datasets:[
    {type:'bar',label:'Počet tříd',data:t.map(x=>x.t),backgroundColor:cssv('--c5'),borderRadius:5,yAxisID:'y',order:2,barPercentage:.6},
    {type:'line',label:'Průměr žáků na třídu',data:t.map(x=>x.avg),borderColor:cssv('--c0'),backgroundColor:'transparent',borderWidth:2.6,tension:.3,pointRadius:2.5,yAxisID:'y1',order:1}
  ]},options:{responsive:true,maintainAspectRatio:false,animation:{duration:500},interaction:{mode:'index',intersect:false},
    plugins:{legend:{display:false},tooltip:{callbacks:{label:c=>c.dataset.label+': '+c.parsed.y}}},
    scales:{x:Object.assign(axis(),{ticks:{color:cssv('--muted'),maxRotation:45}}),
      y:Object.assign(axis(),{position:'left',suggestedMin:0,suggestedMax:24,ticks:{color:cssv('--muted')}}),
      y1:{position:'right',grid:{display:false},suggestedMin:0,suggestedMax:30,ticks:{color:cssv('--muted')}}}}});
}
function render(){kpis();skoly();demChart();prirChart();enrollChart();bydlChart();tridyChart();}
render(); bindTheme(render);
document.querySelectorAll('#demSeg button').forEach(b=>b.onclick=()=>{document.querySelectorAll('#demSeg button').forEach(x=>x.classList.remove('on'));b.classList.add('on');demKey=b.dataset.k;demChart();});
document.querySelectorAll('#skSeg button').forEach(b=>b.onclick=()=>{document.querySelectorAll('#skSeg button').forEach(x=>x.classList.remove('on'));b.classList.add('on');skKind=b.dataset.k;enrollChart();});
document.getElementById('modalX').onclick=()=>document.getElementById('modal').hidden=true;
document.getElementById('modalBd').onclick=()=>document.getElementById('modal').hidden=true;
document.addEventListener('keydown',e=>{if(e.key==='Escape')document.getElementById('modal').hidden=true;});
window.addEventListener('load',()=>{Object.values(charts).forEach(c=>{try{c.resize();}catch(e){}});});
</script>'''.replace("DATA_JSON", data_json)

open("skolstvi.html", "w", encoding="utf-8").write(pc.page("Školství", "Školství — Jak žijí Střelice", skol_body, body_scripts=skol_scripts))

print("HOTOVO: index.html + skolstvi.html (demografie", len(dem), "let)")
