#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Automatická aktualizace portálu strelice.jaksemame.cz.

Postup:
  1. Prohledá web obce – najde nové ZO usnesení a RO zápisy.
  2. Stáhne PDF, naparsuje, přidá do datasetu.
  3. Pro nové ZO: hledá odpovídající video na YouTube kanálu @tvstreliceubrna,
     stáhne titulky a zarovná kapitoly.
  4. Přegeneruje dotčené HTML stránky.
  5. Commitne a pushne → deploy se spustí automaticky.
  6. Vypíše souhrn pro GitHub Issue.

Spuštění:
  python scripts/update_portal.py [--dry-run]
"""
import sys, os, json, re, subprocess, argparse
from datetime import date
from pathlib import Path
from urllib.parse import unquote
import requests
from bs4 import BeautifulSoup


def _extract_cislo(title, href):
    """Číslo zasedání z názvu/URL. Dekóduje %xx a snese 'č. 100', 'č._100',
    'č.29' i 'N. zasedání'. Ankot na 'č' (RO č./ZO č.), pak na 'N. zasedání'."""
    s = (title or '') + ' ' + unquote(href or '')
    for pat in (r'[čČ]\.?\s*[_\xa0]*\s*(\d{1,3})(?!\d)',
                r'(\d{1,3})\.\s*zasedání'):
        m = re.search(pat, s, re.I)
        if m:
            return int(m.group(1))
    return None

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
import zasedani as zs

MIN_OBDOBI = zs.LEGACY

# Nadřazené stránky: obec pro každé volební období zakládá podstránku s příponou
# „-2022-2026“, „-2026-2030“ … Scraper je najde sám a projde všechna období od
# MIN_OBDOBI (starší portál nemá a nenačítá). Staré období se prochází dál,
# ať se nic neztratí, když obec pozdní zápis přidá ještě tam.
ZO_PARENT_URL = "https://www.streliceubrna.cz/obec/samosprava/zastupitelstvo-obce-strelice/usneseni"
RO_PARENT_URL = "https://www.streliceubrna.cz/obec/samosprava/rada-obce-strelice/zapisy-rady-obce-strelice"
# záloha, kdyby nadřazená stránka nešla načíst
ZO_FALLBACK = {"2022-2026": ZO_PARENT_URL + "/usneseni-ze-zasedani-zastupitelstva-obce-strelice-2022-2026"}
RO_FALLBACK = {"2022-2026": RO_PARENT_URL + "/zapisy-rady-obce-strelice-2022-2026"}
YT_CHANNEL = "https://www.youtube.com/@tvstreliceubrna/videos"
BASE_OBEC = "https://www.streliceubrna.cz"

HEADERS = {'User-Agent': 'Mozilla/5.0 (compatible; StrelicePortalBot/1.0)'}


# ──────────────────────────────────────────────
# Pomocné funkce
# ──────────────────────────────────────────────

def fetch(url, timeout=30):
    r = requests.get(url, headers=HEADERS, timeout=timeout)
    r.raise_for_status()
    return r

def soup(url):
    return BeautifulSoup(fetch(url).text, 'html.parser')

def run(cmd, cwd=ROOT, check=True, capture=False):
    """Spustí shell příkaz."""
    kwargs = dict(cwd=cwd, check=check)
    if capture:
        kwargs['capture_output'] = True
        kwargs['text'] = True
        kwargs['encoding'] = 'utf-8'
    print(f"  $ {' '.join(str(c) for c in cmd)}", flush=True)
    return subprocess.run(cmd, **kwargs)


# ──────────────────────────────────────────────
# Detekce nových dokumentů
# ──────────────────────────────────────────────

def period_pages(parent_url, fallback):
    """{obdobi: url} podstránek volebních období odkazovaných z nadřazené stránky.
    Bere jen odkazy pod `parent_url` končící „-RRRR-RRRR“ (menu webu odkazuje i jinam)."""
    path = parent_url.replace(BASE_OBEC, '')
    pages = {}
    try:
        s = soup(parent_url)
        for a in s.find_all('a', href=True):
            rel = a['href'].split('?')[0].split('#')[0].rstrip('/').replace(BASE_OBEC, '')
            m = re.search(r'-(\d{4})-(\d{4})$', rel)
            if not rel.startswith(path + '/') or not m:
                continue
            ob = f"{m.group(1)}-{m.group(2)}"
            if ob >= MIN_OBDOBI:
                pages[ob] = BASE_OBEC + rel
    except Exception as e:
        print(f"WARN: nelze načíst {parent_url}: {e}")
    for ob, url in fallback.items():
        pages.setdefault(ob, url)
    return dict(sorted(pages.items()))


def scrape_links(parent_url, fallback, doc_re):
    """[(klíč, číslo, období, title, pdf_url)] ze všech podstránek období."""
    results, seen = [], set()
    for ob, page in period_pages(parent_url, fallback).items():
        try:
            s = soup(page)
        except Exception as e:
            # nové období může mít podstránku až s prvním zápisem (do té doby 404)
            print(f"WARN: nelze načíst stránku období {ob}: {e}")
            continue
        for a in s.find_all('a', href=True):
            href = a['href']
            title = a.get_text(strip=True)
            if '.pdf' not in href.lower():
                continue
            if not re.search(doc_re, href + title, re.I):
                continue
            url = href if href.startswith('http') else BASE_OBEC + href
            cislo = _extract_cislo(title, href)
            k = zs.key_for(cislo, ob) if cislo else None
            if k and k not in seen:
                seen.add(k)
                results.append((k, cislo, ob, title, url))
    return results


def scrape_zo_links():
    """ZO usnesení na webu obce (všechna období od MIN_OBDOBI)."""
    return scrape_links(ZO_PARENT_URL, ZO_FALLBACK, r'usnesení|usnesen')


def scrape_ro_links():
    """RO zápisy na webu obce (všechna období od MIN_OBDOBI)."""
    return scrape_links(RO_PARENT_URL, RO_FALLBACK, r'zápis|zapis|RO')


def known_zo():
    data = json.loads((ROOT / 'dataset_ZO.json').read_text(encoding='utf-8'))
    return {zs.key(m) for m in data}

def known_ro():
    data = json.loads((ROOT / 'dataset_RO.json').read_text(encoding='utf-8'))
    return {zs.key(m) for m in data}


# ──────────────────────────────────────────────
# YouTube – hledání videa pro ZO zasedání
# ──────────────────────────────────────────────

def ytdlp(args):
    """Spustí yt-dlp (binárku, jinak modul — Windows Store Python ji nemá v PATH)."""
    try:
        return run(['yt-dlp'] + args, capture=True, check=False)
    except FileNotFoundError:
        return run([sys.executable, '-m', 'yt_dlp'] + args, capture=True, check=False)


_UPLOAD = {}


def video_upload_date(vid):
    """Datum nahrání videa „RRRRMMDD“ (seznam kanálu přes --flat-playlist ho nedává → dotaz na video)."""
    if vid not in _UPLOAD:
        try:
            r = ytdlp(['--skip-download', '--no-warnings', '--print', '%(upload_date)s',
                       f'https://www.youtube.com/watch?v={vid}'])
            out = (r.stdout or '').strip().splitlines()
            _UPLOAD[vid] = out[-1] if out and re.fullmatch(r'\d{8}', out[-1]) else ''
        except Exception as e:
            print(f"  WARN: datum nahrání {vid}: {e}")
            _UPLOAD[vid] = ''
    return _UPLOAD[vid]


def download_caps(vid):
    """Stáhne české automatické titulky videa do data/video/caps/ (z nich build_video_casy.py
    počítá časy jednotlivých bodů). Nepovinné: když YouTube titulky nedá, zůstane jen video."""
    caps = ROOT / 'data' / 'video' / 'caps'
    dest = caps / f'cap_{vid}.cs-orig.vtt'
    if dest.exists() and dest.stat().st_size > 500:
        return True
    caps.mkdir(parents=True, exist_ok=True)
    try:
        ytdlp(['--write-auto-subs', '--sub-langs', 'cs-orig', '--sub-format', 'vtt', '--skip-download',
               '--no-warnings', '-o', str(caps / f'cap_{vid}.%(ext)s'), f'https://www.youtube.com/watch?v={vid}'])
    except Exception as e:
        print(f"  WARN: titulky {vid}: {e}")
    ok = dest.exists() and dest.stat().st_size > 500
    print(f"  Titulky {vid}: {'staženy' if ok else 'nedostupné (časy bodů se nespočítají)'}")
    return ok


def fetch_yt_channel_videos():
    """
    Stáhne seznam videí z kanálu @tvstreliceubrna (jednou, výsledek cachujeme v paměti).
    Vrátí list [(vid_id, title, upload_date)] nebo [] při chybě.
    """
    print(f"  Stahuji seznam videí z YouTube kanálu...")
    args = ['--flat-playlist',
            '--print', '%(id)s\t%(title)s\t%(upload_date)s',
            '--playlist-end', '50',
            '--no-warnings',
            YT_CHANNEL]
    try:
        result = ytdlp(args)
        lines = (result.stdout or '').strip().splitlines()
    except FileNotFoundError:
        print("  WARN: yt-dlp není nainstalováno")
        return []
    except Exception as e:
        print(f"  WARN: yt-dlp selhalo: {e}")
        return []

    videos = []
    for line in lines:
        parts = line.split('\t', 2)
        if len(parts) >= 2:
            videos.append((parts[0], parts[1], parts[2] if len(parts) > 2 else ''))
    print(f"  Nalezeno {len(videos)} videí na kanálu.")
    return videos


def match_video_for_zo(cislo, datum_iso, videos, label=None):
    """Vybere nejlepší video ze seznamu `videos` pro ZO zasedání číslo `cislo`
    (`label` = klíč zasedání do výpisu)."""
    if not datum_iso:
        return None
    date_nodash = datum_iso.replace('-', '')
    day, month, year = datum_iso[8:10], datum_iso[5:7], datum_iso[:4]
    date_cz = f"{int(day)}.{int(month)}.{year}"

    # Datum musí sedět vždy: číslo zasedání se v každém volebním období počítá znovu od 1,
    # takže „1. ustavující zasedání“ z 11/2026 by jinak padlo k ZO 1 z 10/2022 (stalo se 6. 11. 2026).
    # Ověří ho datum v názvu videa, nebo — u videa zastupitelstva — nahrání do 60 dnů po zasedání.
    # Názvy videí obce datum obvykle nemají a --flat-playlist datum nahrání nedává („NA“),
    # proto se u takového kandidáta zjistí dotazem na video (stalo se u ustavujícího 5. 11. 2026).
    zas = date.fromisoformat(datum_iso)
    candidates = []
    for vid_id, title, upload in videos:
        if date_cz not in title.replace(' ', ''):
            # bez data v názvu jen video zastupitelstva s číslem zasedání v názvu
            if not (re.search(r'zastupitel', title, re.I) and re.search(rf'(?<!\d){cislo}\.', title)):
                continue
            if not re.fullmatch(r'\d{8}', upload or ''):
                upload = video_upload_date(vid_id)
            try:
                up_ok = 0 <= (date(int(upload[:4]), int(upload[4:6]), int(upload[6:8])) - zas).days <= 60
            except (ValueError, IndexError):
                up_ok = False
            if not up_ok:
                continue
        score = 4
        if re.search(r'\bzastupitelstv', title, re.I):
            score += 2
        if re.search(rf'\b{cislo}\b', title):
            score += 3
        candidates.append((score, vid_id, title))

    if not candidates:
        return None
    candidates.sort(reverse=True)
    best_score, best_id, best_title = candidates[0]
    print(f"  ZO {label or cislo}: video {best_id} – {best_title!r} (skóre {best_score})")
    return best_id


# ──────────────────────────────────────────────
# Přidání záznamu do datasetu
# ──────────────────────────────────────────────

def append_to_dataset(path, new_entry):
    data = json.loads(path.read_text(encoding='utf-8'))
    data.append(new_entry)
    data.sort(key=zs.sort_key)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding='utf-8')


def add_video_to_map(key, video_id):
    """Řádek „<klíč zasedání> <videoId>“ (klíč „29“ / „2026-1“, viz zasedani.py)."""
    map_path = ROOT / 'data' / 'video' / 'map.txt'
    lines = [l for l in map_path.read_text(encoding='utf-8').splitlines() if l.split()]
    # zkontroluj zda už existuje
    if any(line.split()[0] == str(key) for line in lines):
        return
    lines.append(f"{key} {video_id}")
    lines.sort(key=lambda l: zs.key_sort(l.split()[0]), reverse=True)
    map_path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(f"  map.txt: přidáno ZO {key} → {video_id}")


# ──────────────────────────────────────────────
# Kontrola chybějících videí pro existující ZO
# ──────────────────────────────────────────────

def mapped_videos():
    """Vrátí set klíčů ZO zasedání („29“, „2026-1“), která už mají video v map.txt."""
    map_path = ROOT / 'data' / 'video' / 'map.txt'
    if not map_path.exists():
        return set()
    mapped = set()
    for line in map_path.read_text(encoding='utf-8').splitlines():
        parts = line.strip().split()
        if parts:
            mapped.add(parts[0])
    return mapped

def check_missing_videos(dry_run=False, videos=None):
    """
    Pro ZO zasedání v datasetu, která ještě nemají video v map.txt,
    zkusí najít video na YouTube kanálu.
    `videos` – předvyplněný seznam z fetch_yt_channel_videos() (sdílíme fetch z main).
    Vrátí seznam (klíč zasedání, video_id) nově nalezených videí.
    """
    print("\n[VIDEO] Kontrola chybějících videí pro ZO...")
    zo_data = json.loads((ROOT / 'dataset_ZO.json').read_text(encoding='utf-8'))
    mapped = mapped_videos()
    without_video = [m for m in zo_data if zs.key(m) not in mapped]

    if not without_video:
        print("  Všechna ZO zasedání mají video.")
        return []

    print(f"  ZO bez videa: {[zs.key(m) for m in without_video]}")
    if videos is None:
        videos = fetch_yt_channel_videos()
    found = []
    for m in without_video:
        k = zs.key(m)
        vid = match_video_for_zo(m['cislo_zasedani'], m.get('datum', ''), videos, label=k)
        if vid and not dry_run:
            add_video_to_map(k, vid)
            download_caps(vid)
        if vid:
            found.append((k, vid))

    return found


# ──────────────────────────────────────────────
# Vypsané zakázky (profil zadavatele)
# ──────────────────────────────────────────────

def check_profil_zakazky():
    """Stáhne profil zadavatele (scripts/fetch_profil_zakazky.py). Vrací (nové zakázky,
    změnilo se něco). Výpadek profilu nevadí — zůstanou předchozí data."""
    path = ROOT / 'data' / 'profil_zakazky.json'
    before = path.read_text(encoding='utf-8') if path.exists() else ''
    old_ids = {z['id'] for z in json.loads(before)['zakazky']} if before else set()
    r = run([sys.executable, 'scripts/fetch_profil_zakazky.py'], check=False)
    if r.returncode:
        print("  Profil zadavatele nedostupný — ponechávám předchozí data.")
        return [], False
    after = path.read_text(encoding='utf-8')
    new = [z for z in json.loads(after)['zakazky'] if z['id'] not in old_ids]
    return new, after != before


# ──────────────────────────────────────────────
# Rebuild HTML stránek
# ──────────────────────────────────────────────

def rebuild(scripts):
    for s in scripts:
        print(f"  Rebuild: {s}")
        run(['python', s], cwd=ROOT)


# ──────────────────────────────────────────────
# Git commit
# ──────────────────────────────────────────────

def git_commit(message, files=None):
    """Připraví commit — push řeší workflow (aby mělo správné credentials)."""
    if files:
        run(['git', 'add'] + [str(f) for f in files])
    else:
        run(['git', 'add', '-A'])
    r = run(['git', 'diff', '--cached', '--quiet'], check=False)
    if r.returncode == 0:
        print("  Žádné změny k commitu.")
        return False
    run(['git', 'commit', '-m', message])
    # push záměrně vynecháme — provede ho krok v check_web.yml
    return True


# ──────────────────────────────────────────────
# Hlavní logika
# ──────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true',
                        help='Pouze detekuj, nic nepiš ani nepushuj')
    args = parser.parse_args()

    print("=== Kontrola nových dokumentů ===")

    new_zo = []
    new_ro = []
    summary_lines = []
    _yt_videos = None   # lazy: stáhneme kanál jen pokud budeme potřebovat

    def yt_videos():
        nonlocal _yt_videos
        if _yt_videos is None:
            _yt_videos = fetch_yt_channel_videos()
        return _yt_videos

    # ── ZO ──────────────────────────────────────
    print("\n[ZO] Kontrola usnesení...")
    already_zo = known_zo()
    for key, cislo, obd, title, url in scrape_zo_links():
        if key in already_zo:
            continue
        print(f"  Nové ZO: {key} – {title}")
        if args.dry_run:
            summary_lines.append(f"- ZO {key}: {title} ({url})")
            continue

        # parsuj
        try:
            from scripts.parse_zo import parse as parse_zo
        except ImportError:
            sys.path.insert(0, str(ROOT / 'scripts'))
            from parse_zo import parse as parse_zo

        print(f"  Parsuju PDF: {url}")
        try:
            entry = parse_zo(url, cislo_hint=cislo)
        except Exception as e:
            print(f"  CHYBA parsování ZO {key}: {e}")
            summary_lines.append(f"- ZO {key}: chyba parsování — {e}")
            continue
        entry['obdobi'] = obd
        key = zs.key(entry)        # číslo z PDF má přednost před číslem z odkazu
        if key in already_zo:
            continue
        already_zo.add(key)

        # video
        video_id = match_video_for_zo(entry['cislo_zasedani'], entry.get('datum', ''), yt_videos(), label=key)
        if video_id:
            add_video_to_map(key, video_id)
            download_caps(video_id)

        # dataset
        append_to_dataset(ROOT / 'dataset_ZO.json', entry)
        new_zo.append((key, title, url, video_id))
        summary_lines.append(
            f"- **ZO {key}** ({entry.get('datum_text', '')}): "
            f"{entry.get('pocet_bodu', 0)} usnesení"
            + (f", video {video_id}" if video_id else ", video nenalezeno")
        )

    # ── RO ──────────────────────────────────────
    print("\n[RO] Kontrola zápisů...")
    already_ro = known_ro()
    for key, cislo, obd, title, url in scrape_ro_links():
        if key in already_ro:
            continue
        print(f"  Nové RO: {key} – {title}")
        if args.dry_run:
            summary_lines.append(f"- RO {key}: {title} ({url})")
            continue

        try:
            from scripts.parse_ro import parse as parse_ro
        except ImportError:
            sys.path.insert(0, str(ROOT / 'scripts'))
            from parse_ro import parse as parse_ro

        print(f"  Parsuju PDF: {url}")
        try:
            entry = parse_ro(url, cislo_hint=cislo)
        except Exception as e:
            print(f"  CHYBA parsování RO {key}: {e}")
            summary_lines.append(f"- RO {key}: chyba parsování — {e}")
            continue
        entry['obdobi'] = obd
        key = zs.key(entry)
        if key in already_ro:
            continue
        already_ro.add(key)

        append_to_dataset(ROOT / 'dataset_RO.json', entry)
        new_ro.append((key, title, url))
        summary_lines.append(
            f"- **RO {key}** ({entry.get('datum_text', '')}): "
            f"{entry.get('pocet_bodu', 0)} usnesení"
        )

    # ── Chybějící videa pro existující ZO ────────
    # Předáme sdílený seznam videí — kanál se stáhne max. jednou za běh.
    new_videos = check_missing_videos(dry_run=args.dry_run, videos=yt_videos() if not args.dry_run else None)
    for key, vid in new_videos:
        summary_lines.append(f"- **Video ZO {key}**: přidáno {vid} → timestamps přegenerovány")

    # ── Vypsané zakázky z profilu zadavatele ─────
    new_pz, pz_changed = ([], False) if args.dry_run else check_profil_zakazky()
    for z in new_pz:
        summary_lines.append(f"- **Vypsaná zakázka** ({z['datum']}): {z['nazev']} · [profil]({z['url']})")

    if not new_zo and not new_ro and not new_videos and not pz_changed:
        print("\nŽádné nové dokumenty, videa ani zakázky.")
        Path(ROOT / '.no_update').write_text('ok')
        return

    if args.dry_run:
        print("\n=== DRY RUN – souhrn nálezů ===")
        for l in summary_lines:
            print(" ", l)
        return

    # ── Rebuild ──────────────────────────────────
    print("\n[BUILD] Přegenerovávám HTML...")
    to_rebuild = []   # build_portal.py se přidává až na konec (čte vygenerované stránky)
    if new_zo or new_ro:
        # nové parcely v usneseních -> souřadnice pro prokliky do katastru
        # (inkrementální, selhání jednotlivých dotazů ČÚZK skript toleruje)
        to_rebuild.insert(0, 'geocode_parcely.py')
    if new_zo or new_videos:
        to_rebuild.append('build_video_casy.py')
        to_rebuild.append('build_zastupitelstvo.py')
        to_rebuild.append('build_investice.py')
    if new_ro:
        to_rebuild.append('build_zapisy.py')
        to_rebuild.append('build_investice.py')
    if new_zo or new_ro:
        to_rebuild.append('build_zakazky.py')   # nové zakázky firem z usnesení
        # čtou data z investice.html / zakazky.html → až po nich
        to_rebuild.append('build_hledat.py')    # hledání + Moje ulice
        to_rebuild.append('build_obdobi.py')    # bilance období + aktivita zastupitelů
        to_rebuild.append('build_aktualizace.py')   # nejnovější RO/ZO na stránce o aktualizaci
    if pz_changed:
        to_rebuild.append('build_zakazky.py')      # sekce Vypsané zakázky

    to_rebuild.append('build_portal.py')
    seen = set()
    to_rebuild = [s for s in to_rebuild if not (s in seen or seen.add(s))]
    rebuild(to_rebuild)

    # ── Commit ───────────────────────────────────
    print("\n[GIT] Commit a push...")
    parts = []
    if new_zo:
        parts.append("ZO " + ', '.join(str(c) for c, *_ in new_zo))
    if new_ro:
        parts.append("RO " + ', '.join(str(c) for c, *_ in new_ro))
    if new_videos:
        parts.append("video ZO " + ', '.join(str(c) for c, _ in new_videos))
    if pz_changed:
        parts.append(f"zakázky z profilu ({len(new_pz)} nových)" if new_pz else "zakázky z profilu (změny)")
    msg = f"Auto: {', '.join(parts)}\n\nAutomaticky zpracováno scriptem update_portal.py.\n"
    committed = git_commit(msg)

    # ── Souhrn ───────────────────────────────────
    print("\n=== SOUHRN ===")
    for l in summary_lines:
        print(" ", l)

    summary_path = ROOT / '.update_summary.md'
    summary_path.write_text(
        "## Nové dokumenty a videa na portálu\n\n"
        + "\n".join(summary_lines)
        + "\n\n_Automaticky zpracováno, commitnuto a nasazeno._",
        encoding='utf-8'
    )
    print(f"\nSouhrn zapsán do {summary_path}")


if __name__ == '__main__':
    main()
