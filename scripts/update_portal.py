#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Automatická aktualizace portálu jakzijistrelice.cz.

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
from pathlib import Path
import requests
from bs4 import BeautifulSoup

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

ZO_LIST_URL = (
    "https://www.streliceubrna.cz/obec/samosprava/zastupitelstvo-obce-strelice"
    "/usneseni/usneseni-ze-zasedani-zastupitelstva-obce-strelice-2022-2026"
)
RO_LIST_URL = (
    "https://www.streliceubrna.cz/obec/samosprava/rada-obce-strelice"
    "/zapisy-rady-obce-strelice/zapisy-rady-obce-strelice-2022-2026"
)
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

def scrape_zo_links():
    """Vrátí seznam (cislo, title, pdf_url) pro ZO usnesení na webu obce."""
    results = []
    try:
        s = soup(ZO_LIST_URL)
    except Exception as e:
        print(f"WARN: nelze načíst ZO stránku: {e}")
        return results

    for a in s.find_all('a', href=True):
        href = a['href']
        title = a.get_text(strip=True)
        # hledáme PDF soubory s usnesením
        if '.pdf' not in href.lower():
            continue
        if not re.search(r'usnesení|usnesen', href + title, re.I):
            continue
        url = href if href.startswith('http') else BASE_OBEC + href
        # extrahuj číslo zasedání z názvu/url
        m = re.search(r'[ZzčČ]\.?\s*(\d+)|(\d+)\.\s*zasedání', title + href, re.I)
        cislo = int(m.group(1) or m.group(2)) if m else None
        if cislo:
            results.append((cislo, title, url))

    return results

def scrape_ro_links():
    """Vrátí seznam (cislo, title, pdf_url) pro RO zápisy na webu obce."""
    results = []
    try:
        s = soup(RO_LIST_URL)
    except Exception as e:
        print(f"WARN: nelze načíst RO stránku: {e}")
        return results

    for a in s.find_all('a', href=True):
        href = a['href']
        title = a.get_text(strip=True)
        if '.pdf' not in href.lower():
            continue
        if not re.search(r'zápis|zapis|RO', href + title, re.I):
            continue
        url = href if href.startswith('http') else BASE_OBEC + href
        m = re.search(r'[RrčČ]\.?\s*(\d+)|(\d+)\.\s*zasedání', title + href, re.I)
        cislo = int(m.group(1) or m.group(2)) if m else None
        if cislo:
            results.append((cislo, title, url))

    return results


def known_zo():
    data = json.loads((ROOT / 'dataset_ZO.json').read_text(encoding='utf-8'))
    return {m['cislo_zasedani'] for m in data}

def known_ro():
    data = json.loads((ROOT / 'dataset_RO.json').read_text(encoding='utf-8'))
    return {m['cislo_zasedani'] for m in data}


# ──────────────────────────────────────────────
# YouTube – hledání videa pro ZO zasedání
# ──────────────────────────────────────────────

def find_video_for_zo(cislo, datum_iso):
    """
    Hledá video na kanálu @tvstreliceubrna odpovídající zasedání číslo `cislo`.
    Vrátí video_id nebo None.
    Strategie: titulek videa obsahuje číslo zasedání nebo datum.
    """
    print(f"  Hledám video pro ZO {cislo} ({datum_iso})...")
    try:
        result = run([
            'yt-dlp', '--flat-playlist', '--print', '%(id)s\t%(title)s\t%(upload_date)s',
            '--playlist-end', '30',  # posledních 30 videí kanálu
            YT_CHANNEL,
        ], capture=True, check=False)
        lines = (result.stdout or '').strip().splitlines()
    except FileNotFoundError:
        print("  WARN: yt-dlp není nainstalováno")
        return None

    date_nodash = datum_iso.replace('-', '')
    year = datum_iso[:4]
    month = datum_iso[5:7]
    day = datum_iso[8:10]
    date_cz = f"{int(day)}.{int(month)}.{year}"

    candidates = []
    for line in lines:
        parts = line.split('\t', 2)
        if len(parts) < 2:
            continue
        vid_id, title = parts[0], parts[1]
        upload = parts[2] if len(parts) > 2 else ''

        # skóre shody
        score = 0
        if re.search(r'\bzastupitelstvo\b', title, re.I):
            score += 2
        if re.search(rf'\b{cislo}\b', title):
            score += 3
        if date_cz in title or date_nodash == upload:
            score += 4
        if score > 0:
            candidates.append((score, vid_id, title))

    if not candidates:
        print(f"  Video pro ZO {cislo} nenalezeno.")
        return None

    candidates.sort(reverse=True)
    best_score, best_id, best_title = candidates[0]
    print(f"  Nalezeno video: {best_id} – {best_title!r} (skóre {best_score})")
    return best_id


# ──────────────────────────────────────────────
# Přidání záznamu do datasetu
# ──────────────────────────────────────────────

def append_to_dataset(path, new_entry):
    data = json.loads(path.read_text(encoding='utf-8'))
    data.append(new_entry)
    data.sort(key=lambda m: m['cislo_zasedani'])
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding='utf-8')


def add_video_to_map(cislo, video_id):
    map_path = ROOT / 'data' / 'video' / 'map.txt'
    lines = map_path.read_text(encoding='utf-8').splitlines()
    # zkontroluj zda už existuje
    if any(line.startswith(str(cislo) + ' ') for line in lines):
        return
    lines.append(f"{cislo} {video_id}")
    lines.sort(key=lambda l: int(l.split()[0]) if l.split() else 0, reverse=True)
    map_path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(f"  map.txt: přidáno ZO {cislo} → {video_id}")


# ──────────────────────────────────────────────
# Kontrola chybějících videí pro existující ZO
# ──────────────────────────────────────────────

def mapped_videos():
    """Vrátí set čísel ZO zasedání, která už mají video v map.txt."""
    map_path = ROOT / 'data' / 'video' / 'map.txt'
    if not map_path.exists():
        return set()
    mapped = set()
    for line in map_path.read_text(encoding='utf-8').splitlines():
        parts = line.strip().split()
        if parts:
            try:
                mapped.add(int(parts[0]))
            except ValueError:
                pass
    return mapped

def check_missing_videos(dry_run=False):
    """
    Pro ZO zasedání v datasetu, která ještě nemají video v map.txt,
    zkusí najít video na YouTube kanálu.
    Vrátí seznam (cislo, video_id) nově nalezených videí.
    """
    print("\n[VIDEO] Kontrola chybějících videí pro ZO...")
    zo_data = json.loads((ROOT / 'dataset_ZO.json').read_text(encoding='utf-8'))
    mapped = mapped_videos()
    without_video = [m for m in zo_data if m['cislo_zasedani'] not in mapped]

    if not without_video:
        print("  Všechna ZO zasedání mají video.")
        return []

    print(f"  ZO bez videa: {[m['cislo_zasedani'] for m in without_video]}")
    found = []
    for m in without_video:
        vid = find_video_for_zo(m['cislo_zasedani'], m.get('datum', ''))
        if vid and not dry_run:
            add_video_to_map(m['cislo_zasedani'], vid)
            found.append((m['cislo_zasedani'], vid))
        elif vid:
            found.append((m['cislo_zasedani'], vid))

    return found


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
    if files:
        run(['git', 'add'] + [str(f) for f in files])
    else:
        run(['git', 'add', '-A'])
    # zkontroluj jestli je co commitovat
    r = run(['git', 'diff', '--cached', '--quiet'], check=False)
    if r.returncode == 0:
        print("  Žádné změny k commitu.")
        return False
    run(['git', 'commit', '-m', message])
    run(['git', 'push', 'origin', 'main'])
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

    # ── ZO ──────────────────────────────────────
    print("\n[ZO] Kontrola usnesení...")
    already_zo = known_zo()
    for cislo, title, url in scrape_zo_links():
        if cislo in already_zo:
            continue
        print(f"  Nové ZO: {cislo} – {title}")
        if args.dry_run:
            summary_lines.append(f"- ZO {cislo}: {title} ({url})")
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
            print(f"  CHYBA parsování ZO {cislo}: {e}")
            summary_lines.append(f"- ZO {cislo}: chyba parsování — {e}")
            continue

        # video
        video_id = find_video_for_zo(cislo, entry.get('datum', ''))
        if video_id:
            add_video_to_map(cislo, video_id)

        # dataset
        append_to_dataset(ROOT / 'dataset_ZO.json', entry)
        new_zo.append((cislo, title, url, video_id))
        summary_lines.append(
            f"- **ZO {cislo}** ({entry.get('datum_text', '')}): "
            f"{entry.get('pocet_bodu', 0)} usnesení"
            + (f", video {video_id}" if video_id else ", video nenalezeno")
        )

    # ── RO ──────────────────────────────────────
    print("\n[RO] Kontrola zápisů...")
    already_ro = known_ro()
    for cislo, title, url in scrape_ro_links():
        if cislo in already_ro:
            continue
        print(f"  Nové RO: {cislo} – {title}")
        if args.dry_run:
            summary_lines.append(f"- RO {cislo}: {title} ({url})")
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
            print(f"  CHYBA parsování RO {cislo}: {e}")
            summary_lines.append(f"- RO {cislo}: chyba parsování — {e}")
            continue

        append_to_dataset(ROOT / 'dataset_RO.json', entry)
        new_ro.append((cislo, title, url))
        summary_lines.append(
            f"- **RO {cislo}** ({entry.get('datum_text', '')}): "
            f"{entry.get('pocet_bodu', 0)} usnesení"
        )

    # ── Chybějící videa pro existující ZO ────────
    new_videos = check_missing_videos(dry_run=args.dry_run)
    for cislo, vid in new_videos:
        summary_lines.append(f"- **Video ZO {cislo}**: přidáno {vid} → timestamps přegenerovány")

    if not new_zo and not new_ro and not new_videos:
        print("\nŽádné nové dokumenty ani videa.")
        Path(ROOT / '.no_update').write_text('ok')
        return

    if args.dry_run:
        print("\n=== DRY RUN – souhrn nálezů ===")
        for l in summary_lines:
            print(" ", l)
        return

    # ── Rebuild ──────────────────────────────────
    print("\n[BUILD] Přegenerovávám HTML...")
    to_rebuild = ['build_portal.py']
    if new_zo or new_videos:
        to_rebuild.append('build_video_casy.py')
        to_rebuild.append('build_zastupitelstvo.py')
        to_rebuild.append('build_investice.py')
    if new_ro:
        to_rebuild.append('build_zapisy.py')
        to_rebuild.append('build_investice.py')

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
