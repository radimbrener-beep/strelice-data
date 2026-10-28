#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generuje sekci portálu 'Zakázky obce — komu obec platí' (zakazky.html).
Všechna usnesení RO+ZO s určitelnou firmou (zhotovitelem/dodavatelem)
a částkou — žebříček dodavatelů, vývoj po letech, tabulka zakázek.
Stejný styl jako dotace.html (Komu obec přispívá)."""
import sys, json, re
import portal_common as pc
from firmy import firm, firm_key, canon_name, dedup_projects, INCOME_RE, GIFT_RE, is_dodatek
sys.stdout.reconfigure(encoding="utf-8")

CHARTJS = open("data/vendor/chart.umd.js", encoding="utf-8").read()

ro = json.load(open("dataset_RO.json", encoding="utf-8"))
zo = json.load(open("dataset_ZO.json", encoding="utf-8"))

# zjevné ne-zakázky: uznání dluhu, splátkové kalendáře
_SKIP = re.compile(r"uznání dluhu|splátkov", re.IGNORECASE)

items = []
for src, mid in (("RO", ro), ("ZO", zo)):
    for m in mid:
        for b in m["body"]:
            c = b.get("castka")
            if not c or _SKIP.search(b["text"]) or INCOME_RE.search(b["text"]) or GIFT_RE.search(b["text"]):
                continue   # ne-zakázky, platby SMĚREM K obci (developeři) a dary
            f = firm(b["text"])
            if not f:
                continue
            items.append([m.get("datum") or "", c, src, m.get("cislo_zasedani"),
                          b["text"], m.get("url") or "", f])

items = dedup_projects(items)   # RO vyhodnocení ↔ ZO smlouva = jedna zakázka

# kanonizace názvu firmy: nejdřív ruční aliasy (překlepy — data/firmy_aliasy.json),
# pak nejčastější psaná varianta v rámci normalizovaného klíče
from collections import Counter, defaultdict
for it in items:
    it[6] = canon_name(it[6])
variants = defaultdict(Counter)
for it in items:
    variants[firm_key(it[6])][it[6]] += 1
canon = {k: v.most_common(1)[0][0] for k, v in variants.items()}
for it in items:
    it[6] = canon[firm_key(it[6])]

years = sorted({int(it[0][:4]) for it in items if it[0]})
# řádky pro JS: [rok, firma, castka, datum, zdroj, cislo, url, text, is_dodatek]
rows = [[int(it[0][:4]) if it[0] else 0, it[6], it[1], it[0], it[2], it[3], it[5],
         it[4][:300] + ("…" if len(it[4]) > 300 else ""), 1 if is_dodatek(it[4]) else 0]
        for it in items if it[0]]
rows.sort(key=lambda r: -r[2])

# vypsané zakázky z profilu zadavatele (scripts/fetch_profil_zakazky.py)
try:
    _pz = json.load(open("data/profil_zakazky.json", encoding="utf-8"))
except FileNotFoundError:
    _pz = {"profil": "", "zakazky": []}
PROFIL_URL = _pz["profil"]
# názvy firem tak, jak jsou na profilu (aliasy z usnesení by mohly sloučit různé firmy)
# [datum, název, url, stav, druh, dodavatel, cena, předpokl. hodnota, lhůta, nabídky[[firma, cena, vyloučen, vítěz]]]
pz = []
for z in _pz["zakazky"]:
    nab = [[n["firma"], n["cena"], 1 if n["vyloucen"] else 0,
            1 if z["dodavatel_ico"] and n["ico"] == z["dodavatel_ico"] else 0] for n in z["nabidky"]]
    nab.sort(key=lambda n: (n[1] is None, n[1] or 0))
    pz.append([z["datum"], z["nazev"], z["url"], z["stav"], z["druh"],
               z["dodavatel"], z["cena"],
               z["predpokladana_hodnota"], z["lhuta"], nab])
pz_nab = [len(z[9]) for z in pz if z[3] == "zadáno" and z[9]]
pz_od = min((z[0][:4] for z in pz), default="")
pz_lead = ""
if pz_nab:
    pz_lead = (f"Do zadaných zakázek přišlo v průměru <b>{sum(pz_nab) / len(pz_nab):.1f}</b> nabídky, "
               f"<b>{sum(1 for n in pz_nab if n == 1)}</b> z nich mělo jedinou nabídku.").replace(".", ",", 1)

DATA = {"years": years, "rows": rows, "pz": pz}
data_json = json.dumps(DATA, ensure_ascii=False, separators=(",", ":"))

n_firem = len({r[1] for r in rows})
n_zak = sum(1 for r in rows if not r[8])   # počet zakázek bez dodatků
total = sum(r[2] for r in rows)

body = '''<header class="hero">
  <h1>Zakázky obce <span style="font-size:17px;font-weight:500;color:var(--muted)">· komu obec platí</span></h1>
  <p>Firmy, které od obce Střelice získávají zakázky — stavby, opravy, projekty, dodávky i služby. Vytaženo z usnesení rady a zastupitelstva ''' + f"{years[0]}–{years[-1]}" + ''': kdo, kolik a za co. Doplňuje sekci <a href="investice.html" style="color:var(--accent)">Investice</a> (jen stavby) o kompletní pohled podle dodavatelů. Níže jsou i <a href="#vypsane" style="color:var(--accent)">zakázky vypsané na profilu zadavatele</a> — kdo podal nabídku a za kolik.</p>
  <div class="chips"><span class="chip">''' + str(n_zak) + ''' zakázek</span><span class="chip">''' + str(n_firem) + ''' firem</span><span class="chip">zdroj: usnesení RO a ZO</span><span class="chip">částky orientační z textů usnesení</span></div>
</header>

<div id="pzLive"></div>

<div class="cards" id="kpis"></div>

<section>
  <div class="sec-h"><h2>Objem zakázek po letech</h2><span class="hint">mil. Kč · klikni na sloupec roku pro detail</span></div>
  <div class="panel">
    <div class="chartbox sm"><canvas id="totChart"></canvas></div>
    <p class="note">Souhrn částek z usnesení, kde je uvedena firma i cena — typicky smlouvy o dílo, vyhodnocení zakázek, nabídky a dodávky. Částka je orientační (cena v okamžiku rozhodnutí, bez pozdějších dodatků, pokud nejsou v samostatném usnesení).</p>
  </div>
</section>

<section>
  <div class="sec-h"><h2>Kdo zakázky získává</h2><span class="hint">vyber rok, nebo souhrn všech let</span></div>
  <div class="ctrls"><span class="lbl">Období</span><span class="seg" id="yearSeg"></span></div>
  <div class="panel">
    <div class="sec-h" style="margin:0 0 8px"><h2 style="font-size:16px">Žebříček dodavatelů</h2><span class="hint" id="recHint"></span></div>
    <div class="chartbox" id="recBox"><canvas id="recChart"></canvas></div>
  </div>
  <div class="panel" style="margin-top:18px">
    <div class="sec-h" style="margin:0 0 8px;flex-wrap:wrap;gap:10px"><h2 style="font-size:16px">Dodavatelé ve vybraném období</h2>
      <input id="q" type="text" placeholder="hledat dodavatele / zakázku…" style="margin-left:auto">
      <button class="dlbtn" id="dlBtn" title="Stáhnout všechny zakázky za všechny roky jako CSV">⬇ Stáhnout vše (CSV)</button></div>
    <div class="tablewrap"><table id="tbl"><thead></thead><tbody>''' + pc.skel_tr(8) + '''</tbody></table></div>
    <div id="moreWrap"></div>
    <p class="note">Řazeno podle celkové částky za období. <b>Klikni na řádek firmy</b> — rozbalí se její jednotlivé zakázky. Zachyceny jsou jen zakázky, kde usnesení uvádí firmu (s.r.o., a.s., …) i částku — drobné nákupy bez usnesení, platby fyzickým osobám a faktury tu nejsou. Tatáž zakázka schválená radou i zastupitelstvem se počítá jednou. Plné texty najdete v sekcích <a href="zapisy.html" style="color:var(--accent)">Rada obce</a> a <a href="zastupitelstvo.html" style="color:var(--accent)">Zastupitelstvo</a>.</p>
  </div>
</section>

<section id="vypsane">
  <div class="sec-h"><h2>Vypsané zakázky</h2><span class="hint">profil zadavatele · ''' + f"{len(pz)} zakázek od roku {pz_od}" + '''</span></div>
  <div class="panel">
    <p class="pz-lead">Zakázky, které obec vypsala na svém <a href="''' + PROFIL_URL + '''" target="_blank" rel="noopener" style="color:var(--accent)">profilu zadavatele</a> — od výzvy přes nabídky až po vybranou firmu. ''' + pz_lead + '''</p>
    <div class="pz-ctrl"><span class="seg" id="pzSeg"></span><input id="pzQ" type="text" placeholder="hledat zakázku / firmu…"></div>
    <div class="tablewrap"><table id="pzTbl"><thead><tr><th>Vypsáno</th><th>Zakázka</th><th>Stav</th><th class="r">Nabídky</th><th>Vybraná firma</th><th class="r">Cena bez DPH</th></tr></thead><tbody></tbody></table></div>
    <div id="pzMore"></div>
    <p class="note"><b>Klikni na řádek</b> — rozbalí se všechny nabídky s cenami. Ceny jsou bez DPH tak, jak je obec uvedla na profilu; když smluvní cena chybí, je uvedena vítězná nabídka. „Předpokládaná hodnota" je odhad obce před soutěží. Na profilu jsou zakázky, které obec soutěžila elektronicky — menší nákupy a zakázky zadané napřímo tu nejsou (najdete je v tabulce dodavatelů výše podle usnesení). Nové zakázky se kontrolují automaticky třikrát denně.</p>
  </div>
</section>

<div class="modal" id="modal" hidden>
  <div class="modal-bd" id="modalBd"></div>
  <div class="modal-card"><div class="modal-h"><b id="modalT"></b><button class="iconbtn" id="modalX" aria-label="Zavřít">✕</button></div>
    <div class="modal-c" id="modalC"></div></div>
</div>
<style>
#tbl{width:100%;border-collapse:collapse;font-size:13.5px}
#tbl thead th{text-align:left;color:var(--muted);font-weight:600;font-size:11.5px;letter-spacing:.02em;
  padding:8px 14px 8px 0;border-bottom:1px solid var(--line)}
#tbl thead th.r{text-align:right}
#tbl tbody td{padding:11px 14px 11px 0;border-bottom:1px solid var(--line);vertical-align:top}
#tbl td.r{text-align:right;white-space:nowrap;font-variant-numeric:tabular-nums;font-weight:600}
#tbl td.dt{white-space:nowrap;color:var(--muted);font-size:12.5px}
#tbl td.ucel{color:var(--muted);line-height:1.5}
tr.grow{cursor:pointer;transition:background .12s}
tr.grow:hover{background:var(--inset)}
tr.grow td.fn{font-weight:600;white-space:nowrap}
tr.grow .car{display:inline-block;width:18px;color:var(--faint);font-size:11px;transition:transform .15s}
tr.grow.open .car{transform:rotate(90deg)}
.cnt{display:inline-block;font-size:11px;padding:2px 9px;border-radius:999px;background:var(--inset);color:var(--muted);border:1px solid var(--line);white-space:nowrap}
.cnt.dod{margin-left:5px;background:transparent;color:var(--faint)}
#q{font:inherit;font-size:13px;padding:7px 12px;border:1px solid var(--line);border-radius:10px;
  background:var(--surface);color:var(--text);outline:none;min-width:240px;transition:.16s}
#q:focus{border-color:var(--accent);box-shadow:0 0 0 3px var(--accent-soft)}
.dodtag{display:inline-block;font-size:10.5px;padding:1px 7px;border-radius:999px;background:var(--inset);color:var(--faint);border:1px solid var(--line);vertical-align:middle;margin-right:2px}
#tbl tr.sub td{background:var(--surface2);font-size:12.5px}
#tbl tr.sub td:first-child{padding-left:30px}
.zsrc{display:inline-block;font-size:11.5px;padding:2px 8px;border-radius:999px;background:var(--inset);color:var(--muted);text-decoration:none;border:1px solid var(--line);white-space:nowrap}
.zsrc:hover{color:var(--accent);border-color:var(--accent)}
.srccell{display:flex;flex-direction:column;gap:4px;align-items:flex-start}
.tablewrap{overflow-x:auto}
#pzTbl{width:100%;border-collapse:collapse;font-size:13.5px}
#pzTbl thead th{text-align:left;color:var(--muted);font-weight:600;font-size:11.5px;padding:8px 12px 8px 0;border-bottom:1px solid var(--line)}
#pzTbl th.r,#pzTbl td.r{text-align:right}
#pzTbl tbody td{padding:10px 12px 10px 0;border-bottom:1px solid var(--line);vertical-align:top}
#pzTbl td.r{white-space:nowrap;font-variant-numeric:tabular-nums}
#pzTbl td.dt{white-space:nowrap;color:var(--muted);font-size:12.5px}
#pzTbl tr.prow{cursor:pointer;transition:background .12s}
#pzTbl tr.prow:hover{background:var(--inset)}
#pzTbl tr.prow .car{display:inline-block;width:16px;color:var(--faint);font-size:11px;transition:transform .15s}
#pzTbl tr.prow.open .car{transform:rotate(90deg)}
#pzTbl .pzn{font-weight:600;margin-right:6px}
.pzsub{font-size:11.5px;color:var(--faint);margin-top:2px}
#pzTbl tr.nab td{background:var(--surface2);font-size:12.5px;padding-top:7px;padding-bottom:7px}
#pzTbl tr.nab td.zn{padding-left:16px}
#pzTbl tr.nab.win td{color:var(--text);font-weight:600}
#pzTbl tr.nab .vyl{color:var(--faint);text-decoration:line-through}
.pst{display:inline-block;font-size:11px;font-weight:600;padding:2px 9px;border-radius:999px;border:1px solid var(--line);white-space:nowrap}
.pst.zad{color:var(--c0);background:color-mix(in srgb,var(--c0) 12%,transparent)}
.pst.zru,.pst.bez{color:var(--muted);background:var(--inset)}
.pst.pro{color:var(--amber);background:color-mix(in srgb,var(--amber) 14%,transparent);border-color:color-mix(in srgb,var(--amber) 40%,transparent)}
.pz-lead{margin:0 0 12px;line-height:1.6}
.pz-ctrl{display:flex;flex-wrap:wrap;gap:10px;align-items:center;margin-bottom:8px}
#pzQ{font:inherit;font-size:13px;padding:7px 12px;border:1px solid var(--line);border-radius:10px;background:var(--surface);color:var(--text);outline:none;min-width:220px;margin-left:auto}
#pzQ:focus{border-color:var(--accent);box-shadow:0 0 0 3px var(--accent-soft)}
.pzlive{margin:18px 0 0;padding:14px 16px;border-radius:var(--radius);background:var(--surface);border:1px solid var(--line);border-left:4px solid var(--amber)}
.pzlive b{font-family:var(--font-d)}
.pzlive ul{margin:6px 0 0;padding-left:18px;line-height:1.6}
.morebtn{margin:14px auto 0;display:block;background:var(--inset);border:1px solid var(--line);color:var(--text);
  font:inherit;font-size:13px;font-weight:500;padding:9px 20px;border-radius:10px;cursor:pointer;transition:.16s}
.morebtn:hover{border-color:var(--accent);color:var(--accent)}
@media(max-width:640px){
  #tbl thead{display:none}
  #tbl,#tbl tbody{display:block}
  #tbl tbody tr{display:block;padding:12px 4px;border-bottom:1px solid var(--line)}
  #tbl tbody td{display:block;padding:2px 0;border:none;text-align:left}
  #tbl td.dt,#tbl td.firma,#tbl td.r{display:inline-block;vertical-align:middle;margin-right:8px}
  #pzTbl thead{display:none}
  #pzTbl,#pzTbl tbody{display:block}
  #pzTbl tbody tr{display:block;padding:10px 4px;border-bottom:1px solid var(--line)}
  #pzTbl tbody td{display:inline-block;padding:2px 10px 2px 0;border:none;text-align:left}
  #pzTbl tbody td:empty{display:none}
  #pzTbl tr.prow td.zn{display:block}
  #pzQ{margin-left:0;min-width:0;flex:1}
}
</style>'''

scripts = '<script>' + CHARTJS + '''</script>
<script>
const D=DATA_JSON, R=D.rows, YRS=D.years;
const nf=new Intl.NumberFormat('cs-CZ');
const charts={};
function axis(){return {grid:{color:cssv('--line')},ticks:{color:cssv('--muted')}};}
function mk(id,cfg){if(charts[id])charts[id].destroy();charts[id]=new Chart(document.getElementById(id),cfg);}
function castka(v){return v>=1e6?(v/1e6).toLocaleString('cs-CZ',{maximumFractionDigits:2})+' mil. Kč':nf.format(Math.round(v/1000))+' tis. Kč';}
function fmtDate(iso){if(!iso)return '—';const p=iso.split('-');return p[2]+'. '+(+p[1])+'. '+p[0];}
let year='vse', shown=15;
const PAGE=15;
function sel(){return year==='vse'?R:R.filter(r=>r[0]===+year);}

const barLabels={id:'barLabels',afterDatasetsDraw(ch){
  const {ctx}=ch;
  ch.getDatasetMeta(0).data.forEach((pt,j)=>{
    const v=ch.data.datasets[0].data[j];
    const {x,y}=pt.getProps(['x','y'],true);
    ctx.save();ctx.font='bold 11px sans-serif';
    ctx.fillStyle=cssv('--text');ctx.textAlign='center';ctx.textBaseline='bottom';
    ctx.fillText(v.toLocaleString('cs-CZ',{maximumFractionDigits:1})+' mil',x,y-3);
    ctx.restore();});
}};
function totChart(){
  const tot=YRS.map(y=>R.reduce((a,r)=>r[0]===y?a+r[2]:a,0)/1e6);
  mk('totChart',{type:'bar',data:{labels:YRS,datasets:[{data:tot,backgroundColor:YRS.map(y=>(''+y)===year?cssv('--c3'):cssv('--c0')),borderRadius:6,barPercentage:.6}]},
    options:{responsive:true,maintainAspectRatio:false,animation:{duration:500},layout:{padding:{top:20}},
      onClick:(e,a,ch)=>{const el=ch.getElementsAtEventForMode(e,'nearest',{intersect:true},true)[0];if(el)selectYear(''+YRS[el.index],true);},
      onHover:(e,els)=>{if(e.native&&e.native.target)e.native.target.style.cursor=els.length?'pointer':'default';},
      plugins:{legend:{display:false},tooltip:{callbacks:{label:c=>c.parsed.y.toLocaleString('cs-CZ',{maximumFractionDigits:2})+' mil. Kč'}}},
      scales:{x:Object.assign(axis(),{grid:{display:false}}),y:{display:false}}},
    plugins:[barLabels]});
}
function kpis(){
  const rr=sel(), tot=rr.reduce((a,r)=>a+r[2],0);
  const nz=rr.filter(r=>!r[8]).length, nd=rr.length-nz;
  const byf={}; rr.forEach(r=>byf[r[1]]=(byf[r[1]]||0)+r[2]);
  const ent=Object.entries(byf).sort((a,b)=>b[1]-a[1]); const top=ent[0]||['—',0];
  const lab=year==='vse'?YRS[0]+'–'+YRS[YRS.length-1]:year;
  const C=[
    ['Objem zakázek '+lab, castka(tot), nz+' zakázek'+(nd?' + '+nd+' dodatků':''),'var(--c0)'],
    ['Největší dodavatel', top[0].length>20?top[0].slice(0,18)+'…':top[0], castka(top[1])+' · '+(tot?Math.round(top[1]/tot*100):0)+' % objemu','var(--c3)'],
    ['Počet firem', String(ent.length), 'dodavatelů se zakázkou','var(--c1)'],
    ['Medián zakázky', castka(rr.length?rr.map(r=>r[2]).sort((a,b)=>a-b)[Math.floor(rr.length/2)]:0), 'polovina zakázek je menší','var(--c4)'],
  ];
  document.getElementById('kpis').innerHTML=C.map(c=>`<div class="kpi" style="--bar:${c[3]}"><div class="lab">${c[0]}</div><div class="val" style="font-size:${String(c[1]).length>13?'18':'24'}px">${c[1]}</div><div class="delta" style="color:var(--muted)">${c[2]}</div></div>`).join('');
}
function recChart(){
  const rr=sel(), byf={};
  rr.forEach(r=>byf[r[1]]=(byf[r[1]]||0)+r[2]);
  let arr=Object.entries(byf).sort((a,b)=>b[1]-a[1]);
  const TOP=25, rest=arr.length-TOP;
  if(arr.length>TOP)arr=arr.slice(0,TOP);
  document.getElementById('recHint').textContent=(year==='vse'?'všechny roky':year)+' · '
    +(rest>0?`top ${TOP} z ${rest+TOP} firem`:arr.length+' firem')+' · klikni na firmu';
  document.getElementById('recBox').style.height=Math.max(260,arr.length*26+40)+'px';
  mk('recChart',{type:'bar',data:{labels:arr.map(e=>e[0]),datasets:[{data:arr.map(e=>e[1]),backgroundColor:cssv('--c0'),borderRadius:4}]},
    options:{indexAxis:'y',responsive:true,maintainAspectRatio:false,animation:{duration:500},
      onClick:(e,a,ch)=>{const el=ch.getElementsAtEventForMode(e,'nearest',{intersect:true},true)[0];if(el)firmDetail(ch.data.labels[el.index]);},
      onHover:(e,els)=>{if(e.native&&e.native.target)e.native.target.style.cursor=els.length?'pointer':'default';},
      plugins:{legend:{display:false},tooltip:{callbacks:{label:c=>castka(c.parsed.x)}}},
      scales:{x:Object.assign(axis(),{ticks:{color:cssv('--muted'),callback:v=>(v/1e6)+' mil'}}),
        y:{ticks:{color:cssv('--text'),font:{size:11}},grid:{display:false}}}}});
}
let expanded=new Set(), gSort=['tot',true], q='';   // řazení skupin: tot | n | f
const norm=s=>(s||'').normalize('NFD').replace(/[\\u0300-\\u036f]/g,'').toLowerCase();
function srcLinks(r){
  const secUrl=(r[4]==='ZO'?'zastupitelstvo.html?zo=':'zapisy.html?ro=')+r[5];
  let s=`<a class="zsrc" href="${secUrl}" onclick="event.stopPropagation()">${r[4]} č.&nbsp;${r[5]}</a>`;
  if(r[6])s+=`<a class="zsrc" href="${r[6]}" target="_blank" rel="noopener" onclick="event.stopPropagation()" title="Originální zápis (PDF)">PDF&nbsp;&#8599;</a>`;
  return `<div class="srccell">${s}</div>`;
}
function table(){
  // seskupit po firmách, seřadit podle celkové částky za vybrané období
  const g={};
  sel().forEach(r=>{(g[r[1]]=g[r[1]]||[]).push(r);});
  const nq=norm(q);
  let entries=Object.entries(g);
  if(nq)entries=entries.filter(([f,rs])=>norm(f).includes(nq)||rs.some(r=>norm(r[7]).includes(nq)));
  const groups=entries.map(([f,rs])=>({f,n:rs.filter(r=>!r[8]).length,nd:rs.filter(r=>r[8]).length,
      tot:rs.reduce((a,r)=>a+r[2],0),
      rows:rs.slice().sort((a,b)=>(b[3]||'').localeCompare(a[3]||''))}));
  const [sk,sd]=gSort;
  groups.sort((a,b)=>{const A=a[sk],B=b[sk];
    const c=typeof A==='string'?A.localeCompare(B,'cs'):A-B; return sd?-c:c;});
  const slice=groups.slice(0,shown);
  const ar=k=>'<span class="ar">'+(k===sk?(sd?'▼':'▲'):'↕')+'</span>';
  document.querySelector('#tbl thead').innerHTML='<tr><th class="thsort" data-k="f">Dodavatel'+ar('f')+'</th>'
    +'<th class="thsort" data-k="n">Zakázky'+ar('n')+'</th><th class="r thsort" data-k="tot">Celkem'+ar('tot')+'</th><th></th></tr>';
  document.querySelectorAll('#tbl thead .thsort').forEach(th=>th.onclick=()=>{
    const k=th.dataset.k;
    gSort=[k, gSort[0]===k?!gSort[1]:k!=='f'];   // firma vzestupně, čísla sestupně
    table();});
  document.querySelector('#tbl tbody').innerHTML=slice.length?slice.map(gr=>{
    // shoda jen v textu zakázky (ne v názvu firmy) -> rovnou rozbalit, ať je vidět proč
    const open=expanded.has(gr.f)||(nq&&!norm(gr.f).includes(nq));
    const n=gr.n, pl=n===1?'zakázka':(n<5?'zakázky':'zakázek');
    const dbadge=gr.nd?`<span class="cnt dod">+${gr.nd} ${gr.nd<5?'dodatky':'dodatků'}</span>`:'';
    let h=`<tr class="grow${open?' open':''}" data-f="${gr.f.replace(/"/g,'&quot;')}">
      <td class="fn"><span class="car">▶</span>${gr.f}</td>
      <td><span class="cnt">${n} ${pl}</span>${dbadge}</td>
      <td class="r">${castka(gr.tot)}</td>
      <td>${year!=='vse'?`<a class="zsrc" href="#" data-hist="${gr.f.replace(/"/g,'&quot;')}">celá historie</a>`:''}</td></tr>`;
    if(open)h+=gr.rows.map(r=>
      `<tr class="sub"><td class="dt">${fmtDate(r[3])}</td>`+
      `<td class="ucel" colspan="1">${r[8]?'<span class="dodtag">dodatek</span> ':''}${r[7]}</td><td class="r">${castka(r[2])}</td><td>${srcLinks(r)}</td></tr>`).join('');
    return h;
  }).join(''):'<tr><td colspan="4" style="color:var(--faint);text-align:center;padding:22px">Nic nenalezeno — zkuste jiný výraz.</td></tr>';
  const wrap=document.getElementById('moreWrap');
  wrap.innerHTML=groups.length>shown?`<button class="morebtn" id="more">Zobrazit další firmy (${groups.length-shown})</button>`:'';
  const mb=document.getElementById('more'); if(mb)mb.onclick=()=>{shown+=PAGE;table();};
}
function firmDetail(name){
  const all=R.filter(r=>r[1]===name).sort((a,b)=>(a[3]||'').localeCompare(b[3]||''));
  if(!all.length)return;
  const tot=all.reduce((a,r)=>a+r[2],0);
  let h='<table class="mtab"><thead><tr><th>Datum</th><th>Částka</th><th>Předmět</th></tr></thead><tbody>';
  h+=all.map(r=>{
    const secUrl=(r[4]==='ZO'?'zastupitelstvo.html?zo=':'zapisy.html?ro=')+r[5];
    return `<tr><td style="white-space:nowrap">${fmtDate(r[3])}<br><a class="zsrc" href="${secUrl}">${r[4]} č.&nbsp;${r[5]}</a></td>`+
      `<td><b>${castka(r[2])}</b></td><td style="text-align:left;white-space:normal;color:var(--muted)">${r[7]}</td></tr>`;}).join('');
  h+=`<tr class="total"><td>Celkem (${all.length} ${all.length===1?'zakázka':(all.length<5?'zakázky':'zakázek')})</td><td>${castka(tot)}</td><td></td></tr></tbody></table>`;
  document.getElementById('modalT').textContent=name;
  document.getElementById('modalC').innerHTML=h;
  document.getElementById('modal').hidden=false;
}
function renderSel(){kpis();recChart();shown=PAGE;expanded=new Set();table();}
function selectYear(y,scroll){
  year=y;
  document.querySelectorAll('#yearSeg button').forEach(x=>x.classList.toggle('on',x.dataset.y===y));
  totChart();renderSel();
  if(scroll){const t=document.getElementById('yearSeg');if(t)t.scrollIntoView({behavior:'smooth',block:'start'});}
}
function render(){totChart();renderSel();}

document.getElementById('q').oninput=e=>{q=e.target.value.trim();shown=PAGE;table();};
document.getElementById('yearSeg').innerHTML='<button class="on" data-y="vse">Vše</button>'+YRS.map(y=>`<button data-y="${y}">${y}</button>`).join('');
document.querySelectorAll('#yearSeg button').forEach(b=>b.onclick=()=>selectYear(b.dataset.y));
document.querySelector('#tbl tbody').addEventListener('click',e=>{
  const hist=e.target.closest('a[data-hist]');
  if(hist){e.preventDefault();firmDetail(hist.dataset.hist);return;}
  const tr=e.target.closest('tr.grow');
  if(tr){const f=tr.dataset.f;expanded.has(f)?expanded.delete(f):expanded.add(f);table();}
});
document.getElementById('dlBtn').onclick=()=>dlCSV('strelice_zakazky_firmy.csv',
  ['rok','datum','firma','castka_kc','zdroj','zasedani','typ','predmet'],
  R.map(r=>[r[0],r[3],r[1],r[2],r[4],r[5],r[8]?'dodatek':'zakázka',r[7]]));
document.getElementById('modalX').onclick=()=>document.getElementById('modal').hidden=true;
document.getElementById('modalBd').onclick=()=>document.getElementById('modal').hidden=true;
document.addEventListener('keydown',e=>{if(e.key==='Escape')document.getElementById('modal').hidden=true;});
// --- vypsané zakázky (profil zadavatele) ---
const PZ=D.pz, PZST={'zadáno':'zad','zrušeno':'zru','probíhá':'pro','bez výsledku':'bez'};
let pzStav='vse', pzQ='', pzShown=PAGE; const pzOpen=new Set();
function kc(v){return v?nf.format(v)+'&nbsp;Kč':'—';}
function lhuta(l){if(!l)return '';const [d,t]=l.split('T');return fmtDate(d)+(t?' '+t:'');}
function pzTable(){
  const nq=norm(pzQ);
  let rr=PZ.filter(z=>pzStav==='vse'||z[3]===pzStav);
  if(nq)rr=rr.filter(z=>norm(z[1]).includes(nq)||z[9].some(n=>norm(n[0]).includes(nq)));
  document.querySelector('#pzTbl tbody').innerHTML=rr.length?rr.slice(0,pzShown).map(z=>{
    const id=z[2], open=pzOpen.has(id);
    const sub=[z[4], z[7]?'předpokládaná hodnota '+kc(z[7]):'', z[3]==='probíhá'&&z[8]?'nabídky do '+lhuta(z[8]):''].filter(Boolean).join(' · ');
    let h=`<tr class="prow${open?' open':''}" data-id="${id}"><td class="dt">${fmtDate(z[0])}</td>
      <td class="zn"><span class="car">${z[9].length?'▶':''}</span><span class="pzn">${z[1]}</span><a class="zsrc" href="${z[2]}" target="_blank" rel="noopener" onclick="event.stopPropagation()" title="Detail na profilu zadavatele">profil&nbsp;&#8599;</a>
        <div class="pzsub">${sub}</div></td>
      <td><span class="pst ${PZST[z[3]]}">${z[3]}</span></td>
      <td class="r">${z[9].length?z[9].length+'<span class="pzsub" style="display:inline"> nab.</span>':'—'}</td><td>${z[5]||'—'}</td><td class="r"><b>${kc(z[6])}</b></td></tr>`;
    if(open)h+=z[9].map(n=>`<tr class="nab${n[3]?' win':''}"><td></td><td class="zn"><span class="${n[2]?'vyl':''}">${n[0]}</span>${n[3]?' ✓ vybrána':''}${n[2]?' <span class="pzsub" style="display:inline">vyloučen / odstoupil</span>':''}</td><td></td><td></td><td></td><td class="r">${kc(n[1])}</td></tr>`).join('');
    return h;}).join(''):'<tr><td colspan="6" style="color:var(--faint);text-align:center;padding:22px">Nic nenalezeno.</td></tr>';
  document.getElementById('pzMore').innerHTML=rr.length>pzShown?`<button class="morebtn" id="pzMoreB">Zobrazit další zakázky (${rr.length-pzShown})</button>`:'';
  const mb=document.getElementById('pzMoreB'); if(mb)mb.onclick=()=>{pzShown+=PAGE;pzTable();};
}
if(PZ.length){
  const cnt=s=>PZ.filter(z=>z[3]===s).length;
  document.getElementById('pzSeg').innerHTML=[['vse','Vše ('+PZ.length+')'],...['probíhá','zadáno','zrušeno','bez výsledku'].filter(cnt).map(s=>[s,s[0].toUpperCase()+s.slice(1)+' ('+cnt(s)+')'])]
    .map(([k,l])=>`<button data-s="${k}"${k==='vse'?' class="on"':''}>${l}</button>`).join('');
  document.querySelectorAll('#pzSeg button').forEach(b=>b.onclick=()=>{pzStav=b.dataset.s;pzShown=PAGE;
    document.querySelectorAll('#pzSeg button').forEach(x=>x.classList.toggle('on',x===b));pzTable();});
  document.getElementById('pzQ').oninput=e=>{pzQ=e.target.value.trim();pzShown=PAGE;pzTable();};
  document.querySelector('#pzTbl tbody').addEventListener('click',e=>{const tr=e.target.closest('tr.prow');
    if(tr){const id=tr.dataset.id;pzOpen.has(id)?pzOpen.delete(id):pzOpen.add(id);pzTable();}});
  pzTable();
  const live=PZ.filter(z=>z[3]==='probíhá');
  if(live.length)document.getElementById('pzLive').innerHTML=`<div class="pzlive"><b>Právě vypsané zakázky</b>
    <ul>${live.map(z=>`<li><a href="${z[2]}" target="_blank" rel="noopener" style="color:var(--accent)">${z[1]}</a>${z[8]?' — nabídky do '+lhuta(z[8]):''}</li>`).join('')}</ul>
    <div class="pzsub">Podrobnosti v sekci <a href="#vypsane" style="color:var(--accent)">Vypsané zakázky</a>.</div></div>`;
} else document.getElementById('vypsane').hidden=true;

render();
// proklik z celostránkového hledání: ?firma=Název (otevře historii) nebo ?q=text
(function(){const u=new URLSearchParams(location.search),f=u.get('firma'),qq=u.get('q');
  if(qq){const i=document.getElementById('q');i.value=qq;q=qq.trim();shown=PAGE;table();}
  if(f&&R.some(r=>r[1]===f))firmDetail(f);})();
bindTheme(render);
window.addEventListener('load',()=>{Object.values(charts).forEach(c=>{try{c.resize();}catch(e){}});});
</script>'''.replace("DATA_JSON", data_json)

html = pc.page("Zakázky", "Zakázky obce — Jak žijí Střelice", body, body_scripts=scripts)
open("zakazky.html", "w", encoding="utf-8").write(html)
print(f"HOTOVO: zakazky.html — {len(rows)} zakázek, {n_firem} firem, {total/1e6:.1f} mil Kč, {years[0]}–{years[-1]}")
