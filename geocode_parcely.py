# -*- coding: utf-8 -*-
"""Jednorazove geokoduje parcelni cisla ze zapisu RO na souradnice (definicni
bod parcely) pres bezplatnou INSPIRE WFS sluzbu CUZK (bez autentizace) a ulozi
cache do data/parcely_geo.json. Vsechny parcely jsou v k.u. Strelice u Brna
(kod 757438). build_zapisy.py pak z cache udela prokliky do katastralni mapy.

Spoustet jen obcas (kdyz pribydou nove zapisy) — vyzaduje sit."""
import json, re, os, time
import urllib.parse, urllib.request

ROOT = r"C:\Users\brener\SandboxVS\rozpocet"
KU_CODE = "757438"            # k.u. Strelice u Brna
WFS = "https://services.cuzk.cz/wfs/inspire-cp-wfs.asp"
OUT = os.path.join(ROOT, "data", "parcely_geo.json")
CHUNK = 7   # vic literalu prekroci limit delky URL (query stringu) na serveru IIS

PARC = re.compile(r"(?:p(?:arc)?\.?\s*č\.?|parcel\w*\s*č\.?)\s*(\d{1,5}(?:/\d{1,4})?)", re.IGNORECASE)

# parcely z obou datasetu (rada + zastupitelstvo)
all_p = set()
for ds in ("dataset_RO.json", "dataset_ZO.json"):
    pth = os.path.join(ROOT, ds)
    if os.path.exists(pth):
        d = json.load(open(pth, encoding="utf-8"))
        for r in d:
            for b in r["body"]:
                all_p.update(PARC.findall(b["text"]))

# inkrementalne: preskocit uz nacachovane
geo = json.load(open(OUT, encoding="utf-8")) if os.path.exists(OUT) else {}
parcels = sorted(all_p - set(geo))
print(f"Parcel celkem: {len(all_p)} | v cache: {len(geo)} | k dohledani: {len(parcels)}")


def build_filter(refs):
    inner = "".join(
        "<fes:PropertyIsEqualTo><fes:ValueReference>nationalCadastralReference"
        f"</fes:ValueReference><fes:Literal>{r}</fes:Literal></fes:PropertyIsEqualTo>"
        for r in refs)
    body = inner if len(refs) == 1 else f"<fes:Or>{inner}</fes:Or>"
    return f'<fes:Filter xmlns:fes="http://www.opengis.net/fes/2.0">{body}</fes:Filter>'


def fetch(refs):
    # dvojtecky v typeNames/srsName nechat doslovne (server jinak vraci 404),
    # zakodovat jen hodnotu filtru
    flt = urllib.parse.quote(build_filter(refs), safe="")
    url = (f"{WFS}?service=WFS&version=2.0.0&request=GetFeature"
           f"&typeNames=cp:CadastralParcel&srsName=urn:ogc:def:crs:EPSG::4326"
           f"&count={len(refs) + 5}&filter={flt}")
    req = urllib.request.Request(url, headers={"User-Agent": "strelice-portal/1.0"})
    with urllib.request.urlopen(req, timeout=90) as resp:
        return resp.read().decode("utf-8", errors="replace")


def parse(xml):
    out = {}
    for blk in re.split(r"<cp:CadastralParcel\b", xml)[1:]:
        lab = re.search(r"<cp:label>([^<]+)</cp:label>", blk)
        pos = re.search(r"<gml:pos>\s*([\d.]+)\s+([\d.]+)\s*</gml:pos>", blk)
        if lab and pos:
            out[lab.group(1).strip()] = [round(float(pos.group(1)), 6),
                                         round(float(pos.group(2)), 6)]
    return out


for i in range(0, len(parcels), CHUNK):   # geo uz predplnene z cache (inkrementalne)
    chunk = parcels[i:i + CHUNK]
    refs = [f"{KU_CODE}-{p}" for p in chunk]
    try:
        got = parse(fetch(refs))
        geo.update(got)
        print(f"  chunk {i//CHUNK+1}: dotaz {len(chunk)} -> nalezeno {len(got)}")
    except Exception as e:
        print(f"  chunk {i//CHUNK+1}: CHYBA {e}")
    time.sleep(0.3)

os.makedirs(os.path.dirname(OUT), exist_ok=True)
json.dump(geo, open(OUT, "w", encoding="utf-8"), ensure_ascii=False,
          separators=(",", ":"), sort_keys=True)
miss = [p for p in parcels if p not in geo]
print(f"\nCache celkem: {len(geo)} | nove nenalezeno: {len(miss)}")
print("Nenalezene (prvnich 30):", miss[:30])
print("Ulozeno:", OUT)
