# -*- coding: utf-8 -*-
"""Export dat portálu do SQLite pro MCP server jaksemame.cz/mcp (formát v1).

Každá obec si svým `build_mcp.py` vyrobí `mcp/<obec>.sqlite` se stejnými tabulkami;
server je čte jen pro čtení. Co obec nemá (třeba zápisy rady), zůstane prázdné.
Tento soubor je společný: Ostopovice mají jeho kopii, při změně ho zkopíruj.

Hledání: sloupec `norm` je text malými písmeny bez diakritiky a interpunkce, znak po znaku
stejně dlouhý jako `text` (s mezerou na začátku), takže pozice nálezu v `norm` ukazuje
i do původního textu — server podle ní vyřízne úryvek. U akcí, zakázek a dotací je v `norm`
navíc název/dodavatel/příjemce, tam slouží jen k hledání."""
import json
import os
import re
import sqlite3
import unicodedata
from datetime import date

SCHEMA_VERSION = 1

SCHEMA = """
CREATE TABLE meta (klic TEXT PRIMARY KEY, hodnota TEXT NOT NULL);
-- jedno zasedání zastupitelstva (ZO) nebo rady (RO); id např. „ZO-29“ nebo „ZO-2026-2“
CREATE TABLE jednani (
  id TEXT PRIMARY KEY, organ TEXT NOT NULL, cislo INTEGER, rok INTEGER, datum TEXT,
  nazev TEXT, url_pdf TEXT, video TEXT, shrnuti TEXT, pritomno INTEGER, omluveni TEXT,
  pocet_usneseni INTEGER, pocet_replik INTEGER NOT NULL DEFAULT 0);
CREATE TABLE usneseni (
  id INTEGER PRIMARY KEY, jednani_id TEXT NOT NULL, poradi INTEGER NOT NULL, oznaceni TEXT,
  kategorie TEXT, tema TEXT, castka REAL, pro INTEGER, proti INTEGER, zdrzel INTEGER,
  text TEXT NOT NULL, norm TEXT NOT NULL);
CREATE INDEX usneseni_jednani ON usneseni (jednani_id);
-- jmenovité hlasování (jen kde ho zápis uvádí); hlas = pro | proti | zdrzel | nehlasoval
CREATE TABLE hlasy (usneseni_id INTEGER NOT NULL, osoba TEXT NOT NULL, hlas TEXT NOT NULL);
CREATE INDEX hlasy_usneseni ON hlasy (usneseni_id);
-- zastupitelé; klic = krátké jméno z výpisů hlasování
CREATE TABLE osoby (klic TEXT PRIMARY KEY, jmeno TEXT NOT NULL, funkce TEXT, od_zasedani INTEGER, do_zasedani INTEGER);
-- repliky z přepisů videí; role s = předsedající, z = zastupitel, o = veřejnost (anonymně), k = návrhová komise
CREATE TABLE promluvy (
  id INTEGER PRIMARY KEY, jednani_id TEXT NOT NULL, bod INTEGER, bod_nazev TEXT, poradi INTEGER NOT NULL,
  mluvci TEXT NOT NULL, role TEXT, osoba TEXT, cas INTEGER, text TEXT NOT NULL, norm TEXT NOT NULL);
CREATE INDEX promluvy_jednani ON promluvy (jednani_id, bod);
-- rozpočet; granularita: polozka (plný výkaz) | druh | oblast (souhrny, kde detail není)
CREATE TABLE rozpocet (
  rok INTEGER NOT NULL, obdobi TEXT, granularita TEXT NOT NULL, strana TEXT NOT NULL,
  druh TEXT, oblast TEXT, paragraf TEXT, paragraf_nazev TEXT, polozka TEXT, polozka_nazev TEXT,
  schvaleny REAL, upraveny REAL, skutecnost REAL);
CREATE TABLE kapitalove (rok INTEGER PRIMARY KEY, kapitalove REAL, vydaje REAL);
-- konkrétní investiční akce (z usnesení nebo z profilu zadavatele)
CREATE TABLE akce (
  id INTEGER PRIMARY KEY, datum TEXT, rok INTEGER, castka REAL, organ TEXT, jednani_id TEXT,
  nazev TEXT, text TEXT NOT NULL, skupina TEXT, zhotovitel TEXT, url TEXT, zdroj TEXT, norm TEXT NOT NULL);
CREATE TABLE zakazky (
  id INTEGER PRIMARY KEY, datum TEXT, rok INTEGER, dodavatel TEXT, castka REAL, organ TEXT,
  jednani_id TEXT, text TEXT NOT NULL, dodatek INTEGER NOT NULL DEFAULT 0, url TEXT, norm TEXT NOT NULL);
-- výběrová řízení z profilu zadavatele; stav = zadáno | zrušeno | probíhá | bez výsledku;
-- postup = druh řízení (přímé zadání, zakázka malého rozsahu, otevřené řízení…);
-- cena = smluvní (nebo nabídka vybrané firmy), vše bez DPH
CREATE TABLE vyberova_rizeni (
  id TEXT PRIMARY KEY, datum TEXT, rok INTEGER, nazev TEXT NOT NULL, druh TEXT, postup TEXT, stav TEXT,
  predpokladana_hodnota REAL, lhuta TEXT, dodavatel TEXT, dodavatel_ico TEXT, cena REAL,
  pocet_nabidek INTEGER NOT NULL DEFAULT 0, url TEXT, norm TEXT NOT NULL);
-- podané nabídky; cena bez DPH; vybrana = 1 u vítěze, vyloucen = 1 u vyloučené / stažené nabídky
CREATE TABLE nabidky (
  rizeni_id TEXT NOT NULL, firma TEXT NOT NULL, ico TEXT, cena REAL,
  vybrana INTEGER NOT NULL DEFAULT 0, vyloucen INTEGER NOT NULL DEFAULT 0, norm TEXT NOT NULL);
CREATE INDEX nabidky_rizeni ON nabidky (rizeni_id);
CREATE TABLE dotace (
  id INTEGER PRIMARY KEY, rok INTEGER, prijemce TEXT NOT NULL, castka REAL, ucel TEXT, url TEXT, norm TEXT NOT NULL);
"""


def _fold_char(c):
    if not c.isalnum():  # i interpunkce na mezeru, aby „(Bartoňová“ našla hledaná „bart…“ od začátku slova
        return " "
    d = unicodedata.normalize("NFD", c)[0].lower()
    return d if len(d) == 1 else "?"


def norm(text):
    """Text pro hledání: malá písmena bez diakritiky, stejná délka jako `text` + úvodní mezera."""
    return " " + "".join(_fold_char(c) for c in text)


def clean(text):
    """Bílé znaky na jednu mezeru (norm pak sedí znak po znaku) a pryč odrážky ze Symbol fontu."""
    return re.sub(r"\s+", " ", (text or "").replace("", "•")).strip()


def num(v):
    if v in (None, "", "None"):
        return None
    try:
        return float(str(v).replace(",", "."))
    except ValueError:
        return None


class Export:
    def __init__(self, path, obec, nazev, web, **meta):
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        self.path = path
        self.tmp = path + ".tmp"
        if os.path.exists(self.tmp):
            os.remove(self.tmp)
        self.db = sqlite3.connect(self.tmp)
        self.db.executescript(SCHEMA)
        self.meta = {"schema": SCHEMA_VERSION, "obec": obec, "nazev": nazev, "web": web,
                     "aktualizovano": date.today().isoformat(), **meta}

    def jednani(self, id, organ, **k):
        cols = ["id", "organ"] + list(k)
        self.db.execute(f"INSERT INTO jednani ({','.join(cols)}) VALUES ({','.join('?' * len(cols))})",
                        [id, organ] + [json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict)) else v
                                       for v in k.values()])

    def usneseni(self, jednani_id, poradi, text, hlasy=None, **k):
        text = clean(text)
        cols = ["jednani_id", "poradi", "text", "norm"] + list(k)
        cur = self.db.execute(f"INSERT INTO usneseni ({','.join(cols)}) VALUES ({','.join('?' * len(cols))})",
                              [jednani_id, poradi, text, norm(text)] + list(k.values()))
        for osoba, hlas in (hlasy or {}).items():
            self.db.execute("INSERT INTO hlasy VALUES (?,?,?)", (cur.lastrowid, osoba, hlas))
        return cur.lastrowid

    def osoba(self, klic, jmeno, funkce="", od=None, do=None):
        self.db.execute("INSERT INTO osoby VALUES (?,?,?,?,?)", (klic, jmeno, funkce, od, do))

    def promluva(self, jednani_id, poradi, mluvci, text, **k):
        text = clean(text)
        cols = ["jednani_id", "poradi", "mluvci", "text", "norm"] + list(k)
        self.db.execute(f"INSERT INTO promluvy ({','.join(cols)}) VALUES ({','.join('?' * len(cols))})",
                        [jednani_id, poradi, mluvci, text, norm(text)] + list(k.values()))

    def rozpocet(self, **k):
        self.db.execute(f"INSERT INTO rozpocet ({','.join(k)}) VALUES ({','.join('?' * len(k))})", list(k.values()))

    def kapitalove(self, rok, kapitalove, vydaje):
        self.db.execute("INSERT INTO kapitalove VALUES (?,?,?)", (rok, kapitalove, vydaje))

    def _row(self, table, text, extra_norm="", **k):
        text = clean(text)
        cols = ["text", "norm"] + list(k)
        self.db.execute(f"INSERT INTO {table} ({','.join(cols)}) VALUES ({','.join('?' * len(cols))})",
                        [text, norm(clean(extra_norm + " " + text) if extra_norm else text)] + list(k.values()))

    def akce(self, text, **k):
        self._row("akce", text, k.get("nazev") or "", **k)

    def zakazka(self, text, **k):
        self._row("zakazky", text, k.get("dodavatel") or "", **k)

    def rizeni(self, id, nazev, nabidky=(), **k):
        """Výběrové řízení; nabidky = [{firma, ico, cena, vybrana, vyloucen}]."""
        nazev = clean(nazev)
        # „výjimka“ = zakázka malého rozsahu mimo zákon o zadávání (tak ji uvádí i detail na profilu)
        k["postup"] = {"výjimka": "zakázka malého rozsahu"}.get(k.get("postup") or "", k.get("postup") or None)
        nabidky = [n for n in nabidky if n.get("firma")]
        firmy = " ".join(n["firma"] for n in nabidky)
        cols = ["id", "nazev", "pocet_nabidek", "norm"] + list(k)
        self.db.execute(f"INSERT INTO vyberova_rizeni ({','.join(cols)}) VALUES ({','.join('?' * len(cols))})",
                        [id, nazev, len(nabidky), norm(clean(nazev + " " + firmy))] + list(k.values()))
        for n in nabidky:
            self.db.execute("INSERT INTO nabidky VALUES (?,?,?,?,?,?,?)",
                            (id, n["firma"], n.get("ico") or None, n.get("cena"),
                             1 if n.get("vybrana") else 0, 1 if n.get("vyloucen") else 0, norm(clean(n["firma"]))))

    def dotace(self, prijemce, ucel, **k):
        ucel = clean(ucel)
        self.db.execute(f"INSERT INTO dotace (prijemce, ucel, norm{''.join(',' + c for c in k)}) "
                        f"VALUES (?,?,?{',?' * len(k)})",
                        [prijemce, ucel, norm(clean(prijemce + " " + ucel))] + list(k.values()))

    def close(self):
        for t in ("jednani", "usneseni", "promluvy", "rozpocet", "akce", "zakazky", "vyberova_rizeni", "dotace"):
            self.meta["pocet_" + t] = self.db.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        self.db.executemany("INSERT INTO meta VALUES (?,?)",
                            [(k, json.dumps(v, ensure_ascii=False) if not isinstance(v, str) else v)
                             for k, v in self.meta.items()])
        self.db.execute("UPDATE jednani SET pocet_replik = (SELECT COUNT(*) FROM promluvy p WHERE p.jednani_id = jednani.id)")
        self.db.commit()
        self.db.execute("VACUUM")
        self.db.close()
        os.replace(self.tmp, self.path)
        return self.meta
