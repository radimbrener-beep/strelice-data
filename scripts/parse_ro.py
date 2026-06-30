#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Parsuje PDF zápisu ze zasedání RO (Rada obce Střelice).
Vrací dict kompatibilní s dataset_RO.json.
"""
import re, sys, json, io
import pdfplumber
import requests

DATE_RE  = re.compile(r'(\d{1,2})\.\s*(\d{1,2})\.\s*(\d{4})')
CISLO_RE = re.compile(r'z\s+(\d+)\.\s+zasedání\s+Rady\s+obce', re.I)

# Záhlaví sekce: "Rada obce schvaluje:", "Rada obce bere na vědomí:" atd.
SEKCE_HDR_RE = re.compile(
    r'^Rada\s+obce\s+(schvaluje|bere\s+na\s+vědomí|neschvaluje|projednala?|ukládá|pověřuje|doporučuje)\s*:?\s*$',
    re.I | re.M)

KAT_NORM = {
    'schvaluje': 'schvaluje',
    'bere na vědomí': 'bere na vědomí',
    'bere na vedomi': 'bere na vědomí',
    'neschvaluje': 'neschvaluje',
    'projednala': 'projednala',
    'projednal': 'projednala',
    'ukládá': 'ukládá',
    'pověřuje': 'pověřuje',
    'doporučuje': 'doporučuje',
}

STRIP_TAIL_RE = re.compile(
    r'\s*\.?\s*(?:RO|Rada\s+obce)\s+a?\s*pověřuje\s+starostu\s+(?:obce\s+)?podpisem\s+smlouvy\.?$',
    re.I)


def pdf_text(source):
    if isinstance(source, str) and source.startswith('http'):
        r = requests.get(source, timeout=60)
        r.raise_for_status()
        source = io.BytesIO(r.content)
    with pdfplumber.open(source) as pdf:
        return '\n'.join(p.extract_text() or '' for p in pdf.pages)


def clean(text):
    text = re.sub(r'\s+', ' ', text).strip()
    text = STRIP_TAIL_RE.sub('', text)
    text = text.strip().rstrip('.')
    # odstraň vedoucí bullet •
    text = re.sub(r'^[•\-]\s*', '', text).strip()
    return text


def parse(source, cislo_hint=None):
    url = source if isinstance(source, str) and source.startswith('http') else ''
    raw = pdf_text(source)

    # datum
    dm = DATE_RE.search(raw)
    if dm:
        d, mn, y = int(dm.group(1)), int(dm.group(2)), int(dm.group(3))
        datum = f"{y}-{mn:02d}-{d:02d}"
        datum_text = f"{d}. {mn}. {y}"
        rok = y
    else:
        datum = datum_text = ''
        rok = None

    cm = CISLO_RE.search(raw)
    cislo = int(cm.group(1)) if cm else (cislo_hint or 0)

    body = []

    # Projdeme řádky dokumentu, sledujeme aktivní kategorii a sbíráme bullet položky
    active_kat = 'schvaluje'   # defaultní kategorie na začátku (první sekce bývá schvaluje)
    active_kat_full = 'Rada obce schvaluje'
    current_item_lines = []

    def flush_item():
        if not current_item_lines:
            return
        text = clean(' '.join(current_item_lines))
        if len(text) >= 10:
            body.append({
                'kategorie': active_kat,
                'kategorie_full': active_kat_full,
                'tema': None,
                'castka': None,
                'vydaj': None,
                'text': text,
            })
        current_item_lines.clear()

    lines = raw.splitlines()
    in_content = False  # přeskočíme záhlaví zápisu (datum, místo...)

    for line in lines:
        stripped = line.strip()

        # Přechod do obsahu zápisu (jakmile narazíme na první "Rada obce X:")
        hm = SEKCE_HDR_RE.match(stripped)
        if hm:
            flush_item()
            in_content = True
            kat_raw = re.sub(r'\s+', ' ', hm.group(1).strip().lower())
            active_kat = KAT_NORM.get(kat_raw, kat_raw)
            active_kat_full = f"Rada obce {kat_raw}"
            continue

        if not in_content:
            continue

        # Bullet = nová položka
        if stripped.startswith('•'):
            flush_item()
            current_item_lines.append(stripped[1:].strip())
        elif current_item_lines:
            # Pokračování aktuální položky (zalamování textu)
            # Přeskočíme stránkové záhlaví (číslo stránky, opakovaný titulek)
            if re.match(r'^\d+$', stripped) or 'Zápis z' in stripped:
                continue
            current_item_lines.append(stripped)

    flush_item()

    return {
        'soubor': url.split('/')[-1] if url else '',
        'url': url,
        'cislo_zasedani': cislo,
        'datum': datum,
        'datum_text': datum_text,
        'rok': rok,
        'pocet_bodu': len(body),
        'body': body,
        'raw_text': raw,
    }


if __name__ == '__main__':
    src = sys.argv[1]
    hint = int(sys.argv[2]) if len(sys.argv) > 2 else None
    result = parse(src, hint)
    sys.stdout.reconfigure(encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False, indent=2))
