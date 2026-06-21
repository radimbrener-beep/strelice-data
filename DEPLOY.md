# Nasazení portálu „Jak žijí Střelice" na data.strelicnik.cz

Web je sada **statických HTML stránek** (vše inlinované — CSS, Chart.js i data).
Nasazení běží přes **GitHub Actions → FTP na Wedos**: po každém `git push` do větve
`main` se portálové HTML nahrají na hosting.

## Jak to funguje
1. Lokálně se z dat vygenerují HTML (`python build_*.py`).
2. Změny se commitnou a pushnou do GitHubu (větev `main`).
3. GitHub Action [`.github/workflows/deploy.yml`](.github/workflows/deploy.yml) vezme
   všechny `*.html` z kořene (kromě `_*.html`) a nahraje je přes FTP do docrootu subdomény.

---

## Jednorázové nastavení (musíš udělat ty)

### 1) Wedos — subdoména a FTP
- V administraci Wedos (WAPI/WebAdmin) u hostingu vytvoř **subdoménu `data.strelicnik.cz`**
  a nasměruj její **docroot** do vyhrazené složky (ať tam nic jiného není).
- Zjisti **FTP přístup**: server (např. `wfilesXX.wedos.net` nebo `ftp.strelicnik.cz`),
  **login** a **heslo**. Pozn. cílové složky (server-dir) — typicky cesta k docrootu
  subdomény (musí v secretu končit lomítkem `/`).

### 2) GitHub — repozitář a secrets
- Vytvoř repozitář (může být **Private**).
- V `Settings → Secrets and variables → Actions → New repository secret` přidej:
  | Secret | Hodnota |
  |---|---|
  | `FTP_SERVER` | FTP server z Wedosu |
  | `FTP_USERNAME` | FTP login |
  | `FTP_PASSWORD` | FTP heslo |
  | `FTP_DIR` | docroot subdomény, končí `/` (např. `/` nebo `/data.strelicnik.cz/www/`) |

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
