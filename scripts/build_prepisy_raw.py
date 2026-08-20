#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fáze 1 přepisů jednání ZO: stáhne automatické titulky (cs-orig) z YouTube
záznamů, rozseká je podle časů jednotlivých bodů (video_casy.json) a uloží
SUROVÝ přepis po bodech + oficiální usnesení a výsledek hlasování jako kotvu.

Výstup (regenerovatelné, proto v gitignorovaném data/):
  data/prepisy/vtt/zo{N}.cs-orig.vtt   – stažené titulky (cache)
  data/prepisy/zo{N}_raw.json          – surový přepis po bodech

Čištění (fáze 2) čte tyto _raw.json a produkuje committed prepisy/{N}.json.
"""
import json, sys, re, subprocess, os
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
ROOT = Path(__file__).resolve().parent.parent
VTT_DIR = ROOT / 'data' / 'prepisy' / 'vtt'
RAW_DIR = ROOT / 'data' / 'prepisy'
VTT_DIR.mkdir(parents=True, exist_ok=True)

TS = re.compile(r'(\d{2}):(\d{2}):(\d{2})\.\d{3}\s+-->')


def secs(h, m, s):
    return int(h) * 3600 + int(m) * 60 + int(s)


def download_vtt(vid, dest):
    """Stáhne cs-orig auto-titulky, vrátí True/False."""
    if dest.exists() and dest.stat().st_size > 500:
        return True
    tmpl = str(dest).replace('.cs-orig.vtt', '.%(ext)s')
    try:
        subprocess.run([
            'python', '-m', 'yt_dlp', '--write-auto-subs', '--sub-langs', 'cs-orig',
            '--sub-format', 'vtt', '--skip-download', '--js-runtimes', 'deno',
            '-o', tmpl, f'https://www.youtube.com/watch?v={vid}',
        ], cwd=ROOT, check=False, capture_output=True, text=True, encoding='utf-8')
    except Exception as e:
        print(f'    yt-dlp chyba: {e}')
    return dest.exists() and dest.stat().st_size > 500


def parse_segments(vtt_path):
    """VTT -> [(start_s, text)], dedup rolujících řádků, >> = ▶ (změna mluvčího)."""
    raw = vtt_path.read_text(encoding='utf-8')
    segs, last = [], ''
    for blk in re.split(r'\n\n+', raw):
        lines = blk.strip().splitlines()
        if not lines:
            continue
        t, txt = None, []
        for l in lines:
            m = TS.search(l)
            if m:
                t = secs(*m.groups()); continue
            if l.strip() == 'WEBVTT' or l.startswith(('Kind:', 'Language:')):
                continue
            c = re.sub(r'<[^>]+>', '', l).replace('&gt;&gt;', '▶').replace('&nbsp;', ' ').strip()
            if c:
                txt.append(c)
        if not txt:
            continue
        new = txt[-1]
        if new and new != last:
            segs.append((t if t is not None else (segs[-1][0] if segs else 0), new))
            last = new
    return segs


def slice_by_bod(segs, bodytimes, body):
    """Rozseká segmenty podle časů bodů. bodytimes: {index:sekundy}."""
    mapped = sorted(((int(k), v) for k, v in bodytimes.items()), key=lambda kv: kv[1])
    out = []
    for i, (idx, start) in enumerate(mapped):
        end = mapped[i + 1][1] if i + 1 < len(mapped) else 10 ** 9
        txt = ' '.join(t for (ss, t) in segs if start <= ss < end)
        txt = re.sub(r'\s+', ' ', txt).strip()
        b = body[idx] if idx < len(body) else {}
        out.append({
            'index': idx,
            'start': start,
            'usneseni': b.get('text', ''),
            'hlasovani': b.get('hlasovani'),
            'raw': txt,
            'slov': len(txt.split()),
        })
    return out


def main():
    vc = json.load(open(ROOT / 'video_casy.json', encoding='utf-8'))
    zo = {x['cislo_zasedani']: x for x in json.load(open(ROOT / 'dataset_ZO.json', encoding='utf-8'))}

    todo = sorted((int(k), v) for k, v in vc.items() if (v.get('bodytimes') and v.get('vid')))
    print(f'Zasedání s videem i časy bodů: {len(todo)}')
    grand = 0
    done, skipped = [], []
    for cislo, v in todo:
        vid = v['vid']
        vtt = VTT_DIR / f'zo{cislo}.cs-orig.vtt'
        ok = download_vtt(vid, vtt)
        if not ok:
            print(f'  ZO {cislo}: titulky NEDOSTUPNÉ ({vid}) – přeskočeno')
            skipped.append(cislo); continue
        segs = parse_segments(vtt)
        body = zo.get(cislo, {}).get('body', [])
        sliced = slice_by_bod(segs, v['bodytimes'], body)
        words = sum(b['slov'] for b in sliced)
        grand += words
        out = {'cislo_zasedani': cislo, 'vid': vid,
               'datum': zo.get(cislo, {}).get('datum', ''),
               'datum_text': zo.get(cislo, {}).get('datum_text', ''),
               'body': sliced}
        (RAW_DIR / f'zo{cislo}_raw.json').write_text(
            json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')
        print(f'  ZO {cislo}: {len(sliced)} bodů, {words:,} slov -> zo{cislo}_raw.json')
        done.append((cislo, len(sliced), words))

    print(f'\nHOTOVO: {len(done)} zasedání, celkem {grand:,} slov surového přepisu.')
    if skipped:
        print(f'Bez titulků (přeskočeno): {skipped}')


if __name__ == '__main__':
    main()
