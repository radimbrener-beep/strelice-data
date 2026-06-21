#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generuje sekci portálu 'Komu obec přispívá' (dotace.html) z dat
data/dotace_strelice.csv (poskytnuté dotace spolkům 2022–2026)."""
import sys, csv, json
import portal_common as pc
sys.stdout.reconfigure(encoding="utf-8")

CHARTJS = open("data/vendor/chart.umd.js", encoding="utf-8").read()

rows = []
for r in csv.DictReader(open("data/dotace_strelice.csv", encoding="utf-8-sig"), delimiter=";"):
    try: amt = int(r["castka"])
    except: amt = 0
    rows.append([int(r["rok"]), r["prijemce"].strip(), amt, r["ucel"].strip()])
years = sorted({x[0] for x in rows})
DATA = {"years": years, "rows": rows}
data_json = json.dumps(DATA, ensure_ascii=False, separators=(",", ":"))

body = '''<header class="hero">
  <h1>Komu obec přispívá <span style="font-size:17px;font-weight:500;color:var(--muted)">· dotace spolkům</span></h1>
  <p>Dotace, které obec Střelice poskytla spolkům a organizacím v letech ''' + f"{years[0]}–{years[-1]}" + ''' — kolik, komu a na co. Zdroj: veřejnoprávní smlouvy zveřejněné obcí.</p>
  <div class="chips"><span class="chip">''' + str(len(rows)) + ''' smluv</span><span class="chip">zdroj: streliceubrna.cz</span><span class="chip">doplňuje agregované transfery v sekci Rozpočet</span></div>
</header>

<div class="cards" id="kpis"></div>

<section>
  <div class="sec-h"><h2>Celkem rozděleno po letech</h2><span class="hint">mil. Kč · klikni na sloupec roku pro detail</span></div>
  <div class="panel">
    <div class="chartbox sm"><canvas id="totChart"></canvas></div>
    <p class="note">Objem dotací spolkům roste — z ''' + f"{years[0]}" + ''' na ''' + f"{years[-1]}" + '''. Dominují dva sportovní kluby (TJ Sokol a FK Střelice), které dlouhodobě tvoří zhruba polovinu celkové částky.</p>
  </div>
</section>

<section>
  <div class="sec-h"><h2>Příjemci ve vybraném roce</h2><span class="hint">vyber rok</span></div>
  <div class="ctrls"><span class="lbl">Rok</span><span class="seg" id="yearSeg"></span></div>
  <div class="panel">
    <div class="sec-h" style="margin:0 0 8px"><h2 style="font-size:16px">Žebříček příjemců</h2><span class="hint" id="recHint"></span></div>
    <div class="chartbox" id="recBox"><canvas id="recChart"></canvas></div>
  </div>
  <div class="panel" style="margin-top:18px">
    <div class="sec-h" style="margin:0 0 8px"><h2 style="font-size:16px">Všechny dotace ve vybraném roce</h2></div>
    <div class="tablewrap"><table id="tbl"><thead></thead><tbody></tbody></table></div>
    <p class="note">Částka a účel jsou ze smlouvy o poskytnutí dotace. U několika smluv (zejm. SRPZŠ) není účel ve smlouvě jednotně uveden. <b>Klikni na příjemce</b> (ve žebříčku i v tabulce) pro jeho celou historii dotací.</p>
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
  padding:8px 16px 8px 0;border-bottom:1px solid var(--line);position:sticky;top:0;background:var(--surface);vertical-align:bottom}
#tbl tbody td{padding:11px 16px 11px 0;border-bottom:1px solid var(--line);vertical-align:top}
#tbl td:first-child,#tbl th:first-child{width:30%;min-width:180px;padding-right:22px}
#tbl td:first-child{line-height:1.4}
#tbl th:nth-child(2),#tbl td:nth-child(2){text-align:right;white-space:nowrap;font-variant-numeric:tabular-nums;
  width:104px;padding-right:26px}
#tbl td:nth-child(3){color:var(--muted);line-height:1.5}
#tbl tr.total td{font-weight:680;border-top:2px solid var(--text);background:var(--surface2);padding-top:12px;padding-bottom:12px}
#tbl tbody tr.clk{cursor:pointer;transition:background .12s}
#tbl tbody tr.clk:hover{background:var(--inset)}
</style>'''

scripts = '<script>' + CHARTJS + '''</script>
<script>
const D=DATA_JSON, R=D.rows, YRS=D.years;
const nf=new Intl.NumberFormat('cs-CZ');
const charts={};
function cv(n){return getComputedStyle(document.documentElement).getPropertyValue(n).trim();}
function axis(){return {grid:{color:isDark()?'#1f2a40':'#eef2f7'},ticks:{color:cv('--muted')}};}
function mk(id,cfg){if(charts[id])charts[id].destroy();charts[id]=new Chart(document.getElementById(id),cfg);}
const tt={backgroundColor:isDark()?'#0b1120':'#0f172a',titleColor:'#fff',bodyColor:'#e2e8f0',borderColor:cv('--accent'),borderWidth:1,padding:10,cornerRadius:9};
let year=YRS[YRS.length-1];

const barLabels={id:'barLabels',afterDatasetsDraw(ch){
  const {ctx}=ch;
  ch.data.datasets.forEach((_,i)=>{
    ch.getDatasetMeta(i).data.forEach((pt,j)=>{
      const v=ch.data.datasets[i].data[j];
      const {x,y}=pt.getProps(['x','y'],true);
      ctx.save();ctx.font='bold 11px sans-serif';
      ctx.fillStyle=cv('--text');ctx.textAlign='center';ctx.textBaseline='bottom';
      ctx.fillText(v.toLocaleString('cs-CZ',{maximumFractionDigits:2})+' mil.',x,y-3);
      ctx.restore();
    });
  });
}};
function totChart(){
  const tot=YRS.map(y=>R.reduce((a,r)=>r[0]==y?a+r[2]:a,0)/1e6);
  mk('totChart',{type:'bar',data:{labels:YRS,datasets:[{data:tot,backgroundColor:cv('--c0'),borderRadius:6,barPercentage:.6}]},
    options:{responsive:true,maintainAspectRatio:false,animation:{duration:500},layout:{padding:{top:20}},
      onClick:(e,a,ch)=>{const el=ch.getElementsAtEventForMode(e,'nearest',{intersect:true},true)[0];if(el)selectYear(YRS[el.index],true);},
      onHover:(e,els)=>{if(e.native&&e.native.target)e.native.target.style.cursor=els.length?'pointer':'default';},
      plugins:{legend:{display:false},tooltip:Object.assign({},tt,{callbacks:{label:c=>c.parsed.y.toLocaleString('cs-CZ',{maximumFractionDigits:2})+' mil. Kč'}})},
      scales:{x:Object.assign(axis(),{ticks:{color:cv('--muted')},grid:{display:false}}),y:{display:false}}},
    plugins:[barLabels]});
}
function kpis(){
  const yr=R.filter(r=>r[0]==year), tot=yr.reduce((a,r)=>a+r[2],0);
  const byrec={}; yr.forEach(r=>byrec[r[1]]=(byrec[r[1]]||0)+r[2]);
  const ent=Object.entries(byrec).sort((a,b)=>b[1]-a[1]); const top=ent[0]||['—',0];
  const n=ent.length;
  const C=[
    ['Rozděleno '+year, nf.format(tot)+' Kč', yr.length+' smluv','var(--c0)'],
    ['Největší příjemce', top[0].length>22?top[0].slice(0,20)+'…':top[0], nf.format(top[1])+' Kč','var(--c2)'],
    ['Počet příjemců', String(n), 'spolků a organizací','var(--c1)'],
    ['Dva největší příjemci', (ent.length>1?Math.round((ent[0][1]+ent[1][1])/tot*100):100)+' %', 'podíl na celkovém objemu','var(--c4)'],
  ];
  document.getElementById('kpis').innerHTML=C.map(c=>`<div class="kpi" style="--bar:${c[3]}"><div class="lab">${c[0]}</div><div class="val" style="font-size:${c[1].length>12?'18':'24'}px">${c[1]}</div><div class="delta" style="color:var(--muted)">${c[2]}</div></div>`).join('');
}
function recChart(){
  const yr=R.filter(r=>r[0]==year), byrec={};
  yr.forEach(r=>byrec[r[1]]=(byrec[r[1]]||0)+r[2]);
  const arr=Object.entries(byrec).sort((a,b)=>b[1]-a[1]);
  document.getElementById('recHint').textContent=year+' · '+arr.length+' příjemců · klikni na příjemce';
  document.getElementById('recBox').style.height=Math.max(260,arr.length*26+40)+'px';
  mk('recChart',{type:'bar',data:{labels:arr.map(e=>e[0]),datasets:[{data:arr.map(e=>e[1]),backgroundColor:cv('--c0'),borderRadius:4}]},
    options:{indexAxis:'y',responsive:true,maintainAspectRatio:false,animation:{duration:500},
      onClick:(e,a,ch)=>{const el=ch.getElementsAtEventForMode(e,'nearest',{intersect:true},true)[0];if(el)recDetail(ch.data.labels[el.index]);},
      onHover:(e,els)=>{if(e.native&&e.native.target)e.native.target.style.cursor=els.length?'pointer':'default';},
      plugins:{legend:{display:false},tooltip:Object.assign({},tt,{callbacks:{label:c=>nf.format(c.parsed.x)+' Kč'}})},
      scales:{x:Object.assign(axis(),{ticks:{color:cv('--muted'),callback:v=>v>=1000?(v/1000)+'k':v}}),y:{ticks:{color:cv('--text'),font:{size:11}},grid:{display:false}}}}});
}
function table(){
  const yr=R.filter(r=>r[0]==year).sort((a,b)=>b[2]-a[2]);
  document.querySelector('#tbl thead').innerHTML='<tr><th>Příjemce</th><th>Částka</th><th>Účel (přibližně)</th></tr>';
  document.querySelector('#tbl tbody').innerHTML=yr.map(r=>
    `<tr class="clk" data-r="${r[1].replace(/"/g,'&quot;')}"><td>${r[1]}</td><td><b>${nf.format(r[2])}</b></td><td style="text-align:left;white-space:normal;color:var(--muted)">${r[3]||'—'}</td></tr>`).join('')+
    `<tr class="total"><td>Celkem ${year}</td><td>${nf.format(yr.reduce((a,r)=>a+r[2],0))}</td><td></td></tr>`;
}
function recDetail(name){
  const all=R.filter(r=>r[1]===name).sort((a,b)=>a[0]-b[0]);
  if(!all.length)return;
  const tot=all.reduce((a,r)=>a+r[2],0), yrs=new Set(all.map(r=>r[0])).size;
  let h='<table class="mtab"><thead><tr><th>Rok</th><th>Částka</th><th>Účel (přibližně)</th></tr></thead><tbody>';
  h+=all.map(r=>`<tr><td>${r[0]}</td><td><b>${nf.format(r[2])}</b></td><td style="text-align:left;white-space:normal">${r[3]||'—'}</td></tr>`).join('');
  h+=`<tr class="total"><td>Celkem (${yrs} ${yrs==1?'rok':(yrs<5?'roky':'let')})</td><td>${nf.format(tot)}</td><td></td></tr></tbody></table>`;
  document.getElementById('modalT').textContent=name;
  document.getElementById('modalC').innerHTML=h;
  document.getElementById('modal').hidden=false;
}
function renderYear(){kpis();recChart();table();}
function selectYear(y,scroll){
  year=y;
  document.querySelectorAll('#yearSeg button').forEach(x=>x.classList.toggle('on',+x.dataset.y===y));
  renderYear();
  if(scroll){const t=document.getElementById('yearSeg');if(t)t.scrollIntoView({behavior:'smooth',block:'start'});}
}
function render(){totChart();renderYear();}

document.getElementById('yearSeg').innerHTML=YRS.map(y=>`<button data-y="${y}"${y==year?' class="on"':''}>${y}</button>`).join('');
render();
if(typeof bindTheme==='function')bindTheme(render);
document.querySelectorAll('#yearSeg button').forEach(b=>b.onclick=()=>selectYear(+b.dataset.y));
document.querySelector('#tbl tbody').addEventListener('click',e=>{const tr=e.target.closest('tr.clk[data-r]');if(tr)recDetail(tr.dataset.r);});
document.getElementById('modalX').onclick=()=>document.getElementById('modal').hidden=true;
document.getElementById('modalBd').onclick=()=>document.getElementById('modal').hidden=true;
document.addEventListener('keydown',e=>{if(e.key==='Escape')document.getElementById('modal').hidden=true;});
window.addEventListener('load',()=>{Object.values(charts).forEach(c=>{try{c.resize();}catch(e){}});});
</script>'''.replace("DATA_JSON", data_json)

open("dotace.html", "w", encoding="utf-8").write(
    pc.page("Dotace spolkům", "Komu obec přispívá — Jak žijí Střelice", body, body_scripts=scripts))
print(f"HOTOVO: dotace.html ({len(rows)} dotací, {years[0]}–{years[-1]}, bez oblastí)")
