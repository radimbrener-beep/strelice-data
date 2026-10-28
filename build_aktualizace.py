#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stránka Jak často se data kontrolují (aktualizace.html) — pro každý zdroj
portálu: odkud se bere, jak často se kontroluje (automaticky / ručně) a jak čerstvá
jsou data teď. Časy automatické kontroly odpovídají cronu v .github/workflows/check_web.yml.
Odkazuje se z patičky a ze stránky Metodika; přegeneruje ji scripts/update_portal.py."""
import sys, json, csv
from datetime import date
import portal_common as pc
sys.stdout.reconfigure(encoding="utf-8")

A = 'target="_blank" rel="noopener" style="color:var(--accent)"'
MESICE = ["lednu", "únoru", "březnu", "dubnu", "květnu", "červnu", "červenci",
          "srpnu", "září", "říjnu", "listopadu", "prosinci"]


def posledni(path):
    d = max(json.load(open(path, encoding="utf-8")), key=lambda m: m["datum"])
    return d, date.fromisoformat(d["datum"])


zo, zo_d = posledni("dataset_ZO.json")
ro, ro_d = posledni("dataset_RO.json")
with open("data/strelice_fin_2026.csv", encoding="utf-8-sig") as f:
    fin_m = max(int(r["obdobi"]) for r in csv.DictReader(f, delimiter=";"))

body = f'''<header class="hero">
  <h1>Jak často se data kontrolují</h1>
  <p>Portál nic nevymýšlí — jen přebírá, co zveřejní obec a státní instituce. Tady je u každého zdroje vidět, jak často se kontroluje, jestli to dělá automat, nebo ruka, a jak čerstvá data na portálu právě jsou.</p>
  <div class="chips"><span class="chip">automat 3× denně</span><span class="chip">ruční zdroje průběžně</span><span class="chip">vše s odkazem na originál</span></div>
</header>

<div class="cards">
  <div class="kpi" style="--bar:var(--accent)"><div class="lab">Automatická kontrola webu obce</div><div class="val">3× denně</div><div class="delta" style="color:var(--muted)">orientačně kolem 7, 12 a 15 h</div></div>
  <div class="kpi" style="--bar:var(--c0)"><div class="lab">Nejnovější zastupitelstvo</div><div class="val">{zo_d.day}.&nbsp;{zo_d.month}.</div><div class="delta" style="color:var(--muted)">{zo["cislo_zasedani"]}. zasedání, {zo_d.year}</div></div>
  <div class="kpi" style="--bar:var(--c2)"><div class="lab">Nejnovější rada</div><div class="val">{ro_d.day}.&nbsp;{ro_d.month}.</div><div class="delta" style="color:var(--muted)">{ro["cislo_zasedani"]}. zasedání, {ro_d.year}</div></div>
  <div class="kpi" style="--bar:var(--c3)"><div class="lab">Plnění rozpočtu 2026</div><div class="val">k {MESICE[fin_m - 1]}</div><div class="delta" style="color:var(--muted)">poslední měsíc v MONITORu</div></div>
</div>

<section>
  <div class="sec-h"><h2>Zdroje a jejich kontrola</h2><span class="hint">od nejčastěji kontrolovaných</span></div>
  <div class="panel"><div class="tw"><table class="mtab ak">
    <thead><tr><th>Sekce</th><th>Zdroj</th><th>Jak často</th><th>Jak</th></tr></thead>
    <tbody>
      <tr><td><b>Rada obce</b><br><span class="sub">zápisy, usnesení</span></td><td><a href="https://www.streliceubrna.cz/obec/samosprava/rada-obce-strelice" {A}>zápisy rady na webu obce</a></td><td>3× denně<br><span class="sub">kolem 7 · 12 · 15 h</span></td><td><span class="tag auto">automaticky</span> nový zápis se stáhne, rozebere a do pár minut je na portálu</td></tr>
      <tr><td><b>Zastupitelstvo</b><br><span class="sub">usnesení, hlasování</span></td><td><a href="https://www.streliceubrna.cz/obec/samosprava/zastupitelstvo-obce-strelice" {A}>usnesení ZO na webu obce</a></td><td>3× denně<br><span class="sub">kolem 7 · 12 · 15 h</span></td><td><span class="tag auto">automaticky</span> včetně jmenovitého hlasování a upozornění odběratelům</td></tr>
      <tr><td><b>Videozáznamy zasedání</b></td><td><a href="https://www.youtube.com/@tvstreliceubrna/videos" {A}>YouTube kanál TV Střelice</a></td><td>3× denně<br><span class="sub">kolem 7 · 12 · 15 h</span></td><td><span class="tag auto">automaticky</span> video se přiřadí k zasedání a body programu k časům ve videu</td></tr>
      <tr><td><b>Vypsané zakázky</b><br><span class="sub">stránka Zakázky</span></td><td><a href="https://www.e-zakazky.cz/Profil-Zadavatele/c62ff3fd-035b-4804-850e-f63264638ee2" {A}>profil zadavatele obce</a> (E-zakázky)</td><td>3× denně<br><span class="sub">kolem 7 · 12 · 15 h</span></td><td><span class="tag auto">automaticky</span> nová zakázka, podané nabídky i vybraná firma se převezmou při nejbližší kontrole</td></tr>
      <tr><td><b>Zakázky, Investice (akce), Moje ulice, Bilance období</b></td><td>odvozeno z usnesení rady a zastupitelstva</td><td>s každým novým zápisem<br><span class="sub">kolem 7 · 12 · 15 h</span></td><td><span class="tag auto">automaticky</span> přepočítá se spolu s novým zápisem</td></tr>
      <tr><td><b>Diskuze ze zastupitelstva</b></td><td>titulky videozáznamu</td><td>po každém zasedání se záznamem</td><td><span class="tag ruc">ručně</span> přepis se rozdělí k bodům a redakčně učeše po zveřejnění videa</td></tr>
      <tr><td><b>Plnění rozpočtu letos</b></td><td><a href="https://monitor.statnipokladna.gov.cz" {A}>MONITOR Státní pokladny</a>, FIN 2-12 M</td><td>měsíčně</td><td><span class="tag ruc">ručně</span> MONITOR zveřejňuje měsíční výkazy obcí s odstupem několika týdnů</td></tr>
      <tr><td><b>Rozpočet, Investice (grafy), Srovnání</b></td><td><a href="https://monitor.statnipokladna.gov.cz" {A}>MONITOR Státní pokladny</a></td><td>ročně</td><td><span class="tag ruc">ručně</span> uzavřený rok bývá v MONITORu v březnu–dubnu následujícího roku</td></tr>
      <tr><td><b>Dotace spolkům</b></td><td><a href="https://www.streliceubrna.cz" {A}>veřejnoprávní smlouvy na webu obce</a></td><td>průběžně</td><td><span class="tag ruc">ručně</span> obec smlouvy zveřejňuje nárazově, obvykle po schválení dotací na začátku roku</td></tr>
      <tr><td><b>Školství, Demografie</b></td><td><a href="https://data.csu.gov.cz" {A}>ČSÚ</a>, MŠMT, výroční zprávy škol</td><td>ročně</td><td><span class="tag ruc">ručně</span> po zveřejnění nových ročních dat</td></tr>
      <tr><td><b>Volby</b></td><td><a href="https://www.volby.cz" {A}>volby.cz</a> (ČSÚ)</td><td>po volbách</td><td><span class="tag ruc">ručně</span> po vyhlášení výsledků</td></tr>
    </tbody>
  </table></div></div>
</section>

<section>
  <div class="sec-h"><h2>Jak automatická kontrola funguje</h2></div>
  <div class="panel">
    <p>Třikrát denně — orientačně kolem 7, 12 a 15 hodin — se spustí skript, který projde seznamy zápisů rady a usnesení zastupitelstva na webu obce a porovná je s tím, co už portál zná. Když najde nový dokument, stáhne PDF, vytáhne z něj jednotlivá usnesení a hlasování, dohledá k zasedání videozáznam, přegeneruje dotčené stránky a portál se sám nasadí. Odběratelům upozornění pak přijde zpráva o novém jednání.</p>
    <p>Když se nic nového neobjeví, nic se nemění — datum v patičce tedy ukazuje poslední skutečnou změnu, ne poslední kontrolu.</p>
    <p class="note">Časy jsou orientační: kontrola běží na GitHubu, který naplánované úlohy spouští s proměnlivým, často několikahodinovým zpožděním. Kontrola je proto naplánovaná s předstihem a skutečný čas se může o hodinu i víc lišit oběma směry. V letním čase běží zhruba o hodinu později.</p>
  </div>
</section>

<section>
  <div class="sec-h"><h2>Proč tu něco ještě není</h2></div>
  <div class="panel">
    <table class="mtab"><tbody>
      <tr><td><b>Obec dokument ještě nezveřejnila</b></td><td>zápis rady i usnesení zastupitelstva se zveřejňují až po ověření, obvykle několik dní až dva týdny po zasedání — portál je převezme nejpozději při další kontrole</td></tr>
      <tr><td><b>Zdroj zveřejňuje s odstupem</b></td><td>MONITOR, ČSÚ i školské statistiky vycházejí měsíce po skončení období, které popisují</td></tr>
      <tr><td><b>Ruční krok ještě neproběhl</b></td><td>přepisy diskuzí a sekce označené „ručně" aktualizuje autor portálu ve volném čase — když něco chybí déle, než je uvedeno výše, dejte vědět: ''' + pc.MAIL_LINK + '''</td></tr>
    </tbody></table>
    <p class="note">Podrobnosti o tom, jak se data zpracovávají a jaká mají omezení, jsou na stránce <a href="metodika.html" style="color:var(--accent)">Metodika a zdroje dat</a>.</p>
  </div>
</section>'''

CSS = '''<style>
.tw{overflow-x:auto}
.mtab th,.mtab td{text-align:left;white-space:normal;vertical-align:top}
.mtab th{font-size:12px;color:var(--muted);font-weight:600}
.mtab td:first-child{width:28%}
.ak td:nth-child(3){white-space:nowrap}
.ak .sub{font-size:11.5px;color:var(--faint)}
.tag{display:inline-block;font-size:11px;font-weight:600;padding:1px 8px;border-radius:999px;margin:0 6px 3px 0;border:1px solid var(--line)}
.tag.auto{color:var(--c0);background:color-mix(in srgb,var(--c0) 12%,transparent)}
.tag.ruc{color:var(--muted);background:var(--inset)}
.panel p{line-height:1.6}
@media(max-width:640px){.ak td:nth-child(3){white-space:normal}.mtab td:first-child{width:auto}}
</style>'''

open("aktualizace.html", "w", encoding="utf-8").write(
    pc.page("Aktualizace", "Jak často se data kontrolují — " + pc.BRAND, body, head_scripts=CSS))
print("HOTOVO: aktualizace.html")
