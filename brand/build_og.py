"""Sdílecí obrázky og-image.png (1200×630) pro náhled odkazu — v CI značky „jak se máme".

    python brand/build_og.py

Šablona je HTML se skutečným logem (brand/logo/*-inverse.svg) a písmy z fonts/;
vyfotí ji headless Microsoft Edge. Výstup: og-image.png v kořeni repa každé obce
(Střelice = toto repo, Ostopovice = sousední repo ../ostopovice).
"""
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent          # repo Střelic
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"

# (slug, doména, témata v podtitulu, cílové repo)
OBCE = [
    ("strelice", "strelice.jaksemame.cz",
     "rozpočet · investice · zakázky · dotace · zastupitelstvo · školství", ROOT),
    ("ostopovice", "ostopovice.jaksemame.cz",
     "rozpočet · investice · zakázky · dotace · zastupitelstvo · volby", ROOT.parent / "ostopovice"),
]

TEMPLATE = """<!doctype html><meta charset="utf-8"><style>
{fonts}
html,body{{margin:0;width:1200px;height:630px;overflow:hidden}}
body{{background:#142f3a;color:#e4eeec;font-family:"Atkinson Hyperlegible",sans-serif;position:relative}}
.in{{position:absolute;inset:78px 84px 70px;display:flex;flex-direction:column}}
.logo img{{height:92px;width:auto;display:block}}
h1{{font-family:"Bricolage Grotesque",sans-serif;font-weight:700;font-size:58px;letter-spacing:-.02em;
   margin:62px 0 0;line-height:1.05}}
p{{font-size:29px;color:#a8bec0;margin:18px 0 0}}
.dom{{margin-top:auto;font-family:"Bricolage Grotesque",sans-serif;font-weight:650;font-size:34px;color:#f4b547}}
.bars{{position:absolute;right:84px;bottom:70px;display:flex;align-items:flex-end;gap:16px;opacity:.13}}
.bars i{{width:46px;border-radius:8px;background:#e4eeec}}
</style>
<div class="bars"><i style="height:120px"></i><i style="height:190px"></i><i style="height:290px"></i></div>
<div class="in">
  <div class="logo"><img src="{logo}" alt=""></div>
  <h1>Občanský datový portál</h1>
  <p>{topics}</p>
  <div class="dom">{domain}</div>
</div>"""


def main():
    fonts_css = (ROOT / "fonts" / "fonts.css").read_text(encoding="utf-8")
    fonts_css = fonts_css.replace("url(fonts/", f"url({(ROOT / 'fonts').as_uri()}/")
    with tempfile.TemporaryDirectory() as tmp:
        for slug, domain, topics, repo in OBCE:
            logo = (ROOT / "brand" / "logo" / f"{slug}-logo-inverse.svg").as_uri()
            html = Path(tmp) / f"og_{slug}.html"
            html.write_text(TEMPLATE.format(fonts=fonts_css, logo=logo, topics=topics, domain=domain),
                            encoding="utf-8")
            out = repo / "og-image.png"
            subprocess.run([EDGE, "--headless=new", "--disable-gpu", "--hide-scrollbars",
                            "--allow-file-access-from-files", "--virtual-time-budget=2000",
                            "--window-size=1200,630", f"--screenshot={out}", html.as_uri()],
                           check=True, capture_output=True)
            print(f"HOTOVO: {out}")


if __name__ == "__main__":
    main()
