#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Sekce Demografie (demografie.html) — vývoj počtu obyvatel Střelic.
Zdroj: ČSÚ, demografie obcí okresu Brno-venkov (stav k 1. 1., narození,
zemřelí, přistěhovalí, vystěhovalí) — data/skolstvi/cz0643_demografie.xlsx."""
import sys, json
import openpyxl
import portal_common as pc
sys.stdout.reconfigure(encoding="utf-8")

CHARTJS = open("data/vendor/chart.umd.js", encoding="utf-8").read()
wb = openpyxl.load_workbook("data/skolstvi/cz0643_demografie.xlsx", read_only=True, data_only=True)
rows = []
for r in wb["CZ0643"].iter_rows(min_row=2, values_only=True):
    if str(r[2]).strip() != "Střelice":
        continue
    rows.append({"rok": int(r[0]), "stav": int(r[4]), "nar": int(r[5]), "zem": int(r[6]),
                 "pri": int(r[7]), "vys": int(r[8])})
wb.close()
rows.sort(key=lambda x: x["rok"])
first, last = rows[0], rows[-1]
peak = max(rows, key=lambda x: x["stav"])
growth = (last["stav"] - first["stav"]) / first["stav"] * 100
r10 = [r for r in rows if r["rok"] > last["rok"] - 10]
nat10 = sum(r["nar"] - r["zem"] for r in r10)
mig10 = sum(r["pri"] - r["vys"] for r in r10)


def n(v):
    return f"{v:,}".replace(",", " ")


DATA = {"rows": rows}
data_json = json.dumps(DATA, ensure_ascii=False, separators=(",", ":"))

body = f'''<header class="hero">
  <h1>Jak Střelice rostou <span style="font-size:17px;font-weight:500;color:var(--muted)">· obyvatelé v číslech</span></h1>
  <p>Vývoj počtu obyvatel Střelic podle Českého statistického úřadu od roku {first["rok"]}: kolik lidí se narodilo a zemřelo a kolik se jich přistěhovalo a odstěhovalo.</p>
  <div class="chips"><span class="chip">obec Střelice · okres Brno-venkov</span><span class="chip">{first["rok"]}–{last["rok"]}</span><span class="chip">zdroj: ČSÚ</span></div>
</header>

<div class="cards" id="kpis"></div>

<section>
  <div class="sec-h"><h2>Vývoj počtu obyvatel</h2><span class="hint">stav k 1. 1. · {first["rok"]}–{last["rok"]}</span></div>
  <div class="panel">
    <div class="ctrls"><span class="lbl">Zobrazení</span>
      <span class="seg" id="popSeg"><button class="on" data-k="abs">počet obyvatel</button><button data-k="idx">index ({first["rok"]} = 100)</button></span></div>
    <div class="chartbox"><canvas id="popChart"></canvas></div>
    <p class="note">Od roku {first["rok"]} obec vyrostla o {growth:.0f} % (z {n(first["stav"])} na {n(last["stav"])} obyvatel), nejvíc obyvatel měla v roce {peak["rok"]} ({n(peak["stav"])}).</p>
  </div>
</section>

<section>
  <div class="sec-h"><h2>Odkud přírůstek pochází</h2><span class="hint">přirozený (narození − zemřelí) a migrační (přistěhovalí − vystěhovalí) přírůstek po letech</span></div>
  <div class="panel">
    <div class="chartbox"><canvas id="incChart"></canvas></div>
    <p class="note">Za posledních 10 let ({r10[0]["rok"]}–{last["rok"]}) činil přirozený přírůstek {nat10:+d} a migrační {mig10:+d} obyvatel. Údaj za rok je pohyb během roku; stav k 1. 1. následujícího roku z něj vychází (u let se sčítáním může ČSÚ stav ještě revidovat).</p>
  </div>
</section>

<section>
  <div class="sec-h"><h2>Narození, úmrtí a stěhování</h2><span class="hint">počty osob za rok</span></div>
  <div class="panel">
    <div class="legend" id="movLeg"></div>
    <div class="chartbox"><canvas id="movChart"></canvas></div>
    <p class="note" style="font-size:12.5px">Zdroj: <b>Český statistický úřad</b> — pohyb obyvatelstva v obcích okresu Brno-venkov. Další souvislosti v sekci <a href="skolstvi.html" style="color:var(--accent)">Školství</a>.</p>
  </div>
</section>'''

scripts = '<script>' + CHARTJS + '''</script>
<script>
const D=DATA_JSON, R=D.rows, YRS=R.map(d=>d.rok);
const nf=new Intl.NumberFormat('cs-CZ');
const charts={};
function axis(){return {grid:{color:isDark()?'#1f2a40':'#eef2f7'},ticks:{color:cssv('--muted')}};}
function mk(id,cfg){if(charts[id])charts[id].destroy();charts[id]=new Chart(document.getElementById(id),cfg);}
function kpis(){
  const L=R[R.length-1], F=R[0], P=R[R.length-2];
  const C=[
    ['Počet obyvatel '+L.rok, nf.format(L.stav), 'stav k 1. 1.','var(--c0)'],
    ['Růst od '+F.rok, '+'+((L.stav-F.stav)/F.stav*100).toFixed(0)+' %', 'z '+nf.format(F.stav)+' na '+nf.format(L.stav),'var(--c2)'],
    ['Narození '+L.rok, nf.format(L.nar), 'zemřelí: '+nf.format(L.zem),'var(--c3)'],
    ['Stěhování '+L.rok, (L.pri-L.vys>=0?'+':'')+(L.pri-L.vys), 'přistěhovalí '+L.pri+' · vystěhovalí '+L.vys,'var(--c1)'],
  ];
  document.getElementById('kpis').innerHTML=C.map(c=>`<div class="kpi" style="--bar:${c[3]}"><div class="lab">${c[0]}</div><div class="val">${c[1]}</div><div class="delta" style="color:var(--muted)">${c[2]}</div></div>`).join('');
}
let popMode='abs';
function popChart(){
  const base=R[0].stav, val=R.map(d=>popMode==='idx'?+(d.stav/base*100).toFixed(1):d.stav);
  mk('popChart',{type:'line',data:{labels:YRS,datasets:[{data:val,borderColor:cssv('--c0'),backgroundColor:'transparent',
    borderWidth:2.6,tension:.3,pointRadius:1.8,pointHoverRadius:6}]},
    options:{responsive:true,maintainAspectRatio:false,animation:{duration:600},
      plugins:{legend:{display:false},tooltip:{callbacks:{label:c=>popMode==='idx'
        ?'Index '+c.parsed.y+' ('+nf.format(R[c.dataIndex].stav)+' obyv.)':nf.format(c.parsed.y)+' obyvatel'}}},
      scales:{x:Object.assign(axis(),{ticks:{color:cssv('--muted'),autoSkip:true,maxTicksLimit:14}}),y:axis()}}});
}
function incChart(){
  mk('incChart',{type:'bar',data:{labels:YRS,datasets:[
    {label:'přirozený přírůstek',data:R.map(d=>d.nar-d.zem),backgroundColor:cssv('--c2'),stack:'s'},
    {label:'migrační přírůstek',data:R.map(d=>d.pri-d.vys),backgroundColor:cssv('--c1'),stack:'s'}]},
    options:{responsive:true,maintainAspectRatio:false,animation:{duration:600},
      plugins:{legend:{labels:{color:cssv('--muted')}},tooltip:{mode:'index',intersect:false,
        callbacks:{footer:it=>'celkem: '+it.reduce((a,x)=>a+x.parsed.y,0)}}},
      scales:{x:Object.assign(axis(),{stacked:true,ticks:{color:cssv('--muted'),autoSkip:true,maxTicksLimit:14}}),
        y:Object.assign(axis(),{stacked:true})}}});
}
const MOV=[['nar','narození','--c3'],['zem','zemřelí','--c4'],['pri','přistěhovalí','--c1'],['vys','vystěhovalí','--c5']];
function movChart(){
  document.getElementById('movLeg').innerHTML=MOV.map(m=>`<span><i class="sw" style="background:${cssv(m[2])}"></i>${m[1]}</span>`).join('');
  mk('movChart',{type:'line',data:{labels:YRS,datasets:MOV.map(m=>({label:m[1],data:R.map(d=>d[m[0]]),borderColor:cssv(m[2]),
    backgroundColor:'transparent',borderWidth:2,tension:.3,pointRadius:0,pointHitRadius:8}))},
    options:{responsive:true,maintainAspectRatio:false,animation:{duration:600},interaction:{mode:'index',intersect:false},
      plugins:{legend:{display:false}},
      scales:{x:Object.assign(axis(),{ticks:{color:cssv('--muted'),autoSkip:true,maxTicksLimit:14}}),y:Object.assign(axis(),{beginAtZero:true})}}});
}
function render(){kpis();popChart();incChart();movChart();}
render(); bindTheme(render);
document.querySelectorAll('#popSeg button').forEach(b=>b.onclick=()=>{document.querySelectorAll('#popSeg button').forEach(x=>x.classList.remove('on'));b.classList.add('on');popMode=b.dataset.k;popChart();});
window.addEventListener('load',()=>{Object.values(charts).forEach(c=>{try{c.resize();}catch(e){}});});
</script>'''.replace("DATA_JSON", data_json)

open("demografie.html", "w", encoding="utf-8").write(
    pc.page("Demografie", "Demografie — Jak žijí Střelice", body, body_scripts=scripts))
print(f"HOTOVO -> demografie.html ({len(rows)} let {first['rok']}-{last['rok']}, {last['stav']} obyv.)")
