# -*- coding: utf-8 -*-
"""Extrakce + parsing usneseni Zastupitelstva obce Strelice (ZO) do datasetu.
Tri formaty: A) odrazky + hlasovani, B) cislovany seznam (ustavujici),
C) rozbity OCR (best-effort). Vyuziva temata.py + vydaje.py. Navic zachycuje
vysledek hlasovani (pro/proti/zdrzel) a pocet pritomnych."""
import subprocess, os, shutil, re, json, csv, html as htmllib
from urllib.parse import unquote
import temata, vydaje

ROOT = r"C:\Users\brener\SandboxVS\rozpocet"
PDF_DIR = os.path.join(ROOT, "zastupitelstvo_ZO")
WORK = os.path.join(ROOT, "_work")
TXT_DIR = os.path.join(ROOT, "txt_zo")
HTML_PAGE = os.path.join(ROOT, "_zo_page.html")
os.makedirs(WORK, exist_ok=True)
os.makedirs(TXT_DIR, exist_ok=True)
BASE_URL = "https://www.streliceubrna.cz"

# mapovani nazev -> url
url_by_basename = {}
if os.path.exists(HTML_PAGE):
    page = open(HTML_PAGE, encoding="utf-8", errors="replace").read()
    for rel in re.findall(r'href="([^"]*documents[^"]*\.pdf)"', page):
        rel = htmllib.unescape(rel)
        safe = re.sub(r'[\\/:*?"<>|]', "_", unquote(rel.split("/")[-1]))
        url_by_basename[safe] = BASE_URL + rel

BULLET_CHARS = "".join(chr(c) for c in list(range(0xE000, 0xF900)) +
                       [0x2022, 0x25CF, 0x25AA, 0x2023, 0x2043, 0x00B7, 0x25E6])
BULLET_RE = re.compile("[" + re.escape(BULLET_CHARS) + "]")
VOTE_START = re.compile(r"Pro\s*[–\-:]?\s*\d|Hlasování\b", re.IGNORECASE)
NUM_HDR = re.compile(r"(?:Výpis\s+usnesení\s+z[e]?|Usnesení\s+z)\s+(\d+)\.\s*"
                     r"(?:ustavujícího\s+)?(?:zasedání|Zastupitelstva)", re.IGNORECASE)
NUM_FILE = re.compile(r"(?:_|č\.?\s*)0*(\d+)[_ ]?ZO|ZO[_ ]?č\.?\s*0*(\d+)|Usnesení_?\s*0*(\d+)_ZO", re.IGNORECASE)
DATE_NUM = re.compile(r"dne\s+(\d{1,2})\.\s*(\d{1,2})\.\s*(\d{4})")
DATE_FILE = re.compile(r"(20\d{2})(\d{2})(\d{2})|_(\d{1,2})_(\d{1,2})_(20\d{2})")
MONTHS = {"ledna":1,"února":2,"března":3,"dubna":4,"května":5,"června":6,"července":7,
          "srpna":8,"září":9,"října":10,"listopadu":11,"prosince":12}
DATE_TXT = re.compile(r"dne\s+(\d{1,2})\.\s*([a-zěščřžýáíéúůóňťď]+)\s+(\d{4})", re.IGNORECASE)
# tolerantni: "Zastupitelstvo [obce Strelice/Strelice] <sloveso>" (i preklep Střelíce, slovo mezi)
SPLIT_ZAST = re.compile(r"(?=Zastupitelstvo\s+(?:obce\s+\S+\s+|obce\s+)?"
                        r"(?:schvál|schvaluje|neschvál|vzal|bere|zvolil|volí|pověřil|pověřuje|"
                        r"uložil|ukládá|rozhodl|souhlas|nesouhlas|stanov|vydal|vydáv|projedn|ověřil|konstatoval))")
NUMBERED = re.compile(r"(?ms)^\s*\d+\s*/\s+(.+?)(?=^\s*\d+\s*/\s|\Z)")
FOOTER = re.compile(r"Zaps(al|ala|áno)|Ověřovatel|Vyvěšeno|starosta obce\s*$", re.IGNORECASE)


def extract_text(src):
    tmp_pdf = os.path.join(WORK, "tmp.pdf"); tmp_txt = os.path.join(WORK, "tmp.txt")
    shutil.copyfile(src, tmp_pdf)
    subprocess.run(["pdftotext", "-enc", "UTF-8", tmp_pdf, tmp_txt], capture_output=True, check=True)
    txt = open(tmp_txt, encoding="utf-8", errors="replace").read()
    txt = txt.replace("Střelí", "Střeli")    # font glitch: Střelíce -> Střelice
    return vydaje.fix_ocr_digits(txt)         # OCR 'l' -> '1' v cislech (i v zobrazeni)


# ZO č. 27 (20260429) ma rozbity font v PDF (ztratovy cmap) -> cilene opravy
# zjevne zkomolenych slov; aplikuji se JEN na tento jeden soubor.
_ZO27_FIX = [
    (r"silničmch", "silničních"), (r"obmbmků", "obrubníků"),
    (r"sihiice", "silnice"), (r"111/3945", "III/3945"), (r"\bstavebm\b", "stavební"),
    (r"výměra l m2", "výměra 1 m2"), (r"\bod l\. ", "od 1. "),
    (r"pověhye", "pověřuje"), (r"poskytovám", "poskytování"),
    (r"navýšem", "navýšení"), (r"chodmkem", "chodníkem"),
    (r"kontrolmho", "kontrolního"), (r"\bvýbom\b", "výboru"),
    (r"Stábuho", "Státního"), (r"životaího", "životního"),
    (r"\bzjednání\b", "z jednání"), (r"\bJiň\b", "Jiří"),
    (r"na vědem ZS\b", "na vedení ZŠ"), (r"\búl\.", "ul."),
    (r"\bIC (\d)", r"IČ \1"), (r"\bást\b", "část"),
    (r"\bp č\.", "p. č."), (r"k\. u\. ", "k. ú. "),
    # silne zkomolena veta v bodu 14:
    (r"V ří adě", "V případě"), (r'nedo"de', "nedojde"),
    (r"k oklesu", "k poklesu"), (r"rumem'ch cen n dle", "průměrných cen dle"),
]


def fix_zo27(text):
    for pat, rep in _ZO27_FIX:
        text = re.sub(pat, rep, text)
    return text


def norm(s):
    s = s.replace("­", "")
    s = re.sub(r"\s+", " ", s)
    return s.strip(" \t\n\r-–•·")


def druh(text):
    f = temata.fold(text)
    if "neschval" in f: return "neschvaluje"
    # "bere/vzal na vedomi ... ktere schvalila rada" -> bere na vedomi (PRED 'schval'!)
    if ("bere" in f and "vedom" in f) or ("vzal" in f and "vedom" in f): return "bere na vědomí"
    if "schval" in f: return "schvaluje"
    if "nesouhlas" in f: return "nesouhlasí"
    if "souhlas" in f: return "souhlasí"
    if "poveril" in f or "poveruje" in f: return "pověřuje"
    if "ulozil" in f or "uklada" in f: return "ukládá"
    if "zvolil" in f or "voli " in f or "zvoleni" in f: return "volí"
    if "rozhodl" in f: return "rozhodlo"
    if "stanov" in f or "vydal" in f or "vydav" in f: return "stanovuje"
    if "projedn" in f: return "projednalo"
    return "ostatní"


def cut_vote(seg):
    m = VOTE_START.search(seg)
    if m:
        return seg[:m.start()], seg[m.start():]
    return seg, ""


def parse_vote(tail):
    p = re.search(r"Pro\s*[–\-:]?\s*(\d+)", tail, re.IGNORECASE)
    if not p:
        return None
    a = re.search(r"Proti\s*[–\-:]?\s*(\d+)", tail, re.IGNORECASE)
    z = re.search(r"Zdržel\s+se\s*[–\-:]?\s*(\d+)", tail, re.IGNORECASE)
    pro = int(p.group(1)); proti = int(a.group(1)) if a else 0; zdr = int(z.group(1)) if z else 0
    # sanity: zastupitelstvo ma 15 clenu; nesmyslne hodnoty (rozbity OCR) zahodit
    if pro > 15 or proti > 15 or zdr > 15 or (pro + proti + zdr) > 16:
        return None
    return [pro, int(a.group(1)) if a else None, int(z.group(1)) if z else None]


def segments(text):
    """Vrati seznam (usneseni_text, hlasovaci_tail)."""
    b = BULLET_RE.split(text)
    if len([x for x in b if x.strip()]) >= 5:
        segs = b[1:]                                   # zahodit hlavicku pred 1. odrazkou
    else:
        num = NUMBERED.findall(text)
        if len(num) >= 4:
            segs = num
        else:
            segs = SPLIT_ZAST.split(text)[1:]          # fallback dle "Zastupitelstvo <sloveso>"
    out = []
    for seg in segs:
        usn, tail = cut_vote(seg)
        usn = norm(usn)
        if len(usn) < 10 or FOOTER.match(usn):
            continue
        out.append((usn, tail))
    return out


def parse(fname, text):
    warns = []
    m = NUM_HDR.search(text)
    number = int(m.group(1)) if m else None
    if number is None:
        mf = NUM_FILE.search(fname)
        if mf:
            number = int(next(g for g in mf.groups() if g))
            warns.append("cislo z nazvu")
        else:
            warns.append("CISLO?")
    # datum — hledat jen v hlavicce (jinak chytne interni datum v textu)
    head = text[:220]
    di, dt = None, None
    dm = DATE_NUM.search(head)
    if dm:
        d, mo, y = map(int, dm.groups()); dt = f"{d}. {mo}. {y}"; di = f"{y:04d}-{mo:02d}-{d:02d}"
    else:
        dx = DATE_TXT.search(head)
        if dx and dx.group(2).lower() in MONTHS:
            d = int(dx.group(1)); mo = MONTHS[dx.group(2).lower()]; y = int(dx.group(3))
            dt = f"{d}. {mo}. {y}"; di = f"{y:04d}-{mo:02d}-{d:02d}"
        else:
            df = DATE_FILE.search(fname)
            if df:
                g = df.groups()
                if g[0]: di = f"{g[0]}-{g[1]}-{g[2]}"
                else: di = f"{g[5]}-{int(g[4]):02d}-{int(g[3]):02d}"
                dt = di; warns.append("datum z nazvu")
            else:
                warns.append("DATUM?")
    rok = int(di[:4]) if di else None
    pr = re.search(r"Přítomn[oi]\s*:?\s*(\d+)", text)
    pritomno = int(pr.group(1)) if pr else None

    body = []
    for usn, tail in segments(text):
        body.append({
            "kategorie": druh(usn),
            "tema": temata.classify(usn),
            "castka": vydaje.extract_amount(usn),
            "vydaj": vydaje.bucket(vydaje.extract_amount(usn)),
            "hlasovani": parse_vote(tail),
            "text": usn,
        })
    if not body:
        warns.append("ZADNE BODY")
    return {
        "soubor": fname, "url": url_by_basename.get(fname),
        "cislo_zasedani": number, "datum": di, "datum_text": dt, "rok": rok,
        "pritomno": pritomno, "pocet_bodu": len(body), "body": body,
        "raw_text": text.strip(),
    }, warns


def main():
    pdfs = sorted(f for f in os.listdir(PDF_DIR) if f.lower().endswith(".pdf"))
    meetings, diag = [], []
    for f in pdfs:
        text = extract_text(os.path.join(PDF_DIR, f))
        if "20260429" in f:               # ZO 27 — rozbity font, cilene opravy
            text = fix_zo27(text)
        rec, warns = parse(f, text)
        safe = re.sub(r'[\\/:*?"<>|]', "_", os.path.splitext(f)[0]) + ".txt"
        open(os.path.join(TXT_DIR, safe), "w", encoding="utf-8").write(text)
        meetings.append(rec)
        diag.append((rec["cislo_zasedani"], rec["datum"], rec["pocet_bodu"], "; ".join(warns), f))
    meetings.sort(key=lambda r: (r["cislo_zasedani"] is None, r["cislo_zasedani"] or 0))

    json.dump(meetings, open(os.path.join(ROOT, "dataset_ZO.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)

    def safe_csv(path, header, rows):
        try:
            with open(os.path.join(ROOT, path), "w", encoding="utf-8-sig", newline="") as ch:
                w = csv.writer(ch, delimiter=";"); w.writerow(header); w.writerows(rows)
        except PermissionError:
            print(f"  ! {path} zamceny, preskakuji")

    safe_csv("dataset_ZO_body.csv",
             ["cislo_zasedani","datum","rok","kategorie","tema","castka","vydaj","pro","proti","zdrzel","text","soubor","url"],
             [[r["cislo_zasedani"], r["datum"], r["rok"], b["kategorie"], b["tema"],
               b["castka"] if b["castka"] is not None else "", b["vydaj"],
               (b["hlasovani"] or ["","",""])[0], (b["hlasovani"] or ["","",""])[1], (b["hlasovani"] or ["","",""])[2],
               b["text"], r["soubor"], r["url"] or ""]
              for r in meetings for b in r["body"]])

    # diag
    diag.sort(key=lambda x: (x[0] is None, x[0] or 0))
    ti = sum(r["pocet_bodu"] for r in meetings)
    nums = [r["cislo_zasedani"] for r in meetings if r["cislo_zasedani"]]
    with open(os.path.join(ROOT, "_zo_diag.txt"), "w", encoding="utf-8") as dh:
        dh.write(f"Souboru: {len(meetings)} | bodu: {ti}\n")
        dh.write(f"Cisla: {min(nums)}..{max(nums)} | chybi: {sorted(set(range(min(nums),max(nums)+1))-set(nums))}\n\n")
        cats = {}
        for r in meetings:
            for b in r["body"]: cats[b["kategorie"]] = cats.get(b["kategorie"],0)+1
        dh.write("DRUH: " + ", ".join(f"{k}={v}" for k,v in sorted(cats.items(),key=lambda x:-x[1])) + "\n\n")
        for c, dt, n, wr, f in diag:
            flag = "  <<<" if (wr or n == 0) else ""
            dh.write(f"  ZO {str(c):>3} | {str(dt):>10} | {n:>3} bodu | {wr}{flag}\n")
    print("OK", len(meetings), "souboru,", ti, "bodu")


if __name__ == "__main__":
    main()
