#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stránka Odběry upozornění (odbery.html) — statistika Web Push upozornění.

Data se načtou živě ze serveru (push/api.php?a=stats), anonymně: bez adres a klíčů
zařízení. Druhy upozornění bere z portal_common.PUSH_TOPICS_UI, takže stejný soubor
funguje pro každou obec. Převzato z webu Střeličníku (new.strelicnik.cz/odbery/).
"""
import json
import sys

import portal_common as pc

sys.stdout.reconfigure(encoding="utf-8")

TOPIC = {k: t for k, t in pc.PUSH_TOPICS_UI}
TOPIC["zkouska"] = "Zkoušky"

body = '''<header class="hero">
  <h1>Odběry upozornění</h1>
  <p>Kolik zařízení má zapnutá upozornění z portálu, jak přibývají a kolik upozornění odešlo. O zařízení se ví jen to, přes jakou službu prohlížeče upozornění dostává; komu patří, se neukládá.</p>
</header>

<p class="note od-msg" role="status">Načítám…</p>

<section class="od-section" hidden>
  <div class="cards">
    <div class="kpi" style="--bar:var(--accent)"><div class="lab">Odebírá upozornění</div><div class="val" data-k="total">0</div><div class="delta" style="color:var(--muted)">zařízení</div></div>
    <div class="kpi" style="--bar:var(--c0)"><div class="lab">Doručeno do zařízení</div><div class="val" data-t="odeslano">0</div><div class="delta" style="color:var(--muted)">upozornění celkem</div></div>
    <div class="kpi" style="--bar:var(--c2)"><div class="lab">Zobrazeno na obrazovce</div><div class="val" data-t="zobrazeno">0</div><div class="delta" style="color:var(--muted)">hlásí zařízení samo</div></div>
    <div class="kpi" style="--bar:var(--c3)"><div class="lab">Přihlášení / odhlášení</div><div class="val"><span data-t="prihlaseni">0</span> / <span data-t="odhlaseni">0</span></div><div class="delta" style="color:var(--muted)">celkem</div></div>
  </div>

  <div class="grid2" style="margin-top:18px">
    <div class="panel"><div class="sec-h" style="margin:0 0 8px"><h2 style="font-size:16px">Odběratelé</h2><span class="hint">posledních 30 dní</span></div>
      <div class="od-plot" data-chart="subscribers" data-label="Odběratelé za posledních 30 dní"></div></div>
    <div class="panel"><div class="sec-h" style="margin:0 0 8px"><h2 style="font-size:16px">Doručená upozornění</h2><span class="hint">po dnech</span></div>
      <div class="od-plot" data-chart="sent" data-label="Doručená upozornění po dnech"></div></div>
  </div>

  <div class="od-split">
    <div class="panel"><h3>Co odebírají</h3><ul class="od-bars" data-list="topics"></ul></div>
    <div class="panel"><h3>Doručeno podle druhu</h3><ul class="od-bars" data-list="sent"></ul></div>
    <div class="panel"><h3>Prohlížeče</h3><ul class="od-bars" data-list="services"></ul></div>
  </div>

  <div class="panel" style="margin-top:18px">
    <details class="od-days"><summary>Tabulka po dnech</summary>
      <div class="od-table-wrap"><table class="mtab">
        <thead><tr><th>Den</th><th>Odběratelé</th><th>Přihlášeno</th><th>Odhlášeno</th><th>Doručeno</th><th>Zobrazeno</th><th>Nedoručeno</th></tr></thead>
        <tbody data-table="days"></tbody></table></div>
    </details>
  </div>
</section>

<section class="od-section" hidden>
  <div class="sec-h"><h2>Zařízení</h2><span class="hint">bez adres a klíčů, jen pořadí a služba prohlížeče</span></div>
  <div class="panel"><div class="od-table-wrap"><table class="mtab">
    <thead><tr><th>Č.</th><th>Přihlášeno</th><th>Prohlížeč</th><th>Odebírá</th><th>Naposledy doručeno</th></tr></thead>
    <tbody data-table="devices"></tbody></table></div></div>
  <p class="note">„Zobrazeno“ hlásí telefon nebo počítač sám, když upozornění ukáže. Upozornění si zapnete zvonkem v hlavičce stránky.</p>
</section>'''

CSS = """<style>
.od-plot svg{width:100%;height:auto;display:block}
.od-plot .od-grid{stroke:var(--line);stroke-width:1}
.od-plot .od-axis{fill:var(--muted);font-size:11px;font-family:var(--font-b)}
.od-plot .od-mark{fill:var(--c0)}
.od-plot .od-hit{fill:transparent}
.od-plot .od-bar:hover .od-mark{fill:var(--accent)}
.od-split{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,260px),1fr));gap:18px;margin-top:18px}
.od-split h3{font-size:15px;margin:0 0 10px}
.od-bars{list-style:none;margin:0;padding:0;display:flex;flex-direction:column;gap:8px;font-size:13px}
.od-bars li{display:grid;grid-template-columns:minmax(0,1.3fr) minmax(0,1fr) auto;gap:10px;align-items:center}
.od-bars .od-track{height:8px;border-radius:4px;background:var(--inset);overflow:hidden}
.od-bars .od-fill{display:block;height:100%;background:var(--c0);border-radius:4px}
.od-bars strong{font-variant-numeric:tabular-nums}
.od-bars li.empty{display:block;color:var(--muted)}
.od-days summary{cursor:pointer;font-weight:600;font-size:14px}
.od-table-wrap{overflow-x:auto;margin-top:6px}
.od-table-wrap .mtab td,.od-table-wrap .mtab th{text-align:left}
</style>"""

scripts = '''<script>
const TOPIC=TOPIC_JSON;
const fmt=iso=>{if(!iso)return 'zatím nic';const [y,m,d]=iso.split('-').map(Number);return d+'. '+m+'. '+y;};
const short=iso=>{const [,m,d]=iso.split('-').map(Number);return d+'. '+m+'.';};
const el=(tag,text)=>{const e=document.createElement(tag);if(text!=null)e.textContent=text;return e;};
const NS='http://www.w3.org/2000/svg';
const svgEl=(tag,attrs)=>{const e=document.createElementNS(NS,tag);for(const k in attrs)e.setAttribute(k,String(attrs[k]));return e;};
const msg=document.querySelector('.od-msg');

/* sloupcový graf jedné řady: osa y od nuly, popisky osy x u prvního, prostředního a posledního dne */
function bars(host,days,value,unit){
  const W=600,H=180,L=28,B=22,T=10, max=Math.max(1,...days.map(value)), step=(W-L)/days.length, bw=Math.max(2,step-2);
  const svg=svgEl('svg',{viewBox:'0 0 '+W+' '+H,role:'img','aria-label':host.dataset.label});
  for(const v of [...new Set([0,Math.ceil(max/2),max])]){const y=H-B-(v/max)*(H-B-T);
    svg.append(svgEl('line',{x1:L,x2:W,y1:y,y2:y,class:'od-grid'}));
    const t=svgEl('text',{x:L-6,y:y+4,class:'od-axis','text-anchor':'end'});t.textContent=String(v);svg.append(t);}
  days.forEach((d,i)=>{const v=value(d),h=(v/max)*(H-B-T),x=L+i*step+1,g=svgEl('g',{class:'od-bar'});
    g.append(svgEl('rect',{x:L+i*step,y:T,width:step,height:H-B-T,class:'od-hit'}));
    if(v>0) g.append(svgEl('rect',{x:x,y:H-B-h,width:bw,height:h,rx:Math.min(4,bw/2),class:'od-mark'}));
    const tip=svgEl('title',{});tip.textContent=fmt(d.date)+': '+v+' '+unit;g.append(tip);svg.append(g);});
  for(const i of [0,Math.floor(days.length/2),days.length-1]){
    const t=svgEl('text',{x:L+i*step+step/2,y:H-6,class:'od-axis','text-anchor':'middle'});t.textContent=short(days[i].date);svg.append(t);}
  host.replaceChildren(svg);
}
function barList(host,entries){
  host.replaceChildren();
  if(!entries.length){const li=el('li','zatím nic');li.className='empty';host.append(li);return;}
  const max=Math.max(1,...entries.map(e=>e[1]));
  for(const [name,n] of entries){const li=el('li'),track=el('span'),fill=el('span');
    track.className='od-track';fill.className='od-fill';fill.style.width=(n/max*100)+'%';track.append(fill);
    li.append(el('span',name),track,el('strong',String(n)));host.append(li);}
}
fetch('/push/api.php?a=stats',{cache:'no-store'})
  .then(r=>r.ok?r.json():Promise.reject(new Error(String(r.status))))
  .then(s=>{
    document.querySelector('[data-k="total"]').textContent=String(s.total);
    for(const k in (s.totals||{})){const c=document.querySelector('[data-t="'+k+'"]');if(c)c.textContent=String(s.totals[k]);}
    const days=s.daily||[];
    if(days.length){bars(document.querySelector('[data-chart="subscribers"]'),days,d=>d.subscribers,'odběratelů');
      bars(document.querySelector('[data-chart="sent"]'),days,d=>d.odeslano,'doručených upozornění');}
    barList(document.querySelector('[data-list="topics"]'),Object.entries(s.topics||{}).map(([k,n])=>[TOPIC[k]||k,n]));
    barList(document.querySelector('[data-list="sent"]'),Object.entries(s.sent_by_topic||{}).filter(([k,n])=>k!=='zkouska'||n>0).map(([k,n])=>[TOPIC[k]||k,n]));
    barList(document.querySelector('[data-list="services"]'),Object.entries(s.services||{}));
    const dayRows=document.querySelector('[data-table="days"]');
    for(const d of [...days].reverse()){const tr=el('tr');
      for(const v of [fmt(d.date),d.subscribers,d.prihlaseni,d.odhlaseni,d.odeslano,d.zobrazeno,d.nedoruceno]) tr.append(el('td',String(v)));
      dayRows.append(tr);}
    const body=document.querySelector('[data-table="devices"]');
    for(const d of (s.devices||[])){const tr=el('tr');
      tr.append(el('td',String(d.no)),el('td',fmt(d.since)),el('td',d.service),el('td',d.topics.map(t=>TOPIC[t]||t).join(', ')),
        el('td',fmt(d.last_ok)+(d.failures>0?' ('+d.failures+'× nedoručeno)':'')));
      body.append(tr);}
    if(!(s.devices||[]).length){const tr=el('tr'),td=el('td','Upozornění zatím nemá zapnutá žádné zařízení.');td.colSpan=5;tr.append(td);body.append(tr);}
    document.querySelectorAll('.od-section').forEach(x=>x.hidden=false);
    msg.textContent=s.total===0?'Upozornění zatím nemá zapnutá žádné zařízení. Zapnout je můžete zvonkem v hlavičce.':'';
    if(!msg.textContent) msg.hidden=true;
  })
  .catch(()=>{msg.textContent='Přehled se teď nepodařilo načíst. Zkuste to prosím později.';});
</script>'''.replace("TOPIC_JSON", json.dumps(TOPIC, ensure_ascii=False))

open("odbery.html", "w", encoding="utf-8").write(
    pc.page("Odběry", "Odběry upozornění — " + pc.BRAND, body, head_scripts=CSS, body_scripts=scripts))
print("HOTOVO: odbery.html (statistika upozornění, data živě z push/api.php?a=stats)")
