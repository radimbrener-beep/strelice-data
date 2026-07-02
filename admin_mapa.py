#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Lokální administrace mapy investic — vyklikání poloh akcí.

Spuštění:  python admin_mapa.py   ->  http://localhost:8766

Vlevo seznam investičních akcí (i pojmenovaných míst), klik na akci a pak
klik do mapy = poloha se ihned uloží do data/akce_geo.json (u míst do
data/mista_geo.json). Tlačítkem Přegenerovat se přestaví investice.html.

Čistě lokální nástroj — nikdy se nedeployuje (deploy bere jen *.html
z kořene) a server poslouchá jen na 127.0.0.1."""
import sys, json, subprocess, urllib.parse
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

sys.stdout.reconfigure(encoding="utf-8")
PORT = 8766

AKCE_GEO = "data/akce_geo.json"
MISTA_GEO = "data/mista_geo.json"

MISTA_POPIS = {
    "ou": "Obecní úřad (+ fallback akcí bez místa)", "zs": "Základní škola", "ms": "MŠ novostavba (Školní)",
    "zus": "ZUŠ", "hasici": "Hasičská zbrojnice", "hrbitov": "Hřbitov", "koupaliste": "Koupaliště",
    "sokolovna": "Sokolovna", "dps": "DPS", "nadrazi": "Nádraží", "kostel": "Kostel",
    "od": "Obchodní dům SATOV", "kesi": "Stánek KESI", "trnky": "Hospůdka u Trnků",
    "cov": "ČOV", "lotruvka": "Cyklotrasa Lotrůvka (střed)", "bobrava": "Cyklotrasa Bobrava (střed)",
    "brezeci": "Cesta do Březečí",
}


def load(path, default):
    try:
        return json.load(open(path, encoding="utf-8"))
    except FileNotFoundError:
        return default


def save(path, data):
    json.dump(data, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


_STATIC = None   # akce + parcely + ulice se za běhu admina nemění -> načíst jednou


def payload():
    """Data pro admin stránku — stejné zdroje jako build_investice.py.
    Seznam akcí je nacachovaný (import build_investice trvá sekundy);
    geo soubory se čtou čerstvé z disku, ty se editují."""
    global _STATIC
    if _STATIC is None:
        import build_investice as bi
        _STATIC = {"akce": bi.akce, "pgeo": bi.parcely_geo, "ugeo": bi.ulice_geo}
    return dict(_STATIC, mgeo=load(MISTA_GEO, {}), ageo=load(AKCE_GEO, []),
                mistaPopis=MISTA_POPIS)


# POZN.: geoOf níže je kopie logiky z build_investice.py (JS) — admin ji
# potřebuje k zobrazení aktuální polohy. Při změně pravidel aktualizovat obojí.
HTML = r"""<!DOCTYPE html>
<html lang="cs">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Admin — mapa investic</title>
<link rel="stylesheet" href="/vendor/leaflet.css">
<style>
*{box-sizing:border-box}
body{margin:0;font:14px/1.45 "Segoe UI",sans-serif;display:flex;height:100vh;color:#0f172a}
#side{width:440px;min-width:340px;display:flex;flex-direction:column;border-right:1px solid #d8dee8;background:#f8fafc}
#head{padding:10px 14px;border-bottom:1px solid #d8dee8;background:#fff}
#head h1{font-size:15px;margin:0 0 6px}
#head .sub{font-size:12px;color:#64748b}
#tools{display:flex;gap:8px;padding:8px 14px;border-bottom:1px solid #d8dee8;align-items:center;background:#fff}
#q{flex:1;padding:6px 10px;border:1px solid #cbd5e1;border-radius:8px;font:inherit}
#rebuild{padding:6px 12px;border:1px solid #3d6c9e;background:#3d6c9e;color:#fff;border-radius:8px;cursor:pointer;font:inherit;font-size:13px}
#rebuild:disabled{opacity:.5}
#tabs{display:flex;gap:4px;padding:8px 14px 0;background:#fff}
#tabs button{border:1px solid #cbd5e1;border-bottom:none;background:#eef2f7;padding:6px 14px;border-radius:8px 8px 0 0;cursor:pointer;font:inherit;font-size:13px}
#tabs button.on{background:#fff;font-weight:600}
#list{flex:1;overflow-y:auto}
.row{padding:9px 14px;border-bottom:1px solid #e7ebf1;cursor:pointer}
.row:hover{background:#eef2f7}
.row.sel{background:#dbe7f5;border-left:4px solid #3d6c9e;padding-left:10px}
.row .top{display:flex;gap:8px;align-items:baseline;margin-bottom:2px}
.row .dt{font-size:11.5px;color:#64748b;white-space:nowrap}
.row .amt{font-weight:600;font-size:12.5px;margin-left:auto;white-space:nowrap}
.row .tx{font-size:12.5px;color:#334155;white-space:pre-line}
.badge{font-size:10.5px;padding:1px 7px;border-radius:999px;white-space:nowrap}
.b-man{background:#dcfce7;color:#166534}
.b-auto{background:#e0e7ff;color:#3730a3}
.b-fall{background:#fee2e2;color:#991b1b}
.b-misto{background:#fef3c7;color:#92400e}
#status{padding:8px 14px;font-size:12.5px;border-top:1px solid #d8dee8;background:#fff;min-height:56px}
#status b{color:#3d6c9e}
#map{position:absolute;inset:0}
.selpin{font-size:30px;line-height:30px;text-align:center;text-shadow:0 1px 3px rgba(0,0,0,.45);cursor:grab}
.delbtn{margin-top:5px;font-size:11.5px;color:#b91c1c;background:none;border:1px solid #fca5a5;border-radius:7px;padding:2px 8px;cursor:pointer;display:none}
.row.sel .delbtn.show{display:inline-block}
#hint{position:absolute;z-index:1000;top:10px;right:10px;background:#fff;border:1px solid #cbd5e1;border-radius:10px;padding:8px 13px;font-size:12.5px;box-shadow:0 4px 14px rgba(0,0,0,.12);max-width:290px}
</style>
</head>
<body>
<div id="side">
  <div id="head"><h1>🗺️ Admin — mapa investic</h1>
    <div class="sub">1) vyber akci či místo &nbsp;2) klikni do mapy &nbsp;→ uloží se hned</div></div>
  <div id="tools"><input id="q" placeholder="hledat v akcích…"><button id="rebuild">Přegenerovat web</button></div>
  <div id="tabs"><button class="on" data-t="akce">Akce</button><button data-t="mista">Místa</button></div>
  <div id="list"></div>
  <div id="status">Vyber akci nebo místo.</div>
</div>
<div style="flex:1;position:relative"><div id="map"></div>
  <div id="hint">Zelené = ruční poloha (akce_geo.json) · modré = automaticky (parcela/ulice/místo) · červené = fallback u OÚ.<br>Klik do mapy uloží polohu vybrané položky.</div>
</div>
<script src="/vendor/leaflet.js"></script>
<script>
let D=null, tab='akce', sel=null, marker=null, allMarkers=null;
const map=L.map('map').setView([49.1515,16.497],15);
L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19,attribution:'© OpenStreetMap'}).addTo(map);

// --- kopie geo logiky z build_investice.py (drž v souladu!) ---
const OTHER_KU=/k\.?\s*ú\.?\s*(Troubsk|Ostopovic|Omic|Radostic|Popůvk|Heršpic|Tetčic|Nebovid|Rosic|Žebětín|Bosonoh|Modřic|Želešic|Šlapanic)/i;
const ONP_RE=/na pozemku\s+(?:parc|p)\.?\s*č\.?\s*(\d{1,5}(?:\/\d{1,4})?)/i;
const PARC_RE=/((?:p(?:arc)?\.?\s*č\.?|parcel\w*\s*č\.?)\s*)(\d{1,5}(?:\/\d{1,4})?)/gi;
const OD_RX=/obchodn\p{L}*\s+d[oů]m\p{L}*|SATOV/iu;
const MISTA_RX=[
  [/mateřsk|(?<!\p{L})MŠ(?!\p{L})/u,'ms'],[/základní škol|(?<!\p{L})ZŠ(?!\p{L})/u,'zs'],
  [/(?<!\p{L})ZUŠ(?!\p{L})|uměleck/u,'zus'],
  [/obecní(?:ho)?\s+úřad|radnic/,'ou'],[/hřbitov|pohřeb/,'hrbitov'],[/koupališt/,'koupaliste'],
  [/sokolovn/,'sokolovna'],[/pečovatel|(?<!\p{L})DPS(?!\p{L})/u,'dps'],
  [/KESI/,'kesi'],[/hasič|zbrojnic/i,'hasici'],
  [/u Trnků/i,'trnky'],[/nádraž/i,'nadrazi'],
  [/(?<!\p{L})ČOV(?!\p{L})|čistírn/u,'cov'],[/kostel/,'kostel'],
  [/Lotrůvk/,'lotruvka'],[/Bobrav/,'bobrava'],[/Březeč/,'brezeci']];
const GEN_RX=[[/škol/,'zs']];
const _rxesc=s=>s.replace(/[.*+?^${}()|[\]\\]/g,'\\$&');
let UL_RX=[];
function buildUlRx(){
  UL_RX=Object.keys(D.ugeo).map(nm=>{
    let rx;
    if(nm==='Nová ulice') rx='(Nová ulice|Nové ulici|ulic\\w* Nová|ul\\. Nová)';
    else if(/á$/.test(nm)) rx=_rxesc(nm.slice(0,-1))+'(á|é|ou)(?!\\p{L})';
    else if(/í$/.test(nm)) rx=_rxesc(nm)+'(ho|mu|m|ch)?(?!\\p{L})';
    else rx=_rxesc(nm)+'(?!\\p{L})';
    return [new RegExp(rx,'u'),nm];
  });
}
function geoOf(text){
  for(const o of D.ageo){if(text.includes(o.match)){
    const g=o.geo||(o.misto&&D.mgeo[o.misto]);
    if(g)return {g,src:o.misto?'ručně → '+(D.mistaPopis[o.misto]||o.misto):'ručně'};
    break;}}
  if(OTHER_KU.test(text))return null;
  if(OD_RX.test(text)&&D.mgeo.od)return {g:D.mgeo.od,src:'místo: obchodní dům'};
  const onp=text.match(ONP_RE); if(onp&&D.pgeo[onp[1]])return {g:D.pgeo[onp[1]],src:'parcela '+onp[1]};
  for(const mm of text.matchAll(PARC_RE)){const g=D.pgeo[mm[2]];if(g)return {g,src:'parcela '+mm[2]};}
  for(const [rx,k] of MISTA_RX){if(rx.test(text)&&D.mgeo[k])return {g:D.mgeo[k],src:'místo: '+k};}
  for(const [rx,nm] of UL_RX){if(rx.test(text))return {g:D.ugeo[nm],src:'ulice '+nm};}
  for(const [rx,k] of GEN_RX){if(rx.test(text)&&D.mgeo[k])return {g:D.mgeo[k],src:'místo: '+k};}
  return D.mgeo.ou?{g:D.mgeo.ou,src:'fallback OÚ',fb:true}:null;
}
// --- konec kopie ---

const nf=new Intl.NumberFormat('cs-CZ');
function castka(v){return v>=1e6?(v/1e6).toLocaleString('cs-CZ',{maximumFractionDigits:2})+' mil':nf.format(Math.round(v/1000))+' tis.';}
function fmtD(iso){if(!iso)return '—';const p=iso.split('-');return p[2]+'. '+(+p[1])+'. '+p[0];}
function manual(t){return D.ageo.find(o=>t.includes(o.match));}

function renderList(){
  const q=(document.getElementById('q').value||'').toLowerCase();
  const el=document.getElementById('list'); el.innerHTML='';
  if(tab==='akce'){
    D.akce.forEach((x,i)=>{
      if(q && !x[4].toLowerCase().includes(q))return;
      const r=geoOf(x[4]), man=manual(x[4]);
      const b=man?('<span class="badge b-man">ručně'+(man.misto?' → '+man.misto:'')+'</span>'):(r&&r.fb?'<span class="badge b-fall">u OÚ</span>':'<span class="badge b-auto">'+(r?r.src:'—')+'</span>');
      const div=document.createElement('div');
      div.className='row'+(sel&&sel.type==='akce'&&sel.i===i?' sel':'');
      div.innerHTML=`<div class="top"><span class="dt">${fmtD(x[0])}</span>${b}<span class="amt">${castka(x[1])}</span></div>
        <div class="tx">${x[4]}</div>
        <button class="delbtn${man?' show':''}">✕ zrušit ruční polohu</button>`;
      div.onclick=()=>selectAkce(i);
      const del=div.querySelector('.delbtn');
      if(del)del.onclick=e=>{e.stopPropagation();delOverride(x[4]);};
      el.appendChild(div);
    });
  }else{
    Object.keys(D.mgeo).forEach(k=>{
      const nm=(D.mistaPopis[k]||k);
      if(q && !nm.toLowerCase().includes(q) && !k.includes(q))return;
      const div=document.createElement('div');
      div.className='row'+(sel&&sel.type==='misto'&&sel.k===k?' sel':'');
      div.innerHTML=`<div class="top"><span class="badge b-misto">${k}</span><span style="font-size:13px">${nm}</span>
        <span class="dt" style="margin-left:auto">${D.mgeo[k][0].toFixed(5)}, ${D.mgeo[k][1].toFixed(5)}</span></div>`;
      div.onclick=()=>selectMisto(k);
      el.appendChild(div);
    });
  }
}
function showAll(){
  if(allMarkers)allMarkers.remove();
  allMarkers=L.layerGroup().addTo(map);
  D.akce.forEach(x=>{
    const r=geoOf(x[4]); if(!r)return;
    const man=!!manual(x[4]);
    L.circleMarker(r.g,{radius:4,color:man?'#16a34a':(r.fb?'#dc2626':'#3d6c9e'),weight:1.4,fillOpacity:.45})
      .bindTooltip(x[4].slice(0,90),{direction:'top'}).addTo(allMarkers);
  });
}
const PIN=L.divIcon({className:'selpin',html:'📍',iconSize:[30,30],iconAnchor:[15,28]});
function setMarker(g,label){
  if(marker)marker.remove();
  marker=L.marker(g,{draggable:true,icon:PIN}).addTo(map).bindTooltip(label,{permanent:false});
  marker.on('dragend',()=>saveSel(marker.getLatLng()));
  map.setView(g,Math.max(map.getZoom(),17));
}
function selectAkce(i){
  sel={type:'akce',i};
  const x=D.akce[i], r=geoOf(x[4]), man=manual(x[4]);
  const cur=man&&man.misto?man.misto:'';
  const opts='<option value="">— nebo přiřaď známé místo —</option>'+
    Object.keys(D.mgeo).map(k=>`<option value="${k}"${k===cur?' selected':''}>${D.mistaPopis[k]||k}</option>`).join('');
  document.getElementById('status').innerHTML=`<b>Akce:</b> ${x[4].slice(0,120)}…<br>
    aktuálně: <b>${r?r.src:'—'}</b> · klikni do mapy / přetáhni špendlík
    <select id="mistoSel" style="font:inherit;font-size:12px;margin-left:6px;max-width:220px">${opts}</select>`;
  document.getElementById('mistoSel').onchange=async e=>{
    if(!e.target.value)return;
    await post('/save-akce',{text:x[4],misto:e.target.value});
    await reloadData();
    document.getElementById('status').innerHTML+=' <b style="color:#16a34a">✓ přiřazeno</b>';
  };
  renderList();
  if(r)setMarker(r.g,'akce'); else if(marker){marker.remove();marker=null;}
}
function selectMisto(k){
  sel={type:'misto',k};
  document.getElementById('status').innerHTML=`<b>Místo:</b> ${D.mistaPopis[k]||k} (${k})<br>
    Pozor: posun místa přemístí <b>všechny</b> akce na něj navázané. Klikni do mapy nebo přetáhni špendlík.`;
  renderList();
  setMarker(D.mgeo[k],k);
}
async function post(url,body){
  const r=await fetch(url,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
  return r.json();
}
async function saveSel(latlng){
  if(!sel)return;
  const g=[+latlng.lat.toFixed(6),+latlng.lng.toFixed(6)];
  if(sel.type==='akce'){
    const x=D.akce[sel.i];
    await post('/save-akce',{text:x[4],geo:g});
  }else{
    await post('/save-misto',{key:sel.k,geo:g});
  }
  await reloadData();
  document.getElementById('status').innerHTML+=` <b style="color:#16a34a">✓ uloženo ${g[0]}, ${g[1]}</b>`;
}
async function delOverride(text){
  await post('/del-akce',{text});
  await reloadData();
}
async function reloadData(){
  D=await (await fetch('/data')).json();
  buildUlRx();renderList();showAll();
  if(sel&&sel.type==='akce'){const r=geoOf(D.akce[sel.i][4]);if(r)setMarker(r.g,'akce');}
  if(sel&&sel.type==='misto')setMarker(D.mgeo[sel.k],sel.k);
}
map.on('click',e=>{if(sel)saveSel(e.latlng);});
document.getElementById('q').oninput=renderList;
document.querySelectorAll('#tabs button').forEach(b=>b.onclick=()=>{
  document.querySelectorAll('#tabs button').forEach(x=>x.classList.toggle('on',x===b));
  tab=b.dataset.t;sel=null;if(marker){marker.remove();marker=null;}renderList();});
document.getElementById('rebuild').onclick=async()=>{
  const btn=document.getElementById('rebuild');btn.disabled=true;btn.textContent='Generuji…';
  const r=await post('/rebuild',{});
  btn.disabled=false;btn.textContent='Přegenerovat web';
  document.getElementById('status').innerHTML='<b>Rebuild:</b> '+(r.ok?'✓ '+r.out:'✗ '+r.out);
};
reloadData().then(()=>document.getElementById('status').textContent='Načteno. Vyber akci nebo místo.');
</script>
</body>
</html>"""


class H(BaseHTTPRequestHandler):
    def _send(self, body, ctype="application/json; charset=utf-8", code=200):
        raw = body.encode("utf-8") if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        p = urllib.parse.urlparse(self.path).path
        if p == "/":
            self._send(HTML, "text/html; charset=utf-8")
        elif p == "/data":
            self._send(json.dumps(payload(), ensure_ascii=False))
        elif p.startswith("/vendor/"):
            fn = "data/vendor/" + p.split("/")[-1]
            try:
                ct = "text/css" if fn.endswith(".css") else "application/javascript"
                self._send(open(fn, "rb").read(), ct + "; charset=utf-8")
            except FileNotFoundError:
                self._send("not found", "text/plain", 404)
        else:
            self._send("not found", "text/plain", 404)

    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(n) or b"{}")
        p = urllib.parse.urlparse(self.path).path
        if p == "/save-akce":
            ageo = load(AKCE_GEO, [])
            text = body["text"]
            # match = celý text usnesení -> jednoznačné; existující záznam přepsat
            ageo = [o for o in ageo if o["match"] not in text and text not in o["match"]]
            entry = {"match": text}
            if body.get("misto"):
                entry["misto"] = body["misto"]     # odkaz na pojmenované místo
            else:
                entry["geo"] = body["geo"]         # pevné souřadnice
            ageo.append(entry)
            save(AKCE_GEO, ageo)
            self._send('{"ok":true}')
        elif p == "/del-akce":
            ageo = load(AKCE_GEO, [])
            text = body["text"]
            ageo = [o for o in ageo if o["match"] not in text]
            save(AKCE_GEO, ageo)
            self._send('{"ok":true}')
        elif p == "/save-misto":
            m = load(MISTA_GEO, {})
            m[body["key"]] = body["geo"]
            save(MISTA_GEO, m)
            self._send('{"ok":true}')
        elif p == "/rebuild":
            r = subprocess.run([sys.executable, "build_investice.py"],
                               capture_output=True, text=True, encoding="utf-8")
            out = (r.stdout or "") + (r.stderr or "")
            self._send(json.dumps({"ok": r.returncode == 0, "out": out.strip()[-300:]}, ensure_ascii=False))
        else:
            self._send("not found", "text/plain", 404)

    def log_message(self, fmt, *args):
        pass


if __name__ == "__main__":
    print(f"Admin mapy investic: http://localhost:{PORT}  (Ctrl+C = konec)")
    payload()   # předehřát cache, ať první požadavek neblokuje
    ThreadingHTTPServer(("127.0.0.1", PORT), H).serve_forever()
