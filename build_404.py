#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stránka 404 (404.html) se zmateným maskotem. Server ji vrací přes ErrorDocument v .htaccess.

Chybová stránka se zobrazuje i na neexistujících adresách v podsložkách (/neco/jineho),
proto má <base href="/">: relativní odkazy, písma i obrázky se pak berou z kořene webu.
"""
import portal_common as pc

LINKS = [("index.html", "Úvodní stránka"), ("hledat.html", "Hledat na portálu"), ("rozpocet.html", "Rozpočet obce")]

body = f'''<section class="e404">
  <span class="e-fig">{pc.mascot_img("09-404", "msk")}</span>
  <div>
    <p class="e-code">Chyba 404</p>
    <h1>Tuhle stránku jsem nenašel</h1>
    <p>Odkaz je možná starý nebo v adrese chybí kousek. Na portálu ale nic nezmizelo, zkuste začít odsud:</p>
    <div class="g-links">{"".join(f'<a href="{h}">{t} <span aria-hidden="true">→</span></a>' for h, t in LINKS)}</div>
  </div>
</section>'''

CSS = """<style>
.e404{display:flex;align-items:center;gap:28px;margin:40px 0 20px}
.e-fig{flex:none;width:220px;height:220px;border-radius:50%;background:var(--msk-bg);display:grid;place-items:center}
.e-fig .msk{width:196px;height:196px}
.e-code{margin:0;font-size:12px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:var(--amber-ink)}
.e404 h1{margin:4px 0 8px;font-size:clamp(26px,4vw,36px)}
.e404 p{color:var(--muted);line-height:1.55}
.g-links{display:flex;flex-wrap:wrap;gap:8px;margin-top:14px}
.g-links a{font-size:14px;font-weight:650;color:var(--accent);text-decoration:none;border:1px solid var(--line);border-radius:999px;padding:8px 15px;background:var(--surface)}
.g-links a:hover{border-color:var(--accent)}
@media(max-width:640px){.e404{flex-direction:column;text-align:center;gap:14px;margin-top:20px}.e-fig{width:160px;height:160px}
  .e-fig .msk{width:142px;height:142px}.g-links{justify-content:center}}
</style>"""

html = pc.page("", "Stránka nenalezena — " + pc.BRAND, body, head_scripts=CSS)
html = html.replace("<head>", '<head>\n<base href="/">\n<meta name="robots" content="noindex">', 1)
open("404.html", "w", encoding="utf-8").write(html)
print("HOTOVO: 404.html")
