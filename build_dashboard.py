#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Sestaví samostatný interaktivní HTML dashboard rozpočtu obce Střelice
z konsolidovaného datasetu FIN 2-12 M. Data + Chart.js jsou vložené přímo
do jednoho .html souboru → funguje offline a dá se sdílet."""
import sys, csv, json
import portal_common as pc
sys.stdout.reconfigure(encoding="utf-8")

CSV = "data/strelice_finm201_2013_2025.csv"
CHARTJS = "data/vendor/chart.umd.js"
OUT = "rozpocet.html"
POP = 3258  # počet obyvatel (2023) pro přepočet na obyvatele

def num(s):
    try: return round(float((s or "").strip()))
    except: return 0

rows_raw = list(csv.DictReader(open(CSV, encoding="utf-8-sig"), delimiter=";"))
years = sorted({int(r["rok"]) for r in rows_raw})

pol, par, rows = {}, {}, []
for r in rows_raw:
    y = int(r["rok"]); p = r["paragraf"]; it = r["polozka"]
    pol[it] = {"n": r["polozka_nazev"], "d": r["druh"], "t": r["trida"],
               "s": r["seskupeni"], "ps": r["podseskupeni"]}
    par[p] = {"n": r["paragraf_nazev"], "o": r["par_oddil"], "g": r["par_skupina"]}
    rows.append([y, p, it, num(r["schvaleny_rozpocet"]),
                 num(r["upraveny_rozpocet"]), num(r["skutecnost"])])

# --- přijaté (získané) dotace: projektové smlouvy z Registru smluv + velké projekty MMR ze závěrečného účtu ---
import re
dotace_in = []
try:
    import openpyxl
    wb = openpyxl.load_workbook("data/rs/ex_party.xlsx", read_only=True, data_only=True); ws = wb.active
    rr = list(ws.iter_rows(values_only=True)); HH = {h: i for i, h in enumerate(rr[0]) if h}
    def gg(r, n): i = HH.get(n); return r[i] if i is not None and i < len(r) else None
    for r in rr[1:]:
        ozn = str(gg(r, "Textové označení smlouvy") or ""); pub = str(gg(r, "Publikující smluvní strana") or "")
        pubd = str(gg(r, "Publikováno") or ""); m = re.search(r"(20\d\d)", pubd)
        vat = gg(r, "Hodnota smlouvy vč. DPH"); nov = gg(r, "Hodnota smlouvy bez DPH")
        val = vat if isinstance(vat, (int, float)) and vat else (nov if isinstance(nov, (int, float)) else 0)
        if re.search(r"fond|intervenční", pub, re.I) and re.search(r"dotac|podpor|rozvoj venkova", ozn, re.I) and val > 0:
            dotace_in.append({"rok": int(m.group(1)) if m else 0, "poskytovatel": pub,
                              "projekt": ozn, "castka": round(val), "zdroj": "Registr smluv"})
except Exception as e:
    print("  pozn.: registr smluv nenačten:", e)
# velké dotace MMR/JMK 2024 (čistý text závěrečného účtu – nejsou v registru smluv, jde o Rozhodnutí)
dotace_in += [
    {"rok": 2024, "poskytovatel": "MMR ČR", "projekt": "Přístavba MŠ Školní", "castka": 28762856, "zdroj": "Závěrečný účet"},
    {"rok": 2024, "poskytovatel": "MMR ČR", "projekt": "Odborná učebna – výtvarný ateliér ZUŠ", "castka": 4112652, "zdroj": "Závěrečný účet"},
]
dotace_in.sort(key=lambda d: (-d["rok"], -d["castka"]))

DATA = {"obec": "Obec Střelice", "ico": "00282618", "nuts": "okres Brno-venkov",
        "pop": POP, "years": years, "pol": pol, "par": par, "rows": rows, "dotaceIn": dotace_in}

chartjs = open(CHARTJS, encoding="utf-8").read()
data_json = json.dumps(DATA, ensure_ascii=False, separators=(",", ":"))

HTML = r"""<!DOCTYPE html>
<html lang="cs" data-theme="dark">
<head>
<script>(function(){try{var t=localStorage.getItem('strelice-theme');if(t)document.documentElement.setAttribute('data-theme',t);}catch(e){}})();</script>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Rozpočet — Jak žijí Střelice</title>
/*FAVICON*/
/*ANALYTICS*/
<style>
:root{
  --bg1:#eef2f9; --bg2:#f8fafc;
  --surface:#ffffff; --surface2:#f8fafc; --inset:#f1f5f9;
  --text:#0f172a; --muted:#64748b; --faint:#94a3b8; --line:#e7ebf1;
  --accent:#3d6c9e; --accent-soft:#e9f0f8;
  --prijmy:#2563eb; --vydaje:#f97316; --pos:#10b981; --neg:#ef4444;
  --shadow:0 1px 2px rgba(15,23,42,.04), 0 4px 16px rgba(15,23,42,.06);
  --shadow-h:0 6px 28px rgba(15,23,42,.12);
  --radius:18px; --radius-sm:12px;
  --c0:#3d6c9e; --c1:#4e9a96; --c2:#7aa05e; --c3:#c2925a; --c4:#9d6f93;
  --c5:#6b7f99; --c6:#5fa3ab; --c7:#b0805f; --c8:#8489ad; --c9:#92a06b;
}
html[data-theme="dark"]{
  --bg1:#0a0f1d; --bg2:#0b1120;
  --surface:#121a2c; --surface2:#0f1626; --inset:#0d1424;
  --text:#e8edf6; --muted:#93a1b8; --faint:#64748b; --line:#1f2a40;
  --accent:#6fa0d0; --accent-soft:#1b2740;
  --prijmy:#60a5fa; --vydaje:#fb923c; --pos:#34d399; --neg:#f87171;
  --c0:#6fa0d0; --c1:#5fc2bd; --c2:#a3cb86; --c3:#e0b277; --c4:#c79ac0;
  --c5:#93a8c6; --c6:#84cdd4; --c7:#d7a585; --c8:#aab0d6; --c9:#bcc78e;
  --shadow:0 1px 2px rgba(0,0,0,.4), 0 8px 28px rgba(0,0,0,.45);
  --shadow-h:0 10px 36px rgba(0,0,0,.6);
}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{margin:0;color:var(--text);
  font-family:"Segoe UI Variable","Segoe UI",-apple-system,BlinkMacSystemFont,Inter,Roboto,Arial,sans-serif;
  font-size:15px;line-height:1.55;
  background:radial-gradient(1200px 600px at 80% -10%, var(--bg1), var(--bg2)) no-repeat;
  background-attachment:scroll; min-height:100vh;
  -webkit-font-smoothing:antialiased}
.wrap{max-width:1160px;margin:0 auto;padding:0 20px 20px}

/* top bar */
.topbar{position:sticky;top:0;z-index:50;background:var(--surface);
  border-bottom:1px solid var(--line)}
.topbar .inner{max-width:1160px;margin:0 auto;padding:11px 20px;display:flex;align-items:center;gap:16px}
.brand{display:flex;align-items:center;gap:11px;font-weight:600;letter-spacing:-.01em}
.brand .dot{width:30px;height:30px;border-radius:9px;display:grid;place-items:center;color:#fff;
  background:linear-gradient(135deg,var(--accent),#06b6d4);font-size:15px;box-shadow:var(--shadow)}
.brand small{display:block;font-weight:400;color:var(--muted);font-size:11.5px;letter-spacing:0}
.nav{display:flex;gap:2px;margin-left:auto;flex-wrap:wrap}
.nav a{padding:7px 13px;border-radius:10px;color:var(--muted);text-decoration:none;font-size:13.5px;
  font-weight:500;transition:.18s;white-space:nowrap}
.nav a:hover{color:var(--text);background:var(--inset)}
.nav a.active{color:var(--accent);background:var(--accent-soft)}
.iconbtn{width:38px;height:34px;border:1px solid var(--line);background:var(--surface);border-radius:10px;
  cursor:pointer;color:var(--muted);display:grid;place-items:center;transition:.18s;font-size:15px}
.iconbtn:hover{color:var(--text);border-color:var(--accent);transform:translateY(-1px)}

/* hero */
.hero{padding:34px 0 8px}
.hero h1{font-size:30px;font-weight:680;letter-spacing:-.02em;margin:0 0 6px;color:var(--text)}
.hero h1 .ac{color:var(--accent)}
.hero p{color:var(--muted);margin:0;font-size:14.5px}
.hero .chips{display:flex;gap:8px;margin-top:14px;flex-wrap:wrap}
.chip{font-size:12px;padding:5px 11px;border-radius:999px;background:var(--inset);color:var(--muted);
  border:1px solid var(--line)}

/* cards */
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(186px,1fr));gap:14px;margin:22px 0 8px}
.kpi{background:var(--surface);border:1px solid var(--line);border-radius:var(--radius);padding:16px 18px;
  box-shadow:var(--shadow);transition:transform .2s, box-shadow .2s;position:relative;overflow:hidden}
.kpi:hover{transform:translateY(-3px);box-shadow:var(--shadow-h)}
.kpi::after{content:"";position:absolute;left:0;top:0;bottom:0;width:4px;background:var(--bar,var(--accent))}
.kpi .lab{font-size:12.5px;color:var(--muted);display:flex;align-items:center;gap:7px}
.kpi .lab i{font-size:15px;color:var(--bar,var(--accent))}
.kpi .val{font-size:26px;font-weight:680;margin-top:7px;letter-spacing:-.02em;font-variant-numeric:tabular-nums}
.kpi .unit{font-size:13px;color:var(--muted);font-weight:500}
.kpi .delta{font-size:12px;margin-top:5px;font-weight:500;display:inline-flex;align-items:center;gap:4px}
.up{color:var(--pos)} .down{color:var(--neg)}

section{margin-top:30px;scroll-margin-top:74px}
.sec-h{display:flex;align-items:baseline;gap:12px;margin:0 0 14px}
.sec-h h2{font-size:19px;font-weight:640;margin:0;letter-spacing:-.01em}
.sec-h .hint{color:var(--faint);font-size:12.5px}
.panel{background:var(--surface);border:1px solid var(--line);border-radius:var(--radius);
  padding:20px 22px;box-shadow:var(--shadow)}
.grid2{display:grid;grid-template-columns:1.55fr 1fr;gap:18px}
@media(max-width:820px){.grid2{grid-template-columns:1fr}.nav a{padding:7px 9px}}

/* controls */
.ctrls{display:flex;flex-wrap:wrap;gap:12px 18px;align-items:center;margin-bottom:6px}
.seg{display:inline-flex;background:var(--inset);border-radius:11px;padding:3px;gap:2px}
.seg button{border:0;background:transparent;color:var(--muted);font:inherit;font-size:13px;font-weight:500;
  padding:6px 13px;border-radius:8px;cursor:pointer;transition:.16s}
.seg button.on{background:var(--surface);color:var(--text);box-shadow:var(--shadow)}
.lbl{font-size:12.5px;color:var(--muted);font-weight:500;margin-right:2px}
select,input[type=text]{font:inherit;font-size:13.5px;padding:7px 11px;border:1px solid var(--line);
  border-radius:10px;background:var(--surface);color:var(--text);outline:none;transition:.16s}
select:focus,input[type=text]:focus{border-color:var(--accent);box-shadow:0 0 0 3px var(--accent-soft)}

/* range slider */
.yearctl{display:flex;align-items:center;gap:14px;margin-top:14px;padding-top:14px;border-top:1px solid var(--line)}
.yearctl .yv{font-size:22px;font-weight:680;color:var(--accent);min-width:60px;font-variant-numeric:tabular-nums}
input[type=range]{-webkit-appearance:none;appearance:none;height:6px;border-radius:999px;flex:1;
  background:linear-gradient(90deg,var(--accent) var(--p,50%), var(--line) var(--p,50%));cursor:pointer}
input[type=range]::-webkit-slider-thumb{-webkit-appearance:none;width:20px;height:20px;border-radius:50%;
  background:var(--surface);border:3px solid var(--accent);box-shadow:var(--shadow);cursor:pointer;transition:.12s}
input[type=range]::-webkit-slider-thumb:hover{transform:scale(1.15)}

.legend{display:flex;flex-wrap:wrap;gap:8px 16px;font-size:12px;color:var(--muted);margin:10px 0}
.legend span{display:inline-flex;align-items:center;gap:6px;cursor:default}
.sw{width:11px;height:11px;border-radius:3px;display:inline-block}
.chartbox{position:relative;width:100%;height:330px;margin-top:6px}
.chartbox.sm{height:290px}
.note{font-size:12px;color:var(--faint);margin-top:12px;line-height:1.6}
.donutwrap{position:relative;display:grid;place-items:center}
.donut-center{position:absolute;text-align:center;pointer-events:none}
.donut-center .t{font-size:11.5px;color:var(--muted)}
.donut-center .v{font-size:22px;font-weight:680;letter-spacing:-.02em}

/* table */
.tbar{display:flex;gap:12px;align-items:center;flex-wrap:wrap;margin-bottom:10px}
.search{flex:1;min-width:180px;position:relative}
.search i{position:absolute;left:11px;top:50%;transform:translateY(-50%);color:var(--faint);font-size:15px}
.search input{width:100%;padding-left:34px}
.tablewrap{max-height:540px;overflow:auto;border:1px solid var(--line);border-radius:var(--radius-sm)}
table{width:100%;border-collapse:collapse;font-size:13px}
th,td{padding:9px 12px;text-align:right;white-space:nowrap;border-bottom:1px solid var(--line)}
th:first-child,td:first-child{text-align:left;white-space:normal}
thead th{position:sticky;top:0;z-index:2;background:var(--surface2);color:var(--muted);font-weight:600;
  cursor:pointer;user-select:none;font-size:12px;letter-spacing:.01em}
thead th:hover{color:var(--text)}
thead th .ar{opacity:.5;font-size:10px}
tbody tr{transition:background .12s}
tbody tr.clk{cursor:pointer}
tbody tr:hover{background:var(--inset)}
tbody td .nm{display:flex;align-items:center;gap:7px}
tbody td .nm i{color:var(--faint);font-size:14px;transition:.15s}
.barcell{position:relative;min-width:120px}
.barcell .b{position:absolute;left:12px;top:50%;transform:translateY(-50%);height:7px;border-radius:4px;
  background:linear-gradient(90deg,var(--accent),#06b6d4);opacity:.85}
.pill{font-size:11px;padding:2px 9px;border-radius:999px;font-weight:600}
.pill.ok{background:rgba(16,185,129,.15);color:var(--pos)}
.pill.warn{background:rgba(249,115,22,.16);color:var(--vydaje)}
.pill.bad{background:rgba(239,68,68,.15);color:var(--neg)}
tr.total td{font-weight:680;border-top:2px solid var(--text);background:var(--surface2)}
tr.subrow td{background:var(--inset);font-size:12.5px}
tr.subrow td:first-child{padding-left:30px;color:var(--muted)}
.fade{animation:fade .35s ease}
@keyframes fade{from{opacity:0;transform:translateY(4px)}to{opacity:1;transform:none}}
.footer{margin-top:18px;color:var(--faint);font-size:11.5px;text-align:center;line-height:1.4;padding-bottom:6px}
/* modal */
.modal{position:fixed;inset:0;z-index:200;display:flex;align-items:center;justify-content:center;padding:18px}
.modal[hidden]{display:none}
.modal-bd{position:absolute;inset:0;background:rgba(15,23,42,.5)}
.modal-card{position:relative;background:var(--surface);border:1px solid var(--line);border-radius:var(--radius);
  max-width:640px;width:100%;max-height:84vh;display:flex;flex-direction:column;
  box-shadow:0 24px 70px rgba(0,0,0,.4);animation:pop .18s ease}
@keyframes pop{from{opacity:0;transform:translateY(10px) scale(.985)}to{opacity:1;transform:none}}
.modal-h{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:15px 18px;border-bottom:1px solid var(--line)}
.modal-h b{font-size:15.5px;font-weight:600}
.modal-c{padding:8px 18px 18px;overflow:auto}
.mtab{width:100%;border-collapse:collapse;font-size:12.5px;margin-top:8px}
.mtab th,.mtab td{padding:7px 8px;border-bottom:1px solid var(--line);text-align:right;white-space:nowrap}
.mtab th:first-child,.mtab td:first-child{text-align:left;white-space:normal}
.mtab th{color:var(--muted);font-weight:600;font-size:11.5px}
.mtab tr.total td{font-weight:680;border-top:2px solid var(--text);background:var(--surface2)}
.mgrid{display:grid;grid-template-columns:1fr 1fr;gap:16px}
@media(max-width:560px){.mgrid{grid-template-columns:1fr}}
.mh{font-size:13px;font-weight:600;margin:4px 0 2px}
.msaldo{margin-top:14px;padding:10px 14px;border-radius:10px;background:var(--inset);font-weight:600;text-align:center}
.mhint{font-size:11.5px;color:var(--faint);margin-top:4px}
</style>
</head>
<body>
<div class="topbar"><div class="inner">
  <a class="brand" href="index.html" style="text-decoration:none;color:inherit"><span class="dot"><svg width="18" height="18" viewBox="0 0 48 48" fill="none" stroke="#fff" stroke-width="3.4" stroke-linecap="round" stroke-linejoin="round"><circle cx="27" cy="21" r="15"/><circle cx="27" cy="21" r="8"/><circle cx="27" cy="21" r="3.4" fill="#fff" stroke="none"/><line x1="5" y1="43" x2="27" y2="21"/><path d="M5 43 l7 -1.4 M5 43 l1.4 -7"/></svg></span>
    <span id="brand">Jak žijí Střelice<small>otevřená data obce</small></span></a>
  <nav class="nav" id="nav"><!--NAV--></nav>
  <button class="iconbtn" id="themeBtn" title="Světlý/tmavý režim">◐</button>
</div></div>

<div class="wrap">
  <header class="hero" id="prehled">
    <h1 id="title">Obec Střelice</h1>
    <p id="meta"></p>
    <div class="chips" id="chips"></div>
  </header>

  <div class="cards" id="kpis"></div>

  <section id="trend-sec">
    <div class="sec-h"><h2>Vývoj příjmů, výdajů a salda</h2><span class="hint">2013–2025 · klouzni rokem dole</span></div>
    <div class="panel">
      <div class="ctrls">
        <span class="lbl">Ukazatel</span>
        <span class="seg" id="metricSeg">
          <button class="on" data-m="5">Skutečnost</button>
          <button data-m="3">Schválený</button>
          <button data-m="4">Upravený</button>
        </span>
      </div>
      <div class="legend">
        <span><i class="sw" style="background:var(--prijmy)"></i>Příjmy</span>
        <span><i class="sw" style="background:var(--vydaje)"></i>Výdaje</span>
        <span><i class="sw" style="background:var(--pos)"></i>Saldo +</span>
        <span><i class="sw" style="background:var(--neg)"></i>Saldo −</span>
      </div>
      <div class="chartbox"><canvas id="trend"></canvas></div>
      <div class="yearctl">
        <span class="lbl">Rok ve fokusu</span>
        <input type="range" id="yearR">
        <span class="yv" id="yearV"></span>
      </div>
    </div>
  </section>

  <section id="prijmy">
    <div class="sec-h"><h2>Struktura příjmů</h2><span class="hint">podle druhu · skutečnost</span></div>
    <div class="grid2">
      <div class="panel">
        <div class="ctrls"><span class="lbl">Zobrazení</span>
          <span class="seg" id="prSeg"><button class="on" data-v="abs">mil. Kč</button><button data-v="pct">podíl %</button></span></div>
        <div class="legend" id="prijmyLeg"></div>
        <div class="chartbox sm"><canvas id="chPrijmy"></canvas></div>
      </div>
      <div class="panel">
        <div class="ctrls"><span class="lbl" id="donutCap">Skladba</span>
          <span class="seg" id="donutSeg"><button data-s="Příjmy">Příjmy</button><button class="on" data-s="Výdaje">Výdaje</button></span></div>
        <div class="donutwrap"><div class="chartbox sm" style="max-width:330px"><canvas id="donut"></canvas></div>
          <div class="donut-center"><div class="t" id="donutT">výdaje</div><div class="v" id="donutV"></div></div></div>
        <div class="legend" id="donutLeg" style="justify-content:center"></div>
      </div>
    </div>
  </section>

  <section id="vydaje">
    <div class="sec-h"><h2>Kam tečou výdaje</h2><span class="hint">podle oblasti · skutečnost</span></div>
    <div class="panel">
      <div class="ctrls"><span class="lbl">Zobrazení</span>
        <span class="seg" id="vySeg"><button class="on" data-v="abs">mil. Kč</button><button data-v="pct">podíl %</button></span></div>
      <div class="legend" id="vydajeLeg"></div>
      <div class="chartbox"><canvas id="chVydaje"></canvas></div>
      <p class="note">Investiční vlna 2023–2024 (přístavba MŠ, učebna ZUŠ, cyklotrasa) zvedla kapitálové výdaje až nad 60 mil. Kč ročně.</p>
    </div>
  </section>

  <section id="detail">
    <div class="sec-h"><h2>Detail — rozklikni rozpočet</h2><span class="hint">řaď, hledej, rozbaluj</span></div>
    <div class="panel">
      <div class="ctrls">
        <span><span class="lbl">Rok</span><select id="dYear"></select></span>
        <span class="seg" id="sideSeg"><button class="on" data-s="Výdaje">Výdaje</button><button data-s="Příjmy">Příjmy</button></span>
        <span><span class="lbl">Seskupit</span>
          <select id="dGroup">
            <option value="o">dle oblasti (na co)</option>
            <option value="t">dle třídy (běžné/kapitál/transfery)</option>
            <option value="s">dle seskupení položek</option>
            <option value="pol">dle konkrétní položky</option>
          </select></span>
      </div>
      <div class="tbar">
        <span class="search"><i class="">⌕</i><input type="text" id="dSearch" placeholder="hledat položku / oblast…"></span>
      </div>
      <div class="tablewrap"><table id="drill"><thead></thead><tbody></tbody></table></div>
      <p class="note">Klik na řádek (u oblasti/třídy) rozbalí konkrétní položky. „% plnění" = skutečnost ÷ upravený rozpočet.</p>
    </div>
  </section>

  <div class="footer">Zdroj: MONITOR Státní pokladny (MF ČR) · výkaz FIN 2-12 M (FINM201) · IČO 00282618 · 2013–2025, roční stav k 31. 12. · hodnoty v Kč.</div>
</div>

<div class="modal" id="modal" hidden>
  <div class="modal-bd" id="modalBd"></div>
  <div class="modal-card">
    <div class="modal-h"><b id="modalT"></b><button class="iconbtn" id="modalX" aria-label="Zavřít">✕</button></div>
    <div class="modal-c" id="modalC"></div>
  </div>
</div>

<script>/*CHARTJS*/</script>
<script>
const DATA = /*DATA*/;
const R = DATA.rows, POL = DATA.pol, PAR = DATA.par, YRS = DATA.years, POP = DATA.pop;
const LY = YRS[YRS.length-1], FY = YRS[0];
let metric = 5, perCap = false, focusYear = LY;
const charts = {};
function paletteNow(){return ['--c0','--c1','--c2','--c3','--c4','--c5','--c6','--c7','--c8','--c9'].map(v=>cssv(v));}
let PAL = paletteNow();
function cssv(n){return getComputedStyle(document.documentElement).getPropertyValue(n).trim();}
function isDark(){return document.documentElement.getAttribute('data-theme')==='dark';}
const druhOf = r => (POL[r[2]]||{}).d || '?';
const sumBy = (pred, m) => R.reduce((a,r)=>pred(r)?a+r[m]:a,0);
const scale = v => perCap ? v/POP : v;
const nf = new Intl.NumberFormat('cs-CZ');
const fmtFull = v => perCap ? nf.format(Math.round(scale(v)))+' Kč/obyv.' : nf.format(Math.round(v))+' Kč';
const fmtM = v => perCap ? nf.format(Math.round(v/POP)) : (v/1e6).toLocaleString('cs-CZ',{maximumFractionDigits:1});
const unitM = () => perCap ? 'Kč/ob.' : 'mil.';

/* ---------- KPI s počítadlem ---------- */
function kpis(){
  const pr=y=>sumBy(r=>r[0]==y&&druhOf(r)=='Příjmy',5), vy=y=>sumBy(r=>r[0]==y&&druhOf(r)=='Výdaje',5);
  const dan=y=>sumBy(r=>r[0]==y&&(POL[r[2]]||{}).t=='Daňové příjmy',5);
  const kap=y=>sumBy(r=>r[0]==y&&druhOf(r)=='Výdaje'&&((POL[r[2]]||{}).t||'').includes('Kapitál'),5);
  const dd=(a,b)=>b?((a-b)/b*100):0;
  const saldo=pr(LY)-vy(LY);
  const C=[
    ['ti','Příjmy '+LY,pr(LY),dd(pr(LY),pr(LY-1)),'var(--prijmy)','arrow-up-right'],
    ['','Výdaje '+LY,vy(LY),dd(vy(LY),vy(LY-1)),'var(--vydaje)','arrow-down-right'],
    ['','Saldo '+LY,saldo,null,saldo>=0?'var(--pos)':'var(--neg)','wallet'],
    ['','Daňové příjmy '+LY,dan(LY),dd(dan(LY),dan(FY)),'var(--accent)','coins'],
    ['','Kapitálové výdaje '+LY,kap(LY),null,'#a855f7','tools'],
  ];
  document.getElementById('kpis').innerHTML = C.map((c,i)=>{
    const dl = c[3]==null ? (c[2]>=0?'přebytek':'schodek')
      : `<span class="${c[3]>=0?'up':'down'}">${c[3]>=0?'▲':'▼'} ${Math.abs(c[3]).toFixed(1)} %</span> ${c[1].includes('Daň')?'vs 2013':'r/r'}`;
    return `<div class="kpi" style="--bar:${c[4]}"><div class="lab">${c[1]}</div>
      <div class="val"><span class="ctr" data-v="${Math.round(scale(c[2]))}">0</span> <span class="unit">${perCap?'Kč/ob.':'Kč'}</span></div>
      <div class="delta">${dl}</div></div>`;
  }).join('');
  animateCounters();
}
function animateCounters(){
  document.querySelectorAll('.ctr').forEach(el=>{
    const target=+el.dataset.v, dur=750, t0=performance.now();
    const fin=()=>{el.textContent=nf.format(target);};
    if(matchMedia('(prefers-reduced-motion: reduce)').matches){fin();return;}
    let frames=0;
    requestAnimationFrame(function step(t){
      frames++;
      const k=Math.min(1,(t-t0)/dur), e=1-Math.pow(1-k,3);
      el.textContent=nf.format(Math.round(target*e));
      if(k<1 && frames<90) requestAnimationFrame(step); else fin();  // tvrdý strop snímků
    });
    setTimeout(fin, dur+90);   // záruka konečné hodnoty
  });
}

/* ---------- vertical focus line plugin ---------- */
const focusPlugin={id:'focus',afterDatasetsDraw(c){
  const x=c.scales.x; if(!x)return; const idx=YRS.indexOf(focusYear); if(idx<0)return;
  const px=x.getPixelForValue(idx), ya=c.chartArea;
  const ctx=c.ctx; ctx.save();
  ctx.strokeStyle=cssv('--accent'); ctx.globalAlpha=.5; ctx.lineWidth=1.5; ctx.setLineDash([4,4]);
  ctx.beginPath();ctx.moveTo(px,ya.top);ctx.lineTo(px,ya.bottom);ctx.stroke();ctx.restore();
}};

function axis(){return {grid:{color:isDark()?'#1f2a40':'#eef2f7'},ticks:{color:cssv('--muted')}};}
function mk(id,cfg){ if(charts[id])charts[id].destroy(); charts[id]=new Chart(document.getElementById(id),cfg); }

/* ---------- detail v popup okně (klik na graf) ---------- */
function showModal(title,html){const m=document.getElementById('modal');
  document.getElementById('modalT').textContent=title;document.getElementById('modalC').innerHTML=html;m.hidden=false;}
function closeModal(){document.getElementById('modal').hidden=true;}
function aggRows(pred,nameFn){const m={};R.forEach(r=>{if(pred(r)){const n=nameFn(r);
  (m[n]=m[n]||[0,0,0]);m[n][0]+=r[3];m[n][1]+=r[4];m[n][2]+=r[5];}});
  return Object.entries(m).map(([name,v])=>({name,schv:v[0],uprav:v[1],skut:v[2]}));}
function detailTable(items){items=items.filter(x=>x.skut!=0||x.uprav!=0).sort((a,b)=>b.skut-a.skut);
  if(!items.length)return '<p class="mhint">Žádné položky pro tento výběr.</p>';
  const t=items.reduce((a,x)=>[a[0]+x.schv,a[1]+x.uprav,a[2]+x.skut],[0,0,0]);
  const pcl=p=>p>105?'warn':p<85?'bad':'ok';
  return `<table class="mtab"><thead><tr><th>Položka</th><th>Schválený</th><th>Upravený</th><th>Skutečnost</th><th>%</th></tr></thead><tbody>`+
    items.map(x=>{const p=x.uprav?x.skut/x.uprav*100:0;return `<tr><td>${x.name}</td><td>${nf.format(x.schv)}</td><td>${nf.format(x.uprav)}</td><td><b>${nf.format(x.skut)}</b></td><td>${x.uprav?`<span class="pill ${pcl(p)}">${p.toFixed(0)} %</span>`:'–'}</td></tr>`;}).join('')+
    `<tr class="total"><td>Celkem</td><td>${nf.format(t[0])}</td><td>${nf.format(t[1])}</td><td>${nf.format(t[2])}</td><td></td></tr></tbody></table>`;}
function miniTable(items){items=items.filter(x=>x.skut!=0).sort((a,b)=>b.skut-a.skut);
  return `<table class="mtab"><tbody>`+items.map(x=>`<tr><td>${x.name}</td><td><b>${nf.format(x.skut)}</b></td></tr>`).join('')+`</tbody></table>`;}
function topOblasti(n){const k={};R.forEach(r=>{if(druhOf(r)=='Výdaje'){const o=(PAR[r[1]]||{}).o||'(jiné)';k[o]=(k[o]||0)+r[5];}});
  return Object.entries(k).sort((a,b)=>b[1]-a[1]).slice(0,n).map(e=>e[0]);}
function clkTrend(idx){const y=YRS[idx];
  const pr=aggRows(r=>r[0]==y&&druhOf(r)=='Příjmy',r=>(POL[r[2]]||{}).t||'(jiné)');
  const vy=aggRows(r=>r[0]==y&&druhOf(r)=='Výdaje',r=>(PAR[r[1]]||{}).o||'(jiné)');
  const prT=pr.reduce((a,x)=>a+x.skut,0),vyT=vy.reduce((a,x)=>a+x.skut,0),s=prT-vyT;
  showModal('Rozpočet '+y+' — přehled',
    '<div class="mgrid"><div><div class="mh">Příjmy: '+nf.format(prT)+' Kč</div>'+miniTable(pr)+'</div>'+
    '<div><div class="mh">Výdaje: '+nf.format(vyT)+' Kč</div>'+miniTable(vy)+'</div></div>'+
    '<div class="msaldo" style="color:'+(s>=0?'var(--pos)':'var(--neg)')+'">Saldo '+y+': '+(s>=0?'+':'')+nf.format(s)+' Kč '+(s>=0?'(přebytek)':'(schodek)')+'</div>'+
    '<p class="mhint">Tip: klikni na výseč jiných grafů pro rozpad na konkrétní položky.</p>');}
function clkPrijmy(di,idx){const t=charts.chPrijmy.data.datasets[di].label,y=YRS[idx];
  showModal('Příjmy '+y+' — '+t, detailTable(aggRows(r=>r[0]==y&&druhOf(r)=='Příjmy'&&((POL[r[2]]||{}).t||'(jiné)')==t, r=>r[2]+' — '+((POL[r[2]]||{}).n||''))));}
function clkVydaje(di,idx){const lbl=charts.chVydaje.data.datasets[di].label,y=YRS[idx];
  if(lbl=='Ostatní'){const top=topOblasti(8);
    showModal('Výdaje '+y+' — ostatní oblasti', detailTable(aggRows(r=>r[0]==y&&druhOf(r)=='Výdaje'&&!top.includes((PAR[r[1]]||{}).o||'(jiné)'), r=>(PAR[r[1]]||{}).o||'(jiné)')));
  } else showModal('Výdaje '+y+' — '+lbl, detailTable(aggRows(r=>r[0]==y&&druhOf(r)=='Výdaje'&&((PAR[r[1]]||{}).o||'(jiné)')==lbl, r=>'§'+r[1]+' '+((PAR[r[1]]||{}).n||''))));}
function clkDonut(idx){const lbl=charts.donut.data.labels[idx],y=focusYear,side=donutSide;
  const keyFn=side=='Výdaje'?(r=>(PAR[r[1]]||{}).o||'(jiné)'):(r=>(POL[r[2]]||{}).t||'(jiné)');
  const nameFn=side=='Výdaje'?(r=>'§'+r[1]+' '+((PAR[r[1]]||{}).n||'')):(r=>r[2]+' — '+((POL[r[2]]||{}).n||''));
  if(lbl=='Ostatní'){const k={};R.forEach(r=>{if(r[0]==y&&druhOf(r)==side){const kk=keyFn(r);k[kk]=(k[kk]||0)+r[5];}});
    const top=Object.entries(k).sort((a,b)=>b[1]-a[1]).slice(0,7).map(e=>e[0]);
    showModal(side+' '+y+' — ostatní', detailTable(aggRows(r=>r[0]==y&&druhOf(r)==side&&!top.includes(keyFn(r)), keyFn)));
  } else showModal(side+' '+y+' — '+lbl, detailTable(aggRows(r=>r[0]==y&&druhOf(r)==side&&keyFn(r)==lbl, nameFn)));}
function chartClick(ch,e,fn){const el=ch.getElementsAtEventForMode(e,'nearest',{intersect:true},true)[0];if(el)fn(el.datasetIndex,el.index);}
const hover=(e,els)=>{if(e.native&&e.native.target)e.native.target.style.cursor=els.length?'pointer':'default';};

/* ---------- trend ---------- */
function trend(){
  const pr=YRS.map(y=>scale(sumBy(r=>r[0]==y&&druhOf(r)=='Příjmy',metric)));
  const vy=YRS.map(y=>scale(sumBy(r=>r[0]==y&&druhOf(r)=='Výdaje',metric)));
  const sa=pr.map((p,i)=>p-vy[i]); const D=v=>perCap?v:v/1e6;
  mk('trend',{plugins:[focusPlugin],data:{labels:YRS,datasets:[
    {type:'bar',label:'Saldo',data:sa.map(D),order:3,borderRadius:5,
     backgroundColor:sa.map(v=>v>=0?cssv('--pos'):cssv('--neg')),
     borderSkipped:false,barPercentage:.6},
    {type:'line',label:'Příjmy',data:pr.map(D),order:1,borderColor:cssv('--prijmy'),
     backgroundColor:'transparent',borderWidth:2.5,tension:.35,pointRadius:2.5,pointHoverRadius:5},
    {type:'line',label:'Výdaje',data:vy.map(D),order:2,borderColor:cssv('--vydaje'),
     borderWidth:2.5,borderDash:[7,4],tension:.35,pointRadius:2.5,pointHoverRadius:5}
  ]},options:{responsive:true,maintainAspectRatio:false,animation:{duration:600},
    interaction:{mode:'index',intersect:false},
    onClick:(e,a,ch)=>{const el=ch.getElementsAtEventForMode(e,'nearest',{intersect:false},true)[0];if(el)clkTrend(el.index);},onHover:hover,
    plugins:{legend:{display:false},tooltip:tt(true)},
    scales:{x:Object.assign(axis(),{ticks:{color:cssv('--muted'),autoSkip:false,maxRotation:40}}),
      y:Object.assign(axis(),{ticks:{color:cssv('--muted'),callback:v=>v+' '+unitM()}})}}});
}
function tt(milly){return {backgroundColor:isDark()?'#0b1120':'#0f172a',padding:11,cornerRadius:10,
  titleColor:'#fff',bodyColor:'#e2e8f0',borderColor:cssv('--accent'),borderWidth:1,
  callbacks:{label:c=>` ${c.dataset.label}: `+(milly?(perCap?nf.format(Math.round(c.parsed.y))+' Kč/ob.':c.parsed.y.toLocaleString('cs-CZ',{maximumFractionDigits:1})+' mil. Kč'):c.parsed.y.toLocaleString('cs-CZ',{maximumFractionDigits:1})+' %')}};}

/* ---------- stacked struktura ---------- */
function stacked(id,side,keyFn,legId,topN,mode){
  const keys={}; R.forEach(r=>{if(druhOf(r)==side){const k=keyFn(r)||'(ostatní)';keys[k]=(keys[k]||0)+r[5];}});
  let order=Object.entries(keys).sort((a,b)=>b[1]-a[1]).map(e=>e[0]);
  let top=order;
  if(topN&&order.length>topN){top=order.slice(0,topN);order=top.concat(['Ostatní']);}
  const totY=YRS.map(y=>sumBy(r=>r[0]==y&&druhOf(r)==side,5));
  const ds=order.map((k,i)=>({label:k,borderRadius:3,backgroundColor:PAL[i%PAL.length],data:YRS.map((y,j)=>{
    let v=(k=='Ostatní')
      ? R.reduce((a,r)=>(r[0]==y&&druhOf(r)==side&&!top.includes(keyFn(r)||'(ostatní)'))?a+r[5]:a,0)
      : R.reduce((a,r)=>(r[0]==y&&druhOf(r)==side&&(keyFn(r)||'(ostatní)')==k)?a+r[5]:a,0);
    return mode=='pct'? (totY[j]?v/totY[j]*100:0) : (perCap? v/POP : v/1e6);
  })}));
  document.getElementById(legId).innerHTML = order.map((k,i)=>
    `<span><i class="sw" style="background:${PAL[i%PAL.length]}"></i>${k}</span>`).join('');
  mk(id,{type:'bar',data:{labels:YRS,datasets:ds},options:{responsive:true,maintainAspectRatio:false,
    animation:{duration:600},plugins:{legend:{display:false},tooltip:tt(mode!='pct')},
    onClick:(e,a,ch)=>chartClick(ch,e,side=='Příjmy'?clkPrijmy:clkVydaje),onHover:hover,
    scales:{x:Object.assign(axis(),{stacked:true,ticks:{color:cssv('--muted'),autoSkip:false,maxRotation:40}}),
      y:Object.assign(axis(),{stacked:true,max:mode=='pct'?100:undefined,
        ticks:{color:cssv('--muted'),callback:v=>mode=='pct'?v+' %':v+' '+unitM()}})}}});
}

/* ---------- donut (rok ve fokusu) ---------- */
let donutSide='Výdaje';
function donut(){
  const keyFn = donutSide=='Výdaje' ? (r=>(PAR[r[1]]||{}).o||'(jiné)') : (r=>(POL[r[2]]||{}).t||'(jiné)');
  const agg={}; R.forEach(r=>{if(r[0]==focusYear&&druhOf(r)==donutSide){const k=keyFn(r);agg[k]=(agg[k]||0)+r[5];}});
  let arr=Object.entries(agg).sort((a,b)=>b[1]-a[1]); const TOPN=7;
  if(arr.length>TOPN){const rest=arr.slice(TOPN).reduce((a,e)=>a+e[1],0);arr=arr.slice(0,TOPN);if(rest>0)arr.push(['Ostatní',rest]);}
  const tot=arr.reduce((a,e)=>a+e[1],0);
  document.getElementById('donutT').textContent=donutSide.toLowerCase()+' '+focusYear;
  document.getElementById('donutV').textContent=fmtM(tot)+' '+(perCap?'Kč/ob.':'mil.');
  document.getElementById('donutLeg').innerHTML=arr.map((e,i)=>
    `<span><i class="sw" style="background:${PAL[i%PAL.length]}"></i>${e[0].length>26?e[0].slice(0,24)+'…':e[0]}</span>`).join('');
  mk('donut',{type:'doughnut',data:{labels:arr.map(e=>e[0]),
    datasets:[{data:arr.map(e=>e[1]),backgroundColor:arr.map((e,i)=>PAL[i%PAL.length]),
      borderColor:cssv('--surface'),borderWidth:2,hoverOffset:6}]},
    options:{responsive:true,maintainAspectRatio:false,cutout:'66%',animation:{duration:600},
      onClick:(e,a,ch)=>{const el=ch.getElementsAtEventForMode(e,'nearest',{intersect:true},true)[0];if(el)clkDonut(el.index);},onHover:hover,
      plugins:{legend:{display:false},tooltip:Object.assign(tt(false),{callbacks:{label:c=>
        ' '+c.label+': '+fmtM(c.parsed)+(perCap?' Kč/ob.':' mil.')+' ('+(c.parsed/tot*100).toFixed(0)+' %)'}})}}});
}

/* ---------- detail drill ---------- */
let dSide='Výdaje', dExpand=null, dSort=[3,true], dQ='';
function drill(){
  const yr=document.getElementById('dYear').value, grp=document.getElementById('dGroup').value;
  const yf=r=>(yr=='*'||r[0]==+yr);
  const keyName=r=> grp=='o'?((PAR[r[1]]||{}).o||'(neuvedeno)') : grp=='t'?((POL[r[2]]||{}).t||'(neuvedeno)')
    : grp=='s'?((POL[r[2]]||{}).s||'(neuvedeno)') : (r[2]+' — '+((POL[r[2]]||{}).n||''));
  let agg={}, expandable=(grp=='o'||grp=='t')&&!dExpand;
  if(dExpand && (grp=='o'||grp=='t')){
    R.forEach(r=>{if(druhOf(r)==dSide&&yf(r)&&keyName(r)==dExpand){const k=r[2]+' — '+((POL[r[2]]||{}).n||'');
      (agg[k]=agg[k]||[0,0,0])[0]+=r[3];agg[k][1]+=r[4];agg[k][2]+=r[5];}});
  } else { R.forEach(r=>{if(druhOf(r)==dSide&&yf(r)){const k=keyName(r);
      (agg[k]=agg[k]||[0,0,0])[0]+=r[3];agg[k][1]+=r[4];agg[k][2]+=r[5];}}); }
  let arr=Object.entries(agg).map(([k,v])=>[k,v[0],v[1],v[2],v[1]?v[2]/v[1]*100:0]);
  if(dQ)arr=arr.filter(r=>r[0].toLowerCase().includes(dQ));
  const [sc,desc]=dSort; arr.sort((a,b)=>(desc?-1:1)*(typeof a[sc]=='string'?a[sc].localeCompare(b[sc]):a[sc]-b[sc]));
  const tot=arr.reduce((a,r)=>[a[0]+r[1],a[1]+r[2],a[2]+r[3]],[0,0,0]);
  const maxv=Math.max(1,...arr.map(r=>r[3]));
  const H=['Položka / oblast','Schválený','Upravený','Skutečnost','% plnění','podíl'];
  const ar=i=>dSort[0]==i?(dSort[1]?' ▼':' ▲'):'';
  document.querySelector('#drill thead').innerHTML='<tr>'+H.map((h,i)=>
    `<th onclick="setSort(${i==5?3:i})">${h}<span class="ar">${ar(i==5?3:i)}</span></th>`).join('')+'</tr>';
  const pcl=p=>p>105?'warn':p<85?'bad':'ok';
  const crumb = dExpand?`<tr class="subrow"><td colspan="6"><span style="cursor:pointer;color:var(--accent)" onclick="dExpand=null;drill()">← zpět</span> · ${dExpand}</td></tr>`:'';
  document.querySelector('#drill tbody').className='fade';
  document.querySelector('#drill tbody').innerHTML=crumb+
    arr.map(r=>`<tr class="${expandable?'clk':''}" ${expandable?`onclick="dExpand=this.dataset.k;drill()"`:''} data-k="${r[0].replace(/"/g,'&quot;')}">
      <td><span class="nm">${expandable?'<i class="">▸</i>':''}${r[0]}</span></td>
      <td>${nf.format(r[1])}</td><td>${nf.format(r[2])}</td><td><b>${nf.format(r[3])}</b></td>
      <td>${r[2]?`<span class="pill ${pcl(r[4])}">${r[4].toFixed(0)} %</span>`:'–'}</td>
      <td class="barcell"><span class="b" style="width:${(r[3]/maxv*96).toFixed(0)}px"></span></td></tr>`).join('')+
    `<tr class="total"><td>Celkem ${dSide.toLowerCase()}</td><td>${nf.format(tot[0])}</td><td>${nf.format(tot[1])}</td>
      <td>${nf.format(tot[2])}</td><td>${tot[1]?(tot[2]/tot[1]*100).toFixed(0)+' %':''}</td><td></td></tr>`;
}
function setSort(i){dSort=[i,dSort[0]==i?!dSort[1]:true];drill();}

/* ---------- init + události ---------- */
function header(){
  document.getElementById('title').textContent=DATA.obec;
  document.getElementById('meta').textContent='Rozpočtové hospodaření 2013–2025 podle výkazu FIN 2-12 M · 💡 klikni na sloupec/výseč grafu pro detail';
  document.getElementById('chips').innerHTML=['IČO '+DATA.ico, DATA.nuts, 'Jihomoravský kraj',
    '≈ '+nf.format(POP)+' obyvatel','zdroj: MONITOR Státní pokladny']
    .map(c=>`<span class="chip">${c}</span>`).join('');
}
function rebuild(){PAL=paletteNow();trend();
  stacked('chPrijmy','Příjmy',r=>(POL[r[2]]||{}).t,'prijmyLeg',null,prMode);
  stacked('chVydaje','Výdaje',r=>(PAR[r[1]]||{}).o,'vydajeLeg',8,vyMode);
  donut();}
let prMode='abs', vyMode='abs';

header();
['dYear'].forEach(id=>{const s=document.getElementById(id);
  s.innerHTML='<option value="*">souhrn všech let</option>'+YRS.slice().reverse().map(y=>`<option value="${y}">${y}</option>`).join('');
  s.value=LY;});
const yr=document.getElementById('yearR'); yr.min=FY;yr.max=LY;yr.value=focusYear;
function setSlider(){const p=(focusYear-FY)/(LY-FY)*100;yr.style.setProperty('--p',p+'%');document.getElementById('yearV').textContent=focusYear;}
setSlider();
kpis(); rebuild(); drill();

document.getElementById('themeBtn').onclick=()=>{
  const d=isDark(); document.documentElement.setAttribute('data-theme',d?'light':'dark');
  try{localStorage.setItem('strelice-theme',d?'light':'dark');}catch(e){}
  kpis(); rebuild();};
seg('metricSeg',b=>{metric=+b.dataset.m;trend();});
seg('prSeg',b=>{prMode=b.dataset.v;stacked('chPrijmy','Příjmy',r=>(POL[r[2]]||{}).t,'prijmyLeg',null,prMode);});
seg('vySeg',b=>{vyMode=b.dataset.v;stacked('chVydaje','Výdaje',r=>(PAR[r[1]]||{}).o,'vydajeLeg',8,vyMode);});
seg('donutSeg',b=>{donutSide=b.dataset.s;donut();});
seg('sideSeg',b=>{dSide=b.dataset.s;dExpand=null;drill();});
yr.oninput=()=>{focusYear=+yr.value;setSlider();trend();donut();};
document.getElementById('dYear').onchange=()=>{dExpand=null;drill();};
document.getElementById('dGroup').onchange=()=>{dExpand=null;drill();};
document.getElementById('dSearch').oninput=e=>{dQ=e.target.value.toLowerCase().trim();drill();};
function seg(id,fn){const el=document.getElementById(id);el.querySelectorAll('button').forEach(b=>b.onclick=()=>{
  el.querySelectorAll('button').forEach(x=>x.classList.remove('on'));b.classList.add('on');fn(b);});}

/* robustní přepočet velikosti grafů (layout race / resize okna) */
function resizeAll(){Object.values(charts).forEach(c=>{try{c.resize();}catch(e){}});}
let rzT; window.addEventListener('resize',()=>{clearTimeout(rzT);rzT=setTimeout(resizeAll,120);});
window.addEventListener('load',()=>{resizeAll();setTimeout(resizeAll,80);});

/* modal – zavírání */
document.getElementById('modalX').onclick=closeModal;
document.getElementById('modalBd').onclick=closeModal;
document.addEventListener('keydown',e=>{if(e.key=='Escape')closeModal();});

</script>
<footer class="footer">Sestavil <b style="color:var(--muted)">Radim Brener</b> ze surových CSV souborů, jednoho terminálu a hluboké víry, že veřejná data jsou vždy konzistentní 🙃 &nbsp;·&nbsp; Python &thinsp;·&thinsp; Chart.js &thinsp;·&thinsp; MONITOR SP &thinsp;·&thinsp; ČSÚ &thinsp;·&thinsp; 2025–2026</footer>
</body>
</html>"""

nav_links = "".join(
    f'<a href="{href}"{" class=\"active\"" if label == "Rozpočet" else ""}>{label}</a>'
    for href, label in pc.SECTIONS)
HTML = (HTML.replace("/*CHARTJS*/", chartjs).replace("/*DATA*/", data_json)
        .replace("/*FAVICON*/", pc.FAVICON_LINK).replace("<!--NAV-->", nav_links)
        .replace("/*ANALYTICS*/", pc.ANALYTICS))
open(OUT, "w", encoding="utf-8").write(HTML)
print(f"HOTOVO -> {OUT}  ({len(HTML)//1024} kB, {len(rows)} radku, roky {years[0]}-{years[-1]})")
