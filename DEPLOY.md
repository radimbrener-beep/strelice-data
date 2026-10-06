# Nasazení portálu „Jak se máme, Střelice?"

## Domény (od 10/2026)
| adresa | složka na Wedosu | poznámka |
|---|---|---|
| **jaksemame.cz** | `/www/domains/jaksemame.cz/` | rozcestník obcí (`build_jaksemame.py`) |
| **strelice.jaksemame.cz** | `/www/subdom/strelice/` | hlavní adresa Střelic (canonical) |
| **ostopovice.jaksemame.cz** | `/www/subdom/ostopovice/` | repo ostopovice-data |
| jakzijistrelice.cz | `/www/domains/jakzijistrelice.cz/` | stará adresa → 301 na https://strelice.jaksemame.cz (`redirect/jakzijistrelice/.htaccess`) |

Subdomény na Wedosu sdílí složku `/www/subdom/<název>/` napříč doménami hostingu —
proto `ostopovice.jaksemame.cz` i `ostopovice.jakzijistrelice.cz` jedou ze stejné složky.

Web je sada **statických HTML stránek** (vše inlinované — CSS, Chart.js i data).
Nasazení běží přes **GitHub Actions → FTP na Wedos**: po každém `git push` do větve
`main` se portálové HTML nahrají na hosting.

## Jak to funguje
1. Lokálně se z dat vygenerují HTML (`python build_*.py`).
2. Změny se commitnou a pushnou do GitHubu (větev `main`).
3. GitHub Action [`.github/workflows/deploy.yml`](.github/workflows/deploy.yml) vezme
   všechny `*.html` z kořene (kromě `_*.html`), písma a favikony a nahraje je přes FTP
   do složek podle tabulky domén výše (portál, rozcestník, přesměrování staré domény).

---

## Jednorázové nastavení (musíš udělat ty)

### 1) Wedos — domény, subdomény a FTP
- Doména `jaksemame.cz` je na hostingu jako alias; vlastní web aliasu = složka
  `/www/domains/jaksemame.cz/` (stačí, aby existovala).
- Subdomény (`strelice`, `ostopovice`, …) se zakládají v administraci hostingu a mapují
  se do `/www/subdom/<název>/`. Nová obec = nová subdoména + nový deploy krok.
- HTTPS: administrace hostingu → **HTTPS** → *nastavení domén certifikátu* → přidat doménu
  a subdomény → **Aplikovat změny** (šíření na server trvá až desítky minut).
- Zjisti **FTP přístup**: server (např. `wfilesXX.wedos.net`), **login** a **heslo**.
  Cílové složky jsou přímo v `deploy.yml` (`server-dir`, končí lomítkem).

### 2) GitHub — repozitář a secrets
- Vytvoř repozitář (může být **Private**).
- V `Settings → Secrets and variables → Actions → New repository secret` přidej:
  | Secret | Hodnota |
  |---|---|
  | `FTP_SERVER` | FTP server z Wedosu |
  | `FTP_USERNAME` | FTP login |
  | `FTP_PASSWORD` | FTP heslo |

### 3) Push a první deploy
- Po napojení repa stačí pushnout do `main`; Action se spustí sama.
  (Lze i ručně: záložka *Actions* → *Deploy na Wedos* → *Run workflow*.)

---

## Běžná aktualizace (změna obsahu)
```bash
python build_portal.py        # + další build_*.py podle toho, co se měnilo
git add -A
git commit -m "popis změny"
git push                      # → GitHub Action nahraje na web
```

## Pozn.
- Pokud FTPS nepojede, změň v `deploy.yml` `protocol: ftps` na `ftp`.
- Surová data (PDF, ZIP, stažené CSV) nejsou v repu (viz `.gitignore`) — generátory je
  čtou z lokální složky `data/` a z `*_RO/` / `*_ZO/`.
