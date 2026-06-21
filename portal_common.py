#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Společné prvky portálu obce Střelice: sdílené CSS, hlavička s navigací
mezi sekcemi, přepínač světlý/tmavý režim, patička. Každá stránka je
samostatný HTML soubor (data + Chart.js vložené) → funguje po dvojkliku
i odděleně; navigace mezi sekcemi funguje, leží-li soubory ve stejné složce."""
import urllib.parse

SECTIONS = [
    ("index.html",    "Přehled"),
    ("rozpocet.html", "Rozpočet"),
    ("investice.html", "Investice"),
    ("dotace.html",   "Dotace spolkům"),
    ("skolstvi.html", "Školství"),
    ("zapisy.html",   "Rada obce"),
    ("zastupitelstvo.html", "Zastupitelstvo"),
]

SHARED_CSS = r"""
:root{
  --bg1:#eef2f9; --bg2:#f8fafc; --surface:#fff; --surface2:#f8fafc; --inset:#f1f5f9;
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
  --bg1:#0a0f1d; --bg2:#0b1120; --surface:#121a2c; --surface2:#0f1626; --inset:#0d1424;
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
  font-size:15px;line-height:1.55;background:radial-gradient(1200px 600px at 80% -10%, var(--bg1), var(--bg2)) no-repeat;
  min-height:100vh;-webkit-font-smoothing:antialiased}
.wrap{max-width:1160px;margin:0 auto;padding:0 20px 20px}
.ptop{position:sticky;top:0;z-index:50;background:var(--surface);border-bottom:1px solid var(--line)}
.ptop .in{max-width:1160px;margin:0 auto;padding:11px 20px;display:flex;align-items:center;gap:16px}
.brand{display:flex;align-items:center;gap:11px;font-weight:600;letter-spacing:-.01em;text-decoration:none;color:var(--text)}
.brand .dot{width:30px;height:30px;border-radius:9px;display:grid;place-items:center;color:#fff;
  background:linear-gradient(135deg,var(--accent),#5fa3ab);font-size:14px;box-shadow:var(--shadow)}
.brand small{display:block;font-weight:400;color:var(--muted);font-size:11.5px;letter-spacing:0}
.pnav{display:flex;gap:2px;margin-left:auto;flex-wrap:wrap}
.pnav a{padding:7px 13px;border-radius:10px;color:var(--muted);text-decoration:none;font-size:13.5px;font-weight:500;transition:.18s;white-space:nowrap}
.pnav a:hover{color:var(--text);background:var(--inset)}
.pnav a.active{color:var(--accent);background:var(--accent-soft)}
.iconbtn{width:38px;height:34px;border:1px solid var(--line);background:var(--surface);border-radius:10px;cursor:pointer;color:var(--muted);display:grid;place-items:center;transition:.18s;font-size:15px}
.iconbtn:hover{color:var(--text);border-color:var(--accent)}
.hero{padding:34px 0 8px}
.hero h1{font-size:30px;font-weight:680;letter-spacing:-.02em;margin:0 0 6px;color:var(--text)}
.hero p{color:var(--muted);margin:0;font-size:14.5px}
.chips{display:flex;gap:8px;margin-top:14px;flex-wrap:wrap}
.chip{font-size:12px;padding:5px 11px;border-radius:999px;background:var(--inset);color:var(--muted);border:1px solid var(--line)}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(186px,1fr));gap:14px;margin:22px 0 8px}
.kpi{background:var(--surface);border:1px solid var(--line);border-radius:var(--radius);padding:16px 18px;box-shadow:var(--shadow);transition:transform .2s,box-shadow .2s;position:relative;overflow:hidden}
.kpi:hover{transform:translateY(-3px);box-shadow:var(--shadow-h)}
.kpi::after{content:"";position:absolute;left:0;top:0;bottom:0;width:4px;background:var(--bar,var(--accent))}
.kpi .lab{font-size:12.5px;color:var(--muted)}
.kpi .val{font-size:26px;font-weight:680;margin-top:7px;letter-spacing:-.02em;font-variant-numeric:tabular-nums}
.kpi .delta{font-size:12px;margin-top:5px;font-weight:500}
.up{color:var(--pos)} .down{color:var(--neg)}
section{margin-top:30px;scroll-margin-top:74px}
.sec-h{display:flex;align-items:baseline;gap:12px;margin:0 0 14px}
.sec-h h2{font-size:19px;font-weight:640;margin:0;letter-spacing:-.01em}
.sec-h .hint{color:var(--faint);font-size:12.5px}
.panel{background:var(--surface);border:1px solid var(--line);border-radius:var(--radius);padding:20px 22px;box-shadow:var(--shadow)}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:18px}
@media(max-width:820px){.grid2{grid-template-columns:1fr}.pnav a{padding:7px 9px}}
.ctrls{display:flex;flex-wrap:wrap;gap:12px 18px;align-items:center;margin-bottom:6px}
.seg{display:inline-flex;background:var(--inset);border-radius:11px;padding:3px;gap:2px}
.seg button{border:0;background:transparent;color:var(--muted);font:inherit;font-size:13px;font-weight:500;padding:6px 13px;border-radius:8px;cursor:pointer;transition:.16s}
.seg button.on{background:var(--surface);color:var(--text);box-shadow:var(--shadow)}
.lbl{font-size:12.5px;color:var(--muted);font-weight:500;margin-right:2px}
.legend{display:flex;flex-wrap:wrap;gap:8px 16px;font-size:12px;color:var(--muted);margin:10px 0}
.legend span{display:inline-flex;align-items:center;gap:6px}
.sw{width:11px;height:11px;border-radius:3px;display:inline-block}
.chartbox{position:relative;width:100%;height:330px;margin-top:6px}
.chartbox.sm{height:280px}
.note{font-size:12px;color:var(--faint);margin-top:12px;line-height:1.6}
.footer{margin-top:18px;color:var(--faint);font-size:11.5px;text-align:center;line-height:1.4;padding-bottom:6px}
/* rozcestník */
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:18px;margin-top:8px}
.tile{display:flex;flex-direction:column;gap:10px;background:var(--surface);border:1px solid var(--line);border-radius:var(--radius);
  padding:22px 22px;box-shadow:var(--shadow);text-decoration:none;color:var(--text);transition:transform .2s,box-shadow .2s;position:relative}
.tile:hover{transform:translateY(-4px);box-shadow:var(--shadow-h)}
.tile.soon{opacity:.65;pointer-events:none}
.tile .ic{width:46px;height:46px;border-radius:13px;display:grid;place-items:center;font-size:22px;color:#fff;background:linear-gradient(135deg,var(--accent),#5fa3ab)}
.tile h3{margin:4px 0 0;font-size:18px;font-weight:640}
.tile p{margin:0;color:var(--muted);font-size:13.5px;line-height:1.55}
.tile .go{margin-top:auto;font-size:13px;color:var(--accent);font-weight:600}
.tile .badge{position:absolute;top:16px;right:16px;font-size:11px;padding:3px 9px;border-radius:999px;background:var(--inset);color:var(--muted)}
.statline{display:flex;gap:18px;flex-wrap:wrap;margin-top:6px;font-size:12.5px;color:var(--muted)}
.statline b{color:var(--text);font-weight:600}
/* modal */
.modal{position:fixed;inset:0;z-index:200;display:flex;align-items:center;justify-content:center;padding:18px}
.modal[hidden]{display:none}
.modal-bd{position:absolute;inset:0;background:rgba(15,23,42,.5)}
.modal-card{position:relative;background:var(--surface);border:1px solid var(--line);border-radius:var(--radius);max-width:640px;width:100%;max-height:84vh;display:flex;flex-direction:column;box-shadow:0 24px 70px rgba(0,0,0,.4)}
.modal-h{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:15px 18px;border-bottom:1px solid var(--line)}
.modal-h b{font-size:15.5px;font-weight:600}
.modal-c{padding:8px 18px 18px;overflow:auto}
.mtab{width:100%;border-collapse:collapse;font-size:12.5px;margin-top:8px}
.mtab th,.mtab td{padding:7px 8px;border-bottom:1px solid var(--line);text-align:right;white-space:nowrap}
.mtab th:first-child,.mtab td:first-child{text-align:left;white-space:normal}
.mtab th{color:var(--muted);font-weight:600;font-size:11.5px}
.mtab tr.total td{font-weight:680;border-top:2px solid var(--text);background:var(--surface2)}
"""

TARGET_SVG = ('<svg width="18" height="18" viewBox="0 0 48 48" fill="none" stroke="#fff" '
    'stroke-width="3.4" stroke-linecap="round" stroke-linejoin="round">'
    '<circle cx="27" cy="21" r="15"/><circle cx="27" cy="21" r="8"/>'
    '<circle cx="27" cy="21" r="3.4" fill="#fff" stroke="none"/>'
    '<line x1="5" y1="43" x2="27" y2="21"/><path d="M5 43 l7 -1.4 M5 43 l1.4 -7"/></svg>')

# favikona — terč se šípem na zaobleném čtverci (SVG data URI, funguje offline)
_FAV_SVG = ("<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 48 48'>"
    "<rect width='48' height='48' rx='11' fill='#3d6c9e'/>"
    "<circle cx='27' cy='21' r='13' fill='none' stroke='#fff' stroke-width='3.4'/>"
    "<circle cx='27' cy='21' r='7' fill='none' stroke='#fff' stroke-width='3.4'/>"
    "<line x1='6' y1='42' x2='27' y2='21' stroke='#fff' stroke-width='3.4' stroke-linecap='round'/>"
    "<circle cx='27' cy='21' r='3' fill='#fff'/></svg>")
FAVICON_LINK = '<link rel="icon" href="data:image/svg+xml,' + urllib.parse.quote(_FAV_SVG) + '">'

def topbar(active):
    links = "".join(
        f'<a href="{href}"{" class=\"active\"" if name==active else ""}>{name}</a>'
        for href, name in SECTIONS)
    return f'''<div class="ptop"><div class="in">
  <a class="brand" href="index.html"><span class="dot">{TARGET_SVG}</span><span>Jak žijí Střelice<small>otevřená data obce</small></span></a>
  <nav class="pnav">{links}</nav>
  <button class="iconbtn" id="themeBtn" title="Světlý/tmavý režim">◐</button>
</div></div>'''

THEME_INIT = r"""(function(){try{var t=localStorage.getItem('strelice-theme');if(t)document.documentElement.setAttribute('data-theme',t);}catch(e){}})();"""

THEME_JS = r"""
function bindTheme(after){var b=document.getElementById('themeBtn');if(!b)return;
  b.onclick=function(){var d=document.documentElement.getAttribute('data-theme')==='dark';
    document.documentElement.setAttribute('data-theme',d?'light':'dark');
    try{localStorage.setItem('strelice-theme',d?'light':'dark');}catch(e){}
    if(after)after();};}
function cssv(n){return getComputedStyle(document.documentElement).getPropertyValue(n).trim();}
function isDark(){return document.documentElement.getAttribute('data-theme')==='dark';}
"""

def page(active, title, body, head_scripts="", body_scripts=""):
    footer = '<footer class="footer">Sestavil <b style="color:var(--muted)">Radim Brener</b> ze surových CSV souborů, jednoho terminálu a hluboké víry, že veřejná data jsou vždy konzistentní 🙃 &nbsp;·&nbsp; Python &thinsp;·&thinsp; Chart.js &thinsp;·&thinsp; MONITOR SP &thinsp;·&thinsp; ČSÚ &thinsp;·&thinsp; 2025–2026</footer>'
    return f'''<!DOCTYPE html>
<html lang="cs" data-theme="dark">
<head>
<script>{THEME_INIT}</script>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
{FAVICON_LINK}
<style>{SHARED_CSS}</style>
{head_scripts}
</head>
<body>
{topbar(active)}
<div class="wrap">
{body}
{footer}
</div>
<script>{THEME_JS}</script>
{body_scripts}
</body>
</html>'''
