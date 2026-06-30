#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Parsuje PDF výpisu usnesení ze ZO (Zastupitelstvo obce Střelice).
Zvládá dva formáty:
  - Formát A (textové PDF, ZO 1-26): položky oddělené hlasovacím řádkem
    "Pro – N (...) Proti – N Zdržel se – N (...)"
  - Formát B (OCR sken, ZO 27+): "Bod N. text ... N/YYYY/ZNN ... Hlasování: Pro Proti Zdržel se / N N N"
"""
import re, sys, json, io
import pdfplumber
import requests

# ── Datum ────────────────────────────────────────────────────────────────────
_MONTHS = {
    'ledna':1,'února':2,'března':3,'dubna':4,'května':5,'června':6,
    'července':7,'srpna':8,'září':9,'října':10,'listopadu':11,'prosince':12,
}
DATE_WORD_RE = re.compile(r'(\d{1,2})\.\s+(' + '|'.join(_MONTHS) + r')\s+(\d{4})', re.I)
DATE_NUM_RE  = re.compile(r'(\d{1,2})\.\s*(\d{1,2})\.\s*(\d{4})')

# ── Číslo zasedání ───────────────────────────────────────────────────────────
CISLO_RE = re.compile(
    r'z\s+(\d+)\.\s+(?:ustavující(?:ho)?\s+)?zasedání|'
    r'(\d+)\.\s+(?:ustavující(?:ho)?\s+)?[Zz]astupitelstv',
    re.I)

# ── Počet přítomných ─────────────────────────────────────────────────────────
PRITOMNO_RE = re.compile(r'[Pp]řítomno[:\s]+(\d+)', re.I)

# ── Formát A: hlasování "Pro – N (...) Proti – N Zdržel se – N (...)" ─────────
VOTE_A_RE = re.compile(
    r'Pro\s*[–\-]\s*(\d+)\s*(?:\([^)]*\))?\s*'
    r'Proti\s*[–\-]\s*(\d+)\s*(?:\([^)]*\))?\s*'
    r'Zdržel\s*se\s*[–\-]\s*(\d+)\s*(?:\([^)]*\))?',
    re.S | re.I)

# ── Formát B (OCR): "Bod N. text ... N/YYYY/ZNN" ──────────────────────────────
BOD_RE    = re.compile(r'Bod\s+(\d+)\.\s+(.+?)(?=\nBod\s+\d+\.|\Z)', re.S)
USN_ID_RE = re.compile(r'\d+/\d{4}/Z\d+')  # N/YYYY/ZNN – usnesení ID

# ── Kategorie ─────────────────────────────────────────────────────────────────
_KATS = [
    (re.compile(r'\bschvaluje\b|\bschválilo\b|\bscválilo\b', re.I), 'schvaluje'),
    (re.compile(r'\bukládá\b|\buložilo\b', re.I), 'ukládá'),
    (re.compile(r'\bpověřuje\b|\bpověřilo\b', re.I), 'pověřuje'),
    (re.compile(r'\bneschvaluje\b|\bneschválilo\b', re.I), 'neschvaluje'),
    (re.compile(r'\bvolí\b|\bzvolilo\b', re.I), 'volí'),
    (re.compile(r'\bvypovídá\b|\bvypovědělo\b', re.I), 'vypovídá'),
    (re.compile(r'\bbere\b.*\bna vědomí\b|\bvzalo\b.*\bna vědomí\b|\bkonstatoval', re.I | re.S), 'bere na vědomí'),
]
def detect_kat(text):
    for pat, kat in _KATS:
        if pat.search(text):
            return kat
    return 'jiné'


# ── Načtení PDF ───────────────────────────────────────────────────────────────
def pdf_text(source):
    if isinstance(source, str) and source.startswith('http'):
        r = requests.get(source, timeout=60)
        r.raise_for_status()
        source = io.BytesIO(r.content)
    with pdfplumber.open(source) as pdf:
        return '\n'.join(p.extract_text() or '' for p in pdf.pages)


# ── Pomocné ────────────────────────────────────────────────────────────────────
def parse_date(raw):
    m = DATE_WORD_RE.search(raw)
    if m:
        d, mn, y = int(m.group(1)), _MONTHS[m.group(2).lower()], int(m.group(3))
        return f"{y}-{mn:02d}-{d:02d}", f"{d}. {mn}. {y}", y
    m = DATE_NUM_RE.search(raw)
    if m:
        d, mn, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        return f"{y}-{mn:02d}-{d:02d}", f"{d}. {mn}. {y}", y
    return '', '', None

def _item(text, hl):
    text = re.sub(r'\s+', ' ', text).strip().rstrip('.')
    return {'kategorie': detect_kat(text), 'tema': None, 'castka': None,
            'vydaj': None, 'hlasovani': hl, 'text': text}


# ── Parser formátu A (textové PDF) ────────────────────────────────────────────
def parse_format_a(raw):
    """
    Položky jsou odděleny hlasovacím řádkem.
    Každá hlasovací match → text PŘED ní = text usnesení.
    """
    body = []
    prev_end = 0

    # Najdeme první výskyt "Přítomno:" nebo první usnesení
    # (přeskočíme záhlaví se jmény přítomných)
    header_end = 0
    hm = re.search(r'\n\s*(?:Omluveni|Nepřítomni|[•\s]+Zastupitelstvo\b)', raw, re.I)
    if hm:
        header_end = hm.start()

    for vm in VOTE_A_RE.finditer(raw):
        chunk = raw[max(prev_end, header_end):vm.start()].strip()
        prev_end = vm.end()
        hl = [int(vm.group(1)), int(vm.group(2)), int(vm.group(3))]

        # Odstraň čísla usnesení (N/YYYY/ZNN), záhlaví, prázdné řádky
        chunk = USN_ID_RE.sub('', chunk).strip()
        lines = [l.strip() for l in chunk.splitlines()]
        # Odstraň řádky záhlaví (přítomní, omluvení) a řádky jen s čísly
        lines = [l for l in lines if len(l) > 4
                 and not re.fullmatch(r'[\d\s/\.]+', l)
                 and not re.match(r'^(Přítomno|Omluveni|Nepřítomn|Výpis\s+usnesení)', l, re.I)]
        text = ' '.join(lines).strip()
        # Odstraň úvodní jmenovitý seznam (končí za posledním jménem před prvním slovesem)
        text = re.sub(r'^(?:[A-ZÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ][a-záčďéěíňóřšťúůýž]+\s+)*', '', text).strip()

        # Přeskoč příliš krátký text (pokračování, "a pana X.")
        if len(text) < 15:
            continue
        # Pokud text začíná "a pan(í)" – je to pokračování ověřovatele apod., přidej k předchozímu
        if re.match(r'^a\s+pan[íi]?\b', text, re.I) and body:
            body[-1]['text'] += ' ' + text
            continue

        body.append(_item(text, hl))

    return body


# ── Parser formátu B (OCR sken) ───────────────────────────────────────────────
def parse_format_b(raw):
    """
    Každá položka začíná 'Bod N. text ... N/YYYY/ZNN ... hlasovací čísla'.
    Čísla Pro/Proti/Zdržel jsou na řádku ve formátu "15 0 0" nebo "15 O O".
    """
    body = []
    for bm in BOD_RE.finditer(raw):
        blok = bm.group(2)

        # Stáhni usnesení ID (N/YYYY/ZNN) a hlasovací sekci
        blok_clean = USN_ID_RE.sub('', blok)

        # Hlasovací čísla: řádek za "Hlasování:" nebo poslední řádek s čísly
        hl = [None, None, None]
        vote_section = re.search(r'Hlasování\s*:.+', blok_clean, re.S)
        search_in = vote_section.group(0) if vote_section else blok_clean
        for line in reversed(search_in.splitlines()):
            line_n = line.replace('O', '0').replace('o', '0')
            nums = re.findall(r'\d+', line_n)
            # hlasovací čísla musí být malá (max 20 zastupitelů) + součet ≤ 20
            if len(nums) >= 3:
                a, b, c = int(nums[0]), int(nums[1]), int(nums[2])
                if a <= 20 and b <= 20 and c <= 20 and a + b + c <= 20:
                    hl = [a, b, c]
                    break
            if len(nums) == 1 and re.search(r'^\s*\d+\s+[O0]\s+[O0]\s*$', line_n):
                n = int(nums[0])
                if n <= 20:
                    hl = [n, 0, 0]
                    break

        # Text: odstraň hlasovací sekci
        text_blok = re.sub(r'Hlasování\s*:.*', '', blok_clean, flags=re.S).strip()
        # Odstraň záhlavní čísla bodů ("Bod N." už oddělil regex)
        text_blok = re.sub(r'^\d+\.\s*', '', text_blok).strip()
        text_blok = re.sub(r'\s+', ' ', text_blok).strip().rstrip('.')

        if len(text_blok) < 10:
            continue
        body.append(_item(text_blok, hl))

    return body


# ── Hlavní parser ─────────────────────────────────────────────────────────────
def parse(source, cislo_hint=None):
    url = source if isinstance(source, str) and source.startswith('http') else ''
    raw = pdf_text(source)

    datum_iso, datum_text, rok = parse_date(raw)
    cm = CISLO_RE.search(raw)
    cislo = int(next(g for g in cm.groups() if g)) if cm else (cislo_hint or 0)
    pm = PRITOMNO_RE.search(raw)
    pritomno = int(pm.group(1)) if pm else None

    # Detekce formátu
    if BOD_RE.search(raw) and USN_ID_RE.search(raw):
        body = parse_format_b(raw)
    else:
        body = parse_format_a(raw)

    return {
        'soubor': url.split('/')[-1] if url else '',
        'url': url,
        'cislo_zasedani': cislo,
        'datum': datum_iso,
        'datum_text': datum_text,
        'rok': rok,
        'pritomno': pritomno,
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
