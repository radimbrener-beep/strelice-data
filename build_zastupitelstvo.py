#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generuje sekci 'Zastupitelstvo' portálu (zastupitelstvo.html) — procházení
usnesení Zastupitelstva obce Střelice 2022–2026. Stejné jako sekce Rada obce:
hledání, filtr roku/tématu/objemu výdaje, témata, částky, prokliky parcel do
katastru. Navíc u každého usnesení VÝSLEDEK HLASOVÁNÍ (pro–proti–zdržel) a
účast na zasedání. Data z dataset_ZO.json, vše inlinované → funguje offline."""
import sys, json, os, re, unicodedata
import portal_common as pc
import temata
import vydaje
sys.stdout.reconfigure(encoding="utf-8")

# --- jmenovité hlasování z výpisu usnesení (raw_text) ---
# Formát: "Pro – 13 (Bartoňová, Brener, …)  Proti – 0  Zdržel se – 1 (Hloušková)"
VOTE_RE = re.compile(
    r'Pro\s*[–-]\s*(\d+)\s*(?:\(([^)]*)\))?\s*'
    r'Proti\s*[–-]\s*(\d+)\s*(?:\(([^)]*)\))?\s*'
    r'Zdržel\s*se\s*[–-]\s*(\d+)\s*(?:\(([^)]*)\))?', re.S)


def _names(s):
    s = re.sub(r'\s+', ' ', (s or '')).strip()
    if not s or 'všichni' in s.lower():
        return []
    return [x.strip() for x in s.split(',') if x.strip()]


def parse_votes(rt):
    """Vrať seznam bloků hlasování z raw_textu: text + počty a jména proti/zdržel."""
    blocks, last = [], 0
    for m in VOTE_RE.finditer(rt or ""):
        text = re.sub(r'\s+', ' ', (rt[last:m.start()])).strip().lstrip('• ').strip()
        last = m.end()
        blocks.append({"text": text, "pro": _names(m.group(2)),
                       "pn": int(m.group(3)), "proti": _names(m.group(4)),
                       "zn": int(m.group(5)), "zdrzel": _names(m.group(6))})
    return blocks


def _fold(s):
    return ''.join(c for c in unicodedata.normalize('NFD', (s or '').lower())
                   if unicodedata.category(c) != 'Mn')


def _vt(s):
    return set(re.findall(r'[a-z0-9]{4,}', _fold(s)))

CHARTJS = open("data/vendor/chart.umd.js", encoding="utf-8").read()
src = json.load(open("dataset_ZO.json", encoding="utf-8"))
GEO_PATH = os.path.join("data", "parcely_geo.json")
parcely_geo = json.load(open(GEO_PATH, encoding="utf-8")) if os.path.exists(GEO_PATH) else {}
# časové kotvy záznamů zasedání (z YouTube titulků) — viz build_video_casy.py
VCAS = json.load(open("video_casy.json", encoding="utf-8")) if os.path.exists("video_casy.json") else {}

cats = []
def ci(c):
    if c not in cats:
        cats.append(c)
    return cats.index(c)

present = {b.get("tema", temata.OSTATNI) for r in src for b in r["body"]}
tlist = [t for t in temata.ORDER if t in present]
ti_index = {t: i for i, t in enumerate(tlist)}

meet = []
# procedurální "pověřuje ... podpisem (smlouvy)" = jen přívažek k předchozímu
# věcnému usnesení; nezobrazujeme jako samostatný řádek, jen jako štítek u rodiče.
SIGN_RE = re.compile(r'pověřuje\b.*\bpodpis', re.I)
for r in sorted(src, key=lambda r: r["cislo_zasedani"]):
    vc = VCAS.get(str(r["cislo_zasedani"]))
    bt = (vc.get("bodytimes") or {}) if vc else {}
    blocks = parse_votes(r.get("raw_text", ""))
    bt_toks = [(_vt(bk["text"]), bk) for bk in blocks]

    def dissent_for(text, hl):
        """Jména proti/zdržel pro nejednomyslné hlasování — blok se shodnými počty a textem."""
        if not hl or ((hl[1] or 0) == 0 and (hl[2] or 0) == 0):
            return None
        it_t = _vt(text)
        best, bestsc = None, -1
        for tk, bk in bt_toks:
            if bk["pn"] == (hl[1] or 0) and bk["zn"] == (hl[2] or 0):
                sc = len(it_t & tk)
                if sc > bestsc:
                    bestsc, best = sc, bk
        if best and bestsc >= 3 and (best["proti"] or best["zdrzel"]):
            return [best.get("pro", []), best["proti"], best["zdrzel"]]
        return None

    # polozka: [druh_idx, tema_idx, castka|null, hlasovani|null, text, sign(0/1), cas|null, dissent|null]
    items = []
    parent = None
    for ix, b in enumerate(r["body"]):
        if b["kategorie"] == "pověřuje" and SIGN_RE.search(b["text"]):
            if parent is not None:
                parent[5] = 1   # k rodiči přidáme „pověřen k podpisu"
            continue
        it = [ci(b["kategorie"]), ti_index[b.get("tema", temata.OSTATNI)],
              b.get("castka"), b.get("hlasovani"), b["text"], 0, bt.get(str(ix)),
              dissent_for(b["text"], b.get("hlasovani"))]
        items.append(it)
        parent = it
    meet.append({
        "n": r["cislo_zasedani"], "d": r["datum"], "y": r["rok"],
        "u": r["url"] or "", "p": r.get("pritomno"),
        "b": items,
        # záznam jednání: video id + kapitoly [čas_s, čísloBodu, popisek]
        "v": (vc["vid"] if vc else None),
        "ch": ([[c["t"], c["bod"], c["label"]] for c in vc["chapters"]] if vc else []),
    })

DATA = {"cats": cats, "temata": tlist, "vbuckets": vydaje.ORDER, "meet": meet, "pgeo": parcely_geo}
data_json = json.dumps(DATA, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")

n_m = len(meet)
n_i = sum(len(m["b"]) for m in meet)
yrs = sorted({m["y"] for m in meet})
n_tem = len([t for t in tlist if t != temata.OSTATNI])
def sp(n):
    return f"{n:,}".replace(",", " ")

PAGE_CSS = r"""<style>
.zsearch{position:relative;flex:1 1 280px;min-width:220px}
.zsearch input{width:100%;padding:10px 14px 10px 38px;border:1px solid var(--line);border-radius:12px;
  background:var(--surface);color:var(--text);font:inherit;font-size:14.5px;outline:none;transition:.16s}
.zsearch input:focus{border-color:var(--accent);box-shadow:0 0 0 3px var(--accent-soft)}
.zsearch .si{position:absolute;left:13px;top:50%;transform:translateY(-50%);color:var(--faint);font-size:15px;pointer-events:none}
.zsearch .clr{position:absolute;right:8px;top:50%;transform:translateY(-50%);border:0;background:transparent;color:var(--faint);
  cursor:pointer;font-size:16px;padding:4px 7px;border-radius:8px;display:none}
.zsearch .clr:hover{color:var(--text);background:var(--inset)}
.chipbtn{font-size:12.5px;padding:6px 12px;border-radius:999px;background:var(--inset);color:var(--muted);
  border:1px solid var(--line);cursor:pointer;font-weight:500;transition:.16s;display:inline-flex;align-items:center;gap:7px}
.chipbtn:hover{color:var(--text)}
.chipbtn.on{background:var(--accent-soft);color:var(--accent);border-color:var(--accent)}
.chipbtn .dotc{width:9px;height:9px;border-radius:3px;display:inline-block}
.chipbtn b{font-weight:700;font-variant-numeric:tabular-nums}
.ctrlrow{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin-top:11px}
.ctrlrow .lbl{align-self:center}
.rmeta{font-size:12.5px;color:var(--muted);margin:14px 0 12px}
.rmeta b{color:var(--text);font-weight:600}
.feed{display:flex;flex-direction:column;gap:9px}
.zmt{border:1px solid var(--line);border-radius:var(--radius-sm);background:var(--surface2);overflow:hidden;transition:border-color .16s}
.zmt:hover{border-color:var(--accent)}
.zmt-h{width:100%;border:0;background:transparent;cursor:pointer;display:flex;align-items:center;gap:14px;
  padding:13px 16px;text-align:left;font:inherit;color:var(--text)}
.zmt-num{font-weight:700;font-size:14.5px;letter-spacing:-.01em;min-width:60px;color:var(--accent)}
.zmt-date{color:var(--text);font-size:13.5px;min-width:104px;font-variant-numeric:tabular-nums}
.zmt-count{color:var(--faint);font-size:12.5px;white-space:nowrap}
.zmt-sp{margin-left:auto}
.zmt-arrow{color:var(--faint);font-size:12px;transition:transform .18s;margin-left:6px}
.zmt.open .zmt-arrow{transform:rotate(90deg)}
.zmt-body{padding:4px 16px 16px;border-top:1px solid var(--line)}
.zgrp{margin-top:14px}
.zgrp-h{display:flex;align-items:center;gap:8px;font-size:11.5px;font-weight:700;color:var(--muted);
  text-transform:uppercase;letter-spacing:.04em;margin-bottom:7px}
.zgrp-h .dotc{width:10px;height:10px;border-radius:3px}
.zitem{position:relative;padding:9px 13px 9px 16px;border-radius:9px;background:var(--surface);
  border:1px solid var(--line);margin-bottom:7px;font-size:13.5px;line-height:1.55}
.zitem::before{content:"";position:absolute;left:0;top:7px;bottom:7px;width:3px;border-radius:3px;background:var(--ic,var(--accent))}
.zitem mark{background:rgba(250,204,21,.45);color:inherit;border-radius:3px;padding:0 1px}
html[data-theme="dark"] .zitem mark{background:rgba(250,204,21,.30)}
.ztags{display:flex;flex-wrap:wrap;gap:7px;margin-top:8px}
.zcat{display:inline-flex;align-items:center;font-size:10.5px;font-weight:700;letter-spacing:.03em;
  text-transform:uppercase;color:var(--cc);background:var(--inset);border:1px solid var(--line);
  padding:2px 9px;border-radius:999px}
.zitem.zsub{margin-left:30px}
@media(max-width:680px){.zitem.zsub{margin-left:16px}}
.ztag{display:inline-flex;align-items:center;gap:6px;font-size:11px;color:var(--muted);
  background:var(--inset);border:1px solid var(--line);padding:2px 9px 2px 8px;border-radius:999px;cursor:pointer}
.ztag:hover{color:var(--text);border-color:var(--accent)}
.ztag i{width:8px;height:8px;border-radius:2px;display:inline-block}
.zmoney{display:inline-flex;align-items:center;gap:6px;font-size:11.5px;font-weight:700;color:var(--text);
  background:var(--inset);border:1px solid var(--line);padding:2px 9px 2px 8px;border-radius:999px;cursor:pointer;
  font-variant-numeric:tabular-nums}
.zmoney:hover{border-color:var(--accent)}
.zmoney i{width:8px;height:8px;border-radius:2px;display:inline-block;background:var(--mc,var(--accent))}
.zvote{display:inline-flex;align-items:center;gap:6px;font-size:11px;color:var(--muted);
  background:var(--inset);border:1px solid var(--line);padding:2px 9px;border-radius:999px;font-variant-numeric:tabular-nums}
.zvote b{color:var(--text);font-weight:700}
.zvote.contested{color:var(--accent);border-color:var(--accent)}
.zvote.contested b{color:var(--accent)}
.zsign{display:inline-flex;align-items:center;gap:5px;font-size:11px;color:var(--muted);
  background:var(--inset);border:1px dashed var(--line);padding:2px 9px;border-radius:999px}
.zvote.hasnames{cursor:default}
.vseg{border:0;background:transparent;font:inherit;color:inherit;cursor:pointer;padding:0 1px;
  text-decoration:underline dotted;text-underline-offset:3px}
.vseg b{font-variant-numeric:tabular-nums}
.vseg:hover,.vseg.on{text-decoration:underline}
.vseg0{padding:0 1px}
.vpop{margin-top:8px;font-size:12px;color:var(--muted);line-height:1.55}
.vpop b{color:var(--text);font-weight:600}
.zct2{display:inline-flex;align-items:center;gap:5px;font-size:11.5px;font-weight:600;color:var(--accent);
  background:var(--accent-soft);border:1px solid var(--line);padding:2px 9px;border-radius:999px;
  text-decoration:none;font-variant-numeric:tabular-nums}
.zct2:hover{border-color:var(--accent)}
.parc{color:var(--accent);text-decoration:none;border-bottom:1px dashed var(--accent);
  white-space:nowrap;font-variant-numeric:tabular-nums;cursor:pointer}
.parc:hover{background:var(--accent-soft);border-bottom-style:solid}
.parc::after{content:"\1F4CD";font-size:9px;margin-left:1px;vertical-align:super;opacity:.7}
.zpdf{font-size:12px;color:var(--accent);text-decoration:none;font-weight:600;white-space:nowrap;
  padding:3px 8px;border-radius:8px;border:1px solid var(--line)}
.zpdf:hover{border-color:var(--accent);background:var(--accent-soft)}
.zyt{font-size:12px;color:#e23b2e;text-decoration:none;font-weight:600;white-space:nowrap;
  padding:3px 8px;border-radius:8px;border:1px solid var(--line);display:inline-flex;align-items:center;gap:5px}
.zyt:hover{border-color:#e23b2e;background:rgba(226,59,46,.08)}
.zrec{margin-top:16px;border:1px solid var(--line);border-radius:var(--radius-sm);background:var(--surface);overflow:hidden}
.zrec-h{display:flex;align-items:center;gap:9px;flex-wrap:wrap;padding:11px 14px;border-bottom:1px solid var(--line);
  font-size:12.5px;font-weight:700;color:var(--text)}
.zrec-h .yt{color:#e23b2e;font-size:15px}
.zrec-h a{color:var(--accent);text-decoration:none;font-weight:600}
.zrec-h a:hover{text-decoration:underline}
.zrec-h .sub{color:var(--faint);font-weight:500;font-size:11.5px}
.zchaps{display:flex;flex-direction:column}
.zchap{display:flex;align-items:baseline;gap:11px;padding:7px 14px;text-decoration:none;color:var(--text);
  border-bottom:1px solid var(--line);transition:background .12s}
.zchaps .zchap:last-child{border-bottom:0}
.zchap:hover{background:var(--accent-soft)}
.zchap .ct{color:var(--accent);font-weight:700;font-size:12.5px;font-variant-numeric:tabular-nums;
  min-width:50px;display:inline-flex;align-items:center;gap:4px}
.zchap .ct::before{content:"\25B6";font-size:9px}
.zchap .cb{color:var(--faint);font-size:11px;min-width:46px;white-space:nowrap}
.zchap .cl{color:var(--muted);font-size:12.5px;line-height:1.4}
.zchap:hover .cl{color:var(--text)}
.znote{font-size:11px;color:var(--faint);padding:8px 14px 10px;margin:0;line-height:1.5}
.empty{text-align:center;color:var(--muted);padding:42px 14px;font-size:14.5px}
.zmore{margin:16px auto 0;display:block;padding:10px 20px;border:1px solid var(--line);background:var(--surface);
  border-radius:12px;color:var(--accent);font-weight:600;cursor:pointer;font:inherit;font-size:13.5px}
.zmore:hover{border-color:var(--accent);background:var(--accent-soft)}
@media(max-width:680px){.zmt-date{min-width:0}.zmt-count{display:none}.zmt-h{gap:10px;padding:12px 13px}}
</style>"""

year_btns = '<button class="on" data-k="all">Vše</button>' + "".join(
    f'<button data-k="{y}">{y}</button>' for y in yrs)

body = '''<header class="hero">
  <h1>Usnesení zastupitelstva</h1>
  <p>Procházejte usnesení Zastupitelstva obce Střelice z volebního období 2022–2026. U každého usnesení najdete výsledek hlasování, téma, případnou částku i prokliky parcel do katastrální mapy.</p>
  <div class="chips">
    <span class="chip">''' + f"{yrs[0]}–{yrs[-1]}" + '''</span>
    <span class="chip">''' + f"{sp(n_m)} zasedání" + '''</span>
    <span class="chip">''' + f"{sp(n_i)} usnesení" + '''</span>
    <span class="chip">''' + f"{n_tem} tematických oblastí" + '''</span>
    <span class="chip">zdroj: streliceubrna.cz</span>
  </div>
</header>

<section>
  <div class="sec-h"><h2>Procházení usnesení</h2><span class="hint">klikni na zasedání pro rozbalení · hledání ignoruje diakritiku</span></div>
  <div class="panel">
    <div class="ctrlrow">
      <div class="zsearch">
        <span class="si">&#128269;</span>
        <input id="q" type="search" placeholder="Hledat v usneseních… (např. rozpočet, smlouva, pozemek, dotace)" autocomplete="off">
        <button class="clr" id="clr" title="Vymazat">&#10005;</button>
      </div>
    </div>
    <div class="ctrlrow">
      <span class="lbl">Rok</span><span class="seg" id="yearSeg">''' + year_btns + '''</span>
      <span class="lbl" style="margin-left:8px">Řadit</span>
      <span class="seg" id="sortSeg"><button class="on" data-k="new">Nejnovější</button><button data-k="old">Nejstarší</button></span>
    </div>
    <div class="ctrlrow" id="temaRow"></div>
    <div class="ctrlrow" id="vydRow"></div>
    <div class="rmeta" id="rmeta"></div>
    <div class="feed" id="feed"></div>
    <button class="zmore" id="more" style="display:none"></button>
  </div>
</section>

<section>
  <div class="grid2">
    <div class="panel">
      <div class="sec-h" style="margin:0 0 8px"><h2 style="font-size:16px">Usnesení podle tématu</h2></div>
      <div class="chartbox" style="height:430px"><canvas id="temaChart"></canvas></div>
    </div>
    <div class="panel">
      <div class="sec-h" style="margin:0 0 8px"><h2 style="font-size:16px">Usnesení podle objemu výdaje</h2></div>
      <div class="chartbox" style="height:300px"><canvas id="vydChart"></canvas></div>
      <p class="note">Částka = nejvyšší hodnota v Kč uvedená v textu usnesení; orientační ukazatel (smlouvy, zakázky, dotace). Klikni na sloupec/štítek pro filtr.</p>
    </div>
  </div>
  <p class="note">U každého usnesení je uveden výsledek hlasování (pro · proti · zdržel se), je-li v zápise k dispozici; zvýrazněné jsou body, kde někdo hlasoval proti nebo se zdržel. Témata i částky jsou přiřazeny automaticky. Osobní údaje fyzických osob nejsou ze zákonných důvodů uváděny.</p>
</section>

<div class="footer">
  Data sestavena z výpisů usnesení zveřejněných na <b>streliceubrna.cz</b> · sekce Zastupitelstvo obce Střelice 2022–2026.<br>
  Část portálu <b>Jak žijí Střelice</b> — otevřená data obce. Texty usnesení jsou přepisem oficiálních zápisů.
</div>'''

scripts = '<script>' + CHARTJS + '''</script>
<script>
const D=DATA_JSON, CATS=D.cats, TEMATA=D.temata, VBUCKETS=D.vbuckets, MEET=D.meet;
const PGEO=D.pgeo||{};
const nf=new Intl.NumberFormat('cs-CZ');
const PAGE=20;
let q='', year='all', tema='all', vyd='all', sort='new', shown=PAGE;
const openSet=new Set();
const charts={};

// DRUH usneseni zastupitelstva
const CATCOL={'schvaluje':'--pos','neschvaluje':'--neg','bere na vědomí':'--c0','projednalo':'--c3',
  'souhlasí':'--c1','nesouhlasí':'--neg','volí':'--c8','pověřuje':'--c6','ukládá':'--c2',
  'rozhodlo':'--c4','stanovuje':'--c7','ostatní':'--c5'};
const CATORDER=['schvaluje','neschvaluje','bere na vědomí','projednalo','souhlasí','nesouhlasí',
  'volí','pověřuje','ukládá','rozhodlo','stanovuje','ostatní'];
function catVar(c){return 'var('+(CATCOL[c]||'--c5')+')';}
function catOrd(c){const i=CATORDER.indexOf(c);return i<0?99:i;}

const TPAL=['--c0','--c2','--c3','--c1','--c4','--c6','--c5','--c7','--c8','--c9','--prijmy','--vydaje','--pos','--neg','--accent'];
function temaName(name){return name==='Ostatní'?'--faint':TPAL[Math.max(0,TEMATA.indexOf(name))%TPAL.length];}
function temaVar(name){return 'var('+temaName(name)+')';}
function temaRGB(name){return cssv(temaName(name));}

const VB=[['do 10 tis. Kč',10000],['10–50 tis. Kč',50000],['50–100 tis. Kč',100000],
          ['100–500 tis. Kč',500000],['0,5–1 mil. Kč',1000000],['nad 1 mil. Kč',Infinity]];
const VNONE='Bez částky';
const VBCOL={'do 10 tis. Kč':'--c1','10–50 tis. Kč':'--c2','50–100 tis. Kč':'--c3',
  '100–500 tis. Kč':'--c7','0,5–1 mil. Kč':'--vydaje','nad 1 mil. Kč':'--neg','Bez částky':'--faint'};
function vbucket(a){ if(a==null) return VNONE; for(const x of VB){ if(a<x[1]) return x[0]; } return VB[VB.length-1][0]; }
function vbVar(b){return 'var('+(VBCOL[b]||'--faint')+')';}
function vbRGB(b){return cssv(VBCOL[b]||'--faint');}

function fold(s){return (s||'').toLowerCase().normalize('NFD').replace(/[\\u0300-\\u036f]/g,'');}
function esc(s){return (s||'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));}
function fmtDate(iso){const p=iso.split('-');return (+p[2])+'. '+(+p[1])+'. '+p[0];}
function plurBod(n){return n===1?'usnesení':(n>=2&&n<=4?'usnesení':'usnesení');}
function fmtKc(v){ if(v==null) return '';
  if(v>=1e6){ const m=v/1e6; return (m>=10?m.toFixed(1):m.toFixed(2)).replace('.',',')+' mil. Kč'; }
  return nf.format(Math.round(v))+' Kč'; }

function hl(text,qf){
  if(!qf) return esc(text);
  let folded='', map=[];
  for(let i=0;i<text.length;i++){const f=fold(text[i]);for(let j=0;j<f.length;j++){folded+=f[j];map.push(i);}}
  let out='', last=0, idx=0, p;
  while((p=folded.indexOf(qf,idx))>=0){
    const os=map[p], oe=(p+qf.length<=map.length)?map[p+qf.length-1]+1:text.length;
    out+=esc(text.slice(last,os))+'<mark>'+esc(text.slice(os,oe))+'</mark>';
    last=oe; idx=p+qf.length;
  }
  return out+esc(text.slice(last));
}

const PARC_RE=/((?:p(?:arc)?\\.?\\s*č\\.?|parcel\\w*\\s*č\\.?)\\s*)(\\d{1,5}(?:\\/\\d{1,4})?)/gi;
const OTHER_KU=/k\\.?\\s*ú\\.?\\s*(Troubsk|Ostopovic|Omic|Radostic|Popůvk|Heršpic|Tetčic|Nebovid|Rosic|Žebětín|Bosonoh|Modřic|Želešic|Šlapanic)/i;
function linkifyParc(html, allow){
  if(!allow) return html;
  return html.replace(PARC_RE,(m,pre,num)=>{
    const g=PGEO[num]; if(!g) return m;
    const u=`https://www.ikatastr.cz/#kde=${g[0]},${g[1]},18&mapa=zakladni&vrstvy=parcelybudovy&info=${g[0]},${g[1]}`;
    return pre+`<a class="parc" href="${u}" target="_blank" rel="noopener" onclick="event.stopPropagation()" title="Parcela č. ${num} v katastrální mapě (k.ú. Střelice u Brna)">${num}</a>`;
  });
}

function axis(){return {grid:{color:isDark()?'#1f2a40':'#eef2f7'},ticks:{color:cssv('--muted')}};}
function mk(id,cfg){if(charts[id])charts[id].destroy();charts[id]=new Chart(document.getElementById(id),cfg);}
const _yset=[...new Set(MEET.map(m=>m.y))].sort((a,b)=>a-b);

function buildTemaChips(){
  const counts={}; let tot=0;
  for(const m of MEET) for(const it of m.b){const t=TEMATA[it[1]];counts[t]=(counts[t]||0)+1;tot++;}
  let html=`<span class="lbl">Téma</span><button class="chipbtn${tema==='all'?' on':''}" data-t="all">Vše <b>${nf.format(tot)}</b></button>`;
  for(const t of TEMATA){
    if(!counts[t]) continue;
    html+=`<button class="chipbtn${tema===t?' on':''}" data-t="${esc(t)}"><span class="dotc" style="background:${temaVar(t)}"></span>${esc(t)} <b>${nf.format(counts[t])}</b></button>`;
  }
  const row=document.getElementById('temaRow'); row.innerHTML=html;
  row.querySelectorAll('.chipbtn').forEach(b=>b.onclick=()=>{tema=b.dataset.t; shown=PAGE; buildTemaChips(); render();});
}

function buildVydChips(){
  const counts={};
  for(const m of MEET) for(const it of m.b){const b=vbucket(it[2]);counts[b]=(counts[b]||0)+1;}
  let html=`<span class="lbl">Hodnota</span><button class="chipbtn${vyd==='all'?' on':''}" data-v="all">Vše</button>`;
  for(const b of VBUCKETS){
    if(!counts[b] || b===VNONE) continue;
    html+=`<button class="chipbtn${vyd===b?' on':''}" data-v="${esc(b)}"><span class="dotc" style="background:${vbVar(b)}"></span>${esc(b)} <b>${nf.format(counts[b])}</b></button>`;
  }
  const row=document.getElementById('vydRow'); row.innerHTML=html;
  row.querySelectorAll('.chipbtn').forEach(b=>b.onclick=()=>{vyd=b.dataset.v; shown=PAGE; buildVydChips(); render();});
}

function filtered(){
  const qf=fold(q);
  const itemMode = qf!=='' || tema!=='all' || vyd!=='all';
  const res=[];
  for(const m of MEET){
    if(year!=='all' && m.y!=+year) continue;
    let items=m.b;
    if(tema!=='all') items=items.filter(it=>TEMATA[it[1]]===tema);
    if(vyd!=='all') items=items.filter(it=>vbucket(it[2])===vyd);
    if(qf) items=items.filter(it=>fold(it[4]).indexOf(qf)>=0);
    if(itemMode && items.length===0) continue;
    res.push([m,items]);
  }
  res.sort((A,B)=> sort==='new' ? B[0].d.localeCompare(A[0].d) : A[0].d.localeCompare(B[0].d));
  return {res,itemMode,qf};
}

function voteBadge(v, nm){
  if(!v) return '';
  const pr=v[0]??0, pt=v[1]??0, zd=v[2]??0;
  const cls = (pt>0||zd>0) ? ' contested' : '';
  if(!nm)
    return `<span class="zvote${cls}" title="Hlasování: pro ${pr}, proti ${pt}, zdržel se ${zd}">`+
           `pro <b>${pr}</b> · proti <b>${pt}</b> · zdržel <b>${zd}</b></span>`;
  const seg=(lab,n,names)=> (names&&names.length)
    ? `<button type="button" class="vseg" data-lab="${lab}" data-names="${esc(names.join(', '))}">${lab} <b>${n}</b></button>`
    : `<span class="vseg0">${lab} <b>${n}</b></span>`;
  return `<span class="zvote${cls} hasnames" title="Klikni na číslo pro jména">`+
         `${seg('pro',pr,nm[0])} · ${seg('proti',pt,nm[1])} · ${seg('zdržel',zd,nm[2])}</span>`;
}

function fmtT(s){return Math.floor(s/60)+':'+String(s%60).padStart(2,'0');}
function plurKap(n){return (n>=2&&n<=4)?'kapitoly':'kapitol';}
function recHTML(m){
  if(!m.v) return '';
  const full='https://youtu.be/'+m.v;
  let inner;
  if(m.ch && m.ch.length){
    inner='<div class="zchaps">'+m.ch.map(c=>{
      const bod=c[1]?`bod ${c[1]}`:'';
      return `<a class="zchap" href="${full}?t=${c[0]}" target="_blank" rel="noopener" onclick="event.stopPropagation()">`+
             `<span class="ct">${fmtT(c[0])}</span><span class="cb">${bod}</span>`+
             `<span class="cl">${esc(c[2])}</span></a>`;
    }).join('')+'</div>'+
    '<p class="znote">Časy i popisky bodů jsou odvozené z automatického přepisu (titulků YouTube) — orientační, mohou se o pár vteřin lišit; popisek je útržek řečeného při otevření bodu.</p>';
  } else {
    inner='<p class="znote">Pro toto zasedání nejsou k dispozici titulky pro rozpad na body — k dispozici je celý záznam.</p>';
  }
  const sub = (m.ch&&m.ch.length)?` <span class="sub">· ${m.ch.length} ${plurKap(m.ch.length)}, klikni na čas a skoč ve videu</span>`:'';
  return `<div class="zrec"><div class="zrec-h"><span class="yt">&#9654;</span>Záznam jednání`+
         ` · <a href="${full}?t=0" target="_blank" rel="noopener" onclick="event.stopPropagation()">otevřít celé video &#8599;</a>${sub}`+
         `</div>${inner}</div>`;
}

function cardHTML(m,items,open,qf){
  const cnt=items.length;
  let bodyHTML='';
  if(open){
    // usnesení v pořadí, jak na zasedání šla (program), ne sdružená podle druhu;
    // navazující pověření/uložení se lehce odsadí pod předchozí bod
    const SUB={'pověřuje':1,'ukládá':1};
    const rows=items.map(it=>{
      const c=CATS[it[0]], col=catVar(c);
      const th=TEMATA[it[1]], amt=it[2], vts=it[3];
      const money=amt!=null?`<span class="zmoney" data-v="${esc(vbucket(amt))}" title="Objem: ${esc(vbucket(amt))}"><i style="background:${vbVar(vbucket(amt))}"></i>${fmtKc(amt)}</span>`:'';
      const txt=linkifyParc(hl(it[4],qf), !OTHER_KU.test(it[4]));
      const sign=it[5]?`<span class="zsign" title="Zastupitelstvo zároveň pověřilo starostu/radu podpisem příslušné smlouvy">&#10003; pověřeno k podpisu</span>`:'';
      const tl=(m.v&&it[6])?`<a class="zct2" href="https://youtu.be/${m.v}?t=${it[6]}" target="_blank" rel="noopener" onclick="event.stopPropagation()" title="Skočit na projednávání tohoto bodu v záznamu jednání">&#9654; ${fmtT(it[6])}</a>`:'';
      const cat=`<span class="zcat" style="--cc:${col}">${esc(c)}</span>`;
      return `<div class="zitem${SUB[c]?' zsub':''}" style="--ic:${col}"><div>${txt}</div>`+
             `<div class="ztags">${cat}<span class="ztag" data-t="${esc(th)}"><i style="background:${temaVar(th)}"></i>${esc(th)}</span>${money}${voteBadge(vts,it[7])}${sign}${tl}</div><div class="vpop" hidden></div></div>`;
    }).join('');
    bodyHTML='<div class="zmt-body">'+recHTML(m)+rows+'</div>';
  }
  const pdf=m.u?`<a class="zpdf" href="${esc(m.u)}" target="_blank" rel="noopener" onclick="event.stopPropagation()">PDF&nbsp;&#8599;</a>`:'';
  const yt=m.v?`<a class="zyt" href="https://youtu.be/${m.v}?t=0" target="_blank" rel="noopener" onclick="event.stopPropagation()" title="Záznam jednání na YouTube (od začátku)">&#9654;&nbsp;záznam</a>`:'';
  const pres=m.p?` · ${m.p} přít.`:'';
  return `<div class="zmt${open?' open':''}">
    <button class="zmt-h" data-n="${m.n}">
      <span class="zmt-num">ZO ${m.n}</span>
      <span class="zmt-date">${fmtDate(m.d)}</span>
      <span class="zmt-count">${cnt} ${plurBod(cnt)}${pres}</span>
      <span class="zmt-sp"></span>
      ${yt}${pdf}
      <span class="zmt-arrow">&#9654;</span>
    </button>${bodyHTML}</div>`;
}

function render(){
  const {res,itemMode,qf}=filtered();
  const totalItems=res.reduce((a,x)=>a+x[1].length,0);
  document.getElementById('rmeta').innerHTML = res.length
    ? `Zobrazeno <b>${res.length}</b> zasedání · <b>${nf.format(totalItems)}</b> usnesení ${itemMode?'odpovídá filtru':'celkem'}`
    : '';
  const feed=document.getElementById('feed'), more=document.getElementById('more');
  if(!res.length){feed.innerHTML='<div class="empty">Žádná usnesení neodpovídají zadanému filtru. Zkuste jiný výraz nebo zrušte filtr.</div>';more.style.display='none';return;}
  const slice=res.slice(0,shown);
  feed.innerHTML=slice.map(([m,items])=>cardHTML(m,items, itemMode||openSet.has(m.n), qf)).join('');
  more.style.display = res.length>shown ? 'block':'none';
  more.textContent = 'Zobrazit další zasedání ('+(res.length-shown)+')';
  feed.querySelectorAll('.zmt-h').forEach(h=>h.onclick=()=>{
    const n=+h.dataset.n;
    if(openSet.has(n)) openSet.delete(n); else openSet.add(n);
    render();
  });
  feed.querySelectorAll('.ztag').forEach(tg=>tg.onclick=(e)=>{e.stopPropagation(); setTema(tg.dataset.t);});
  feed.querySelectorAll('.zmoney').forEach(mo=>mo.onclick=(e)=>{e.stopPropagation(); setVyd(mo.dataset.v);});
  const VLAB={pro:'Pro',proti:'Proti','zdržel':'Zdržel se'};
  feed.querySelectorAll('.vseg').forEach(seg=>seg.onclick=(e)=>{
    e.stopPropagation();
    const item=seg.closest('.zitem'), pop=item.querySelector('.vpop'), cur=seg.dataset.lab;
    if(!pop.hidden && pop.dataset.cur===cur){ pop.hidden=true; pop.dataset.cur=''; seg.classList.remove('on'); return; }
    item.querySelectorAll('.vseg.on').forEach(s=>s.classList.remove('on'));
    seg.classList.add('on');
    pop.innerHTML=`<b>${VLAB[cur]||cur} (${seg.querySelector('b').textContent}):</b> ${esc(seg.dataset.names)}`;
    pop.hidden=false; pop.dataset.cur=cur;
  });
}

function temaChart(){
  const counts=TEMATA.map(t=>MEET.reduce((a,m)=>a+m.b.filter(it=>TEMATA[it[1]]===t).length,0));
  const pairs=TEMATA.map((t,i)=>[t,counts[i]]).sort((a,b)=>b[1]-a[1]);
  mk('temaChart',{type:'bar',data:{labels:pairs.map(p=>p[0]),datasets:[{
      data:pairs.map(p=>p[1]),backgroundColor:pairs.map(p=>temaRGB(p[0])),borderRadius:4,maxBarThickness:26}]},
    options:{indexAxis:'y',responsive:true,maintainAspectRatio:false,animation:{duration:500},
      onClick:(e,a,ch)=>{const el=ch.getElementsAtEventForMode(e,'nearest',{intersect:true},true)[0]; if(el) setTema(pairs[el.index][0]);},
      onHover:(e,els)=>{if(e.native)e.native.target.style.cursor=els.length?'pointer':'default';},
      plugins:{legend:{display:false},tooltip:{callbacks:{label:c=>nf.format(c.parsed.x)+' usnesení'}}},
      scales:{x:Object.assign(axis(),{beginAtZero:true}),
              y:Object.assign(axis(),{ticks:{color:cssv('--text'),autoSkip:false,font:{size:11.5}}})}}});
}

function vydChart(){
  const labels=VB.map(x=>x[0]);
  const counts=labels.map(b=>MEET.reduce((a,m)=>a+m.b.filter(it=>vbucket(it[2])===b).length,0));
  mk('vydChart',{type:'bar',data:{labels,datasets:[{data:counts,
      backgroundColor:labels.map(b=>vbRGB(b)),borderRadius:5,maxBarThickness:54}]},
    options:{responsive:true,maintainAspectRatio:false,animation:{duration:500},
      onClick:(e,a,ch)=>{const el=ch.getElementsAtEventForMode(e,'nearest',{intersect:true},true)[0]; if(el) setVyd(labels[el.index]);},
      onHover:(e,els)=>{if(e.native)e.native.target.style.cursor=els.length?'pointer':'default';},
      plugins:{legend:{display:false},tooltip:{callbacks:{label:c=>nf.format(c.parsed.y)+' usnesení'}}},
      scales:{x:Object.assign(axis(),{ticks:{color:cssv('--muted'),font:{size:10.5},maxRotation:30,minRotation:0}}),
              y:Object.assign(axis(),{beginAtZero:true})}}});
}

function setYear(y){
  year=String(y); shown=PAGE;
  document.querySelectorAll('#yearSeg button').forEach(b=>b.classList.toggle('on', b.dataset.k===year));
  render();
}
function setTema(t){
  tema=String(t); shown=PAGE; buildTemaChips(); render();
  document.getElementById('feed').scrollIntoView({behavior:'smooth',block:'start'});
}
function setVyd(v){
  vyd=String(v); shown=PAGE; buildVydChips(); render();
  document.getElementById('feed').scrollIntoView({behavior:'smooth',block:'start'});
}
const qIn=document.getElementById('q'), clr=document.getElementById('clr');
qIn.addEventListener('input',()=>{q=qIn.value; shown=PAGE; clr.style.display=q?'block':'none'; render();});
clr.onclick=()=>{q=''; qIn.value=''; clr.style.display='none'; qIn.focus(); shown=PAGE; render();};
document.querySelectorAll('#yearSeg button').forEach(b=>b.onclick=()=>{
  document.querySelectorAll('#yearSeg button').forEach(x=>x.classList.remove('on')); b.classList.add('on');
  year=b.dataset.k; shown=PAGE; render();});
document.querySelectorAll('#sortSeg button').forEach(b=>b.onclick=()=>{
  document.querySelectorAll('#sortSeg button').forEach(x=>x.classList.remove('on')); b.classList.add('on');
  sort=b.dataset.k; render();});
document.getElementById('more').onclick=()=>{shown+=PAGE; render();};

function redraw(){temaChart(); vydChart();}
q=qIn.value||''; clr.style.display=q?'block':'none';
buildTemaChips(); buildVydChips(); render(); temaChart(); vydChart();
// otevření konkrétního zasedání přes URL (?zo=N) — proklik z jiných sekcí (Investice)
(function openFromUrl(){
  const p=new URLSearchParams(location.search).get('zo'); if(!p) return;
  const n=+p; if(!MEET.some(m=>m.n===n)) return;
  openSet.add(n); year='all'; shown=MEET.length;
  document.querySelectorAll('#yearSeg button').forEach(b=>b.classList.toggle('on',b.dataset.k==='all'));
  render();
  setTimeout(()=>{const h=document.querySelector('.zmt-h[data-n="'+n+'"]'); if(!h) return;
    const c=h.closest('.zmt'); c.scrollIntoView({behavior:'smooth',block:'center'});
    c.style.transition='box-shadow .3s'; c.style.boxShadow='0 0 0 2px var(--accent)';
    setTimeout(()=>{c.style.boxShadow='';},2600);},160);
})();
bindTheme(redraw);
window.addEventListener('load',()=>{Object.values(charts).forEach(c=>{try{c.resize();}catch(e){}});});
</script>'''.replace("DATA_JSON", data_json)

html = pc.page("Zastupitelstvo", "Usnesení zastupitelstva — Jak žijí Střelice", body,
               head_scripts=PAGE_CSS, body_scripts=scripts)
open("zastupitelstvo.html", "w", encoding="utf-8").write(html)
print("HOTOVO: zastupitelstvo.html —", n_m, "zasedání,", n_i, "usnesení")
