# -*- coding: utf-8 -*-
"""Extrakce + parsing zapisu Rady obce Strelice do jednotneho datasetu."""
import subprocess, os, shutil, re, json, csv, html as htmllib
from urllib.parse import unquote
import temata  # tematicka klasifikace bodu
import vydaje  # extrakce vyse vydaje + velikostni pasmo

ROOT = r"C:\Users\brener\SandboxVS\rozpocet"
PDF_DIR = os.path.join(ROOT, "zapisy_RO")
WORK = os.path.join(ROOT, "_work")
TXT_DIR = os.path.join(ROOT, "txt")
HTML_PAGE = os.path.join(ROOT, "_zapisy_page.html")
os.makedirs(WORK, exist_ok=True)
os.makedirs(TXT_DIR, exist_ok=True)

BASE_URL = "https://www.streliceubrna.cz"

# --- mapovani lokalni nazev souboru -> plne URL (z ulozeneho HTML) ---
url_by_basename = {}
if os.path.exists(HTML_PAGE):
    page = open(HTML_PAGE, encoding="utf-8", errors="replace").read()
    for rel in re.findall(r'href="([^"]*documents[^"]*\.pdf)"', page):
        rel = htmllib.unescape(rel)
        base = unquote(rel.split("/")[-1])
        safe = re.sub(r'[\\/:*?"<>|]', "_", base)
        url_by_basename[safe] = BASE_URL + rel

# --- bullet detekce ---
# Skutecna odrazka v PDF je znak U+F0B7 (PUA glyf z fontu Symbol/Wingdings).
# Mnozinu odrazek stavime pres chr()+hex (cisty ASCII zdroj, nic se nerozbije):
#  - cely PUA rozsah 0xE000..0xF8FF (sem patri 0xF0B7)
#  - + bezne odrazkove glyfy. POMLCKA (0x2D) zamerne NENI v mnozine.
_BULLET_CODES = list(range(0xE000, 0xF900)) + [
    0x2022, 0x25AA, 0x25CF, 0x25E6, 0x2023, 0x2043, 0x2219, 0x00B7,
    0x2027, 0x25A0, 0x25CB, 0x2043, 0x204C, 0x204D, 0x2756,
]
BULLET_CHARS = "".join(chr(c) for c in _BULLET_CODES)
BULLET_RE = re.compile("[" + re.escape(BULLET_CHARS) + "]")

SECTION_RE = re.compile(r"^\s*(Rada obce [^\n:]{1,60}):\s*$", re.MULTILINE)
FOOTER_RE = re.compile(r"Rada obce Střelice se ve všech bodech|Členové rady obce Střelice|Zpracoval\s*:", re.IGNORECASE)
NUM_RE = re.compile(r"Zápis\s+z(?:e)?\s+(\d+)\.\s*zasedán", re.IGNORECASE)
NUM_FILE_RE = re.compile(r"č\.?\s*0*(\d+)", re.IGNORECASE)
DATE_RE = re.compile(r"(\d{1,2})\.\s*(\d{1,2})\.\s*(\d{4})")
DATE_FILE_RE = re.compile(r"(20\d{2})(\d{2})(\d{2})")


def extract_text(src):
    tmp_pdf = os.path.join(WORK, "tmp.pdf")
    tmp_txt = os.path.join(WORK, "tmp.txt")
    shutil.copyfile(src, tmp_pdf)
    subprocess.run(["pdftotext", "-enc", "UTF-8", tmp_pdf, tmp_txt],
                   capture_output=True, check=True)
    txt = open(tmp_txt, encoding="utf-8", errors="replace").read()
    txt = txt.replace("Střelí", "Střeli")    # font glitch: Střelíce -> Střelice
    return vydaje.fix_ocr_digits(txt)         # OCR 'l' -> '1' v cislech (i v zobrazeni)


def norm(s):
    s = s.replace(chr(0x00AD), "")          # soft hyphen
    s = re.sub(r"\s+", " ", s)              # sjednotit bile znaky
    return s.strip(" \t\n\r")


def parse(fname, text):
    warns = []
    # --- cislo zasedani ---
    m = NUM_RE.search(text)
    number = int(m.group(1)) if m else None
    if number is None:
        mf = NUM_FILE_RE.search(fname)
        number = int(mf.group(1)) if mf else None
        warns.append("cislo z nazvu souboru" if number is not None else "CISLO NENALEZENO")

    # --- header region (pred prvni sekci) pro datum ---
    sec_iter = list(SECTION_RE.finditer(text))
    header_region = text[:sec_iter[0].start()] if sec_iter else text[:600]

    # --- datum ---
    datum_iso, datum_text = None, None
    dm = DATE_RE.search(header_region) or DATE_RE.search(text[:800])
    if dm:
        d, mo, y = int(dm.group(1)), int(dm.group(2)), int(dm.group(3))
        datum_text = f"{d}. {mo}. {y}"
        if 1 <= d <= 31 and 1 <= mo <= 12 and 2022 <= y <= 2027:
            datum_iso = f"{y:04d}-{mo:02d}-{d:02d}"
        else:
            warns.append("DATUM PODEZRELE")
    if datum_iso is None:
        df = DATE_FILE_RE.search(fname)
        if df:
            datum_iso = f"{df.group(1)}-{df.group(2)}-{df.group(3)}"
            datum_text = datum_text or datum_iso
            warns.append("datum z nazvu souboru")
        else:
            warns.append("DATUM NENALEZENO")

    rok = int(datum_iso[:4]) if datum_iso else None

    # --- orezat paticku ---
    fm = FOOTER_RE.search(text)
    body_text = text[:fm.start()] if fm else text
    if not fm:
        warns.append("paticka nenalezena")

    # --- sekce + body ---
    secs = list(SECTION_RE.finditer(body_text))
    items = []
    if not secs:
        warns.append("ZADNE SEKCE")
    for i, sm in enumerate(secs):
        kat_full = sm.group(1).strip()
        kat = re.sub(r"^Rada obce\s+", "", kat_full).strip()
        start = sm.end()
        end = secs[i + 1].start() if i + 1 < len(secs) else len(body_text)
        chunk = body_text[start:end]
        parts = [norm(p) for p in BULLET_RE.split(chunk)]
        parts = [p for p in parts if len(p) > 1]
        if not parts:
            parts = [norm(p) for p in re.split(r"\n\s*\n", chunk) if len(norm(p)) > 1]
            if parts:
                warns.append(f"sekce '{kat}' bez odrazek -> deleno odstavci")
        for p in parts:
            amt = vydaje.extract_amount(p)
            items.append({"kategorie": kat, "kategorie_full": kat_full,
                          "tema": temata.classify(p), "castka": amt,
                          "vydaj": vydaje.bucket(amt), "text": p})

    if not items:
        warns.append("ZADNE BODY")

    return {
        "soubor": fname,
        "url": url_by_basename.get(fname),
        "cislo_zasedani": number,
        "datum": datum_iso,
        "datum_text": datum_text,
        "rok": rok,
        "pocet_bodu": len(items),
        "body": items,
        "raw_text": text.strip(),
    }, warns


def main():
    pdfs = sorted([f for f in os.listdir(PDF_DIR) if f.lower().endswith(".pdf")])
    meetings = []
    diag = []
    for f in pdfs:
        text = extract_text(os.path.join(PDF_DIR, f))
        rec, warns = parse(f, text)
        safe_txt = re.sub(r'[\\/:*?"<>|]', "_", os.path.splitext(f)[0]) + ".txt"
        with open(os.path.join(TXT_DIR, safe_txt), "w", encoding="utf-8") as th:
            th.write(text)
        meetings.append(rec)
        cats = sorted(set(b["kategorie"] for b in rec["body"]))
        diag.append((rec["cislo_zasedani"], rec["datum"], rec["pocet_bodu"],
                     ", ".join(cats), "; ".join(warns), f))

    meetings.sort(key=lambda r: (r["cislo_zasedani"] is None, r["cislo_zasedani"] or 0))

    # --- JSON master ---
    with open(os.path.join(ROOT, "dataset_RO.json"), "w", encoding="utf-8") as jh:
        json.dump(meetings, jh, ensure_ascii=False, indent=2)

    def safe_csv(path, header, rows):
        """Zapise CSV; pokud je soubor zamceny (otevreny v Excelu), jen varuje."""
        try:
            with open(os.path.join(ROOT, path), "w", encoding="utf-8-sig", newline="") as ch:
                w = csv.writer(ch, delimiter=";")
                w.writerow(header)
                w.writerows(rows)
        except PermissionError:
            print(f"  ! VAROVANI: {path} je zamceny (otevreny v Excelu?) — preskakuji zapis.")

    # --- CSV tidy (1 radek = 1 bod) ---
    safe_csv("dataset_RO_body.csv",
             ["cislo_zasedani", "datum", "rok", "kategorie", "tema", "castka", "vydaj", "text", "soubor", "url"],
             [[r["cislo_zasedani"], r["datum"], r["rok"], b["kategorie"], b.get("tema", ""),
               b.get("castka", "") if b.get("castka") is not None else "", b.get("vydaj", ""),
               b["text"], r["soubor"], r["url"] or ""]
              for r in meetings for b in r["body"]])

    # --- CSV prehled (1 radek = 1 zasedani) ---
    safe_csv("dataset_RO_zasedani.csv",
             ["cislo_zasedani", "datum", "rok", "pocet_bodu", "soubor", "url"],
             [[r["cislo_zasedani"], r["datum"], r["rok"], r["pocet_bodu"], r["soubor"], r["url"] or ""]
              for r in meetings])

    # --- diagnostika ---
    diag.sort(key=lambda x: (x[0] is None, x[0] or 0))
    total_items = sum(r["pocet_bodu"] for r in meetings)
    all_cats = {}
    for r in meetings:
        for b in r["body"]:
            all_cats[b["kategorie"]] = all_cats.get(b["kategorie"], 0) + 1
    with open(os.path.join(ROOT, "_diag.txt"), "w", encoding="utf-8") as dh:
        dh.write(f"Souboru: {len(meetings)} | celkem bodu: {total_items}\n")
        nums = [r["cislo_zasedani"] for r in meetings if r["cislo_zasedani"] is not None]
        dh.write(f"Rozsah cisel: {min(nums)}..{max(nums)} | unikatnich: {len(set(nums))}\n")
        missing = sorted(set(range(min(nums), max(nums) + 1)) - set(nums))
        dh.write(f"Chybejici cisla v rade: {missing}\n")
        dups = sorted([n for n in set(nums) if nums.count(n) > 1])
        dh.write(f"Duplicitni cisla: {dups}\n\n")
        dh.write("KATEGORIE (cetnost):\n")
        for k, v in sorted(all_cats.items(), key=lambda x: -x[1]):
            dh.write(f"  {v:4d}  {k}\n")
        dh.write("\nPER SOUBOR  [cislo | datum | #bodu | kategorie | VAROVANI]\n")
        for c, dt, n, cats, wr, f in diag:
            flag = "  <<<" if (wr or n == 0) else ""
            dh.write(f"  {str(c):>3} | {str(dt):>10} | {n:>3} | {cats[:55]:<55} | {wr}{flag}\n")
    print("OK", len(meetings), "souboru,", total_items, "bodu")


if __name__ == "__main__":
    main()
