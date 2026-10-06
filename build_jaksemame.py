#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Rozcestník jaksemame.cz → jaksemame/index.html (obce na subdoménách).

Samostatná stránka bez navigace portálu; barvy, písma a logo ze sdílené značky
(portal_common, brand/). Deploy ji nahraje do /www/domains/jaksemame.cz/ spolu
s fonts/ a favikonami. Novou obec stačí přidat do OBCE.
"""
import os
import portal_common as pc

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


# téma podle systému (bez přepínače): tmavé tokeny portálu převedené na media query
dark = pc.TOKENS_CSS.split('html[data-theme="dark"]{', 1)[1].rsplit("}", 1)[0]
TOKENS = pc.TOKENS_CSS.split('html[data-theme="dark"]{', 1)[0] + \
    "@media (prefers-color-scheme: dark){:root{" + dark + "}}\n"

CSS = pc.FONTS_CSS + TOKENS + r"""
*{box-sizing:border-box}
body{margin:0;background:var(--bg2);color:var(--text);font-family:var(--font-b);font-size:16px;line-height:1.55;-webkit-font-smoothing:antialiased}
.wrap{max-width:880px;margin:0 auto;padding-inline:20px;padding-block:64px 40px;display:flex;flex-direction:column;gap:40px;min-height:100vh}
.lg-i{fill:var(--ink)}.lg-o{fill:var(--accent)}.lg-a{fill:var(--amber)}.lg-q{fill:var(--muted)}
header svg{height:56px;width:auto;max-width:100%;display:block}
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
footer{margin-top:auto;padding-top:22px;border-top:1px solid var(--line);color:var(--faint);font-size:13px}
@media (prefers-reduced-motion: reduce){.obec{transition:none}.obec:hover{transform:none}}
"""


def card(slug, kde, popis):
    return (f'<a class="obec" href="//{slug}.jaksemame.cz/">{svg(slug + "-header.svg")}'
            f'<span class="kde">{kde}</span><p>{popis}</p>'
            f'<span class="go">Otevřít portál →</span><span class="url">{slug}.jaksemame.cz</span></a>')


HTML = f"""<!DOCTYPE html>
<html lang="cs">
<head>
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
    {svg("jaksemame-header.svg").replace("<svg ", '<svg role="img" aria-label="Jak se máme" ', 1)}
    <h1>Občanský datový portál obcí</h1>
    <p class="lead">Veřejná data obce na jednom místě a srozumitelně: kolik obec vybere a utratí, co staví, komu platí
    a jak rozhoduje zastupitelstvo. Každé číslo má odkaz na původní zdroj.</p>
  </header>
  <main class="obce" aria-label="Obce">
    {"".join(card(*o) for o in OBCE)}
  </main>
  <footer>Nezávislý občanský projekt, není oficiálním webem žádné obce · data z veřejných zdrojů
  (MONITOR Státní pokladny, ČSÚ, zápisy obcí) · Radim Brener</footer>
</div>
</body>
</html>
"""

os.makedirs(OUT_DIR, exist_ok=True)
with open(os.path.join(OUT_DIR, "index.html"), "w", encoding="utf-8") as f:
    f.write(HTML)
print(f"HOTOVO: jaksemame/index.html ({len(HTML) // 1024} kB, {len(OBCE)} obce)")
