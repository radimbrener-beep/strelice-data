# -*- coding: utf-8 -*-
"""Extrakce orientacni vyse vydaje z textu usneseni a zarazeni do velikostniho
pasma. Castka = nejvyssi hodnota v Kc nalezena v textu. Resi oddelovac tisicu
MEZEROU, nedelitelnou mezerou i TECKOU (rada pise '40 890 Kc', zastupitelstvo
'724.852,63 Kc'), desetinnou carku, 'mil.' a 'tis.'. Vylucuje zjevne
NEvydajove velke castky (terminovany vklad, pojistna hodnota, ucetni).
Jednotkove ceny (Kc/m2) se ignoruji."""
import re

# oddelovac tisicu: mezera, nedelitelna mezera ( ), tecka
_MIL = re.compile(r"(\d+(?:[  .]\d{3})*(?:,\d+)?)\s*mil(?:\.|ion\w*)?\s*(?:Kč|korun)")
_TIS = re.compile(r"(\d+(?:,\d+)?)\s*tis(?:\.|íc\w*)?\s*(?:Kč|korun)")
_PLAIN = re.compile(r"(\d{1,3}(?:[  .]\d{3})+|\d+)(?:,(\d+)|,\s*[-–—−])?\s*Kč(?!\s*/)")
_TERMVKLAD = re.compile(r"termínovan\w*\s+vklad|termínovaného vkladu|na termínovaný", re.IGNORECASE)
_POJIST = re.compile(r"pojist", re.IGNORECASE)
# ucetni / nevydajove kontexty: castka = hodnota majetku, ne realny vydaj
_NONSPEND = re.compile(r"inventarizac|vyřazen|likvidac|rezervního fondu|"
                       r"výsledk\w* hospodař|rozdělení výsledku", re.IGNORECASE)

# Strop verohodnosti: nektera usneseni obsahuji TABULKY (rozpis podilu na
# financovani, naklady stavby za cely svazek), ktere pdftotext zplosti a cisla
# z bunek se slepi mezerami v jedno obri cislo. Cely rocni rozpocet obce je
# ~124 mil Kc, nejvetsi realna jednotliva zakazka ~27 mil; jednotliva castka
# nad timto stropem je vzdy artefakt z tabulky -> ignorovat.
_CEILING = 80_000_000

# Zacatek tabulky rozpisu nakladu (typicky u smluv o financovani ČOV/vodovodu):
# vse za timto markerem jsou cisla z bunek tabulky, ne castka rozhodnuti.
# Castku tedy bereme jen z textu PRED tabulkou.
_TABLE_CUT = re.compile(r"rozdělení nákladů|rozpis podílu|podíl na nákladech|počet\s+EO\b",
                        re.IGNORECASE)

# DODATKY ke smlouvam: text casto uvadi NAVYSENI/SNIZENI ceny ("navýší se o X")
# I novou CELKOVOU/KONECNOU cenu (kumulativni soucet vc. puvodni smlouvy).
# Rozhodnuti tehdy commituje jen tu ZMENU, ne cely celek (puvodni smlouva uz je
# zapoctena ve svem usneseni) -> jinak dvoji-zapocet. Bereme tedy deltu.
# OCR: 'l' byva chybne misto '1' v cisle ('o l 695 691' = 1 695 691).
_OCR_L = re.compile(r"(?<![0-9A-Za-zÀ-ž])l(?=\s?\d)")
_PRICE_CHANGE = re.compile(r"dodat\w*|nav[ýy]š\w*|sn[íi]ž\w*|pon[íi]ž\w*|v[íi]cepr\w*|m[ée]n[ěe]pr\w*",
                           re.IGNORECASE)
_NUM = r"(\d{1,3}(?:[\s.]\d{3})+|\d+)(?:,(\d+))?"   # \s chyta i nedelitelne mezery
_KC = r"(?:\s*,?\s*[-–—−])?\s*Kč"                    # pripousti i zapis "4.748,- Kč"
_INC = re.compile(
    r"(?:nav[ýy]š\w*|zv[ýy]š\w*|sn[íi]ž\w*|pon[íi]ž\w*|zvyšuj\w*|snižuj\w*|v[íi]cepr\w*|m[ée]n[ěe]pr\w*)"
    r"[^.;:]{0,40}?(?:\bo|ve\s+výši|v\s+hodnotě)\s+" + _NUM + _KC, re.IGNORECASE)

# NABIDKA: schvaluje se "cena nabidky X" (cena te nabidky), ne uvedena velikost
# projektu. Napr. nabidka dotacni kancelare: "uznatelne vydaje 14 mil ... cena
# nabidky 445 000 Kc" -> rozhodujicich je 445 000.
_OFFER = re.compile(r"(?:cena\s+nabídky|nabídkov\w*\s+cena)[^.;:]{0,20}?" + _NUM + _KC,
                    re.IGNORECASE)
# PROJEKTOVE ODHADY (uznatelne/odhadovane vydaje, naklady projektu/akce, hodnota
# projektu) = velikost projektu pro zadost o dotaci, ne primy vydaj tohoto
# rozhodnuti (vlastni stavba se zapocte zvlast pres smlouvu o dilo) -> vyloucit.
_CTX_COST = re.compile(
    r"(?:uznateln\w*|odhadovan\w*\s+\w*\s*výdaj\w*|náklad\w*\s+(?:projektu|akce|stavby)|hodnot\w*\s+projektu)"
    r"[^.;:]{0,25}?(\d{1,3}(?:[\s.]\d{3})*(?:,\d+)?|\d+(?:,\d+)?)\s*(mil(?:\.|ion\w*)?|tis(?:\.|íc\w*)?)?\s*(?:Kč|korun)",
    re.IGNORECASE)


def _amt_from(rx, text):
    """Castka z prvni shody regexu, jehoz posledni dve skupiny jsou (cela, des.)."""
    m = rx.search(text)
    if not m:
        return None
    dec = m.group(2) or ""
    try:
        return float(_strip(m.group(1)) + ("." + dec if dec else ""))
    except ValueError:
        return None


def _increment(text):
    """Vyse navyseni/snizeni ceny u dodatku (delta), nebo None."""
    return _amt_from(_INC, text)


def _context_costs(text):
    """Hodnoty projektovych odhadu (uznatelne vydaje apod.) k vylouceni z kandidatu."""
    out = []
    for m in _CTX_COST.finditer(text):
        try:
            v = float(_strip(m.group(1)).replace(",", "."))
        except ValueError:
            continue
        u = (m.group(2) or "").lower()
        if u.startswith("mil"):
            v *= 1_000_000
        elif u.startswith("tis"):
            v *= 1_000
        out.append(round(v))
    return out


def fix_ocr_digits(text):
    """Oprava OCR glitche 'l' -> '1' v cisle (napr. 'o l 695 691' = '1 695 691').
    Pouzitelne i na zobrazovany text, aby sedel s extrahovanou castkou."""
    return _OCR_L.sub("1", text)


def _strip(s):
    return s.replace(" ", "").replace(" ", "").replace(".", "")


def _amounts(text):
    vals = []
    for m in _MIL.finditer(text):
        vals.append(float(_strip(m.group(1)).replace(",", ".")) * 1_000_000)
    for m in _TIS.finditer(text):
        vals.append(float(m.group(1).replace(",", ".")) * 1000)
    for m in _PLAIN.finditer(text):
        whole = _strip(m.group(1))
        dec = m.group(2) or ""
        vals.append(float(whole + ("." + dec if dec else "")))
    return vals


def extract_amount(text):
    """Orientacni vyse vydaje v Kc, nebo None. U dodatku/zmen ceny bere ZMENU
    (navyseni/snizeni), ne celkovou kumulativni cenu (ta by dvoji-zapocetla)."""
    mt = _TABLE_CUT.search(text)            # uriznout tabulku rozpisu nakladu
    if mt:
        text = text[:mt.start()]
    text = _OCR_L.sub("1", text)            # OCR: 'l' -> '1' v cisle ('o l 695' = 1 695)
    if _TERMVKLAD.search(text) or _NONSPEND.search(text):   # presun rezerv / ucetni = ne vydaj
        return None
    amt = None
    if _PRICE_CHANGE.search(text):          # dodatek/zmena ceny -> rozhoduje delta, ne celek
        amt = _increment(text)
    if amt is None:
        amt = _amt_from(_OFFER, text)       # nabidka -> rozhoduje cena nabidky, ne odhad projektu
    if amt is None:
        vals = [v for v in _amounts(text) if v <= _CEILING]   # odfiltrovat artefakty z tabulek
        if not vals:
            return None
        ctx = set(_context_costs(text))     # vyloucit projektove odhady (uznatelne vydaje apod.)
        amt = max([v for v in vals if round(v) not in ctx] or vals)
    if amt > _CEILING:
        return None
    if _POJIST.search(text) and amt > 2_000_000:   # pojistna hodnota majetku = ne vydaj
        return None
    return round(amt)


# velikostni pasma (horni mez, vyjma)
_BUCKETS = [
    ("do 10 tis. Kč", 10_000),
    ("10–50 tis. Kč", 50_000),
    ("50–100 tis. Kč", 100_000),
    ("100–500 tis. Kč", 500_000),
    ("0,5–1 mil. Kč", 1_000_000),
    ("nad 1 mil. Kč", float("inf")),
]
NONE_BUCKET = "Bez částky"
ORDER = [b for b, _ in _BUCKETS] + [NONE_BUCKET]


def bucket(v):
    if v is None:
        return NONE_BUCKET
    for name, hi in _BUCKETS:
        if v < hi:
            return name
    return _BUCKETS[-1][0]
