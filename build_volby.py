#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Sekce Volby (volby.html) — jak Střelice volí.

Hlavní část: komunální volby 2026 (data/volby/strelice_kv2026.json ze
scripts/fetch_kv2026.py) — nové zastupitelstvo, srovnání s rokem 2022, preferenční
hlasy a posuny v pořadí, výpočet mandátů, okrsky, věk a pohlaví.
(Celostátní volby — sněmovna, prezident — byly ze stránky na přání odebrány; data zůstávají
v data/volby/strelice_volby.json, odkud fetch_kv2026.py bere komunální volby 2022 ke srovnání.)"""
import sys, json, math
import portal_common as pc
sys.stdout.reconfigure(encoding="utf-8")

kv = json.load(open("data/volby/strelice_kv2026.json", encoding="utf-8"))

# --- strany: krátké názvy, barvy (stejné jako v roce 2022) a protějšek z roku 2022 ---
PARTY = {
    # barvy kandidátek podle uživatele: KDU žlutá, Střeličník tyrkysová, nezávislí šedá, STAN magenta
    # (pastelové tóny pro světlý i tmavý režim jsou v CSS níže: --p-kdu, --p-str, --p-snk, --p-stan)
    1: ("KDU-ČSL a nestraníci", "--p-kdu", "KDU-ČSL a nestraníci"),
    2: ("Střeličník a nezávislí", "--p-str", "Sdružení občanů Střeličník"),
    3: ("Sdružení nezávislých kandidátů", "--p-snk", "Sdružení nezávislých kandidátů Střelice"),
    4: ("Starostové a nezávislí", "--p-stan", "STAROSTOVÉ A NEZÁVISLÍ"),
}
prev = {s["nazev"]: s for s in kv["prev"]["strany"]}
for s in kv["strany"]:
    kr, col, prevname = PARTY[s["c"]]
    s["kratky"], s["barva"] = kr, col
    p = prev.get(prevname)
    s["prev"] = {"pct": p["pct"], "mandaty": p["mandaty"], "nazev": p["nazev"]} if p else None
kv["strany"].sort(key=lambda s: -s["hlasy"])                 # kandidátky od nejsilnější
used_prev = {PARTY[c][2] for c in PARTY}
missing = [s for n, s in prev.items() if n not in used_prev]      # strany z 2022, které nekandidovaly

# --- výpočet mandátů (d'Hondt, jak ho uvádí ČSÚ: hlasy / 1, 2, 3, …) ---
M = kv["mandaty"]
quot = sorted(((v, s["c"], i + 1) for s in kv["strany"] for i, v in enumerate(s["podily"])), reverse=True)
win = quot[:M]
q_last, q_first_out = win[-1][0], quot[M][0]
for s in kv["strany"]:
    m = s["mandaty"]
    s["chybi"] = max(0, math.floor(q_last * (m + 1) - s["hlasy"]) + 1)     # hlasů k dalšímu mandátu
assert all(sum(1 for w in win if w[1] == s["c"]) == s["mandaty"] for s in kv["strany"]), "d'Hondt nesedí s ČSÚ"

# --- kandidáti: kdo překročil hranici pro přednostní postup ---
for k in kv["kandidati"]:
    s = next(x for x in kv["strany"] if x["c"] == k["strana"])
    k["nad_hranici"] = k["hlasy"] >= s["hranice"]

zv = [k for k in kv["kandidati"] if k["zvolen"]]
S = {
    "pokracuje": sum(k["pokracuje"] for k in zv), "novi": sum(not k["pokracuje"] for k in zv),
    "zen_kand": sum(k["zena"] for k in kv["kandidati"]), "zen_zv": sum(k["zena"] for k in zv),
    "vek_kand": round(sum(k["vek"] for k in kv["kandidati"]) / len(kv["kandidati"]), 1),
    "vek_zv": round(sum(k["vek"] for k in zv) / len(zv), 1),
    "bezpp_zv": sum(k["prislusnost"] == "bez politické příslušnosti" for k in zv),
    "q_last": round(q_last, 2), "q_first_out": round(q_first_out, 2),
    "win": [[round(v, 2), c, d] for v, c, d in win],
    "missing": [{"nazev": s["nazev"], "pct": s["pct"]} for s in missing],
}
kv["S"] = S
u = kv["ucast"]
dp = round(u["pct"] - kv["prev"]["ucast"], 2)
top = max(kv["kandidati"], key=lambda k: k["hlasy"])
gen = kv["generovano"]
gen_txt = f'{int(gen[8:10])}. {int(gen[5:7])}. {gen[:4]}'


def f2(v, d=2):
    return f"{v:.{d}f}".replace(".", ",")


def cz(n):
    return f"{n:,}".replace(",", " ")


body = f'''<header class="hero">
  <h1>Komunální volby 2026 <span style="font-size:17px;font-weight:500;color:var(--muted)">· Střelice</span></h1>
  <p>Kdo zasedne v zastupitelstvu na příští čtyři roky, jak dopadly kandidátky proti roku {kv["prev"]["rok"]}, jak preferenční hlasy přeskládaly pořadí kandidátů a jak se hlasy přepočítaly na mandáty. Volby proběhly {kv["datum"]}.</p>
  <div class="chips"><span class="chip">{M} zastupitelů</span><span class="chip">{len(kv["strany"])} kandidátky · {len(kv["kandidati"])} kandidátů</span><span class="chip">2 volební okrsky</span><span class="chip">zdroj: ČSÚ · volby.gov.cz</span></div>
</header>

<div class="cards">
  <div class="kpi" style="--bar:var(--c0)"><div class="lab">Volební účast</div><div class="val">{f2(u["pct"])} %</div>
    <div class="delta {'up' if dp >= 0 else 'down'}">{'▲' if dp >= 0 else '▼'} {f2(abs(dp))} p. b. proti {kv["prev"]["rok"]}</div></div>
  <div class="kpi" style="--bar:var(--c1)"><div class="lab">Přišlo volit</div><div class="val">{cz(u["obalky"])}</div>
    <div class="delta" style="color:var(--muted)">z {cz(u["volici"])} voličů v seznamu</div></div>
  <div class="kpi" style="--bar:var(--c2)"><div class="lab">Nové zastupitelstvo</div><div class="val">{S["pokracuje"]} + {S["novi"]}</div>
    <div class="delta" style="color:var(--muted)">{S["pokracuje"]} pokračuje, {S["novi"]} nových</div></div>
  <div class="kpi" style="--bar:var(--amber)"><div class="lab">Nejvíc preferenčních hlasů</div><div class="val" style="font-size:21px">{top["jmeno"].split(",")[0]}</div>
    <div class="delta" style="color:var(--muted)">{cz(top["hlasy"])} hlasů</div></div>
</div>

<section>
  <div class="sec-h"><h2>Nové zastupitelstvo</h2><span class="hint">{M} křesel · najeďte na křeslo pro jméno</span></div>
  <div class="grid2">
    <div class="panel">
      <div id="hemi" class="hemi"></div>
      <div class="legend" id="hemiLeg" style="justify-content:center"></div>
    </div>
    <div class="panel">
      <div class="sec-h" style="margin:0 0 10px"><h2 style="font-size:16px">Výsledky kandidátek</h2><span class="hint">podíl hlasů 2026 · tenký proužek = {kv["prev"]["rok"]}</span></div>
      <div id="partyRes"></div>
      <p class="note">Každý volič měl {M} hlasů a mohl je rozdělit napříč kandidátkami. Celkem padlo {cz(u["platne_hlasy"])} platných hlasů.<span id="missNote"></span></p>
    </div>
  </div>
</section>

<section>
  <div class="sec-h"><h2>Zvolení zastupitelé</h2><span class="hint">po kandidátkách, v pořadí, v jakém získali mandát</span></div>
  <div id="zvoleni" class="zvwrap"></div>
  <p class="note">„Pokračuje" = byl/a členem zastupitelstva i v období 2022–2026 (včetně náhradníků, kteří nastoupili během období). Starostu, místostarostu a radu obce zvolí nové zastupitelstvo na ustavujícím zasedání. Práce zastupitelstva je v sekci <a href="zastupitelstvo.html" style="color:var(--accent)">Zastupitelstvo</a>.</p>
</section>

<section>
  <div class="sec-h"><h2>Jak preferenční hlasy přeskládaly pořadí</h2><span class="hint">kandidáti v pořadí na kandidátce</span></div>
  <div class="panel">
    <div class="seg" id="prefSeg"></div>
    <div id="pref" class="pref"></div>
    <p class="note">Kandidát, který získá aspoň o 10 % víc hlasů, než je průměr na jednoho kandidáta své kandidátky (svislá čára), postupuje dopředu. Takoví kandidáti dostanou mandát přednostně, seřazení podle počtu hlasů; zbylé mandáty se obsadí podle pořadí na kandidátce. Stejně se určuje i pořadí náhradníků.</p>
  </div>
</section>

<section>
  <div class="sec-h"><h2>Jak se hlasy přepočítaly na mandáty</h2><span class="hint">d'Hondtova metoda</span></div>
  <div class="panel">
    <div class="tblwrap"><table class="dh" id="dh"></table></div>
    <div id="dhNote" class="dhnote"></div>
    <p class="note">Hlasy každé kandidátky se postupně dělí čísly 1, 2, 3, … a {M} nejvyšších podílů získá mandát (zvýrazněno). Poslední mandát připadl podílu {f2(S["q_last"])}, první nevítězný podíl měl {f2(S["q_first_out"])}.</p>
  </div>
</section>

<section>
  <div class="sec-h"><h2>Dva volební okrsky</h2><span class="hint">účast a výsledky kandidátek podle místa hlasování</span></div>
  <div class="grid2" id="okrsky"></div>
</section>

<section>
  <div class="sec-h"><h2>Kdo kandidoval a kdo byl zvolen</h2><span class="hint">věk a pohlaví</span></div>
  <div class="grid2">
    <div class="panel">
      <div class="sec-h" style="margin:0 0 10px"><h2 style="font-size:16px">Věk</h2><span class="hint">průměr: kandidáti {f2(S["vek_kand"], 1)} · zvolení {f2(S["vek_zv"], 1)} let</span></div>
      <div id="vek"></div>
    </div>
    <div class="panel">
      <div class="sec-h" style="margin:0 0 10px"><h2 style="font-size:16px">Ženy a muži</h2><span class="hint">kandidátky {S["zen_kand"]} z {len(kv["kandidati"])} · zvolené {S["zen_zv"]} z {len(zv)}</span></div>
      <div id="zeny"></div>
      <p class="note">Bez politické příslušnosti je {S["bezpp_zv"]} z {len(zv)} zvolených, ostatní jsou členy politické strany nebo hnutí.</p>
    </div>
  </div>
</section>

<section>
  <div class="panel">
    <p class="note" style="margin:0;font-size:12.5px">Zdroj: <b>Český statistický úřad</b> — <a href="https://volby.gov.cz/app/kv2026/cs/20261009/home" target="_blank" rel="noopener" style="color:var(--accent)">volby.gov.cz</a> (komunální volby 2026, data k {gen_txt}) a <a href="https://www.volby.cz" target="_blank" rel="noopener" style="color:var(--accent)">volby.cz</a> (komunální volby {kv["prev"]["rok"]}). Výpočet mandátů a pořadí kandidátů je přepočtený z oficiálních dat a souhlasí s výsledkem ČSÚ. Pohlaví je určené podle tvaru příjmení a souhlasí s oficiálním přehledem ČSÚ.</p>
  </div>
</section>'''

CSS = """<style>
:root{--p-kdu:#f3c75f;--p-str:#5ec4c6;--p-snk:#adb7bc;--p-stan:#e08ac0}
html[data-theme="dark"]{--p-kdu:#efc35b;--p-str:#62c8ca;--p-snk:#96a3a9;--p-stan:#e597cb}
.hemi svg{width:100%;height:auto;display:block;max-width:460px;margin:4px auto 0}
.hemi .seat{transition:transform .15s;transform-box:fill-box;transform-origin:center;cursor:default}
.hemi .seat:hover,.hemi .seat.hl{transform:scale(1.18)}
.hemi .mid{font-family:var(--font-d);fill:var(--ink)}
.hemi .tip{font-size:13px;fill:var(--text)}
.pres{display:flex;flex-direction:column;gap:14px}
.pr-h{display:flex;justify-content:space-between;gap:10px;align-items:baseline;font-size:14px;margin-bottom:6px;flex-wrap:wrap}
.pr-h b{font-family:var(--font-d);font-size:17px;color:var(--ink);font-variant-numeric:tabular-nums}
.pr-h .seats{font-size:12.5px;color:var(--muted)}
.pr-t{position:relative;height:12px;border-radius:6px;background:var(--inset)}
.pr-t i{position:absolute;left:0;top:0;bottom:0;border-radius:6px}
.pr-t em{position:absolute;left:0;bottom:-6px;height:3px;border-radius:2px;background:var(--muted);opacity:.55}
.pr-d{font-size:12px;margin-top:9px;color:var(--muted)}
.pr-d .up{color:var(--pos)} .pr-d .down{color:var(--neg)}
.zvwrap{display:flex;flex-direction:column;gap:18px}
.zvp h3{font-size:15px;margin:0 0 10px;display:flex;align-items:center;gap:8px}
.zvp h3 i{width:11px;height:11px;border-radius:3px;display:inline-block}
.zvp h3 span{color:var(--muted);font-weight:500;font-family:var(--font-b);font-size:13px}
.zvgrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:12px}
.zv{background:var(--surface);border:1px solid var(--line);border-radius:var(--radius-sm);padding:14px 16px 13px;display:flex;flex-direction:column;gap:5px;position:relative;overflow:hidden}
.zv::before{content:"";position:absolute;left:0;top:0;bottom:0;width:4px;background:var(--pc)}
.zv .nm{font-family:var(--font-d);font-weight:680;font-size:16px;color:var(--ink);line-height:1.25}
.zv .meta{font-size:12.5px;color:var(--muted);line-height:1.4}
.zv .row{display:flex;gap:6px;flex-wrap:wrap;margin-top:4px;align-items:center}
.zv .tag{font-size:11.5px;padding:2px 8px;border-radius:999px;background:var(--inset);border:1px solid var(--line);color:var(--muted)}
.zv .tag.up{color:var(--amber-ink);border-color:color-mix(in srgb,var(--amber) 55%,transparent);background:color-mix(in srgb,var(--amber) 14%,transparent)}
.zv .tag.new{color:var(--accent);border-color:color-mix(in srgb,var(--accent) 45%,transparent);background:var(--accent-soft)}
.zv .hl{margin-left:auto;font-family:var(--font-d);font-weight:700;font-size:15px;color:var(--ink);font-variant-numeric:tabular-nums}
.zv .hl small{font-family:var(--font-b);font-weight:400;font-size:11.5px;color:var(--muted)}
.pref{margin-top:14px;display:flex;flex-direction:column;gap:4px;position:relative}
.prefmsg{font-size:13.5px;background:var(--inset);border-radius:10px;padding:10px 14px;margin-bottom:10px;color:var(--text)}
.prefmsg b{color:var(--ink)}
.pf{display:grid;grid-template-columns:28px minmax(120px,210px) 1fr 104px;gap:10px;align-items:center;font-size:13px;min-height:26px}
.pf .po{color:var(--faint);font-variant-numeric:tabular-nums;text-align:right}
.pf .nm{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.pf.z .nm{font-weight:700;color:var(--ink)}
.pf .bar{position:relative;height:16px}
.pf .bar i{position:absolute;left:0;top:0;bottom:0;border-radius:4px;background:var(--pc);opacity:.32}
.pf.z .bar i{opacity:1}
.pf .bar b{position:absolute;top:50%;transform:translateY(-50%);font-size:11.5px;font-weight:600;color:var(--muted);padding-left:6px;font-variant-numeric:tabular-nums}
.pf .thr{position:absolute;top:-3px;bottom:-3px;width:0;border-left:2px dashed var(--ink);opacity:.5}
.pf .res{font-size:11.5px;color:var(--muted);text-align:right;white-space:nowrap}
.pf.z .res{color:var(--ink);font-weight:600}
.pf .res .mv{color:var(--amber-ink);font-weight:700}
.pfh{display:grid;grid-template-columns:28px minmax(120px,210px) 1fr 104px;gap:10px;font-size:11px;color:var(--faint);text-transform:uppercase;letter-spacing:.05em;margin-bottom:2px}
@media(max-width:640px){.pf,.pfh{grid-template-columns:22px 1fr 84px;}.pf .bar{grid-column:2/4;grid-row:2}.pf{row-gap:2px;padding-bottom:6px}.pfh .b{display:none}}
.tblwrap{overflow-x:auto}
table.dh{border-collapse:separate;border-spacing:4px;font-size:12.5px;font-variant-numeric:tabular-nums;min-width:640px}
table.dh th{font-weight:600;color:var(--muted);font-size:11.5px;text-align:right;padding:2px 6px}
table.dh th.pn{text-align:left;color:var(--text);font-size:13px;white-space:nowrap}
table.dh th.pn i{width:10px;height:10px;border-radius:3px;display:inline-block;margin-right:7px;vertical-align:0}
table.dh td{text-align:right;padding:6px 7px;border-radius:7px;background:var(--inset);color:var(--faint)}
table.dh td.w{background:color-mix(in srgb,var(--pc) 72%,transparent);color:var(--ink);font-weight:700}
table.dh td.last{outline:2px solid var(--amber);outline-offset:-2px}
table.dh td.next{outline:2px dashed var(--faint);outline-offset:-2px;color:var(--text)}
html[data-theme="dark"] table.dh td.w{color:#0d191e}
.dhnote{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:10px;margin-top:14px}
.dhnote div{background:var(--inset);border-radius:10px;padding:10px 12px;font-size:12.5px;color:var(--muted)}
.dhnote b{display:block;font-family:var(--font-d);font-size:18px;color:var(--ink);font-variant-numeric:tabular-nums}
.okr .uc{display:flex;align-items:baseline;gap:10px;margin-bottom:14px}
.okr .uc b{font-family:var(--font-d);font-size:30px;color:var(--ink);font-variant-numeric:tabular-nums}
.okr .uc span{font-size:13px;color:var(--muted)}
.stack{display:flex;height:30px;border-radius:8px;overflow:hidden;margin-bottom:10px}
.stack i{display:block;height:100%}
.okr .rows{display:flex;flex-direction:column;gap:5px;font-size:13px}
.okr .rows div{display:flex;align-items:center;gap:8px}
.okr .rows i{width:10px;height:10px;border-radius:3px;flex:none}
.okr .rows b{margin-left:auto;font-variant-numeric:tabular-nums}
.okr .rows .rh{font-size:11px;color:var(--faint);text-transform:uppercase;letter-spacing:.05em}
.okr .rows .rh b{font-weight:600}
.okr .rows .dv{width:86px;text-align:right;font-size:12px;color:var(--muted);font-variant-numeric:tabular-nums}
.okr h3{font-size:16px;margin:0 0 4px}
.okr .top{margin-top:14px;padding-top:12px;border-top:1px solid var(--line);font-size:12.5px;color:var(--muted)}
.okr .top b{color:var(--text);font-weight:600}
.vk{display:flex;flex-direction:column;gap:8px}
.vk .r{display:grid;grid-template-columns:62px 1fr;gap:10px;align-items:center;font-size:12.5px}
.vk .r span{color:var(--muted);text-align:right;font-variant-numeric:tabular-nums}
.vk .bars{display:flex;flex-direction:column;gap:3px}
.vk .bars div{height:10px;border-radius:5px;min-width:2px}
.vk .k{background:color-mix(in srgb,var(--c5) 70%,transparent)}
.vk .z{background:var(--c0)}
.vkl{display:flex;gap:16px;font-size:12px;color:var(--muted);margin-top:12px}
.vkl i{width:10px;height:10px;border-radius:3px;display:inline-block;margin-right:6px;vertical-align:-1px}
.dots{display:flex;flex-wrap:wrap;gap:5px;margin:4px 0 6px}
.dots i{width:14px;height:14px;border-radius:50%;background:color-mix(in srgb,var(--c5) 45%,transparent)}
.dots i.w{background:var(--c1)}
.dots i.e{box-shadow:0 0 0 2px var(--surface),0 0 0 3.5px var(--ink)}
.dl{font-size:12.5px;color:var(--muted);margin:10px 0 4px}
</style>"""

data_json = json.dumps({"K": kv}, ensure_ascii=False, separators=(",", ":"))

scripts = '''<script>
const ALL=DATA_JSON, K=ALL.K, S=K.S;
const nf=new Intl.NumberFormat('cs-CZ');
const f2=v=>v.toLocaleString('cs-CZ',{minimumFractionDigits:2,maximumFractionDigits:2});
const pct=v=>f2(v)+' %';
const esc=s=>String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const P={}; K.strany.forEach(s=>P[s.c]=s);
const pc=c=>'var('+P[c].barva+')';
const ORD={}; K.strany.forEach((s,i)=>ORD[s.c]=i);   // kandidátky od nejsilnější (pořadí z builderu)
const zvol=K.kandidati.filter(k=>k.zvolen).sort((a,b)=>ORD[a.strana]-ORD[b.strana]||a.poradi_vysl-b.poradi_vysl);

/* --- půlkruh zastupitelstva: 15 křesel ve 3 řadách, strany zleva doprava --- */
function hemi(){
  const W=460,H=244,cx=W/2,cy=226,rows=[[104,4],[148,5],[192,6]],r=19;
  let seats=[];
  rows.forEach(([R,n])=>{for(let i=0;i<n;i++){const a=Math.PI-(i+0.5)*Math.PI/n;seats.push({x:cx+R*Math.cos(a),y:cy-R*Math.sin(a),a});}});
  seats.sort((p,q)=>q.a-p.a);
  let svg=`<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Rozdělení ${K.mandaty} mandátů">`;
  seats.forEach((s,i)=>{const z=zvol[i];
    svg+=`<circle class="seat" data-i="${i}" cx="${s.x.toFixed(1)}" cy="${s.y.toFixed(1)}" r="${r}" fill="${pc(z.strana)}" stroke="var(--surface)" stroke-width="2"><title>${esc(z.jmeno)} · ${esc(P[z.strana].kratky)}</title></circle>`;});
  svg+=`<text class="mid" x="${cx}" y="${cy-30}" text-anchor="middle" font-size="40" font-weight="750">${K.mandaty}</text>`;
  svg+=`<text class="tip" id="hemiTip" x="${cx}" y="${cy-4}" text-anchor="middle">mandátů</text></svg>`;
  document.getElementById('hemi').innerHTML=svg;
  const tip=document.getElementById('hemiTip');
  document.querySelectorAll('#hemi .seat').forEach(el=>{
    el.addEventListener('mouseenter',()=>{const z=zvol[+el.dataset.i];tip.textContent=z.jmeno.split(',')[0];});
    el.addEventListener('mouseleave',()=>{tip.textContent='mandátů';});});
  document.getElementById('hemiLeg').innerHTML=K.strany.map(s=>
    `<span><i class="sw" style="background:${pc(s.c)}"></i>${esc(s.kratky)} · ${s.mandaty}</span>`).join('');
}

/* --- výsledky kandidátek 2026 vs 2022 --- */
function partyRes(){
  const mx=Math.max(...K.strany.map(s=>Math.max(s.pct,s.prev?s.prev.pct:0)))*1.08;
  document.getElementById('partyRes').innerHTML='<div class="pres">'+K.strany.map(s=>{
    const d=s.prev?s.pct-s.prev.pct:null, dm=s.prev?s.mandaty-s.prev.mandaty:null;
    const dtxt=d==null?'v roce 2022 nekandidovala':
      `<span class="${d>=0?'up':'down'}">${d>=0?'▲':'▼'} ${f2(Math.abs(d))} p. b.</span> proti ${f2(s.prev.pct)} % v roce 2022`+
      (dm===0?' · mandáty beze změny':` · mandáty ${dm>0?'+':''}${dm}`)+(s.prev.nazev!==s.nazev?` <span title="v roce 2022 jako ${esc(s.prev.nazev)}">(2022: ${esc(s.prev.nazev)})</span>`:'');
    return `<div><div class="pr-h"><span>${esc(s.nazev)}</span><span><b>${pct(s.pct)}</b> <span class="seats">· ${s.mandaty} mand.</span></span></div>
      <div class="pr-t"><i style="width:${s.pct/mx*100}%;background:${pc(s.c)}"></i>${s.prev?`<em style="width:${s.prev.pct/mx*100}%"></em>`:''}</div>
      <div class="pr-d">${nf.format(s.hlasy)} hlasů · ${dtxt}</div></div>`;}).join('')+'</div>';
  if(S.missing.length) document.getElementById('missNote').innerHTML=' Oproti roku 2022 nekandidovala '+
    S.missing.map(m=>`${esc(m.nazev)} (tehdy ${f2(m.pct)} %)`).join(', ')+'.';
}

/* --- karty zvolených --- */
function zvoleni(){
  document.getElementById('zvoleni').innerHTML=K.strany.map(s=>{
    const list=zvol.filter(z=>z.strana===s.c);
    return `<div class="zvp"><h3><i style="background:${pc(s.c)}"></i>${esc(s.nazev)}<span>· ${list.length} ${list.length===1?'mandát':list.length<5?'mandáty':'mandátů'}</span></h3><div class="zvgrid">`+
      list.map(z=>{
        // mandát jen díky preferenčním hlasům = podle pořadí na kandidátce by se do počtu mandátů nevešel(a)
        const pref=z.poradi>s.mandaty;
        return `<div class="zv" style="--pc:${pc(s.c)}"><div class="nm">${esc(z.jmeno)}</div>
          <div class="meta">${z.vek} let · ${esc(z.povolani)}</div>
          <div class="row">${z.pokracuje?'<span class="tag">pokračuje</span>':'<span class="tag new">nově v zastupitelstvu</span>'}
            ${pref?`<span class="tag up" title="Na kandidátce byl${z.zena?'a':''} ${z.poradi}., kandidátka získala ${s.mandaty} mandáty — zvolen${z.zena?'a':''} díky preferenčním hlasům.">↑ díky preferenčním hlasům (z ${z.poradi}. místa)</span>`:''}
            <span class="hl">${nf.format(z.hlasy)} <small>hlasů</small></span></div></div>`;}).join('')+'</div></div>';}).join('');
}

/* --- preferenční hlasy: kandidátka po kandidátce --- */
let prefSel=K.strany[0].c;
function prefSeg(){
  document.getElementById('prefSeg').innerHTML=K.strany.map(s=>
    `<button type="button" class="${s.c===prefSel?'on':''}" data-c="${s.c}">${esc(s.kratky)}</button>`).join('');
  document.querySelectorAll('#prefSeg button').forEach(b=>b.onclick=()=>{prefSel=+b.dataset.c;prefSeg();pref();});
}
function pref(){
  const s=P[prefSel], list=K.kandidati.filter(k=>k.strana===prefSel).sort((a,b)=>a.poradi-b.poradi);
  const mx=Math.max(...list.map(k=>k.hlasy))*1.12, thr=s.hranice/mx*100;
  let h=`<div class="pfh"><span>#</span><span>kandidát</span><span class="b">preferenční hlasy · čára = hranice ${nf.format(Math.round(s.hranice))}</span><span style="text-align:right">výsledek</span></div>`;
  h+=list.map(k=>{
    const zv=k.zena?'zvolena':'zvolen', nh=k.zena?'náhradnice':'náhradník';
    const arrow=k.nad_hranici?' <span class="mv" title="překročil(a) hranici a postoupil(a) dopředu">↑</span>':'';
    const res=k.zvolen?`${arrow} ${zv} ${k.poradi_vysl}.`:`${k.poradi_vysl}. ${nh}${arrow}`;
    return `<div class="pf${k.zvolen?' z':''}" style="--pc:${pc(prefSel)}"><span class="po">${k.poradi}.</span>
      <span class="nm" title="${esc(k.jmeno)} · ${k.vek} let">${esc(k.jmeno.split(',')[0])}</span>
      <span class="bar"><i style="width:${k.hlasy/mx*100}%"></i><b style="left:${k.hlasy/mx*100}%">${nf.format(k.hlasy)}</b><span class="thr" style="left:${thr}%"></span></span>
      <span class="res">${res}</span></div>`;}).join('');
  // co preferenční hlasy reálně změnily: kdo se dostal dovnitř místo kandidáta výš na kandidátce
  const byList=list.slice(0,s.mandaty), inn=list.filter(k=>k.zvolen&&k.poradi>s.mandaty), out=byList.filter(k=>!k.zvolen);
  const nm=k=>esc(k.jmeno.split(',')[0]);
  const msg=inn.length
    ? `Preferenční hlasy změnily složení: ${inn.map(k=>`<b>${nm(k)}</b> (${k.poradi}. na kandidátce)`).join(', ')} ${inn.length>1?'získali':'získal'+(inn[0].zena?'a':'')} mandát. Podle pořadí na kandidátce by ${out.length>1?'mandáty patřily kandidátům':'mandát patřil'} ${out.map(k=>`<b>${nm(k)}</b> (${k.poradi}.)`).join(', ')}.`
    : (s.mandaty>1 && list.some(k=>k.zvolen&&k.poradi_vysl!==k.poradi)
      ? 'Zvoleno bylo prvních '+s.mandaty+' z kandidátky; preferenční hlasy změnily jen pořadí, v jakém mandáty získali (a pořadí náhradníků).'
      : 'Mandát'+(s.mandaty>1?'y získali':' získal')+' kandidáti v pořadí podle kandidátky; preferenční hlasy ovlivnily jen pořadí náhradníků.');
  h=`<div class="prefmsg">${msg}</div>`+h;
  document.getElementById('pref').innerHTML=h;
}

/* --- d'Hondt --- */
function dh(){
  const cols=Math.max(8,Math.max(...K.strany.map(s=>s.mandaty))+1), win=new Set(S.win.map(w=>w[1]+'-'+w[2])), last=S.win[S.win.length-1];
  let h='<tr><th class="pn"></th>'+Array.from({length:cols},(_,i)=>`<th>÷ ${i+1}</th>`).join('')+'<th>mandátů</th></tr>';
  K.strany.forEach(s=>{
    h+=`<tr style="--pc:${pc(s.c)}"><th class="pn"><i style="background:${pc(s.c)}"></i>${esc(s.kratky)}</th>`;
    for(let d=1;d<=cols;d++){const v=s.podily[d-1], key=s.c+'-'+d;
      const cls=win.has(key)?('w'+(last[1]===s.c&&last[2]===d?' last':'')):(Math.abs(v-S.q_first_out)<0.01?'next':'');
      h+=`<td class="${cls}">${nf.format(Math.round(v))}</td>`;}
    h+=`<th style="color:var(--ink);font-size:14px">${s.mandaty}</th></tr>`;});
  document.getElementById('dh').innerHTML=h;
  document.getElementById('dhNote').innerHTML=K.strany.map(s=>
    `<div><b>${nf.format(s.chybi)}</b>hlasů chybělo kandidátce ${esc(s.kratky)} k ${s.mandaty+1}. mandátu — to je zhruba ${Math.ceil(s.chybi/K.mandaty)} voličů, kteří by jí dali všech ${K.mandaty} hlasů</div>`).join('');
}

/* --- okrsky --- */
function okrsky(){
  const o=K.okrsky;
  document.getElementById('okrsky').innerHTML=o.map((ok,idx)=>{
    const other=o[1-idx];
    const top=K.kandidati.slice().sort((a,b)=>b.okrsky[idx]-a.okrsky[idx]).slice(0,3);
    return `<div class="panel okr"><h3>Okrsek ${ok.c}</h3>
      <div class="uc"><b>${pct(ok.ucast)}</b><span>účast · ${nf.format(ok.obalky)} z ${nf.format(ok.volici)} voličů</span></div>
      <div class="stack">${K.strany.map(s=>`<i style="width:${ok.strany[s.c][1]}%;background:${pc(s.c)}" title="${esc(s.kratky)} ${pct(ok.strany[s.c][1])}"></i>`).join('')}</div>
      <div class="rows"><div class="rh"><span>kandidátka</span><b>podíl</b><span class="dv">vs. okrsek ${other.c}</span></div>${K.strany.map(s=>{const v=ok.strany[s.c][1], d=v-other.strany[s.c][1];
        return `<div><i style="background:${pc(s.c)}"></i>${esc(s.kratky)}<b>${pct(v)}</b><span class="dv">${d>=0?'+':'−'}${f2(Math.abs(d))}</span></div>`;}).join('')}</div>
      <div class="top">Nejvíc hlasů v okrsku: ${top.map(k=>`<b>${esc(k.jmeno.split(',')[0])}</b> ${nf.format(k.okrsky[idx])}`).join(' · ')}</div>
    </div>`;}).join('');
}

/* --- věk a pohlaví --- */
function vek(){
  const groups=[[18,29],[30,39],[40,49],[50,59],[60,99]];
  const n=k=>groups.map(([a,b])=>k.filter(x=>x.vek>=a&&x.vek<=b).length);
  const kc=n(K.kandidati), zc=n(zvol), mx=Math.max(...kc);
  document.getElementById('vek').innerHTML='<div class="vk">'+groups.map((g,i)=>
    `<div class="r"><span>${g[1]>90?g[0]+'+':g[0]+'–'+g[1]}</span><div class="bars">
      <div class="k" style="width:${kc[i]/mx*100}%" title="${kc[i]} kandidátů"></div>
      <div class="z" style="width:${zc[i]/mx*100}%" title="${zc[i]} zvolených"></div></div></div>`).join('')+
    `</div><div class="vkl"><span><i style="background:color-mix(in srgb,var(--c5) 70%,transparent)"></i>kandidáti (${K.kandidati.length})</span><span><i style="background:var(--c0)"></i>zvolení (${zvol.length})</span></div>`+
    `<p class="note">Nejmladší zvolený: ${esc(minBy(zvol,'vek').jmeno.split(',')[0])} (${minBy(zvol,'vek').vek} let) · nejstarší: ${esc(maxBy(zvol,'vek').jmeno.split(',')[0])} (${maxBy(zvol,'vek').vek} let).</p>`;
}
const minBy=(a,k)=>a.reduce((m,x)=>x[k]<m[k]?x:m), maxBy=(a,k)=>a.reduce((m,x)=>x[k]>m[k]?x:m);
function zeny(){
  const all=K.kandidati.slice().sort((a,b)=>(b.zena-a.zena)||(b.zvolen-a.zvolen));
  const zv=zvol.slice().sort((a,b)=>(b.zena-a.zena));
  document.getElementById('zeny').innerHTML=
    `<div class="dl">Kandidáti (${K.kandidati.length})</div><div class="dots">${all.map(k=>`<i class="${k.zena?'w':''} ${k.zvolen?'e':''}" title="${esc(k.jmeno)}"></i>`).join('')}</div>`+
    `<div class="dl">Zvolení (${zvol.length})</div><div class="dots">${zv.map(k=>`<i class="${k.zena?'w':''}" title="${esc(k.jmeno)}"></i>`).join('')}</div>`+
    `<div class="vkl"><span><i style="background:var(--c1);border-radius:50%"></i>žena</span><span><i style="background:color-mix(in srgb,var(--c5) 45%,transparent);border-radius:50%"></i>muž</span><span><i style="border-radius:50%;box-shadow:0 0 0 1.5px var(--ink)"></i>zvolen/a</span></div>`;
}

function render(){hemi();partyRes();zvoleni();prefSeg();pref();dh();okrsky();vek();zeny();}
render(); bindTheme(render);
</script>'''.replace("DATA_JSON", data_json)

open("volby.html", "w", encoding="utf-8").write(
    pc.page("Volby", "Komunální volby 2026 — Jak žijí Střelice", body, head_scripts=CSS, body_scripts=scripts))
print(f"HOTOVO -> volby.html (komunál 2026: {len(kv['strany'])} kandidátky, {len(zv)} zvolených, "
      f"pokračuje {S['pokracuje']}, nových {S['novi']})")
