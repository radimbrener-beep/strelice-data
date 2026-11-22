# AGENTS.md — popis projektu pro AI nástroje

Tento soubor je vstupní bod pro AI asistenty (Claude Code, Codex, Copilot, Cursor…) i pro lidi,
kteří na projektu začínají. Popisuje, co projekt dělá, proč, jak je postavený a na co si dát pozor.
`CLAUDE.md` na tento soubor jen odkazuje.

## Co to je a proč

**„Jak se máme, Střelice?“** je veřejný, nestranný datový portál obce **Střelice** (okres Brno-venkov,
IČO 00282618). Běží na **https://strelice.jaksemame.cz**.

Cíl: aby běžný občan bez znalosti úředních dokumentů rychle zjistil, **jak obec hospodaří a co se
v ní rozhoduje**. Patří sem rozpočet, investice, zakázky, dotace spolkům, usnesení rady
a zastupitelstva, kdo jak hlasoval a co kdo na zasedání řekl. Data se berou jen z veřejných
oficiálních zdrojů a ke každé sekci je uvedený zdroj.

Zásady obsahu:
- **Nestrannost.** Jen fakta ze zdrojů, žádné hodnocení ani přívlastky jako „kontroverzní“ nebo „úspěšný“.
- **Soukromí.** Fyzické osoby (kupující, žadatelé, občané v diskuzi) se nejmenují. Jmenují se firmy
  a zastupitelé při výkonu funkce.
- **Texty na webu** píše jeden autor, proto v první osobě jednotného čísla („přidal jsem“, nikdy „jsme přidali“).
  Veškerý obsah i komentáře v kódu jsou česky.

Projekt patří do rodiny **jaksemame.cz**. Ta má rozcestník obcí na `jaksemame.cz` (zdrojový kód je v tomto repu)
a portál Ostopovic v samostatném repu `ostopovice-data`. Oba portály sdílejí MCP server
a backend upozornění.

## Sekce portálu (stránky)

Každá stránka je **samostatné statické HTML**: CSS, JS (Chart.js, Leaflet) i data jsou vložené přímo
do stránky. Na hostingu neběží žádný backend, výjimkou jsou jen `push/` a `mcp/` v PHP. Každou stránku generuje jeden Python skript:

| stránka | generátor | obsah |
|---|---|---|
| `index.html` (+ `skolstvi.html`) | `build_portal.py` | úvod: rozcestník, „Co je nového“, poutač „Období v číslech“; školství |
| `rozpocet.html` | `build_dashboard.py` | příjmy a výdaje 2013–dosud (MONITOR), drill-down paragraf × položka |
| `srovnani.html` | `build_srovnani.py` (+ `build_srovnani_data.py`) | finanční zdraví a srovnání se sousedními obcemi na obyvatele |
| `investice.html` | `build_investice.py` | kapitálové výdaje, akce na mapě, propojení na usnesení a smlouvy |
| `zakazky.html` | `build_zakazky.py` | komu obec platí (firmy z usnesení) a výběrová řízení z profilu zadavatele |
| `dotace.html` | `build_dotace_page.py` | dotace spolkům (z registru smluv) |
| `demografie.html` | `build_demografie.py` | obyvatelstvo (ČSÚ) |
| `volby.html` | `build_volby.py` | výsledky voleb v obci (volby.cz) |
| `zapisy.html` | `build_zapisy.py` | Rada obce (RO): zápisy, shrnutí, témata, hledání, parcely → katastr |
| `zastupitelstvo.html` | `build_zastupitelstvo.py` | Zastupitelstvo (ZO): usnesení, hlasování, účast, video s časy bodů, přepis diskuze |
| `obdobi.html` | `build_obdobi.py` | bilance volebního období 2022–2026 a aktivita zastupitelů |
| `hledat.html` | `build_hledat.py` | hledání napříč portálem a „Moje ulice“ |
| `ai.html` | `build_ai.py` | „Ptejte se AI“: návod na MCP server |
| `aktualizace.html`, `metodika.html`, `odbery.html`, `404.html` | `build_aktualizace.py`, `build_metodika.py`, `build_odbery.py`, `build_404.py` | provozní stránky |
| `jaksemame/index.html` | `build_jaksemame.py` | rozcestník obcí na jaksemame.cz |

Sdílený vzhled je v **`portal_common.py`**: `page()`, hlavička a navigace (`SECTIONS`, `NAV`),
CSS tokeny, světlý a tmavý režim, barvy a ikony témat, maskot, zvonek upozornění a hash verze `sw.js`.
Značka (logo „Bublina“, barvy) je ve `brand/`, písma ve `fonts/`.

## Zdroje dat

| data | zdroj | kde v repu |
|---|---|---|
| rozpočet (plnění) | MONITOR Státní pokladny, FIN 2-12 M (`FINM201`), paragraf × položka | `data/strelice_finm201_2013_2025.csv`, `data/strelice_fin_2026.csv` (`build_strelice.py`, `build_fin2026.py`) |
| zápisy Rady obce | PDF na streliceubrna.cz | `dataset_RO.json` (+ CSV) |
| usnesení Zastupitelstva | PDF na streliceubrna.cz | `dataset_ZO.json` (+ CSV) |
| videa ZO | YouTube kanál TV Střelice (`@tvstreliceubrna`) | `data/video/map.txt`, `video_casy.json` |
| přepisy diskuze ZO | YouTube titulky vyčištěné jazykovým modelem | `prepisy/<klíč>.json` |
| shrnutí jednání | jazykový model z textu usnesení | `data/shrnuti/zo.json`, `ro.json` |
| dotace spolkům | registr smluv (ne OCR) | `data/dotace_strelice.csv` |
| výběrová řízení | profil zadavatele | `data/profil_zakazky.json` (`scripts/fetch_profil_zakazky.py`) |
| demografie a školství | ČSÚ, výroční zprávy školy | `data/skolstvi/` |
| parcely | ČÚZK INSPIRE WFS (k. ú. 757438) | `data/parcely_geo.json` (`geocode_parcely.py`) |

Pomocné moduly:
- `temata.py`: pravidlová klasifikace usnesení do témat.
- `vydaje.py`: vytažení částky z textu usnesení a opravy chyb OCR.
- `firmy.py`: normalizace názvů firem.
- `zastupitele.py`: složení ZO 2022–2026.
- `zasedani.py`: klíč zasedání, viz níže.

## Klíč zasedání a volební období (důležité)

Čísla ZO i RO se v každém volebním období počítají **znovu od 1**. Jednání se proto nikdy
neidentifikuje samotným `cislo_zasedani`, ale **klíčem** ze `zasedani.py`:
- období **2022–2026** má holé číslo, například `"29"`. Je to kvůli zpětné kompatibilitě starých odkazů
  `?zo=29`, `?ro=104` a id push notifikací.
- další období mají tvar `"<rok začátku>-<číslo>"`, například `"2026-1"`. MCP id je pak `ZO-2026-1`,
  push id `zastupitelstvo-2026-1` a odkaz `?zo=2026-1`.
- období se bere z pole `obdobi` záznamu (zapisuje ho scraper), jinak z data přes `zasedani.ZACATKY`.

Klíč se používá v `data/video/map.txt` (řádky `<klíč> <videoId>`), ve `video_casy.json`,
v `prepisy/<klíč>.json`, v `data/shrnuti/*.json` a v `published.json`. Při přidávání čehokoli
k jednání vždy použij `zasedani.key(m)`.

Bilance období (`obdobi.html`), aktivita zastupitelů (`zastupitele.py`) a poutač na úvodu
jsou zatím **jen za 2022–2026**. Složení zastupitelstva 2026–2030 není v `zastupitele.py` doplněné.

## Automatika (GitHub Actions)

- **`.github/workflows/check_web.yml`** běží 3× denně a spouští `scripts/update_portal.py`. Ten:
  1. najde na webu obce podstránky volebních období (od 2022–2026 dál) a v nich nová PDF ZO a RO;
  2. rozparsuje je přes `scripts/parse_zo.py` a `parse_ro.py`, které musí klasifikovat stejně jako plné
     buildery `_build_zo.py` a `_build_dataset.py`;
  3. přiřadí video z YouTube. Shodovat se musí datum: buď je v názvu videa, nebo je video nahrané
     do 60 dnů po zasedání. Pak stáhne titulky a `build_video_casy.py` spočítá časy bodů;
  4. zkontroluje profil zadavatele a přegeneruje dotčené stránky;
  5. commitne změny (`Auto: …`) a spustí nasazení.
- **`.github/workflows/deploy.yml`** se spouští po pushi do `main`. Sestaví `push/feed.json` (`build_push.py`)
  a SQLite pro MCP (`build_mcp.py`), nahraje HTML a soubory přes FTP na Wedos a rozešle push upozornění.
  Přístupové údaje jsou v GitHub secrets (`FTP_*`, `PUSH_TOKEN`), nikdy ne v repu.

**Ručně (jazykovým modelem) se musí doplnit:**
- **shrnutí** nového jednání do `data/shrnuti/zo.json` / `ro.json`, podle `data/shrnuti/_SPEC.md`;
- **přepis diskuze** nového ZO. Postup: `scripts/build_prepisy_raw.py` → vyčistit podle `prepisy/_SPEC.md`
  → `prepisy/<klíč>.json` → `build_zastupitelstvo.py`. Pole `index` je pořadí usnesení (od 0)
  a kopíruje se 1:1 z raw. Vzor je `prepisy/_styl_vzor.json`.

## MCP server a upozornění

- **`jaksemame/mcp/`** obsahuje MCP server v PHP 8.0 (Streamable HTTP, bez stavu) na `https://jaksemame.cz/mcp/`
  (lomítko na konci je nutné). Data `mcp/<obec>.sqlite` staví `build_mcp.py`. Server má 9 nástrojů
  (hledat, jednani, diskuze, rozpocet, investice, zakazky, vyberova_rizeni, dotace, obce).
  Testy: `php mcp-tests/run.php`. Potřebují lokální `jaksemame/mcp/config.local.php` (je v .gitignore).
- **`push/`** obsahuje Web Push upozornění (PHP + SQLite na hostingu). Testy: `php push-tests/run.php`.
  Novinku portálu ohlásíš záznamem v `data/push_novinky.json`.

## Jak pracovat lokálně

```bash
pip install requests beautifulsoup4 pdfplumber yt-dlp Pillow
python build_zastupitelstvo.py          # přegenerovat jednu stránku
python build_portal.py                  # úvod pouštěj až nakonec (čte ostatní stránky)
python scripts/update_portal.py --dry-run   # co nového je na webu obce, bez zápisu
python -m http.server 8765              # náhled na http://localhost:8765/
php mcp-tests/run.php && php push-tests/run.php
```

Na Windows nastav `PYTHONIOENCODING=utf-8`, jinak výpisy s češtinou spadnou.

## Pravidla a úskalí

- **Nejdřív ukázat, pak nasadit.** Změnu na webu ukaž lokálně. Push do `main` znamená okamžité nasazení
  na živý web, takže se dělá až po schválení vlastníkem.
- **Před pushem vždy `git fetch`.** CI mezitím samo commituje nová jednání. Konflikty ve vygenerovaných HTML
  neřeš ručně, přegeneruj je skripty.
- Vygenerovaná HTML a datasety (`dataset_*.json`) **jsou verzované záměrně**. Surová PDF, ZIPy a titulky
  (`data/video/caps/`) verzované nejsou.
- Data se do stránek vkládají jako JSON. Opravuj generátor, ne vygenerované HTML.
- Úvodní panel „Co je nového“ bere u každé sekce nejnovější jednání podle data jednání.
  Datum „přidáno“ pochází z `published.json`.
- Hosting Wedos: PHP 8.0 (bez funkcí z 8.1+), CDN cachuje GET odpovědi 5 minut a neexistující adresy vrací 500.
- Některá PDF mají rozbité fonty (například ZO 27). Opravy jsou v `vydaje.fix_ocr_digits` a v `_build_zo.py`.

Podrobnosti k nasazení, doménám a secrets jsou v [DEPLOY.md](DEPLOY.md), k MCP v [jaksemame/mcp/README.md](jaksemame/mcp/README.md)
a ke značce v [brand/README.md](brand/README.md).
