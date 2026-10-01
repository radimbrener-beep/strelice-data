#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Sekce Volby (volby.html) — jak Střelice volí.
Komunální volby 2022 (složení zastupitelstva, zvolení), sněmovna 2021/2025,
prezident 2023 (2. kolo). Data v data/volby/strelice_volby.json."""
import sys, json
import portal_common as pc
sys.stdout.reconfigure(encoding="utf-8")

CHARTJS = open("data/vendor/chart.umd.js", encoding="utf-8").read()
DATA = json.load(open("data/volby/strelice_volby.json", encoding="utf-8"))
data_json = json.dumps(DATA, ensure_ascii=False, separators=(",", ":"))
kv = DATA["komunalni"]

body = f'''<header class="hero">
  <h1>Jak Střelice volí <span style="font-size:17px;font-weight:500;color:var(--muted)">· výsledky voleb</span></h1>
  <p>Složení zastupitelstva z komunálních voleb {kv["rok"]}, zvolení zastupitelé, a jak obec volí v celostátních volbách — sněmovna {DATA["snemovna"][1]["rok"]} a {DATA["snemovna"][0]["rok"]} a prezident {DATA["prezident"]["rok"]}.</p>
  <div class="chips"><span class="chip">obec Střelice · okres Brno-venkov</span><span class="chip">{kv["mandaty_celkem"]} zastupitelů</span><span class="chip">zdroj: ČSÚ · volby.cz</span></div>
</header>

<div class="cards" id="kpis"></div>

<section>
  <div class="sec-h"><h2>Zastupitelstvo obce</h2><span class="hint">komunální volby {kv["rok"]} · účast {str(kv["ucast"]).replace(".",",")} %</span></div>
  <div class="grid2">
    <div class="panel">
      <div class="sec-h" style="margin:0 0 8px"><h2 style="font-size:16px">Rozdělení mandátů</h2><span class="hint">{kv["mandaty_celkem"]} křesel</span></div>
      <div class="donutwrap"><div class="chartbox sm" style="max-width:320px"><canvas id="seatChart"></canvas></div>
        <div class="donut-center"><div class="t">mandátů</div><div class="v">{kv["mandaty_celkem"]}</div></div></div>
      <div class="legend" id="seatLeg" style="justify-content:center"></div>
    </div>
    <div class="panel">
      <div class="sec-h" style="margin:0 0 8px"><h2 style="font-size:16px">Zisk hlasů stran</h2></div>
      <div class="chartbox sm"><canvas id="partyChart"></canvas></div>
      <p class="note">Volič má tolik hlasů, kolik se volí zastupitelů ({kv["mandaty_celkem"]}), a může je rozdělit napříč stranami.</p>
    </div>
  </div>
  <div class="panel" style="margin-top:18px">
    <div class="sec-h" style="margin:0 0 10px"><h2 style="font-size:16px">Zvolení zastupitelé</h2><span class="hint">podle stran · s počtem přednostních hlasů</span></div>
    <div id="zast"></div>
    <p class="note" style="margin-top:12px">Práce zastupitelstva je v sekci <a href="zastupitelstvo.html" style="color:var(--accent)">Zastupitelstvo</a> (usnesení, hlasování, PDF zápisy).</p>
  </div>
</section>

<section>
  <div class="sec-h"><h2>Jak Střelice volí celostátně</h2><span class="hint">volby do Poslanecké sněmovny</span></div>
  <div class="grid2">
    <div class="panel">
      <div class="sec-h" style="margin:0 0 8px"><h2 style="font-size:16px">Sněmovna {DATA["snemovna"][0]["rok"]}</h2><span class="hint">účast {str(DATA["snemovna"][0]["ucast"]).replace(".",",")} %</span></div>
      <div class="chartbox sm"><canvas id="ps0"></canvas></div>
    </div>
    <div class="panel">
      <div class="sec-h" style="margin:0 0 8px"><h2 style="font-size:16px">Sněmovna {DATA["snemovna"][1]["rok"]}</h2><span class="hint">účast {str(DATA["snemovna"][1]["ucast"]).replace(".",",")} %</span></div>
      <div class="chartbox sm"><canvas id="ps1"></canvas></div>
    </div>
  </div>
  <p class="note"><b>SPOLU</b> v obou posledních sněmovních volbách vede (~37–40 %), <b>ANO</b> je druhé (~24–26 %). Účast v obci je vysoká (přes 75 %).</p>
</section>

<section>
  <div class="sec-h"><h2>Prezidentská volba {DATA["prezident"]["rok"]}</h2><span class="hint">2. kolo · účast {str(DATA["prezident"]["kolo2"]["ucast"]).replace(".",",")} %</span></div>
  <div class="panel">
    <div class="chartbox sm" style="max-width:560px"><canvas id="prez2"></canvas></div>
    <p class="note">Ve 2. kole ve Střelicích získal nejvíc hlasů <b>{max(DATA["prezident"]["kolo2"]["kandidati"], key=lambda k: k["pct"])["n"]}</b> ({str(max(DATA["prezident"]["kolo2"]["kandidati"], key=lambda k: k["pct"])["pct"]).replace(".",",")} %).</p>
  </div>
</section>

<section>
  <div class="panel">
    <p class="note" style="margin:0;font-size:12.5px">Zdroj: <b>Český statistický úřad</b>, <a href="https://www.volby.cz" target="_blank" rel="noopener" style="color:var(--accent)">volby.cz</a> — komunální volby {kv["rok"]}, sněmovna {DATA["snemovna"][1]["rok"]} a {DATA["snemovna"][0]["rok"]}, prezident {DATA["prezident"]["rok"]}. U sněmovních voleb jsou zobrazeny strany s alespoň ~1 % hlasů v obci. Data lze automaticky aktualizovat z otevřených dat volby.cz.</p>
  </div>
</section>'''

scripts = '<script>' + CHARTJS + '''</script>
<script>
const D=DATA_JSON, KV=D.komunalni, PS=D.snemovna, PZ=D.prezident;
const nf=new Intl.NumberFormat('cs-CZ');
const pct=v=>v.toLocaleString('cs-CZ',{minimumFractionDigits:2,maximumFractionDigits:2})+' %';
const charts={};
function axis(){return {grid:{color:isDark()?'#1f2a40':'#eef2f7'},ticks:{color:cssv('--muted')}};}
function mk(id,cfg){if(charts[id])charts[id].destroy();charts[id]=new Chart(document.getElementById(id),cfg);}
const PCOL={'SPOLU':'--c0','ANO':'--c3','STAN':'--c2','Piráti':'--c8','Piráti+STAN':'--c1',
  'SPD':'--c4','AUTO':'--c9','Stačilo!':'--c7','PŘÍSAHA':'--c6'};
const pcol=n=>cssv(PCOL[n]||'--c5');

function kpis(){
  const vit=KV.strany.reduce((a,s)=>s.mandaty>a.mandaty?s:a,KV.strany[0]);
  const C=[
    ['Účast · komunální '+KV.rok, pct(KV.ucast), KV.mandaty_celkem+' zastupitelů','var(--c0)'],
    ['Vítěz komunálních voleb', vit.zkratka, vit.mandaty+' z '+KV.mandaty_celkem+' mandátů','var(--c3)'],
    ['Kandidujících stran', String(KV.strany.length), 'v zastupitelstvu obce','var(--c1)'],
    ['Účast · sněmovna '+PS[0].rok, pct(PS[0].ucast), 'nad celostátním průměrem','var(--c2)'],
  ];
  document.getElementById('kpis').innerHTML=C.map(c=>`<div class="kpi" style="--bar:${c[3]}"><div class="lab">${c[0]}</div><div class="val" style="font-size:20px">${c[1]}</div><div class="delta" style="color:var(--muted)">${c[2]}</div></div>`).join('');
}
function seatChart(){
  const seated=KV.strany.filter(s=>s.mandaty>0);
  mk('seatChart',{type:'doughnut',data:{labels:seated.map(s=>s.zkratka),
    datasets:[{data:seated.map(s=>s.mandaty),backgroundColor:seated.map(s=>cssv(s.barva)),
      borderColor:cssv('--surface'),borderWidth:2,hoverOffset:6}]},
    options:{responsive:true,maintainAspectRatio:false,cutout:'62%',animation:{duration:600},
      plugins:{legend:{display:false},tooltip:{callbacks:{label:c=>c.label+': '+c.parsed+' mandátů'}}}}});
  document.getElementById('seatLeg').innerHTML=seated.map(s=>
    `<span><i class="sw" style="background:${cssv(s.barva)}"></i>${s.zkratka} · ${s.mandaty}</span>`).join('');
}
function partyChart(){
  const s=KV.strany;
  mk('partyChart',{type:'bar',data:{labels:s.map(x=>x.zkratka),datasets:[{label:'Hlasy',
    data:s.map(x=>x.pct),backgroundColor:s.map(x=>cssv(x.barva)),borderRadius:5}]},
    options:{indexAxis:'y',responsive:true,maintainAspectRatio:false,animation:{duration:600},
      plugins:{legend:{display:false},tooltip:{callbacks:{label:c=>pct(c.parsed.x)+' · '+nf.format(KV.strany[c.dataIndex].hlasy)+' hlasů · '+KV.strany[c.dataIndex].mandaty+' mand.'}}},
      scales:{x:Object.assign(axis(),{ticks:{color:cssv('--muted'),callback:v=>v+' %'}}),y:Object.assign(axis(),{ticks:{color:cssv('--muted')}})}}});
}
function zast(){
  const order=KV.strany.filter(s=>s.mandaty>0).map(s=>s.nazev);
  const byParty={}; KV.zastupitele.forEach(z=>{(byParty[z.strana]=byParty[z.strana]||[]).push(z);});
  const barva=n=>{const s=KV.strany.find(x=>x.nazev===n);return s?cssv(s.barva):cssv('--c5');};
  document.getElementById('zast').innerHTML=order.map(n=>{
    const list=(byParty[n]||[]).sort((a,b)=>b.hlasy-a.hlasy);
    return `<div style="margin-bottom:12px">
      <div style="display:flex;align-items:center;gap:8px;font-weight:600;font-size:13.5px;margin-bottom:6px">
        <i style="width:10px;height:10px;border-radius:3px;background:${barva(n)};display:inline-block"></i>${n}
        <span style="color:var(--muted);font-weight:500">· ${list.length} mand.</span></div>
      <div style="display:flex;flex-wrap:wrap;gap:8px">`+
      list.map(z=>`<span style="display:inline-flex;align-items:center;gap:8px;background:var(--inset);border:1px solid var(--line);border-radius:999px;padding:5px 12px;font-size:13px">
        ${z.jmeno}<b style="color:var(--muted);font-weight:600;font-variant-numeric:tabular-nums">${z.hlasy}</b></span>`).join('')+
      `</div></div>`;}).join('');
}
function psChart(id,rec){
  const s=rec.strany;
  mk(id,{type:'bar',data:{labels:s.map(x=>x.n),datasets:[{label:'Hlasy',
    data:s.map(x=>x.pct),backgroundColor:s.map(x=>pcol(x.n)),borderRadius:5}]},
    options:{indexAxis:'y',responsive:true,maintainAspectRatio:false,animation:{duration:600},
      plugins:{legend:{display:false},tooltip:{callbacks:{label:c=>pct(c.parsed.x)+' · '+nf.format(rec.strany[c.dataIndex].hlasy)+' hlasů'}}},
      scales:{x:Object.assign(axis(),{ticks:{color:cssv('--muted'),callback:v=>v+' %'}}),y:Object.assign(axis(),{ticks:{color:cssv('--muted')}})}}});
}
function prezChart(){
  const k=PZ.kolo2.kandidati;
  mk('prez2',{type:'bar',data:{labels:k.map(x=>x.n),datasets:[{label:'Hlasy',
    data:k.map(x=>x.pct),backgroundColor:[cssv('--c2'),cssv('--c3')],borderRadius:6,barPercentage:.6}]},
    options:{indexAxis:'y',responsive:true,maintainAspectRatio:false,animation:{duration:600},
      plugins:{legend:{display:false},tooltip:{callbacks:{label:c=>pct(c.parsed.x)+' · '+nf.format(k[c.dataIndex].hlasy)+' hlasů'}}},
      scales:{x:Object.assign(axis(),{max:100,ticks:{color:cssv('--muted'),callback:v=>v+' %'}}),y:Object.assign(axis(),{ticks:{color:cssv('--muted')}})}}});
}
function render(){kpis();seatChart();partyChart();zast();psChart('ps0',PS[0]);psChart('ps1',PS[1]);prezChart();}
render(); bindTheme(render);
window.addEventListener('load',()=>{Object.values(charts).forEach(c=>{try{c.resize();}catch(e){}});});
</script>'''.replace("DATA_JSON", data_json)

DONUT_CSS = """<style>
.donutwrap{position:relative;display:grid;place-items:center}
.donut-center{position:absolute;text-align:center;pointer-events:none}
.donut-center .t{font-size:11.5px;color:var(--muted)}
.donut-center .v{font-size:22px;font-weight:680;letter-spacing:-.02em}
</style>"""

open("volby.html", "w", encoding="utf-8").write(
    pc.page("Volby", "Volby — Jak žijí Střelice", body, head_scripts=DONUT_CSS, body_scripts=scripts))
print(f"HOTOVO -> volby.html (komunál {kv['rok']}, sněmovna {[p['rok'] for p in DATA['snemovna']]}, prezident {DATA['prezident']['rok']})")
