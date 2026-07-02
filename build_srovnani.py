#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generuje sekci portálu 'Srovnání se sousedy' (srovnani.html):
finanční zdraví obce (dluh, rezervy, saldo, investice — metodika MF) a
srovnání Střelic s okolními obcemi v přepočtu na obyvatele.
Vstup: data/srovnani_obce.json (build_srovnani_data.py)."""
import sys, json
import portal_common as pc
sys.stdout.reconfigure(encoding="utf-8")

CHARTJS = open("data/vendor/chart.umd.js", encoding="utf-8").read()
d = json.load(open("data/srovnani_obce.json", encoding="utf-8"))
YEARS = d["years"]
LY = YEARS[-1]

METRICS = ["prijmy", "vydaje", "kap", "saldo", "dluh", "ucty", "majetek"]
obce = []
for ico, o in d["obce"].items():
    roky = {int(k): v for k, v in o["roky"].items()}
    rec = {"n": o["nazev"], "pop": [roky[y]["pop"] for y in YEARS]}
    for m in METRICS:
        rec[m] = [roky[y][m] for y in YEARS]
    obce.append(rec)
# Střelice první, ostatní podle velikosti
obce.sort(key=lambda x: (x["n"] != "Střelice", -x["pop"][-1]))

# ---- finanční zdraví Střelic (poslední rok) ----
S = obce[0]
i_ly = len(YEARS) - 1
last5 = range(len(YEARS) - 5, len(YEARS))
avg_prijmy4 = sum(S["prijmy"][i] for i in range(len(YEARS) - 4, len(YEARS))) / 4
dluh_pct = S["dluh"][i_ly] / avg_prijmy4 * 100 if avg_prijmy4 else 0
bezne_ly = S["vydaje"][i_ly] - S["kap"][i_ly]
rezervy_mes = S["ucty"][i_ly] / (bezne_ly / 12) if bezne_ly else 0
saldo5 = sum(S["saldo"][i] for i in last5)
inv_podil5 = sum(S["kap"][i] for i in last5) / sum(S["vydaje"][i] for i in last5) * 100

def mil(v): return f"{v/1e6:.1f}".replace(".", ",")
def stav(ok, warn, val):  # semafor: (zelená_podmínka, oranžová_podmínka)
    return "ok" if ok else ("warn" if warn else "bad")

zdravi = [
    ("Dluh obce", ("0 Kč" if S["dluh"][i_ly] == 0 else mil(S["dluh"][i_ly]) + " mil"),
     f"{dluh_pct:.0f} % průměrných příjmů · limit fiskálního pravidla je 60 %",
     stav(dluh_pct < 30, dluh_pct < 60, dluh_pct),
     "Proč to sledovat: splátky dluhu ukrajují z budoucích rozpočtů. Obec bez dluhu má volné ruce na další investice."),
    ("Rezervy na účtech", mil(S["ucty"][i_ly]) + " mil",
     f"pokryjí ≈ {rezervy_mes:.0f} měsíců běžného provozu obce",
     stav(rezervy_mes >= 6, rezervy_mes >= 3, rezervy_mes),
     "Proč to sledovat: rezerva je polštář na nečekané výdaje a vlastní podíl k dotacím. Pod 3 měsíce provozu by byla obec zranitelná."),
    ("Saldo za 5 let", ("+" if saldo5 >= 0 else "−") + mil(abs(saldo5)) + " mil",
     f"souhrn {YEARS[-5]}–{LY} · rok {LY}: {'+' if S['saldo'][i_ly]>=0 else '−'}{mil(abs(S['saldo'][i_ly]))} mil",
     stav(saldo5 > -0.15 * avg_prijmy4, saldo5 > -0.4 * avg_prijmy4, saldo5),
     "Proč to sledovat: schodek v investiční vlně není sám o sobě problém — pokud se hradí z našetřených rezerv, ne z dluhu. Přesně to je případ Střelic."),
    ("Podíl investic", f"{inv_podil5:.0f} %",
     f"z výdajů {YEARS[-5]}–{LY} šlo na rozvoj majetku, ne na provoz",
     stav(inv_podil5 >= 20, inv_podil5 >= 10, inv_podil5),
     "Proč to sledovat: obec, která investuje, zhodnocuje svůj majetek. Pod 10 % by šly peníze hlavně na provoz."),
]
zdravi_html = ""
for lab, val, sub, st, why in zdravi:
    clr = {"ok": "var(--pos)", "warn": "var(--vydaje)", "bad": "var(--neg)"}[st]
    ikona = {"ok": "●", "warn": "●", "bad": "●"}[st]
    zdravi_html += f'''<div class="kpi" style="--bar:{clr}">
      <div class="lab">{lab} <span style="color:{clr};font-size:10px">{ikona}</span></div>
      <div class="val">{val}</div>
      <div class="delta" style="color:var(--muted)">{sub}</div>
      <div class="why">{why}</div></div>'''

DATA = {"years": YEARS, "obce": obce}
data_json = json.dumps(DATA, ensure_ascii=False, separators=(",", ":"))

sous_avg_inv = sum(sum(o["kap"][i] for i in last5) / sum(o["pop"][i] for i in last5) for o in obce[1:]) / len(obce[1:])
strel_inv = sum(S["kap"][i] for i in last5) / sum(S["pop"][i] for i in last5)

body = f'''<header class="hero">
  <h1>Srovnání se sousedy <span style="font-size:17px;font-weight:500;color:var(--muted)">· finanční zdraví obce</span></h1>
  <p>Jak si Střelice vedou vedle okolních obcí? Stejná data ze státní pokladny, stejný výpočet, přepočet na obyvatele — takže čísla jsou opravdu srovnatelná. A k tomu čtyři ukazatele finančního zdraví obce podle metodiky Ministerstva financí.</p>
  <div class="chips"><span class="chip">zdroj: MONITOR Státní pokladny (FIN 2-12 M + rozvaha)</span><span class="chip">obyvatelé: ČSÚ</span><span class="chip">{len(obce)} obcí · {YEARS[0]}–{LY}</span></div>
</header>

<section>
  <div class="sec-h"><h2>Finanční zdraví Střelic</h2><span class="hint">stav {LY} · semafor podle metodiky monitoringu MF</span></div>
  <div class="cards zdravi">{zdravi_html}</div>
</section>

<section>
  <div class="sec-h"><h2>Střelice vs. sousedé</h2><span class="hint">na obyvatele i celkem · přepínač platí pro grafy i tabulku</span></div>
  <div class="ctrls">
    <span class="lbl">Ukazatel</span><span class="seg" id="metSeg"></span>
    <span class="lbl" style="margin-left:8px">Období</span>
    <span class="seg" id="perSeg"><button class="on" data-p="ly">{LY}</button><button data-p="avg5">Ø {YEARS[-5]}–{LY}</button></span>
    <span class="lbl" style="margin-left:8px">Hodnoty</span>
    <span class="seg" id="pcSeg"><button class="on" data-c="1">na obyvatele</button><button data-c="0">celkem</button></span>
  </div>
  <div class="panel">
    <div class="chartbox" id="cmpBox"><canvas id="cmpChart"></canvas></div>
    <p class="note" id="cmpNote"></p>
  </div>
</section>

<section>
  <div class="sec-h"><h2>Vývoj v čase</h2><span class="hint">stejný ukazatel, {YEARS[0]}–{LY} · klikni na jméno v legendě pro skrytí</span></div>
  <div class="panel">
    <div class="legend" id="trLeg"></div>
    <div class="chartbox"><canvas id="trChart"></canvas></div>
    <p class="note">U menších obcí (Omice, Radostice, Silůvky — pod tisíc obyvatel) umí jedna velká stavba nebo prodej pozemků rozhoupat přepočet na obyvatele o desítky procent. Proto se dívejte spíš na trend než na jeden rok.</p>
  </div>
</section>

<section>
  <div class="sec-h"><h2>Přehledová tabulka</h2><span class="hint" id="tblHint">rok {LY}</span></div>
  <div class="panel">
    <div style="display:flex;justify-content:flex-end;margin-bottom:8px"><button class="dlbtn" id="dlCmp" title="Stáhnout tabulku jako CSV">⬇ Stáhnout CSV</button></div>
    <div class="tablewrap"><table id="cmpTbl"><thead></thead><tbody></tbody></table></div>
    <p class="note">Investice Střelic za posledních 5 let: <b>{strel_inv/1000:.0f} tis. Kč na obyvatele</b> (průměr sousedních obcí: {sous_avg_inv/1000:.0f} tis. Kč). Údaje jsou skutečnost z výkazu FIN 2-12 M bez konsolidace — všechny obce počítány stejně, čísla jsou vzájemně srovnatelná. Dluh = úvěry, dluhopisy a návratné výpomoci dle pravidel rozpočtové odpovědnosti (rozvaha). Podrobnosti v <a href="metodika.html" style="color:var(--accent)">metodice</a>.</p>
  </div>
</section>'''

styles = '''<style>
.legend .legi{cursor:pointer;border-radius:7px;padding:2px 8px;transition:.14s;user-select:none;border:1px solid transparent}
.legend .legi:hover{background:var(--inset);border-color:var(--line)}
.legend .legi.off{opacity:.35;text-decoration:line-through}
.zdravi{grid-template-columns:repeat(auto-fit,minmax(230px,1fr))}
.zdravi .kpi .why{font-size:11.5px;color:var(--faint);margin-top:9px;padding-top:9px;border-top:1px dashed var(--line);line-height:1.5}
#cmpTbl{width:100%;border-collapse:collapse;font-size:13px}
#cmpTbl th,#cmpTbl td{padding:9px 10px;text-align:right;white-space:nowrap;border-bottom:1px solid var(--line);font-variant-numeric:tabular-nums}
#cmpTbl th:first-child,#cmpTbl td:first-child{text-align:left}
#cmpTbl thead th{color:var(--muted);font-weight:600;font-size:11.5px}
#cmpTbl tr.hl td{background:var(--accent-soft);font-weight:600}
.tablewrap{overflow-x:auto}
</style>'''

scripts = styles + '<script>' + CHARTJS + '''</script>
<script>
const D=DATA_JSON, YRS=D.years, OB=D.obce, LYI=YRS.length-1;
const nf=new Intl.NumberFormat('cs-CZ');
const charts={};
function axis(){return {grid:{color:isDark()?'#1f2a40':'#eef2f7'},ticks:{color:cssv('--muted')}};}
function mk(id,cfg){if(charts[id])charts[id].destroy();charts[id]=new Chart(document.getElementById(id),cfg);}

const MET=[
 ['prijmy','Příjmy','celkové příjmy obce — daně (RUD), dotace, poplatky, nájmy i prodeje majetku'],
 ['vydaje','Výdaje','běžný provoz + investice'],
 ['kap','Investice','kapitálové výdaje — co obec vkládá do svého majetku'],
 ['dluh','Dluh','úvěry, dluhopisy a návratné výpomoci (fiskální pravidlo); stav k 31. 12.'],
 ['ucty','Rezervy','peníze na bankovních účtech obce k 31. 12.'],
 ['majetek','Majetek','účetní hodnota majetku obce (aktiva netto) — budovy, sítě, pozemky'],
 ['saldo','Saldo','příjmy − výdaje; záporné saldo hrazené z rezerv není dluh'],
];
let met='prijmy', per='ly', perCap=true;
const hidden=new Set();

function valOf(o,m,mode){
  if(mode==='ly') return perCap ? o[m][LYI]/o.pop[LYI] : o[m][LYI];
  let v=0,p=0; for(let i=YRS.length-5;i<YRS.length;i++){v+=o[m][i];p+=o.pop[i];}
  return perCap ? v/(p/5)/5 : v/5;
}
// hodnota do grafu (Kč/obyv. celé, celkem v mil.) + formátování
function chVal(v){return perCap ? Math.round(v) : +(v/1e6).toFixed(1);}
function fmtVal(v){return perCap ? nf.format(Math.round(v))+' Kč/obyv.'
  : (v/1e6).toLocaleString('cs-CZ',{maximumFractionDigits:1})+' mil. Kč';}
function unit(){return perCap ? 'Kč/obyv.' : 'mil. Kč';}

function cmpChart(){
  const mode=per, arr=OB.map(o=>({n:o.n,v:valOf(o,met,mode)})).sort((a,b)=>b.v-a.v);
  const mrec=MET.find(x=>x[0]===met);
  document.getElementById('cmpBox').style.height=Math.max(240,arr.length*34+60)+'px';
  document.getElementById('cmpNote').innerHTML='<b>'+mrec[1]+(perCap?' na obyvatele:':' celkem:')+'</b> '+mrec[2]+'.'
    +(met==='dluh'?' Nulový sloupec = obec bez dluhu.':'')
    +(perCap?'':' Pozor: v absolutních číslech větší obec „vyhrává" skoro vždy — férovější srovnání je na obyvatele.');
  mk('cmpChart',{type:'bar',data:{labels:arr.map(x=>x.n),datasets:[{data:arr.map(x=>chVal(x.v)),
    backgroundColor:arr.map(x=>x.n==='Střelice'?cssv('--accent'):cssv('--c8')),borderRadius:5}]},
    options:{indexAxis:'y',responsive:true,maintainAspectRatio:false,animation:{duration:450},
      plugins:{legend:{display:false},tooltip:{callbacks:{label:c=>nf.format(c.parsed.x)+' '+unit()+(per==='avg5'?' (Ø 5 let)':'')}}},
      scales:{x:Object.assign(axis(),{ticks:{color:cssv('--muted'),callback:v=>nf.format(v)}}),
        y:{ticks:{color:cssv('--text'),font:{size:12.5}},grid:{display:false}}}}});
}
// jména obcí přímo u konce čar (ať se nemusí luštit legenda)
const endLabels={id:'endLabels',afterDatasetsDraw(ch){
  const ctx=ch.ctx, items=[];
  ch.data.datasets.forEach((ds,i)=>{
    if(ds.hidden)return;
    const pts=ch.getDatasetMeta(i).data; if(!pts||!pts.length)return;
    const p=pts[pts.length-1];
    items.push({n:ds.label,x:p.x,y:p.y,c:ds.borderColor,bold:ds.label==='Střelice'});
  });
  items.sort((a,b)=>a.y-b.y);
  for(let i=1;i<items.length;i++) if(items[i].y-items[i-1].y<12.5) items[i].y=items[i-1].y+12.5;
  ctx.save();ctx.textBaseline='middle';ctx.textAlign='left';
  items.forEach(it=>{ctx.font=(it.bold?'700':'500')+' 11px "Segoe UI",sans-serif';
    ctx.fillStyle=it.c;ctx.fillText(it.n,it.x+7,it.y);});
  ctx.restore();
}};
function trChart(){
  const PALS=['--accent','--c1','--c2','--c3','--c4','--c5','--c6','--c7','--c9'];
  const ds=OB.map((o,i)=>({label:o.n,data:YRS.map((y,j)=>chVal(perCap?o[met][j]/o.pop[j]:o[met][j])),
    borderColor:cssv(PALS[i%PALS.length]),backgroundColor:'transparent',
    borderWidth:o.n==='Střelice'?3.2:1.6,pointRadius:o.n==='Střelice'?2.5:0,pointHitRadius:8,
    hidden:hidden.has(o.n),tension:.25}));
  document.getElementById('trLeg').innerHTML=OB.map((o,i)=>
    `<span class="legi${hidden.has(o.n)?' off':''}" data-n="${o.n}" title="Klikni pro skrytí/zobrazení"><i class="sw" style="background:${cssv(PALS[i%PALS.length])}"></i>${o.n}</span>`).join('');
  document.querySelectorAll('#trLeg .legi').forEach(el=>el.onclick=()=>{
    const n=el.dataset.n; hidden.has(n)?hidden.delete(n):hidden.add(n); trChart();});
  mk('trChart',{type:'line',data:{labels:YRS,datasets:ds},
    options:{responsive:true,maintainAspectRatio:false,animation:{duration:450},
      layout:{padding:{right:80}},
      plugins:{legend:{display:false},tooltip:{itemSort:(a,b)=>b.parsed.y-a.parsed.y,
        callbacks:{label:c=>' '+c.dataset.label+': '+nf.format(c.parsed.y)+' '+unit()}}},
      scales:{x:axis(),y:Object.assign(axis(),{ticks:{color:cssv('--muted'),callback:v=>nf.format(v)}})}},
    plugins:[endLabels]});
}
let tblSort=[1,true];   // [index sloupce, sestupně] — výchozí podle počtu obyvatel
function tbl(){
  const H=['Obec','Obyvatel','Příjmy','Výdaje','Investice','Dluh','Rezervy','Majetek'];
  const u=perCap?'Kč/ob.':'mil. Kč';
  document.querySelector('#cmpTbl thead').innerHTML='<tr>'+H.map((h,i)=>
    '<th class="thsort" data-i="'+i+'">'+h+(i>1?' <span style="font-weight:400">'+u+'</span>':'')
    +'<span class="ar">'+(i===tblSort[0]?(tblSort[1]?'▼':'▲'):'↕')+'</span></th>').join('')+'</tr>';
  document.getElementById('tblHint').textContent='rok '+YRS[LYI]+(perCap?', Kč na obyvatele':', mil. Kč celkem');
  const fv=v=>perCap?nf.format(Math.round(v)):(v/1e6).toLocaleString('cs-CZ',{minimumFractionDigits:1,maximumFractionDigits:1});
  const rows=OB.map(o=>({n:o.n,pop:o.pop[LYI],
    vals:['prijmy','vydaje','kap','dluh','ucty','majetek'].map(m=>perCap?o[m][LYI]/o.pop[LYI]:o[m][LYI])}));
  const [si,sd]=tblSort, kv=r=>si===0?r.n:(si===1?r.pop:r.vals[si-2]);
  rows.sort((a,b)=>{const A=kv(a),B=kv(b);
    const c=typeof A==='string'?A.localeCompare(B,'cs'):A-B; return sd?-c:c;});
  document.querySelector('#cmpTbl tbody').innerHTML=rows.map(r=>
    `<tr${r.n==='Střelice'?' class="hl"':''}><td>${r.n}</td><td>${nf.format(r.pop)}</td>`+
    r.vals.map(v=>'<td>'+fv(v)+'</td>').join('')+'</tr>').join('');
  document.querySelectorAll('#cmpTbl thead .thsort').forEach(th=>th.onclick=()=>{
    const i=+th.dataset.i;
    tblSort=[i, tblSort[0]===i?!tblSort[1]:i>0];   // texty vzestupně, čísla sestupně
    tbl();});
  tbl._rows=rows;
}
document.getElementById('metSeg').innerHTML=MET.map((m,i)=>`<button${i==0?' class="on"':''} data-m="${m[0]}">${m[1]}</button>`).join('');
document.querySelectorAll('#metSeg button').forEach(b=>b.onclick=()=>{
  document.querySelectorAll('#metSeg button').forEach(x=>x.classList.remove('on'));b.classList.add('on');
  met=b.dataset.m;cmpChart();trChart();});
document.querySelectorAll('#perSeg button').forEach(b=>b.onclick=()=>{
  document.querySelectorAll('#perSeg button').forEach(x=>x.classList.remove('on'));b.classList.add('on');
  per=b.dataset.p;cmpChart();});
document.querySelectorAll('#pcSeg button').forEach(b=>b.onclick=()=>{
  document.querySelectorAll('#pcSeg button').forEach(x=>x.classList.remove('on'));b.classList.add('on');
  perCap=b.dataset.c==='1';cmpChart();trChart();tbl();});
document.getElementById('dlCmp').onclick=()=>{
  const suf=perCap?'_kc_ob':'_kc';
  dlCSV('strelice_srovnani_obci'+(perCap?'_na_obyvatele':'_celkem')+'.csv',
    ['obec','obyvatel','prijmy'+suf,'vydaje'+suf,'investice'+suf,'dluh'+suf,'rezervy'+suf,'majetek'+suf],
    (tbl._rows||[]).map(r=>[r.n,r.pop].concat(r.vals.map(v=>Math.round(v)))));};
function redraw(){cmpChart();trChart();}
cmpChart();trChart();tbl();
bindTheme(redraw);
window.addEventListener('load',()=>{Object.values(charts).forEach(c=>{try{c.resize();}catch(e){}});});
</script>'''.replace("DATA_JSON", data_json)

html = pc.page("Srovnání", "Srovnání se sousedy — Jak žijí Střelice", body, body_scripts=scripts)
open("srovnani.html", "w", encoding="utf-8").write(html)
print(f"HOTOVO: srovnani.html — {len(obce)} obcí, {YEARS[0]}–{LY}")
