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

DATA = {"years": years, "rows": rows}
data_json = json.dumps(DATA, ensure_ascii=False, separators=(",", ":"))

n_firem = len({r[1] for r in rows})
n_zak = sum(1 for r in rows if not r[8])   # počet zakázek bez dodatků
total = sum(r[2] for r in rows)

body = '''<header class="hero">
  <h1>Zakázky obce <span style="font-size:17px;font-weight:500;color:var(--muted)">· komu obec platí</span></h1>
  <p>Firmy, které od obce Střelice získávají zakázky — stavby, opravy, projekty, dodávky i služby. Vytaženo z usnesení rady a zastupitelstva ''' + f"{years[0]}–{years[-1]}" + ''': kdo, kolik a za co. Doplňuje sekci <a href="investice.html" style="color:var(--accent)">Investice</a> (jen stavby) o kompletní pohled podle dodavatelů.</p>
  <div class="chips"><span class="chip">''' + str(n_zak) + ''' zakázek</span><span class="chip">''' + str(n_firem) + ''' firem</span><span class="chip">zdroj: usnesení RO a ZO</span><span class="chip">částky orientační z textů usnesení</span></div>
</header>

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
    <div class="sec-h" style="margin:0 0 8px"><h2 style="font-size:16px">Dodavatelé ve vybraném období</h2>
      <button class="dlbtn" id="dlBtn" style="margin-left:auto" title="Stáhnout všechny zakázky za všechny roky jako CSV">⬇ Stáhnout vše (CSV)</button></div>
    <div class="tablewrap"><table id="tbl"><thead></thead><tbody></tbody></table></div>
    <div id="moreWrap"></div>
    <p class="note">Řazeno podle celkové částky za období. <b>Klikni na řádek firmy</b> — rozbalí se její jednotlivé zakázky. Zachyceny jsou jen zakázky, kde usnesení uvádí firmu (s.r.o., a.s., …) i částku — drobné nákupy bez usnesení, platby fyzickým osobám a faktury tu nejsou. Tatáž zakázka schválená radou i zastupitelstvem se počítá jednou. Plné texty najdete v sekcích <a href="zapisy.html" style="color:var(--accent)">Rada obce</a> a <a href="zastupitelstvo.html" style="color:var(--accent)">Zastupitelstvo</a>.</p>
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
.dodtag{display:inline-block;font-size:10.5px;padding:1px 7px;border-radius:999px;background:var(--inset);color:var(--faint);border:1px solid var(--line);vertical-align:middle;margin-right:2px}
#tbl tr.sub td{background:var(--surface2);font-size:12.5px}
#tbl tr.sub td:first-child{padding-left:30px}
.zsrc{display:inline-block;font-size:11.5px;padding:2px 8px;border-radius:999px;background:var(--inset);color:var(--muted);text-decoration:none;border:1px solid var(--line);white-space:nowrap}
.zsrc:hover{color:var(--accent);border-color:var(--accent)}
.srccell{display:flex;flex-direction:column;gap:4px;align-items:flex-start}
.tablewrap{overflow-x:auto}
.morebtn{margin:14px auto 0;display:block;background:var(--inset);border:1px solid var(--line);color:var(--text);
  font:inherit;font-size:13px;font-weight:500;padding:9px 20px;border-radius:10px;cursor:pointer;transition:.16s}
.morebtn:hover{border-color:var(--accent);color:var(--accent)}
@media(max-width:640px){
  #tbl thead{display:none}
  #tbl,#tbl tbody{display:block}
  #tbl tbody tr{display:block;padding:12px 4px;border-bottom:1px solid var(--line)}
  #tbl tbody td{display:block;padding:2px 0;border:none;text-align:left}
  #tbl td.dt,#tbl td.firma,#tbl td.r{display:inline-block;vertical-align:middle;margin-right:8px}
}
</style>'''

scripts = '<script>' + CHARTJS + '''</script>
<script>
const D=DATA_JSON, R=D.rows, YRS=D.years;
const nf=new Intl.NumberFormat('cs-CZ');
const charts={};
function axis(){return {grid:{color:isDark()?'#1f2a40':'#eef2f7'},ticks:{color:cssv('--muted')}};}
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
let expanded=new Set(), gSort=['tot',true];   // řazení skupin: tot | n | f
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
  const groups=Object.entries(g).map(([f,rs])=>({f,n:rs.filter(r=>!r[8]).length,nd:rs.filter(r=>r[8]).length,
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
  document.querySelector('#tbl tbody').innerHTML=slice.map(gr=>{
    const open=expanded.has(gr.f);
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
  }).join('');
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
render();
bindTheme(render);
window.addEventListener('load',()=>{Object.values(charts).forEach(c=>{try{c.resize();}catch(e){}});});
</script>'''.replace("DATA_JSON", data_json)

html = pc.page("Zakázky", "Zakázky obce — Jak žijí Střelice", body, body_scripts=scripts)
open("zakazky.html", "w", encoding="utf-8").write(html)
print(f"HOTOVO: zakazky.html — {len(rows)} zakázek, {n_firem} firem, {total/1e6:.1f} mil Kč, {years[0]}–{years[-1]}")
