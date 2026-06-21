#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generuje sekci 'Rada obce' portálu (zapisy.html) — jednoduché procházení
zápisů z Rady obce Střelice 2022–2026. Hledání, filtr roku, tématu a objemu
výdaje; rozklikávací zasedání, u každého bodu druh (pruh + skupina), štítek
tématu a vyčíslená částka; grafy rozložení podle tématu a podle objemu výdaje.
Data (z dataset_RO.json vč. polí 'tema', 'castka') i Chart.js jsou vložené
přímo do souboru → funguje offline. Sdílené prvky z portal_common.py."""
import sys, json, os
import portal_common as pc
import temata
import vydaje
sys.stdout.reconfigure(encoding="utf-8")

CHARTJS = open("data/vendor/chart.umd.js", encoding="utf-8").read()
src = json.load(open("dataset_RO.json", encoding="utf-8"))
# geokodovane parcely (parc. cislo -> [lat, lon]); viz geocode_parcely.py
GEO_PATH = os.path.join("data", "parcely_geo.json")
parcely_geo = json.load(open(GEO_PATH, encoding="utf-8")) if os.path.exists(GEO_PATH) else {}

# --- kompaktni dataset pro stranku (bez raw_text) ---
cats = []          # druhy usneseni (schvaluje, ...)
def ci(c):
    if c not in cats:
        cats.append(c)
    return cats.index(c)

present = {b.get("tema", temata.OSTATNI) for r in src for b in r["body"]}
tlist = [t for t in temata.ORDER if t in present]
ti_index = {t: i for i, t in enumerate(tlist)}

meet = []
for r in sorted(src, key=lambda r: r["cislo_zasedani"]):
    meet.append({
        "n": r["cislo_zasedani"],
        "d": r["datum"],
        "y": r["rok"],
        "u": r["url"] or "",
        # polozka: [druh_idx, tema_idx, castka|null, text]
        "b": [[ci(b["kategorie"]), ti_index[b.get("tema", temata.OSTATNI)], b.get("castka"), b["text"]]
              for b in r["body"]],
    })

DATA = {"cats": cats, "temata": tlist, "vbuckets": vydaje.ORDER, "meet": meet, "pgeo": parcely_geo}
data_json = json.dumps(DATA, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")

# --- souhrnna cisla pro hero ---
n_m = len(meet)
n_i = sum(len(m["b"]) for m in meet)
yrs = sorted({m["y"] for m in meet})
n_tem = len([t for t in tlist if t != temata.OSTATNI])
def sp(n):
    return f"{n:,}".replace(",", " ")

# ---- CSS specificke pro tuto stranku ----
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
.zmt-dots{display:inline-flex;gap:4px;margin-left:auto}
.zmt-dots i{width:8px;height:8px;border-radius:2px;display:inline-block}
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
.ztag{display:inline-flex;align-items:center;gap:6px;font-size:11px;color:var(--muted);
  background:var(--inset);border:1px solid var(--line);padding:2px 9px 2px 8px;border-radius:999px;cursor:pointer}
.ztag:hover{color:var(--text);border-color:var(--accent)}
.ztag i{width:8px;height:8px;border-radius:2px;display:inline-block}
.zmoney{display:inline-flex;align-items:center;gap:6px;font-size:11.5px;font-weight:700;color:var(--text);
  background:var(--inset);border:1px solid var(--line);padding:2px 9px 2px 8px;border-radius:999px;cursor:pointer;
  font-variant-numeric:tabular-nums}
.zmoney:hover{border-color:var(--accent)}
.zmoney i{width:8px;height:8px;border-radius:2px;display:inline-block;background:var(--mc,var(--accent))}
.parc{color:var(--accent);text-decoration:none;border-bottom:1px dashed var(--accent);
  white-space:nowrap;font-variant-numeric:tabular-nums;cursor:pointer}
.parc:hover{background:var(--accent-soft);border-bottom-style:solid}
.parc::after{content:"\1F4CD";font-size:9px;margin-left:1px;vertical-align:super;opacity:.7}
.zpdf{font-size:12px;color:var(--accent);text-decoration:none;font-weight:600;white-space:nowrap;
  padding:3px 8px;border-radius:8px;border:1px solid var(--line)}
.zpdf:hover{border-color:var(--accent);background:var(--accent-soft)}
.empty{text-align:center;color:var(--muted);padding:42px 14px;font-size:14.5px}
.zmore{margin:16px auto 0;display:block;padding:10px 20px;border:1px solid var(--line);background:var(--surface);
  border-radius:12px;color:var(--accent);font-weight:600;cursor:pointer;font:inherit;font-size:13.5px}
.zmore:hover{border-color:var(--accent);background:var(--accent-soft)}
@media(max-width:680px){.zmt-date{min-width:0}.zmt-count{display:none}.zmt-h{gap:10px;padding:12px 13px}}
</style>"""

year_btns = '<button class="on" data-k="all">Vše</button>' + "".join(
    f'<button data-k="{y}">{y}</button>' for y in yrs)

body = '''<header class="hero">
  <h1>Zápisy z Rady obce</h1>
  <p>Procházejte usnesení Rady obce Střelice z volebního období 2022–2026. Hledejte v textu, filtrujte podle roku, tématu a objemu výdaje, otevřete si originální zápis v PDF a u parcelních čísel se proklikněte přímo do katastrální mapy.</p>
  <div class="chips">
    <span class="chip">''' + f"{yrs[0]}–{yrs[-1]}" + '''</span>
    <span class="chip">''' + f"{sp(n_m)} zasedání" + '''</span>
    <span class="chip">''' + f"{sp(n_i)} usnesení" + '''</span>
    <span class="chip">''' + f"{n_tem} tematických oblastí" + '''</span>
    <span class="chip">zdroj: streliceubrna.cz</span>
  </div>
</header>

<section>
  <div class="sec-h"><h2>Procházení zápisů</h2><span class="hint">klikni na zasedání pro rozbalení · hledání ignoruje diakritiku</span></div>
  <div class="panel">
    <div class="ctrlrow">
      <div class="zsearch">
        <span class="si">&#128269;</span>
        <input id="q" type="search" placeholder="Hledat v usneseních… (např. chodník, dotace, pozemek, smlouva)" autocomplete="off">
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
      <p class="note">Částka = nejvyšší hodnota v Kč uvedená v textu usnesení; jde o orientační ukazatel (nákupy, smlouvy, dotace). Vyloučeny jsou zjevné nevýdaje (převody na termínovaný vklad, pojistné hodnoty, inventarizace). Klikni na sloupec/štítek pro filtr.</p>
    </div>
  </div>
  <p class="note">Témata i částky jsou přiřazeny automaticky podle klíčových slov — orientační, u hraničních bodů se mohou překrývat. Osobní údaje fyzických osob nejsou v zápisech ze zákonných důvodů uváděny.</p>
</section>

<div class="footer">
  Data sestavena ze zápisů zveřejněných na <b>streliceubrna.cz</b> · sekce Rada obce Střelice 2022–2026.<br>
  Část portálu <b>Jak žijí Střelice</b> — otevřená data obce. Texty usnesení jsou přepisem oficiálních zápisů.
</div>'''

scripts = '<script>' + CHARTJS + '''</script>
<script>
const D=DATA_JSON, CATS=D.cats, TEMATA=D.temata, VBUCKETS=D.vbuckets, MEET=D.meet;
const PGEO=D.pgeo||{};   // parc. cislo -> [lat,lon] (k.u. Strelice u Brna)
const nf=new Intl.NumberFormat('cs-CZ');
const PAGE=20;
let q='', year='all', tema='all', vyd='all', sort='new', shown=PAGE;
const openSet=new Set();
const charts={};

// DRUH usneseni (barvy reaguji na tema)
const CATCOL={'schvaluje':'--pos','projednala':'--c3','bere na vědomí':'--c0','neschvaluje':'--neg','rozhodla':'--c4'};
const CATORDER=['schvaluje','projednala','bere na vědomí','neschvaluje','rozhodla'];
function catVar(c){return 'var('+(CATCOL[c]||'--c5')+')';}
function catOrd(c){const i=CATORDER.indexOf(c);return i<0?99:i;}

// TEMATA (paleta dle indexu; Ostatní = sedá)
const TPAL=['--c0','--c2','--c3','--c1','--c4','--c6','--c5','--c7','--c8','--c9','--prijmy','--vydaje','--pos','--neg','--accent'];
function temaName(name){return name==='Ostatní'?'--faint':TPAL[Math.max(0,TEMATA.indexOf(name))%TPAL.length];}
function temaVar(name){return 'var('+temaName(name)+')';}
function temaRGB(name){return cssv(temaName(name));}

// OBJEM VYDAJE — pasma (musi odpovidat vydaje.py)
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
function plurBod(n){return n===1?'bod':(n>=2&&n<=4?'body':'bodů');}
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

// parcelni cisla -> proklik do katastralni mapy (iKatastr nad mapy.cz, vrstva katastr)
const PARC_RE=/((?:p(?:arc)?\\.?\\s*č\\.?|parcel\\w*\\s*č\\.?)\\s*)(\\d{1,5}(?:\\/\\d{1,4})?)/gi;
// pokud bod zminuje jine k.u. nez Strelice, parcely nelinkujeme (souradnice mame jen pro Strelice)
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

// ---- chipy TEMAT ----
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

// ---- chipy OBJEMU VYDAJE ----
function buildVydChips(){
  const counts={};
  for(const m of MEET) for(const it of m.b){const b=vbucket(it[2]);counts[b]=(counts[b]||0)+1;}
  let html=`<span class="lbl">Hodnota</span><button class="chipbtn${vyd==='all'?' on':''}" data-v="all">Vše</button>`;
  for(const b of VBUCKETS){
    if(!counts[b] || b===VNONE) continue;   // "Bez částky" z filtru vyřazeno
    html+=`<button class="chipbtn${vyd===b?' on':''}" data-v="${esc(b)}"><span class="dotc" style="background:${vbVar(b)}"></span>${esc(b)} <b>${nf.format(counts[b])}</b></button>`;
  }
  const row=document.getElementById('vydRow'); row.innerHTML=html;
  row.querySelectorAll('.chipbtn').forEach(b=>b.onclick=()=>{vyd=b.dataset.v; shown=PAGE; buildVydChips(); render();});
}

// ---- filtrovani ----
function filtered(){
  const qf=fold(q);
  const itemMode = qf!=='' || tema!=='all' || vyd!=='all';
  const res=[];
  for(const m of MEET){
    if(year!=='all' && m.y!=+year) continue;
    let items=m.b;
    if(tema!=='all') items=items.filter(it=>TEMATA[it[1]]===tema);
    if(vyd!=='all') items=items.filter(it=>vbucket(it[2])===vyd);
    if(qf) items=items.filter(it=>fold(it[3]).indexOf(qf)>=0);
    if(itemMode && items.length===0) continue;
    res.push([m,items]);
  }
  res.sort((A,B)=> sort==='new' ? B[0].d.localeCompare(A[0].d) : A[0].d.localeCompare(B[0].d));
  return {res,itemMode,qf};
}

function cardHTML(m,items,open,qf){
  const present=[...new Set(items.map(it=>CATS[it[0]]))].sort((a,b)=>catOrd(a)-catOrd(b));
  const dots=present.map(c=>`<i style="background:${catVar(c)}" title="${esc(c)}"></i>`).join('');
  const cnt=items.length;
  let bodyHTML='';
  if(open){
    const byCat={};
    for(const it of items){(byCat[CATS[it[0]]]=byCat[CATS[it[0]]]||[]).push(it);}
    const groups=Object.keys(byCat).sort((a,b)=>catOrd(a)-catOrd(b));
    bodyHTML='<div class="zmt-body">'+groups.map(c=>{
      const col=catVar(c);
      const rows=byCat[c].map(it=>{
        const th=TEMATA[it[1]], amt=it[2];
        const money=amt!=null?`<span class="zmoney" data-v="${esc(vbucket(amt))}" title="Objem: ${esc(vbucket(amt))}"><i style="background:${vbVar(vbucket(amt))}"></i>${fmtKc(amt)}</span>`:'';
        const txt=linkifyParc(hl(it[3],qf), !OTHER_KU.test(it[3]));
        return `<div class="zitem" style="--ic:${col}"><div>${txt}</div>`+
               `<div class="ztags"><span class="ztag" data-t="${esc(th)}"><i style="background:${temaVar(th)}"></i>${esc(th)}</span>${money}</div></div>`;
      }).join('');
      return `<div class="zgrp"><div class="zgrp-h"><span class="dotc" style="background:${col}"></span>Rada obce ${esc(c)} · ${byCat[c].length}</div>${rows}</div>`;
    }).join('')+'</div>';
  }
  const pdf=m.u?`<a class="zpdf" href="${esc(m.u)}" target="_blank" rel="noopener" onclick="event.stopPropagation()">PDF&nbsp;&#8599;</a>`:'';
  return `<div class="zmt${open?' open':''}">
    <button class="zmt-h" data-n="${m.n}">
      <span class="zmt-num">RO ${m.n}</span>
      <span class="zmt-date">${fmtDate(m.d)}</span>
      <span class="zmt-count">${cnt} ${plurBod(cnt)}</span>
      <span class="zmt-dots">${dots}</span>
      ${pdf}
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
  if(!res.length){feed.innerHTML='<div class="empty">Žádné zápisy neodpovídají zadanému filtru. Zkuste jiný výraz nebo zrušte filtr.</div>';more.style.display='none';return;}
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
}

// ---- graf: TEMATA ----
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

// ---- graf: OBJEM VYDAJE (jen pasma s castkou) ----
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

// ---- ovladani ----
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
q=qIn.value||''; clr.style.display=q?'block':'none';   // sync po pripadnem obnoveni formulare prohlizecem
buildTemaChips(); buildVydChips(); render(); temaChart(); vydChart();
bindTheme(redraw);
window.addEventListener('load',()=>{Object.values(charts).forEach(c=>{try{c.resize();}catch(e){}});});
</script>'''.replace("DATA_JSON", data_json)

html = pc.page("Rada obce", "Zápisy z Rady obce — Jak žijí Střelice", body,
               head_scripts=PAGE_CSS, body_scripts=scripts)
open("zapisy.html", "w", encoding="utf-8").write(html)
print("HOTOVO: zapisy.html —", n_m, "zasedání,", n_i, "usnesení")
