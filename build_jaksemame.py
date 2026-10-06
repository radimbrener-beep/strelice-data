#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Rozcestník jaksemame.cz → jaksemame/index.html (obce na subdoménách).

Samostatná stránka bez navigace portálu; barvy, písma a logo ze sdílené značky
(portal_common, brand/). Deploy ji nahraje do /www/domains/jaksemame.cz/ spolu
s fonts/ a favikonami. Novou obec stačí přidat do OBCE.
"""
import os
import portal_common as pc
from brand.scene import scene, scene_css, DAY, NIGHT

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(HERE, "jaksemame")

# (slug subdomény, popis obce, co na portálu najdeš)
OBCE = [
    ("strelice", "Střelice u Brna · okres Brno-venkov",
     "Rozpočet, investice, zakázky, dotace spolkům, usnesení zastupitelstva i rady, školství a volby."),
    ("ostopovice", "Ostopovice · okres Brno-venkov",
     "Rozpočet, investice, zakázky, dotace, usnesení zastupitelstva, školství a volby."),
]


def svg(path):
    return open(os.path.join(HERE, "brand", "logo", "web", path), encoding="utf-8").read().strip()


# téma: výchozí podle systému, ruční volba přepínačem (data-theme + localStorage jako na portálech)
THEME_KEY = "jaksemame-theme"
THEME_INIT = ("(function(){var t;try{t=localStorage.getItem('" + THEME_KEY + "')}catch(e){}"
              "if(!t)t=matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light';"
              "document.documentElement.setAttribute('data-theme',t)})();")
THEME_JS = ("document.getElementById('themeBtn').onclick=function(){var r=document.documentElement,"
            "t=r.getAttribute('data-theme')==='dark'?'light':'dark';r.setAttribute('data-theme',t);"
            "try{localStorage.setItem('" + THEME_KEY + "',t)}catch(e){}};")

CSS = pc.FONTS_CSS + pc.TOKENS_CSS + r"""
*{box-sizing:border-box}
body{margin:0;background:var(--bg2);color:var(--text);font-family:var(--font-b);font-size:16px;line-height:1.55;-webkit-font-smoothing:antialiased}
body{display:flex;flex-direction:column;min-height:100vh}
.wrap{flex:1;width:100%;max-width:880px;margin:0 auto;padding-inline:20px;padding-block:64px 48px;display:flex;flex-direction:column;gap:40px}
.lg-i{fill:var(--ink)}.lg-o{fill:var(--accent)}.lg-a{fill:var(--amber)}.lg-q{fill:var(--muted)}
.top{display:flex;align-items:center;justify-content:space-between;gap:16px}
header .top svg{height:56px;width:auto;max-width:100%;display:block;min-width:0}
.themebtn{flex:none;width:40px;height:36px;border:1px solid var(--line);background:var(--surface);border-radius:10px;
  color:var(--muted);cursor:pointer;font-size:16px;display:grid;place-items:center;transition:.18s}
.themebtn:hover{color:var(--text);border-color:var(--accent)}
.themebtn:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
h1{font-family:var(--font-d);font-weight:720;font-size:clamp(28px,4.4vw,40px);letter-spacing:-.025em;color:var(--ink);margin:26px 0 0;text-wrap:balance}
.lead{color:var(--muted);font-size:17px;max-width:62ch;margin:12px 0 0}
.obce{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,340px),1fr));gap:16px}
.obec{display:flex;flex-direction:column;gap:12px;padding:26px 26px 22px;background:var(--surface);border:1px solid var(--line);
  border-radius:var(--radius);box-shadow:var(--shadow);text-decoration:none;color:var(--text);transition:transform .2s,box-shadow .2s,border-color .2s}
.obec:hover{transform:translateY(-3px);box-shadow:var(--shadow-h);border-color:var(--accent)}
.obec:focus-visible{outline:2px solid var(--accent);outline-offset:3px}
.obec svg{height:30px;width:auto;max-width:100%;display:block;align-self:flex-start}
.obec .kde{font-size:13px;color:var(--muted)}
.obec p{margin:0;font-size:15px}
.obec .go{margin-top:auto;padding-top:6px;font-weight:700;font-size:14px;color:var(--accent)}
.obec .url{font-family:var(--font-m);font-size:12.5px;color:var(--faint)}
/* pás s obcemi: ve světlém režimu den, v tmavém noc (barvy SVG přes třídy sk-*) */
.night{height:clamp(200px,26vw,330px)}
.night svg{width:100%;height:100%;display:block}
footer{background:""" + DAY["hill2"] + """;color:#24434d;font-size:13px;padding:6px 20px 26px}
html[data-theme="dark"] .night{background:linear-gradient(#0d191e00,#0d191e 60%)}
html[data-theme="dark"] footer{background:""" + NIGHT["hill2"] + """;color:#a8bec0}
""" + scene_css() + """
footer p{max-width:880px;margin:0 auto}
@media (prefers-reduced-motion: reduce){.obec{transition:none}.obec:hover{transform:none}}
"""


def card(slug, kde, popis):
    return (f'<a class="obec" href="//{slug}.jaksemame.cz/">{svg(slug + "-header.svg")}'
            f'<span class="kde">{kde}</span><p>{popis}</p>'
            f'<span class="go">Otevřít portál →</span><span class="url">{slug}.jaksemame.cz</span></a>')


HTML = f"""<!DOCTYPE html>
<html lang="cs">
<head>
<script>{THEME_INIT}</script>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Jak se máme — občanský datový portál obcí</title>
<meta name="description" content="Občanský datový portál: rozpočet, investice, zakázky a rozhodnutí zastupitelstva obcí srozumitelně a z veřejných zdrojů.">
<meta property="og:title" content="Jak se máme — občanský datový portál obcí">
<meta property="og:description" content="Rozpočet, investice, zakázky a rozhodnutí obcí srozumitelně a z veřejných zdrojů.">
<meta property="og:type" content="website">
{pc.FAVICON_LINK}
<style>{CSS}</style>
</head>
<body>
<div class="wrap">
  <header>
    <div class="top">{svg("jaksemame-header.svg").replace("<svg ", '<svg role="img" aria-label="Jak se máme" ', 1)}
      <button class="themebtn" id="themeBtn" type="button" title="Světlý/tmavý režim" aria-label="Přepnout světlý a tmavý režim">◐</button></div>
    <h1>Občanský datový portál obcí</h1>
    <p class="lead">Veřejná data obce na jednom místě a srozumitelně: kolik obec vybere a utratí, co staví, komu platí
    a jak rozhoduje zastupitelstvo. Každé číslo má odkaz na původní zdroj.</p>
  </header>
  <main class="obce" aria-label="Obce">
    {"".join(card(*o) for o in OBCE)}
  </main>
</div>
<div class="night">{scene(wide=True, preserve="xMidYMax slice", themed=True)}</div>
<footer><p>Nezávislý občanský projekt, není oficiálním webem žádné obce · data z veřejných zdrojů
  (MONITOR Státní pokladny, ČSÚ, zápisy obcí) · Radim Brener</p></footer>
<script>{THEME_JS}</script>
</body>
</html>
"""

os.makedirs(OUT_DIR, exist_ok=True)
with open(os.path.join(OUT_DIR, "index.html"), "w", encoding="utf-8") as f:
    f.write(HTML)
print(f"HOTOVO: jaksemame/index.html ({len(HTML) // 1024} kB, {len(OBCE)} obce)")
