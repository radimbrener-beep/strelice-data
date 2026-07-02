#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Sdílená extrakce zhotovitele/firmy z textů usnesení + deduplikace
záznamů téže akce (rada → zastupitelstvo). Používá build_investice.py
(feed + mapa investic) a build_zakazky.py (žebříček dodavatelů)."""
import re, os, json, unicodedata
from datetime import date

# --- zhotovitel / firma u akce ---
# název firmy se bere AŽ ZA konektorem (společností/firmou) — tím se vynechají
# advokátní/dotační kanceláře (zprostředkovatelé "kanceláří"); cena patří vítězi.
_CONN = r"(?:[Ss]polečnost[íi]|[Ff]irm[ouy])\s+"
_FORM = r"(?:spol\.\s*s\.?\s*r\.?\s*o\.?|s\.\s*r\.\s*o\.?|a\.\s*s\.|v\.\s*o\.\s*s\.)"
_FIRM = re.compile(_CONN + r"([A-ZÁ-Ž0-9][\wáčďéěíňóřšťúůýž.&-]*(?:[ -][\wáčďéěíňóřšťúůýž0-9.&/-]+){0,4}?)\s*,?\s*(" + _FORM + ")")
_FIRM_DROP = re.compile(r"kancelář|advokát|dota[cč]", re.IGNORECASE)
# u KOUPĚ nemovitosti je uvedená firma PRODÁVAJÍCÍ, ne zhotovitel → nezobrazovat
_REALTY_BUY = re.compile(r"kupní smlouv|nákup|koup", re.IGNORECASE)
_REALTY = re.compile(r"budov|pozem|nemovit|jednotk|komerčn", re.IGNORECASE)

_FORMS_NORM = {"sro": "s.r.o.", "as": "a.s.", "vos": "v.o.s."}


def _norm_form(f):
    """Sjednotí zápis právní formy: 's. r. o.'→'s.r.o.', 'spol. s.r.o.'→'spol. s r.o.'"""
    c = re.sub(r"[\s.]", "", f).lower()
    if c.startswith("spol"):
        return "spol. s r.o."
    return _FORMS_NORM.get(c, f.strip())


def firm(text):
    """Název firmy včetně normalizované právní formy ('MATYÁŠ s.r.o.')."""
    if _REALTY_BUY.search(text) and _REALTY.search(text):
        return ""                                     # koupě nemovitosti — firma je prodávající
    for m in _FIRM.finditer(text):
        core = re.sub(r"\s*\d+/20\d\d/[A-Za-z]?\d+\s*", " ", m.group(1))   # vložené ID usnesení
        core = re.sub(r"\s*-\s*", "-", core)                               # sjednotit pomlčku
        core = re.sub(r"\s+", " ", core).strip(" ,.-").replace("POOR", "PORR")
        if len(core) >= 2 and not _FIRM_DROP.search(core):
            return core + " " + _norm_form(m.group(2))
    return ""


def firm_key(name):
    """Klíč pro agregaci: bez právní formy, diakritiky, mezer a velikosti písmen —
    'Dräger Safety s.r.o.' = 'DRAGER SAFETY s.r.o.', 'Deratizace 4D' = 'Deratizace4D'."""
    base = re.sub(r"\s+(spol\. s r\.o\.|s\.r\.o\.|a\.s\.|v\.o\.s\.)$", "", name)
    base = unicodedata.normalize("NFD", base)
    base = "".join(c for c in base if not unicodedata.combining(c))
    return re.sub(r"[^A-Za-z0-9]+", "", base).upper()


# ruční aliasy pro překlepy a přívlastky, které normalizace nesloučí
# (Outsorcing/Outsourcing, ASPHA/ASHPA, DIMENSE architects/DIMENSE);
# data/firmy_aliasy.json = seznam skupin, PRVNÍ položka = kanonický název (dle ARES)
_ALIAS = None


def canon_name(name):
    """Kanonický název firmy dle data/firmy_aliasy.json (jinak beze změny)."""
    global _ALIAS
    if _ALIAS is None:
        _ALIAS = {}
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "firmy_aliasy.json")
        try:
            for g in json.load(open(path, encoding="utf-8")):
                for v in g:
                    _ALIAS[firm_key(v)] = g[0]
        except FileNotFoundError:
            pass
    return _ALIAS.get(firm_key(name), name)


# PŘÍJMY OBCE / developerské smlouvy: firma platí OBCI (příspěvek na občanskou
# vybavenost, plánovací smlouva, symbolický převod infrastruktury) — není to
# zakázka ani investiční výdaj obce, i když text obsahuje firmu a částku.
INCOME_RE = re.compile(
    r"příspěv\w*\s+obci|ve prospěch obce|plánovací smlouv|převodu stav\w* veřejné infrastruktury",
    re.IGNORECASE)

# DARY: darovací smlouvy (firma → obec i obec → spolek) nejsou zakázka za
# dodávku/službu — do žebříčku dodavatelů nepatří (např. dar Čepro a.s. obci).
GIFT_RE = re.compile(r"darovac\w*\s+smlouv|finanční\s+dar|peněžit\w*\s+dar|věcn\w*\s+dar|\bdar\b|\bdaru\b",
                     re.IGNORECASE)


# --- deduplikace záznamů téže akce/projektu ---
def _date(iso):
    try:
        return date.fromisoformat(iso)
    except (ValueError, TypeError):
        return None


_PARC = re.compile(r"p\.?\s*č\.?\s*(\d+(?:/\d+)?)", re.IGNORECASE)


def _parcels(text):
    """Čísla parcel v textu — identita pozemkové akce (různé parcely se stejnou
    částkou jsou různé akce; tatáž parcela napříč fázemi je jedna akce)."""
    return set(_PARC.findall(text))


_KEEP_STRONG = re.compile(r"kupní smlouv|nákup|koup|smlouvu o dílo", re.IGNORECASE)


def _score(it):
    """Která z duplicit nejlépe reprezentuje akci (pro zobrazení)."""
    t = it[4]
    s = 2 if it[2] == "ZO" else 0                       # ZO = závazné schválení
    if _KEEP_STRONG.search(t):
        s += 3
    elif re.search(r"schvál", t, re.IGNORECASE):
        s += 1
    if re.search(r"na vědomí|vzal", t, re.IGNORECASE):
        s -= 3                                          # "bere na vědomí" = slabý záznam
    if re.search(r"úschov", t, re.IGNORECASE):
        s -= 1                                          # smlouva o úschově = vedlejší k nákupu
    return s


def dedup_projects(items):
    """Tentýž projekt/akvizice se ve feedu objeví jen JEDNOU. Dvě položky
    se shodnou částkou splývají, jsou-li: a) z téhož jednání (např. kupní smlouva +
    smlouva o úschově), b) z různých zdrojů (RO vyhodnocení ↔ ZO schválení) v okně
    90 dnů, nebo c) velká specifická částka ≥ 4 mil (tatáž stavba/nemovitost napříč
    časem). Ponechá se nejvýstižnější záznam (_score). Různé projekty s náhodně
    shodnou menší částkou z různých jednání zůstanou oba.
    Formát položky: [datum_iso, castka, zdroj RO/ZO, cislo_zasedani, text, url, ...]
    (indexy 0–5 jsou povinné, další sloupce se zachovají)."""
    kept = []
    for it in sorted(items, key=lambda x: x[0]):
        idx = None
        for i, k in enumerate(kept):
            if k[1] != it[1]:                          # různá částka = různá akce
                continue
            same_meeting = (k[2] == it[2] and k[3] == it[3])
            d1, d2 = _date(k[0]), _date(it[0])
            close = bool(d1 and d2 and abs((d1 - d2).days) <= 90)
            share_parcel = bool(_parcels(k[4]) & _parcels(it[4]))
            if same_meeting or (k[2] != it[2] and close) or share_parcel or it[1] >= 4_000_000:
                idx = i
                break
        if idx is None:
            kept.append(it)
        elif _score(it) > _score(kept[idx]):
            kept[idx] = it
    return kept
