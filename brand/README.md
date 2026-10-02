# Značka „jak se máme"

Vše generuje `python brand/build_brand.py` (potřebuje `pip install fonttools uharfbuzz pillow`
a písmo Bricolage Grotesque v `brand/_src/BricolageGrotesque.ttf`, OFL, z github.com/google/fonts).
Nápis je převedený na křivky, SVG nezávisí na nainstalovaném písmu. Novou obec přidej do `OBCE`
(název v 5. pádě: Střelice, Ostopovice, ale Tišnove, Kuřime). Přehled všech souborů: `brand/preview.html`.

## Logo (`logo/`)
| soubor | použití |
|---|---|
| `jaksemame-logo.svg` / `-inverse` | hlavní logo na světlém / tmavém podkladu |
| `jaksemame-logo-mono-black` / `-mono-white` | jednobarevný tisk, razítka, výšivky |
| `jaksemame-symbol*.svg` | samotný symbol (avatar, malé plochy) |
| `jaksemame-wordmark.svg` | jen nápis |
| `<obec>-logo.svg` / `-inverse` | „jak se máme, Střelice?" – hlavička obecního webu |
| `<obec>-logo-stacked.svg` / `-inverse` | dvouřádková varianta pro mobil a čtvercové formáty |

Ochranná zóna: kolem loga volné místo aspoň výšky sloupců symbolu. Minimální velikost symbolu 16 px
(pod 24 px používej `favicon-16.png`, je ručně kreslený po pixelech).

## Favikony (`favicon/`) – nahrát do kořene webu
```html
<link rel="icon" href="/favicon.ico" sizes="48x48">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<link rel="manifest" href="/site.webmanifest">
<meta name="theme-color" content="#142F3A">
```
`favicon.svg` se sám přepne na světlou verzi, když má prohlížeč tmavý režim.

## Barvy
Inkoust `#142F3A` · Petrolej `#1D6B73` · Jantar `#EFA42A` · Papír `#F2F5F4`
Tmavý režim: text `#E4EEEC` · obec `#8FD0D4` · jantar `#F4B547` · pozadí `#0D191E`
