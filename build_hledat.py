#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Sestaví hledat.html — jedno hledání přes celý portál + „Moje ulice".

Index: usnesení Rady obce a Zastupitelstva (text, téma, částka), přepisy diskuzí
na zastupitelstvu, dodavatelé (zakázky), příjemci dotací a rozpočtové oblasti
(paragrafy). Hledání běží v prohlížeči (bez diakritiky, všechna slova musí sedět).
„Moje ulice" = předpočítané přiřazení usnesení k ulicím (se skloňováním názvu)
+ mapa s ulicí a parcelami zmíněnými v usneseních.

Spouštět PO build_zakazky.py (čte data vložená do zakazky.html)."""
import sys, json, re, os, csv, glob
from collections import defaultdict
import portal_common as pc

sys.stdout.reconfigure(encoding="utf-8")
LEAFLET_JS = open("data/vendor/leaflet.js", encoding="utf-8").read()
LEAFLET_CSS = open("data/vendor/leaflet.css", encoding="utf-8").read()


def embedded(path):
    """DATA vložená do vygenerované stránky (`const D=<json>`)."""
    s = open(path, encoding="utf-8").read()
    i = s.index("const D=") + len("const D=")
    return json.JSONDecoder().raw_decode(s[i:])[0]


ro = json.load(open("dataset_RO.json", encoding="utf-8"))
zo = json.load(open("dataset_ZO.json", encoding="utf-8"))
pgeo = json.load(open("data/parcely_geo.json", encoding="utf-8"))
ugeo = json.load(open("data/ulice_geo.json", encoding="utf-8"))

# položka indexu: [typ, nadpis, text, datum ISO, odkaz, částka|null, podtitul]
IDX = []
for src, mid, page, key in (("RO", ro, "zapisy.html", "ro"), ("ZO", zo, "zastupitelstvo.html", "zo")):
    for m in mid:
        n = m["cislo_zasedani"]
        lbl = f'{"Rada obce" if src == "RO" else "Zastupitelstvo"} č. {n}'
        for b in m["body"]:
            IDX.append([src, lbl, b["text"], m.get("datum") or "", f"{page}?{key}={n}",
                        b.get("castka"), b.get("tema") or ""])

# přepisy diskuzí na zastupitelstvu (jen zasedání se záznamem)
for f in sorted(glob.glob("prepisy/[0-9]*.json")):
    j = json.load(open(f, encoding="utf-8"))
    n = j["cislo_zasedani"]
    m = next((x for x in zo if x["cislo_zasedani"] == n), None)
    for b in j["body"]:
        for t in b["turns"]:
            if len(t["text"]) < 40:
                continue
            IDX.append(["DIS", f'Diskuze · ZO č. {n}', t["text"], (m or {}).get("datum") or "",
                        f"zastupitelstvo.html?zo={n}", None, t["who"]])

# dodavatelé (agregace po firmách z dat stránky Zakázky)
zak = embedded("zakazky.html")
firms = defaultdict(lambda: [0, 0, set(), []])
for r in zak["rows"]:   # [rok, firma, castka, datum, zdroj, cislo, url, text, is_dodatek]
    a = firms[r[1]]
    a[0] += r[2]; a[1] += 0 if r[8] else 1; a[2].add(r[0]); a[3].append(r[7][:120])
for f, (tot, cnt, yrs, txt) in firms.items():
    IDX.append(["ZAK", f, f"{cnt} zakázek · roky {min(yrs)}–{max(yrs)} · " + " · ".join(txt[:3]),
                f"{max(yrs)}-12-31", "zakazky.html?firma=" + f, tot, "dodavatel obce"])

# příjemci dotací
rec = defaultdict(lambda: [0, set(), []])
for r in csv.DictReader(open("data/dotace_strelice.csv", encoding="utf-8-sig"), delimiter=";"):
    a = rec[r["prijemce"].strip()]
    try: a[0] += int(r["castka"])
    except ValueError: pass
    a[1].add(int(r["rok"])); a[2].append(r["ucel"].strip()[:100])
for p, (tot, yrs, uc) in rec.items():
    IDX.append(["DOT", p, f"dotace z rozpočtu obce {min(yrs)}–{max(yrs)} · " + " · ".join(uc[:2]),
                f"{max(yrs)}-12-31", "dotace.html?prijemce=" + p, tot, "příjemce dotace"])

# rozpočtové oblasti (paragrafy) — poslední uzavřený rok
fin = list(csv.DictReader(open("data/strelice_finm201_2013_2025.csv", encoding="utf-8-sig"), delimiter=";"))
LY = max(int(r["rok"]) for r in fin)
par = defaultdict(lambda: [0, 0, ""])
for r in fin:
    if int(r["rok"]) == LY and r["paragraf"] != "0000":
        a = par[(r["paragraf"], r["paragraf_nazev"])]
        v = round(float(r["skutecnost"] or 0))
        if r["druh"] == "Výdaje": a[0] += v
        else: a[1] += v
        a[2] = r["par_oddil"]
for (code, name), (vy, pr, odd) in par.items():
    if not (vy or pr):
        continue
    IDX.append(["ROZ", name, f"{odd} · paragraf {code} · rok {LY}: výdaje {vy/1e6:.2f} mil. Kč".replace(".", ",")
                + (f", příjmy {pr/1e6:.2f} mil. Kč".replace(".", ",") if pr else ""),
                f"{LY}-12-31", "rozpocet.html#detail", vy or pr, "rozpočet obce"])

# --- Moje ulice: usnesení podle ulice (se skloňováním) ---
def street_rx(nm):
    alt = {"Ant. Smutného": r"(?:Ant\.|Antonína)\s*Smutného",
           "Jar. Svobody": r"(?:Jar\.|Jaroslava)\s*Svobody",
           "nám. Svobody": r"(?:nám\.|náměstí|náměstím)\s*Svobody",
           "Nová ulice": r"(?:Nová ulice|Nové ulici|ulic\w* Nová|ul\. Nová)"}
    if nm in alt:
        rx = alt[nm]
    elif nm.endswith("á") and " " not in nm:
        rx = re.escape(nm[:-1]) + r"(?:á|é|ou)"
    elif nm.endswith("í") and " " not in nm:
        rx = re.escape(nm) + r"(?:ho|mu|m|ch)?"
    elif nm.endswith("ova"):
        rx = re.escape(nm[:-1]) + r"(?:a|ě|u|y|ou)"
    else:
        rx = re.escape(nm)
    return re.compile(r"(?<!\w)" + rx + r"(?!\w)")

OTHER_KU = re.compile(r"k\.?\s*ú\.?\s*(Troubsk|Ostopovic|Omic|Radostic|Popůvk|Heršpic|Tetčic|Nebovid|Rosic|Žebětín|Bosonoh|Modřic|Želešic|Šlapanic)", re.I)
PARC = re.compile(r"(?:p(?:arc)?\.?\s*č\.?|parcel\w*\s*č\.?)\s*(\d{1,5}(?:/\d{1,4})?)", re.I)
STREETS = {}
for nm in sorted(ugeo, key=lambda s: s.lower()):
    rx = street_rx(nm)
    hits = [i for i, it in enumerate(IDX) if it[0] in ("RO", "ZO") and rx.search(it[2]) and not OTHER_KU.search(it[2])]
    pts = []
    for i in hits:
        for pc_ in PARC.findall(IDX[i][2]):
            if pc_ in pgeo:
                pts.append([pgeo[pc_][0], pgeo[pc_][1], i])
                break
    STREETS[nm] = {"g": ugeo[nm], "i": hits, "p": pts}

DATA = {"idx": IDX, "ul": STREETS, "ly": LY}
data_json = json.dumps(DATA, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")

body = '''<header class="hero">
  <h1>Hledat na portálu</h1>
  <p>Jedno hledání přes všechno: usnesení rady i zastupitelstva, diskuze na zasedáních, firmy, kterým obec platí, příjemce dotací i položky rozpočtu. Nebo si vyberte svou ulici.</p>
</header>
<section>
  <div class="panel">
    <div class="hsrch"><span class="hico">⌕</span><input id="hq" type="search" autocomplete="off" placeholder="např. chodník, Sokol, koupaliště, ZEMAKO, veřejné osvětlení…" aria-label="Hledat"></div>
    <div class="hopts"><span class="hint">Hledání nerozlišuje diakritiku, velikost písmen ani koncovky; musí sedět všechna zadaná slova.</span>
      <span class="hsamples" id="hsamples"></span></div>
    <div class="htabs" id="htabs"></div>
  </div>
</section>
<section id="ulsec">
  <div class="sec-h"><h2>Moje ulice</h2><span class="hint">co se v ulici řešilo na radě a zastupitelstvu</span></div>
  <div class="panel">
    <div class="ulpick"><label for="ulSel" class="lbl">Ulice</label><select id="ulSel"><option value="">— vyberte ulici —</option></select>
      <span class="hint" id="ulMeta"></span></div>
    <div class="ulgrid" id="ulGrid" hidden>
      <div id="ulMap" class="ulmap"></div>
      <div id="ulList" class="ullist"></div>
    </div>
    <p class="note">Usnesení se k ulici přiřazují podle výskytu názvu v textu (včetně skloňování, např. „v ulici Brněnské"). Body na mapě = parcely uvedené v usneseních; kroužek = ulice. Mapové podklady © přispěvatelé <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener" style="color:var(--accent)">OpenStreetMap</a>.</p>
  </div>
</section>
<section id="res" hidden>
  <div class="sec-h"><h2 id="resH">Výsledky</h2><span class="hint" id="resHint"></span></div>
  <div id="resList"></div>
  <button class="more" id="resMore" hidden>Zobrazit další</button>
</section>'''

CSS = '''<style>''' + LEAFLET_CSS + '''
.hsrch{position:relative}
.hsrch input{width:100%;box-sizing:border-box;font:inherit;font-size:17px;padding:14px 16px 14px 44px;border-radius:12px;border:1px solid var(--line);background:var(--inset);color:var(--text)}
.hsrch input:focus{outline:2px solid var(--accent);outline-offset:1px}
.hico{position:absolute;left:15px;top:50%;transform:translateY(-50%);font-size:20px;color:var(--muted)}
.hopts{display:flex;justify-content:space-between;gap:10px;flex-wrap:wrap;margin-top:10px;align-items:center}
.hsamples button,.htabs button{font:inherit;font-size:12.5px;border:1px solid var(--line);background:var(--inset);color:var(--muted);border-radius:999px;padding:4px 11px;cursor:pointer;margin:2px}
.hsamples button:hover,.htabs button:hover{color:var(--text)}
.htabs{margin-top:12px;display:flex;flex-wrap:wrap;gap:4px}
.htabs button.on{background:var(--accent);color:#fff;border-color:var(--accent)}
.htabs button b{font-weight:700;margin-left:4px}
.hres{display:block;text-decoration:none;color:var(--text);background:var(--surface);border:1px solid var(--line);border-radius:12px;padding:12px 16px;margin-bottom:8px}
.hres:hover{border-color:var(--accent)}
.hres .hh{display:flex;gap:10px;align-items:center;flex-wrap:wrap;font-size:12.5px;color:var(--muted);margin-bottom:4px}
.hres .ht{font-size:14px;line-height:1.5}
.hres mark{background:rgba(250,204,21,.35);color:inherit;border-radius:3px;padding:0 1px}
.htema{display:inline-flex;align-items:center;gap:5px;font-size:11px;color:var(--muted);background:var(--inset);border:1px solid var(--line);border-radius:999px;padding:1px 8px}
.htema i{width:8px;height:8px;border-radius:2px;display:inline-block}
.htype{font-size:11px;font-weight:700;letter-spacing:.02em;padding:2px 8px;border-radius:999px;color:#fff}
.hamt{margin-left:auto;font-weight:600;color:var(--text);font-variant-numeric:tabular-nums}
.more{display:block;margin:10px auto;font:inherit;padding:9px 18px;border-radius:10px;border:1px solid var(--line);background:var(--surface);color:var(--text);cursor:pointer}
.ulpick{display:flex;gap:12px;align-items:center;flex-wrap:wrap}
.ulpick select{font:inherit;padding:8px 10px;border-radius:10px;border:1px solid var(--line);background:var(--inset);color:var(--text);min-width:220px}
.ulgrid{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1.25fr);gap:16px;margin-top:14px}
.ulmap{height:420px;border-radius:12px;border:1px solid var(--line);z-index:0}
.ullist{max-height:420px;overflow:auto;padding-right:4px}
.ullist .hres{padding:10px 12px}
@media(max-width:820px){.ulgrid{grid-template-columns:1fr}.ulmap{height:300px}.ullist{max-height:none}}
.empty{color:var(--muted);padding:18px;text-align:center}
</style>'''

JS = '''<script>''' + LEAFLET_JS + '''</script>
<script>
const D=DATA_JSON, IDX=D.idx, UL=D.ul;
/*TEMAJS*/
const TYPES={RO:['Rada obce','#3b82f6'],ZO:['Zastupitelstvo','#d97706'],DIS:['Diskuze ZO','#8b5cf6'],
  ZAK:['Dodavatel','#0d9488'],DOT:['Dotace','#db2777'],ROZ:['Rozpočet','#16a34a']};
const ORDER=['ZO','RO','DIS','ZAK','DOT','ROZ'];
const fold=s=>(s||'').normalize('NFD').replace(/[\\u0300-\\u036f]/g,'').toLowerCase();
const FT=IDX.map(it=>fold(it[1]+' '+it[2]+' '+(it[6]||'')));
const esc=s=>String(s==null?'':s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const nf=new Intl.NumberFormat('cs-CZ');
function kc(v){if(v==null)return '';return v>=1e6?(v/1e6).toLocaleString('cs-CZ',{maximumFractionDigits:1})+' mil. Kč':nf.format(Math.round(v))+' Kč';}
function fd(iso){if(!iso)return '';const p=iso.split('-');return (+p[2])+'. '+(+p[1])+'. '+p[0];}
// zvýraznění: najdi výskyty tokenů ve fold(textu) a obal originál (délky se po NFD-fold nemění u češtiny)
function hl(text,toks){
  if(!toks.length)return esc(text);
  const f=fold(text); const marks=new Array(text.length).fill(false);
  for(const t of toks){let i=0;while((i=f.indexOf(t,i))>=0){for(let k=i;k<i+t.length;k++)marks[k]=true;i+=t.length;}}
  let out='',on=false;
  for(let i=0;i<text.length;i++){if(marks[i]&&!on){out+='<mark>';on=true;}if(!marks[i]&&on){out+='</mark>';on=false;}out+=esc(text[i]);}
  return out+(on?'</mark>':'');
}
function snippet(text,toks,len){
  len=len||260; if(text.length<=len)return text;
  const f=fold(text); let p=-1; for(const t of toks){const i=f.indexOf(t);if(i>=0&&(p<0||i<p))p=i;}
  if(p<0)return text.slice(0,len)+'…';
  const s=Math.max(0,p-80); return (s>0?'…':'')+text.slice(s,s+len)+(s+len<text.length?'…':'');
}
function link(it,toks){
  // u usnesení předáme hledaný výraz → cílová stránka rovnou vyfiltruje a zvýrazní
  // cílová stránka hledá souvislý výraz → předáme nejdelší kmen dotazu
  if((it[0]==='RO'||it[0]==='ZO')&&toks.length){const t=toks.slice().sort((a,b)=>b.length-a.length)[0];
    return it[4]+'&q='+encodeURIComponent(t);}
  return it[4];
}
function card(i,toks,raw){
  const it=IDX[i], ty=TYPES[it[0]];
  const who=it[0]==='DIS'?' · '+esc(it[6]):(it[6]&&(it[0]==='RO'||it[0]==='ZO')?' · '+esc(it[6]):'');
  const dt=(it[0]==='RO'||it[0]==='ZO'||it[0]==='DIS')?fd(it[3]):'';
  const title=(it[0]==='ZAK'||it[0]==='DOT'||it[0]==='ROZ')?'<b>'+hl(it[1],toks)+'</b> — ':'';
  return `<a class="hres" href="${esc(link(it,toks))}"><div class="hh"><span class="htype" style="background:${ty[1]}">${ty[0]}</span>`+
    `<span>${it[0]==='ZAK'||it[0]==='DOT'||it[0]==='ROZ'?esc(it[6]):esc(it[1])}${dt?' · '+dt:''}${it[0]==='DIS'?who:''}</span>`+
    `${(it[0]==='RO'||it[0]==='ZO')&&it[6]?'<span class="htema"><i style="background:'+temaVar(it[6])+'"></i>'+temaIco(it[6])+esc(it[6])+'</span>':''}`+
    `${it[5]!=null?'<span class="hamt">'+kc(it[5])+'</span>':''}</div>`+
    `<div class="ht">${title}${hl(snippet(it[2],toks),toks)}</div></a>`;
}
let cur=[], curType='all', shown=0; const PAGE=25;
function search(q){
  const raw=q.trim().split(/\\s+/).filter(Boolean);
  // jednoduché „kmenování" kvůli českému skloňování: školní → škol (najde i školou, školy…)
  const stem=t=>t.length>=7?t.slice(0,-2):t.length>=5?t.slice(0,-1):t;
  const toks=raw.map(fold).filter(t=>t.length>=2).map(stem);
  const res=document.getElementById('res'), tabs=document.getElementById('htabs');
  if(!toks.length){res.hidden=true;tabs.innerHTML='';cur=[];return;}
  cur=[];
  for(let i=0;i<IDX.length;i++){const f=FT[i];if(toks.every(t=>f.includes(t)))cur.push(i);}
  // řazení: shoda v názvu (firma/příjemce/oblast) napřed, pak novější
  cur.sort((a,b)=>{const ta=toks.some(t=>fold(IDX[a][1]).includes(t))&&IDX[a][0].length===3&&IDX[a][0]!=='DIS',
    tb=toks.some(t=>fold(IDX[b][1]).includes(t))&&IDX[b][0].length===3&&IDX[b][0]!=='DIS';
    if(ta!==tb)return ta?-1:1; return (IDX[b][3]||'').localeCompare(IDX[a][3]||'');});
  const cnt={};cur.forEach(i=>cnt[IDX[i][0]]=(cnt[IDX[i][0]]||0)+1);
  if(curType!=='all'&&!cnt[curType])curType='all';
  tabs.innerHTML=`<button data-t="all" class="${curType==='all'?'on':''}">Vše<b>${nf.format(cur.length)}</b></button>`+
    ORDER.filter(t=>cnt[t]).map(t=>`<button data-t="${t}" class="${curType===t?'on':''}">${TYPES[t][0]}<b>${nf.format(cnt[t])}</b></button>`).join('');
  tabs.querySelectorAll('button').forEach(b=>b.onclick=()=>{curType=b.dataset.t;search(document.getElementById('hq').value);});
  shown=PAGE; draw(toks,raw);
  res.hidden=false;
  try{history.replaceState(null,'','?q='+encodeURIComponent(q.trim()));}catch(e){}
}
function draw(toks,raw){
  const list=curType==='all'?cur:cur.filter(i=>IDX[i][0]===curType);
  document.getElementById('resH').textContent=list.length?('Nalezeno '+nf.format(list.length)+' výsledků'):'Nic nenalezeno';
  document.getElementById('resHint').textContent=list.length?'klikněte pro detail v příslušné sekci':'';
  document.getElementById('resList').innerHTML=list.length?list.slice(0,shown).map(i=>card(i,toks,raw)).join(''):
    '<div class="empty">Zkuste jiné nebo méně slov — třeba jen kořen slova („chodník" → „chodn").</div>';
  const m=document.getElementById('resMore'); m.hidden=list.length<=shown;
  m.onclick=()=>{shown+=PAGE;draw(toks,raw);};
}
let tmr; const hq=document.getElementById('hq');
hq.addEventListener('input',()=>{clearTimeout(tmr);tmr=setTimeout(()=>search(hq.value),180);});
document.getElementById('hsamples').innerHTML='Zkuste: '+['chodník','koupaliště','Sokol','ČOV','veřejné osvětlení','pozemek'].map(s=>`<button>${s}</button>`).join('');
document.querySelectorAll('#hsamples button').forEach(b=>b.onclick=()=>{hq.value=b.textContent;search(hq.value);document.getElementById('res').scrollIntoView({behavior:'smooth'});});

// --- Moje ulice ---
const sel=document.getElementById('ulSel');
Object.keys(UL).forEach(nm=>{const o=document.createElement('option');o.value=nm;o.textContent=nm+' ('+UL[nm].i.length+')';sel.appendChild(o);});
let map,layer;
function showStreet(nm){
  const grid=document.getElementById('ulGrid'), meta=document.getElementById('ulMeta');
  if(!nm){grid.hidden=true;meta.textContent='';return;}
  const u=UL[nm]; grid.hidden=false;
  const ids=u.i.slice().sort((a,b)=>(IDX[b][3]||'').localeCompare(IDX[a][3]||''));
  meta.innerHTML=ids.length?`<b>${ids.length}</b> usnesení rady a zastupitelstva, nejnovější nahoře`:'v usneseních se ulice nevyskytuje';
  const toks=[];  // bez zvýraznění
  document.getElementById('ulList').innerHTML=ids.length?ids.map(i=>card(i,toks,[])).join(''):'<div class="empty">Žádná usnesení.</div>';
  if(!map){map=L.map('ulMap',{scrollWheelZoom:false});
    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19,attribution:'© OpenStreetMap'}).addTo(map);}
  if(layer)layer.remove(); layer=L.layerGroup().addTo(map);
  L.circle(u.g,{radius:90,color:'#d97706',weight:2,fillOpacity:.12}).addTo(layer).bindTooltip(nm);
  const pts=[u.g];
  u.p.forEach(p=>{const it=IDX[p[2]];pts.push([p[0],p[1]]);
    L.circleMarker([p[0],p[1]],{radius:6,color:'#3b82f6',weight:2,fillOpacity:.6}).addTo(layer)
     .bindPopup(`<b>${esc(it[1])}</b> · ${fd(it[3])}<br>${esc(it[2].slice(0,220))}${it[2].length>220?'…':''}<br><a href="${esc(it[4])}">detail →</a>`);});
  setTimeout(()=>{map.invalidateSize();if(pts.length>1)map.fitBounds(pts,{padding:[30,30],maxZoom:17});else map.setView(u.g,16);},50);
  try{history.replaceState(null,'','?ulice='+encodeURIComponent(nm));}catch(e){}
}
sel.onchange=()=>showStreet(sel.value);
(function(){const u=new URLSearchParams(location.search);
  if(u.get('q')){hq.value=u.get('q');search(hq.value);}
  else if(u.get('ulice')&&UL[u.get('ulice')]){sel.value=u.get('ulice');showStreet(sel.value);document.getElementById('ulsec').scrollIntoView();}
  else hq.focus();})();
bindTheme();
</script>'''.replace("DATA_JSON", data_json).replace("/*TEMAJS*/", pc.TEMA_JS)

html = pc.page("Hledat", "Hledat — Jak žijí Střelice", body, head_scripts=CSS, body_scripts=JS)
open("hledat.html", "w", encoding="utf-8").write(html)
print(f"HOTOVO: hledat.html — {len(IDX)} položek indexu, {len(STREETS)} ulic, {len(html)//1024} kB")
