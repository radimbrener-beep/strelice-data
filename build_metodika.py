#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generuje stránku Metodika a zdroje dat (metodika.html) — centrální
vysvětlení, odkud data pocházejí, jak se zpracovávají a jaká mají omezení.
Odkazuje se z patičky všech stránek portálu."""
import sys
import portal_common as pc
sys.stdout.reconfigure(encoding="utf-8")

body = '''<header class="hero">
  <h1>Metodika a zdroje dat</h1>
  <p>Jak číst data na tomto portálu: odkud pocházejí, jak se zpracovávají, jak často se aktualizují a jaká mají omezení. Když si nejste jistí, co které číslo znamená, odpověď je tady.</p>
  <div class="chips"><span class="chip">nezávislý projekt</span><span class="chip">otevřené zdroje</span><span class="chip">vše ověřitelné v originálech</span></div>
</header>

<section>
  <div class="sec-h"><h2>O portálu</h2></div>
  <div class="panel">
    <p>„Jak žijí Střelice" je <b>nezávislý občanský projekt</b> — není to oficiální web obce Střelice. Všechna data pocházejí z veřejných zdrojů (státní pokladna, ČSÚ, úřední dokumenty obce) a u každé sekce je uveden zdroj i odkaz na originál. Portál data nijak neupravuje ani nehodnotí — jen je skládá dohromady a vizualizuje, aby byla srozumitelná bez účetního vzdělání.</p>
    <p class="note">Našli jste chybu nebo nesoulad? Napište — kontakt najdete na <a href="https://www.strelicnik.cz" target="_blank" rel="noopener" style="color:var(--accent)">strelicnik.cz</a>. Rozhoduje vždy originální dokument, ne tento portál.</p>
  </div>
</section>

<section>
  <div class="sec-h"><h2>Aktualizace dat</h2></div>
  <div class="panel">
    <p>Datum poslední aktualizace je v patičce každé stránky. Jednotlivé sekce se obnovují různým tempem podle toho, kdy jejich zdroj zveřejní nová data:</p>
    <table class="mtab"><tbody>
      <tr><td><b>Rozpočet, Investice, Srovnání</b></td><td>ročně — MONITOR zveřejňuje roční výkazy zpravidla v&nbsp;březnu–dubnu následujícího roku</td></tr>
      <tr><td><b>Zápisy rady, Zastupitelstvo</b></td><td>průběžně — automatická kontrola nových zápisů na webu obce několikrát denně</td></tr>
      <tr><td><b>Dotace spolkům</b></td><td>průběžně — po zveřejnění veřejnoprávních smluv obcí</td></tr>
      <tr><td><b>Školství</b></td><td>ročně — po zveřejnění výročních zpráv škol a dat ČSÚ</td></tr>
    </tbody></table>
  </div>
</section>

<section>
  <div class="sec-h"><h2>Rozpočet</h2><span class="hint">sekce Rozpočet a Srovnání</span></div>
  <div class="panel">
    <p><b>Zdroj:</b> <a href="https://monitor.statnipokladna.gov.cz" target="_blank" rel="noopener" style="color:var(--accent)">MONITOR Státní pokladny</a> (Ministerstvo financí), výkaz <b>FIN 2-12 M</b> — plnění rozpočtu územních samosprávných celků, detail FINM201 v granularitě paragraf&nbsp;×&nbsp;položka. Roční stav k&nbsp;31.&nbsp;12., roky 2013–2025, IČO obce 00282618.</p>
    <p><b>Tři varianty čísel</b>, které v grafech přepínáte:</p>
    <table class="mtab"><tbody>
      <tr><td><b>Schválený rozpočet</b></td><td>plán, který zastupitelstvo schválilo na začátku roku</td></tr>
      <tr><td><b>Upravený rozpočet</b></td><td>plán po rozpočtových opatřeních v průběhu roku (přesuny mezi kapitolami, zapojení dotací a rezerv)</td></tr>
      <tr><td><b>Skutečnost</b></td><td>co se opravdu přijalo a utratilo — pokud není uvedeno jinak, grafy ukazují skutečnost</td></tr>
    </tbody></table>
    <p><b>Třídění:</b> příjmy podle tříd (daňové, nedaňové, kapitálové, transfery), výdaje podle odvětví (paragrafy — „na co") i druhu (položky — „za co"). „%&nbsp;plnění" = skutečnost ÷ upravený rozpočet.</p>
    <p class="note">Přepočty na obyvatele používají počet obyvatel obce dle ČSÚ. Hodnoty jsou v běžných cenách (bez očištění o inflaci).</p>
  </div>
</section>

<section>
  <div class="sec-h"><h2>Srovnání s okolními obcemi</h2></div>
  <div class="panel">
    <p>Finanční data všech obcí pocházejí ze stejného zdroje (MONITOR, FIN 2-12 M) a stejného výpočtu jako data Střelic — čísla jsou tedy plně srovnatelná. Počty obyvatel pro přepočet na hlavu jsou z ČSÚ. Vybrány jsou sousední a blízké obce okresu Brno-venkov; menší obec může mít přepočet na obyvatele „rozkmitaný" jednou velkou investicí — proto grafy ukazují i víceleté průměry.</p>
    <p><b>Ukazatele finančního zdraví</b> vycházejí z metodiky monitoringu MF ČR (tzv. fiskální pravidlo): dlouhodobě záporné saldo, vysoký dluh vůči průměru příjmů (limit 60&nbsp;%) nebo nízká likvidita signalizují riziko. Podrobná metodika: <a href="https://monitor.statnipokladna.gov.cz/metodika" target="_blank" rel="noopener" style="color:var(--accent)">monitor.statnipokladna.gov.cz/metodika</a>.</p>
  </div>
</section>

<section>
  <div class="sec-h"><h2>Investice</h2></div>
  <div class="panel">
    <p><b>Kapitálové výdaje</b> (grafy) jsou z výkazu FIN 2-12 M — jde o výdaje na pořízení a zhodnocení majetku (stavby, pozemky, projekty), na rozdíl od běžných provozních výdajů.</p>
    <p><b>Konkrétní akce</b> (tabulka a mapa) jsou automaticky vytažené z textů usnesení rady a zastupitelstva: bereme body s uvedenou částkou od 100&nbsp;tis.&nbsp;Kč v tématech stavby, doprava a pozemky. Z toho plynou omezení:</p>
    <table class="mtab"><tbody>
      <tr><td><b>Částka je orientační</b></td><td>je z textu usnesení (cena smlouvy o dílo, kupní cena…), ne z účetnictví — skutečně proplacená částka se může lišit o dodatky a vícepráce</td></tr>
      <tr><td><b>Deduplikace</b></td><td>tatáž stavba prochází radou i zastupitelstvem; záznamy se stejnou částkou v okně 90 dnů nebo se stejnou parcelou slučujeme do jednoho</td></tr>
      <tr><td><b>Úplnost</b></td><td>akce bez částky v usnesení (nebo pod prahem) v tabulce nejsou — souhrnné roční investice v grafu ale úplné jsou</td></tr>
    </tbody></table>
  </div>
</section>

<section>
  <div class="sec-h"><h2>Dotace spolkům</h2></div>
  <div class="panel">
    <p><b>Zdroj:</b> veřejnoprávní smlouvy o poskytnutí dotace zveřejněné obcí na <a href="https://www.streliceubrna.cz" target="_blank" rel="noopener" style="color:var(--accent)">streliceubrna.cz</a> (roky 2022–2026). Sekce zachycuje <b>jen dotace poskytnuté přes veřejnoprávní smlouvy</b> — tedy hlavně příspěvky spolkům a organizacím. Neobsahuje drobné dary pod limitem povinného zveřejnění ani transfery příspěvkovým organizacím obce (škola, školka) — ty jsou v sekci Rozpočet jako transfery. Účel dotace je zkrácený výtah ze smlouvy.</p>
  </div>
</section>

<section>
  <div class="sec-h"><h2>Školství</h2></div>
  <div class="panel">
    <p><b>Zdroje:</b> demografie obce z ČSÚ, počty žáků a tříd z výročních zpráv ZŠ a MŠ Střelice a ZUŠ, kapacity z rejstříku škol MŠMT. <b>Kapacita</b> znamená maximální počet žáků zapsaný v rejstříku — ne aktuální prostorové možnosti. Údaj „žáci podle obce bydliště" je z výroční zprávy školy za daný školní rok.</p>
  </div>
</section>

<section>
  <div class="sec-h"><h2>Rada obce a Zastupitelstvo</h2></div>
  <div class="panel">
    <p><b>Zdroj:</b> oficiální zápisy (PDF) z webu obce. Texty usnesení se z PDF vytahují automaticky, proto se mohou ojediněle objevit drobné chyby převodu. U každého usnesení je odkaz na originální PDF — to je vždy rozhodující verze. Zápisy anonymizuje obec (GDPR) ještě před zveřejněním.</p>
    <table class="mtab"><tbody>
      <tr><td><b>Témata</b></td><td>přiřazují se automaticky podle klíčových slov v textu — orientační pomůcka pro filtrování, ne úřední kategorizace</td></tr>
      <tr><td><b>Částky</b></td><td>vytažené z textu usnesení, orientační (viz Investice)</td></tr>
      <tr><td><b>Parcely 📍</b></td><td>čísla parcel v k.ú. Střelice u Brna jsou proklikávací do katastrální mapy (ikatastr.cz)</td></tr>
      <tr><td><b>Video ▶</b></td><td>u zasedání zastupitelstva se záznamem vede odkaz na přesný čas projednávání bodu na YouTube</td></tr>
    </tbody></table>
  </div>
</section>

<section>
  <div class="sec-h"><h2>Stažení dat</h2></div>
  <div class="panel">
    <p>U hlavních tabulek najdete tlačítko <span class="dlbtn" style="cursor:default">⬇ Stáhnout CSV</span> — stáhne právě zobrazená data (oddělovač středník, kódování UTF-8, otevře se přímo v Excelu). Surová zdrojová data jsou k dispozici v původních zdrojích: <a href="https://monitor.statnipokladna.gov.cz/datovy-katalog/open-data" target="_blank" rel="noopener" style="color:var(--accent)">MONITOR open data</a>, <a href="https://data.csu.gov.cz" target="_blank" rel="noopener" style="color:var(--accent)">ČSÚ</a>, <a href="https://www.streliceubrna.cz" target="_blank" rel="noopener" style="color:var(--accent)">web obce</a>.</p>
  </div>
</section>'''

body += '<style>.mtab th,.mtab td{text-align:left;white-space:normal}.mtab td:first-child{width:32%}</style>'
html = pc.page("Metodika", "Metodika a zdroje dat — Jak žijí Střelice", body)
open("metodika.html", "w", encoding="utf-8").write(html)
print("HOTOVO: metodika.html")
