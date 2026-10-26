#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Společné prvky portálu obce Střelice: sdílené CSS, hlavička s navigací
mezi sekcemi, přepínač světlý/tmavý režim, patička. Každá stránka je
samostatný HTML soubor (data + Chart.js vložené) → funguje po dvojkliku
i odděleně; navigace mezi sekcemi funguje, leží-li soubory ve stejné složce."""
import urllib.parse, base64, os, json
from datetime import date

SECTIONS = [
    ("index.html",    "Přehled"),
    ("obdobi.html",   "Bilance"),
    ("rozpocet.html", "Rozpočet"),
    ("srovnani.html", "Srovnání"),
    ("investice.html", "Investice"),
    ("zakazky.html",  "Zakázky"),
    ("dotace.html",   "Dotace spolkům"),
    ("skolstvi.html", "Školství"),
    ("demografie.html", "Demografie"),
    ("volby.html",    "Volby"),
    ("zapisy.html",   "Rada obce"),
    ("zastupitelstvo.html", "Zastupitelstvo"),
]
# hlavní menu: položka = (href, název) nebo skupina (název, [(href, název), ...]) → rozbalovací
NAV = [
    ("index.html", "Přehled"),
    ("Peníze", [("rozpocet.html", "Rozpočet"), ("srovnani.html", "Srovnání"),
                ("investice.html", "Investice"), ("zakazky.html", "Zakázky"),
                ("dotace.html", "Dotace spolkům")]),
    ("zastupitelstvo.html", "Zastupitelstvo"),
    ("zapisy.html", "Rada obce"),
    ("obdobi.html", "Bilance 2022–26"),
    ("Obec", [("skolstvi.html", "Školství"), ("demografie.html", "Demografie"), ("volby.html", "Volby")]),
]
# popisky v rozbalovacím menu (krátká vysvětlivka pod názvem)
NAV_HINT = {"rozpocet.html": "příjmy, výdaje, tok peněz", "srovnani.html": "se sousedními obcemi",
            "investice.html": "co se staví, mapa", "zakazky.html": "komu obec platí",
            "dotace.html": "komu obec přispívá", "zastupitelstvo.html": "usnesení, hlasování, video",
            "zapisy.html": "zápisy z jednání rady", "obdobi.html": "bilance období, zastupitelé",
            "skolstvi.html": "ZŠ, MŠ, ZUŠ, kapacity", "demografie.html": "počet obyvatel, narození, stěhování",
            "volby.html": "komunální volby 2026"}


def nav_html(active):
    """HTML odkazů hlavního menu (skupiny = rozbalovací). `active` = název sekce ze SECTIONS."""
    act = next((h for h, n in SECTIONS + EXTRA_PAGES if n == active), None)
    out = []
    for item in NAV:
        if isinstance(item[1], list):
            label, links = item
            on = any(h == act for h, _ in links)
            sub = "".join(f'<a href="{h}"{" class=\"active\"" if h == act else ""}>{n}'
                          f'{"<small>" + NAV_HINT[h] + "</small>" if h in NAV_HINT else ""}</a>' for h, n in links)
            out.append(f'<div class="ngrp{" on" if on else ""}"><button class="nbtn" type="button" aria-expanded="false">'
                       f'{label}<span class="car">▾</span></button><div class="ndd">{sub}</div></div>')
        else:
            h, n = item
            out.append(f'<a href="{h}"{" class=\"active\"" if h == act else ""}>{n}</a>')
    return "".join(out)


# CSS rozbalovacího menu (sdílené i s rozpocet.html, které má vlastní topbar)
NAV_CSS = """
.ngrp{position:relative}
.nbtn{font:inherit;font-size:13.5px;font-weight:500;color:var(--muted);background:none;border:0;padding:7px 12px;border-radius:10px;cursor:pointer;white-space:nowrap;transition:.18s}
.nbtn:hover,.ngrp.open .nbtn{color:var(--text);background:var(--inset)}
.ngrp.on .nbtn{color:var(--accent);background:var(--accent-soft)}
.nbtn .car{font-size:10px;margin-left:5px;opacity:.7}
.ndd{display:none;position:absolute;top:calc(100% + 6px);left:0;min-width:230px;background:var(--surface);border:1px solid var(--line);border-radius:12px;box-shadow:0 12px 28px rgba(2,8,20,.28);padding:6px;z-index:70}
.ngrp.open .ndd{display:block}
.ndd a{display:block;padding:8px 11px;border-radius:8px;color:var(--text);text-decoration:none;font-size:13.5px;font-weight:500;white-space:nowrap}
.ndd a small{display:block;color:var(--faint);font-size:11.5px;font-weight:400}
.ndd a:hover{background:var(--inset)}
.ndd a.active{color:var(--accent);background:var(--accent-soft)}
@media(min-width:821px){.ngrp:hover .ndd{display:block}.ngrp:hover .ndd::before{content:"";position:absolute;left:0;right:0;top:-8px;height:8px}}
@media(max-width:820px){
  .ngrp{width:100%}
  .nbtn{display:block;width:100%;text-align:left;padding:10px 12px 4px;font-size:11.5px;text-transform:uppercase;letter-spacing:.06em;color:var(--faint);pointer-events:none;background:none!important}
  .nbtn .car{display:none}
  .ndd{display:block;position:static;box-shadow:none;border:0;padding:0 0 4px 8px;min-width:0;background:none}
  .ndd a{padding:10px 12px;font-size:15px}
  .ndd a small{display:none}
  .pnav,.nav{align-items:stretch}
}
@media(max-width:560px){.ptop .in,.topbar .inner{gap:8px;padding-left:14px;padding-right:14px}}
"""

# JS: klik otevře/zavře skupinu (dotyková zařízení), klik mimo zavře
NAV_JS = r"""
(function(){var gs=document.querySelectorAll('.ngrp');
 gs.forEach(function(g){var b=g.querySelector('.nbtn');b.addEventListener('click',function(e){e.stopPropagation();
   var o=!g.classList.contains('open');gs.forEach(function(x){x.classList.remove('open');x.querySelector('.nbtn').setAttribute('aria-expanded','false');});
   if(o){g.classList.add('open');b.setAttribute('aria-expanded','true');}});});
 document.addEventListener('click',function(){gs.forEach(function(x){x.classList.remove('open');});});
 document.addEventListener('keydown',function(e){if(e.key==='Escape')gs.forEach(function(x){x.classList.remove('open');});});})();
"""

# stránky mimo hlavní navigaci (kvůli canonical/og:url)
EXTRA_PAGES = [("hledat.html", "Hledat"), ("odbery.html", "Odběry")]
SEARCH_BTN = ('<a class="iconbtn" href="hledat.html" title="Hledat na portálu (usnesení, firmy, dotace, ulice…)" '
              'aria-label="Hledat" style="text-decoration:none">⌕</a>')

# --- upozornění (Web Push): zvonek v hlavičce + panel, karta na úvodu (push_box) ---
# Backend je v push/ (PHP + SQLite na Wedosu), service worker sw.js, položky k oznámení
# sestaví build_push.py. Převzato z webu Střeličníku (new.strelicnik.cz).
PUSH_TOPICS_UI = [("rada", "Nová jednání rady obce"),
                  ("zastupitelstvo", "Nová jednání zastupitelstva"),
                  ("portal", "Novinky portálu")]
try:
    import hashlib as _hl
    _SW_VER = _hl.sha1(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "sw.js"), "rb").read()).hexdigest()[:10]
except OSError:
    _SW_VER = "0"
PUSH_SW = f"/sw.js?v={_SW_VER}"   # otisk v adrese: Wedos by jinak držel starý sw.js v mezipaměti
BELL_SVG = ('<svg class="ico-bell" viewBox="0 0 24 24" aria-hidden="true"><path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9"/>'
            '<path d="M10.3 21a1.94 1.94 0 0 0 3.4 0"/></svg>')


def push_box(lead=False):
    """Ovládání upozornění. Bez JS a v prohlížeči, který upozornění neumí, se neukáže."""
    topics = "".join(f'<label><input type="checkbox" value="{k}" checked> {t}</label>' for k, t in PUSH_TOPICS_UI)
    intro = ('<p class="pt-lead">Chcete vědět o novém jednání rady nebo zastupitelstva hned, jak se objeví jeho zápis? '
             'Upozornění vám přijde do telefonu nebo počítače, bez registrace a bez e-mailu.</p>') if lead else ''
    return (f'<div class="push-toggle" hidden>{intro}'
            f'<fieldset class="pt-topics"><legend>Co chcete dostávat</legend>{topics}</fieldset>'
            '<button type="button" class="pt-on">Zapnout upozornění</button>'
            '<p class="pt-state" hidden>Upozornění jsou zapnutá. <button type="button" class="pt-off">Vypnout</button></p>'
            '<button type="button" class="pt-latest" hidden>Poslat mi zkušební upozornění</button>'
            '<p class="pt-ios" hidden>Na iPhonu upozornění fungují, když si web přidáte na plochu: v Safari klepněte na Sdílet '
            'a pak na Přidat na plochu. Web potom otevřete z plochy a upozornění zapněte.</p>'
            '<p class="pt-msg" role="status"></p>'
            '<p class="pt-stats"><a href="odbery.html">Kolik lidí upozornění odebírá</a></p></div>')


PUSH_BTN = (f'<button type="button" class="iconbtn pushbtn" id="pushBtn" title="Upozornění na nová jednání" '
            f'aria-label="Upozornění" aria-expanded="false" aria-controls="pushPop" hidden>{BELL_SVG}</button>'
            f'<div class="pushpop" id="pushPop" hidden><b class="pp-h">Upozornění</b>{push_box()}</div>')
SEARCH_BTN = SEARCH_BTN + PUSH_BTN

NAV_CSS = NAV_CSS + """
.pushbtn svg{width:17px;height:17px;fill:none;stroke:currentColor;stroke-width:2;stroke-linecap:round;stroke-linejoin:round}
.pushbtn.on{color:var(--accent);border-color:var(--accent)}
.pushpop{position:absolute;top:calc(100% + 6px);right:16px;width:min(360px,calc(100vw - 32px));z-index:80;background:var(--surface);
  border:1px solid var(--line);border-radius:12px;box-shadow:0 12px 28px rgba(2,8,20,.28);padding:14px 16px}
.pushpop .pp-h{display:block;font-family:var(--font-d);font-size:15px;color:var(--ink);margin-bottom:6px}
.push-toggle{display:flex;flex-direction:column;gap:10px;font-size:13.5px}
.push-toggle[hidden]{display:none}
.push-toggle .pt-lead{margin:0;color:var(--muted);line-height:1.55}
.push-toggle .pt-topics{border:0;margin:0;padding:0;display:flex;flex-direction:column;gap:6px}
.push-toggle .pt-topics legend{font-size:12px;color:var(--muted);margin-bottom:4px;padding:0}
.push-toggle label{display:flex;gap:8px;align-items:center;cursor:pointer}
.push-toggle input[type=checkbox]{accent-color:var(--accent);width:16px;height:16px}
.push-toggle .pt-on,.push-toggle .pt-latest{align-self:flex-start;font:inherit;font-weight:700;font-size:13.5px;border-radius:9px;padding:8px 14px;cursor:pointer}
.push-toggle .pt-on{background:var(--accent);color:var(--surface);border:1px solid var(--accent)}
.push-toggle .pt-latest{background:none;color:var(--accent);border:1px solid var(--line)}
.push-toggle .pt-off{font:inherit;font-size:13px;background:none;border:0;color:var(--accent);text-decoration:underline;cursor:pointer;padding:0}
.push-toggle .pt-state,.push-toggle .pt-ios,.push-toggle .pt-msg{margin:0;line-height:1.5}
.push-toggle .pt-msg{color:var(--muted);font-size:12.5px}
.push-toggle .pt-msg:empty{display:none}
.push-toggle .pt-stats{margin:0;font-size:12.5px}
.push-toggle .pt-stats a{color:var(--muted)}
.push-toggle button:disabled{opacity:.55;cursor:wait}
"""

NAV_JS = NAV_JS + r"""
/* upozornění (Web Push) — převzato z new.strelicnik.cz */
(function(){
  var boxes=[].slice.call(document.querySelectorAll('.push-toggle')); if(!boxes.length) return;
  var btn=document.getElementById('pushBtn'), pop=document.getElementById('pushPop');
  var SW='""" + PUSH_SW + r"""';
  var ua=navigator.userAgent, standalone=matchMedia('(display-mode: standalone)').matches||navigator.standalone===true;
  var ios=/iPhone|iPad|iPod/.test(ua)||(/Macintosh/.test(ua)&&(navigator.maxTouchPoints||0)>1);
  var hasPush='serviceWorker' in navigator&&'PushManager' in window&&'Notification' in window;
  var support=(ios&&!standalone)?'ios':(hasPush?'ok':'no');
  if(support==='no') return;
  var q=function(box,s){return box.querySelector(s);};
  function b64(t){var s=(t+'='.repeat((4-t.length%4)%4)).replace(/-/g,'+').replace(/_/g,'/');return Uint8Array.from(atob(s),function(c){return c.charCodeAt(0);});}
  function show(on,msg){boxes.forEach(function(box){q(box,'.pt-on').hidden=on!==false;q(box,'.pt-state').hidden=on!==true;q(box,'.pt-latest').hidden=on!==true;q(box,'.pt-msg').textContent=msg||'';});
    if(btn) btn.classList.toggle('on',on===true);}
  function busy(b){boxes.forEach(function(box){box.querySelectorAll('button').forEach(function(x){x.disabled=b;});});}
  function post(action,body){return fetch('/push/api.php?a='+action,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)})
    .then(function(r){return (r.status===204?Promise.resolve({}):r.json().catch(function(){return {};})).then(function(j){
      if(!r.ok){var e=new Error(j.error||'Upozornění se nepodařilo zapnout.');e.status=r.status;throw e;}return j;});});}
  var checks=function(){return boxes.reduce(function(a,box){return a.concat([].slice.call(box.querySelectorAll('.pt-topics input')));},[]);};
  var chosen=function(){var s={};[].slice.call(boxes[0].querySelectorAll('.pt-topics input:checked')).forEach(function(c){s[c.value]=1;});return Object.keys(s);};
  var setTopics=function(t){checks().forEach(function(c){c.checked=t.indexOf(c.value)>=0;});};
  var loadT=function(){try{var t=JSON.parse(localStorage.getItem('pushTopics')||'null');return Array.isArray(t)&&t.length?t:null;}catch(e){return null;}};
  var confirmed=loadT()||chosen();
  function confirmT(t){if(!t||!t.length)return;confirmed=t;setTopics(t);try{localStorage.setItem('pushTopics',JSON.stringify(t));}catch(e){}}
  setTopics(confirmed);
  function sub(){return navigator.serviceWorker.getRegistration().then(function(reg){return reg?reg.pushManager.getSubscription():null;});}
  function turnOn(){busy(true);
    Notification.requestPermission().then(function(p){
      if(p!=='granted'){show(false,'Prohlížeč upozornění nepovolil. Povolit je můžete v nastavení webu v prohlížeči.');return;}
      return navigator.serviceWorker.register(SW).then(function(){return navigator.serviceWorker.ready;}).then(function(reg){
        return fetch('/push/api.php?a=key').then(function(r){if(!r.ok)throw new Error('Upozornění teď nejde zapnout. Zkuste to prosím později.');return r.json();})
          .then(function(k){return reg.pushManager.getSubscription().then(function(s){return s||reg.pushManager.subscribe({userVisibleOnly:true,applicationServerKey:b64(k.public_key)});});});
      }).then(function(s){var body=s.toJSON();body.topics=chosen();
        return post('subscribe',body).then(function(r){confirmT(r.topics);show(true,'Hotovo. Upozornění vám budou chodit sem.');},
          function(e){return s.unsubscribe().catch(function(){}).then(function(){throw e;});});});
    }).catch(function(e){show(false,e&&e.message&&!(e instanceof TypeError)?e.message:'Upozornění se nepodařilo zapnout.');})
    .then(function(){busy(false);});}
  function turnOff(){busy(true);sub().then(function(s){if(!s)return;return post('unsubscribe',{endpoint:s.endpoint}).catch(function(){}).then(function(){return s.unsubscribe();});})
    .then(function(){show(false,'Upozornění jsou vypnutá.');},function(){show(false,'Upozornění se nepodařilo vypnout. Vypnout je můžete i v nastavení webu v prohlížeči.');})
    .then(function(){busy(false);});}
  function sendLatest(){busy(true);sub().then(function(s){
      if(!s||Notification.permission!=='granted'){show(false,'V tomto prohlížeči upozornění zapnutá nejsou. Zapněte je znovu.');return;}
      return post('latest',{endpoint:s.endpoint}).then(function(){show(true,'Odesláno. Zkušební upozornění by mělo za chvíli přijít, i když stránku zavřete.');});
    }).catch(function(e){show(e.status===404||e.status===410?false:true,e&&e.message&&!(e instanceof TypeError)?e.message:'Zkoušku se nepodařilo poslat.');})
    .then(function(){busy(false);});}
  boxes.forEach(function(box){box.hidden=false;var sec=box.closest('[data-push-sec]');if(sec)sec.hidden=false;});
  if(btn){btn.hidden=false;btn.addEventListener('click',function(e){e.stopPropagation();var o=pop.hidden;pop.hidden=!o;btn.setAttribute('aria-expanded',o?'true':'false');});
    document.addEventListener('click',function(e){if(!pop.hidden&&!pop.contains(e.target)){pop.hidden=true;btn.setAttribute('aria-expanded','false');}});
    document.addEventListener('keydown',function(e){if(e.key==='Escape'&&!pop.hidden){pop.hidden=true;btn.setAttribute('aria-expanded','false');btn.focus();}});}
  if(support==='ios'){boxes.forEach(function(box){q(box,'.pt-on').hidden=true;q(box,'.pt-topics').hidden=true;q(box,'.pt-ios').hidden=false;});return;}
  checks().forEach(function(c){c.addEventListener('change',function(){
    var box=c.closest('.push-toggle');
    var wanted=[].slice.call(box.querySelectorAll('.pt-topics input:checked')).map(function(x){return x.value;});
    setTopics(wanted);
    if(q(box,'.pt-state').hidden) return;   // ještě nezapnuto: výběr se pošle při zapnutí
    sub().then(function(s){if(!s)return;var body=s.toJSON();body.topics=wanted;
      return post('subscribe',body).then(function(r){confirmT(r.topics);show(true,'Uloženo.');});
    }).catch(function(e){setTopics(confirmed);show(true,e&&e.message?e.message:'Nepodařilo se uložit.');});});});
  boxes.forEach(function(box){q(box,'.pt-on').addEventListener('click',turnOn);q(box,'.pt-off').addEventListener('click',turnOff);q(box,'.pt-latest').addEventListener('click',sendLatest);});
  // stav: ověřit, že zařízení server pořád zná (mohl ho vyřadit); stejné zařízení se jen obnoví
  navigator.serviceWorker.getRegistration().then(function(reg){
    return (reg?reg.pushManager.getSubscription():Promise.resolve(null)).then(function(s){
      if(!s||Notification.permission!=='granted'){show(false);return;}
      var st=loadT(), body=s.toJSON(); if(st) body.topics=st;
      return post('subscribe',body).then(function(r){confirmT(r.topics);show(true);
        navigator.serviceWorker.register(SW).catch(function(){});},function(){show(false);});
    });
  }).catch(function(){show(false);});
})();
"""

# datum sestavení = datum aktualizace dat (stránky se generují po každé změně dat)
_d = date.today()
UPDATED = f"{_d.day}. {_d.month}. {_d.year}"

# kontaktní e-mail chráněný před roboty: v HTML je jen base64 OTOČENÉHO řetězce,
# adresu sestaví až JS v prohlížeči (mailme skript v THEME_JS)
MAIL_LINK = ('<a class="mailme" data-m="emMubWFuemVzQHJlbmVyYg==" '
             'style="color:var(--accent)">e-mail (zapněte si JavaScript)</a>')

# --- vizuální identita „jak se máme" (brand/README.md): petrolej + jantar, Bricolage / Atkinson ---
OLD_NAME = "Jak žijí Střelice"
OBEC_SLUG = "strelice"
BRAND = "Jak se máme, Střelice?"
_HERE = os.path.dirname(os.path.abspath(__file__))
# písma hostovaná u webu (složka fonts/, žádné volání Google) — podmnožiny latin + latin-ext
FONTS_CSS = open(os.path.join(_HERE, "fonts", "fonts.css"), encoding="utf-8").read()
TOKENS_CSS = r"""
:root{
  --bg1:#f2f5f4; --bg2:#f2f5f4; --surface:#fff; --surface2:#f7f9f8; --inset:#e9eeec;
  --text:#1b2b31; --ink:#142f3a; --muted:#58696e; --faint:#8a9a9e; --line:#d9e1de;
  --accent:#1d6b73; --accent-soft:#dcebeb; --amber:#efa42a; --amber-ink:#8a5a08;
  --prijmy:#4fa8ae; --vydaje:#e58a64; --pos:#3b8a5a; --neg:#c0533e;
  --shadow:0 1px 2px rgba(20,47,58,.04), 0 2px 10px rgba(20,47,58,.05);
  --shadow-h:0 6px 22px rgba(20,47,58,.11);
  --radius:14px; --radius-sm:10px;
  --c0:#7cc4c8; --c1:#f2a7a0; --c2:#a5d19a; --c3:#f4c878; --c4:#b9aee6;
  --c5:#a3b8c4; --c6:#8fcde6; --c7:#e3b394; --c8:#a4b9e8; --c9:#cfd58f;
  --font-d:"Bricolage Grotesque","Segoe UI Variable","Segoe UI",system-ui,sans-serif;
  --font-b:"Atkinson Hyperlegible","Segoe UI Variable","Segoe UI",-apple-system,Roboto,Arial,sans-serif;
  --font-m:"IBM Plex Mono",ui-monospace,Consolas,monospace;
}
html[data-theme="dark"]{
  --bg1:#0d191e; --bg2:#0d191e; --surface:#13242a; --surface2:#102026; --inset:#0f1f24;
  --text:#d6e2e0; --ink:#e4eeec; --muted:#8fa4a7; --faint:#62777b; --line:#22373e;
  --accent:#5fb0b5; --accent-soft:#173338; --amber:#f4b547; --amber-ink:#f4b547;
  --prijmy:#6fbfc4; --vydaje:#ee9a76; --pos:#6bc08c; --neg:#e58a75;
  --c0:#6fbfc4; --c1:#ee9f98; --c2:#9bcb8f; --c3:#f0c16a; --c4:#afa4e0;
  --c5:#9aafbc; --c6:#84c6e0; --c7:#dda988; --c8:#9ab0e2; --c9:#c7ce84;
  --shadow:0 1px 2px rgba(0,0,0,.35), 0 6px 22px rgba(0,0,0,.35);
  --shadow-h:0 10px 32px rgba(0,0,0,.5);
  color-scheme:dark;
}
"""
# nadpisy a velká čísla display písmem; logo v hlavičce (barvy SVG přes třídy → přepínají se s tématem)
TYPE_CSS = r"""
h1,h2,h3,.hero h1,.sec-h h2,.tile h3,.kpi .val,.yearctl .yv,.donut-center .v{font-family:var(--font-d);letter-spacing:-.015em}
h1,.hero h1,.sec-h h2,.tile h3{color:var(--ink)}
.hero h1{font-weight:720;letter-spacing:-.025em}
.brand{display:flex;align-items:center;text-decoration:none;color:var(--ink);flex:none;border-radius:8px}
.brand svg{height:30px;width:auto;display:block}
.brand .tagline{margin-left:12px;padding-left:12px;border-left:1px solid var(--line);font-size:12px;line-height:1.25;color:var(--muted);white-space:nowrap}
@media(max-width:1100px){.brand .tagline{display:none}}
.lg-i{fill:var(--ink)}.lg-o{fill:var(--accent)}.lg-a{fill:var(--amber)}.lg-q{fill:var(--muted)}
:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.tile .ic svg{width:24px;height:24px;fill:none;stroke:currentColor;stroke-width:1.8;stroke-linecap:round;stroke-linejoin:round}
/* drobná linková ikona v textu (místo barevných emoji) */
.ico{width:1.05em;height:1.05em;vertical-align:-.17em;fill:none;stroke:currentColor;stroke-width:2;stroke-linecap:round;stroke-linejoin:round}
@media(max-width:560px){.brand svg{height:24px}}
@media(max-width:400px){.brand svg{height:20px}}
"""
BRAND_SVG = open(os.path.join(_HERE, "brand", "logo", "web", f"{OBEC_SLUG}-header.svg"),
                 encoding="utf-8").read().strip()
TAGLINE = "občanský datový portál"
BRAND_HTML = (f'<a class="brand" href="index.html" aria-label="{BRAND} – {TAGLINE}, úvod">{BRAND_SVG}'
              f'<span class="tagline" aria-hidden="true">{TAGLINE}</span></a>')

SHARED_CSS = FONTS_CSS + TOKENS_CSS + r"""
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{margin:0;color:var(--text);
  font-family:var(--font-b);
  font-size:15px;line-height:1.55;background:var(--bg2);
  min-height:100vh;-webkit-font-smoothing:antialiased}
.wrap{max-width:1160px;margin:0 auto;padding:0 20px 20px}
.ptop{position:sticky;top:0;z-index:50;background:var(--surface);border-bottom:1px solid var(--line)}
.ptop .in{max-width:1160px;margin:0 auto;padding:11px 20px;display:flex;align-items:center;gap:16px}
.pnav{display:flex;gap:2px;margin-left:auto;flex-wrap:wrap}
.pnav a{padding:7px 12px;border-radius:10px;color:var(--muted);text-decoration:none;font-size:13.5px;font-weight:500;transition:.18s;white-space:nowrap}
.pnav a:hover{color:var(--text);background:var(--inset)}
.pnav a.active{color:var(--accent);background:var(--accent-soft)}
.pnav{align-items:center}
.iconbtn{width:38px;height:34px;border:1px solid var(--line);background:var(--surface);border-radius:10px;cursor:pointer;color:var(--muted);display:grid;place-items:center;transition:.18s;font-size:15px}
.iconbtn:hover{color:var(--text);border-color:var(--accent)}
.navtoggle{display:none;width:40px;height:34px;border:1px solid var(--line);background:var(--surface);
  border-radius:10px;cursor:pointer;color:var(--text);font-size:17px;place-items:center;margin-left:auto}
.navtoggle:hover{border-color:var(--accent)}
.hero{padding:34px 0 8px}
.hero h1{font-size:30px;font-weight:680;letter-spacing:-.02em;margin:0 0 6px;color:var(--text)}
.hero p{color:var(--muted);margin:0;font-size:14.5px}
.chips{display:flex;gap:8px;margin-top:14px;flex-wrap:wrap}
.chip{font-size:12px;padding:5px 11px;border-radius:999px;background:var(--inset);color:var(--muted);border:1px solid var(--line)}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(186px,1fr));gap:14px;margin:22px 0 8px}
.kpi{background:var(--surface);border:1px solid var(--line);border-radius:var(--radius);padding:16px 18px;box-shadow:var(--shadow);transition:transform .2s,box-shadow .2s;position:relative;overflow:hidden}
.kpi:hover{transform:translateY(-3px);box-shadow:var(--shadow-h)}
.kpi::after{content:"";position:absolute;left:0;top:0;bottom:0;width:4px;background:var(--bar,var(--accent))}
.kpi .lab{font-size:12.5px;color:var(--muted)}
.kpi .val{font-size:26px;font-weight:680;margin-top:7px;letter-spacing:-.02em;font-variant-numeric:tabular-nums}
.kpi .delta{font-size:12px;margin-top:5px;font-weight:500}
.up{color:var(--pos)} .down{color:var(--neg)}
section{margin-top:30px;scroll-margin-top:74px}
.sec-h{display:flex;align-items:baseline;gap:12px;margin:0 0 14px}
.sec-h h2{font-size:19px;font-weight:640;margin:0;letter-spacing:-.01em}
.sec-h .hint{color:var(--faint);font-size:12.5px}
.panel{background:var(--surface);border:1px solid var(--line);border-radius:var(--radius);padding:20px 22px;box-shadow:var(--shadow)}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:18px}
@media(max-width:820px){.grid2{grid-template-columns:1fr}}
@media(max-width:820px){
  .navtoggle{display:grid}
  .pnav{position:absolute;top:100%;left:0;right:0;display:none;flex-direction:column;gap:4px;margin:0;
    background:var(--surface);border-bottom:1px solid var(--line);box-shadow:0 10px 22px rgba(2,8,20,.28);padding:8px 16px 14px;z-index:60}
  .pnav.open{display:flex}
  .pnav a{padding:12px;font-size:15px;border-radius:10px}
}
.ctrls{display:flex;flex-wrap:wrap;gap:12px 18px;align-items:center;margin-bottom:6px}
.seg{display:inline-flex;flex-wrap:wrap;background:var(--inset);border-radius:11px;padding:3px;gap:2px}
.seg button{border:0;background:transparent;color:var(--muted);font:inherit;font-size:13px;font-weight:500;padding:6px 13px;border-radius:8px;cursor:pointer;transition:.16s}
.seg button.on{background:var(--surface);color:var(--text);box-shadow:var(--shadow)}
.lbl{font-size:12.5px;color:var(--muted);font-weight:500;margin-right:2px}
.legend{display:flex;flex-wrap:wrap;gap:8px 16px;font-size:12px;color:var(--muted);margin:10px 0}
.legend span{display:inline-flex;align-items:center;gap:6px}
.sw{width:11px;height:11px;border-radius:3px;display:inline-block}
.chartbox{position:relative;width:100%;height:330px;margin-top:6px}
.chartbox.sm{height:280px}
.note{font-size:12px;color:var(--faint);margin-top:12px;line-height:1.6}
.footer{margin-top:10px;color:var(--faint);font-size:11.5px;text-align:center;line-height:1.4;padding-bottom:6px}
.footer a{color:var(--muted);text-decoration:none;border-bottom:1px dotted var(--faint)}
.footer a:hover{color:var(--accent);border-bottom-color:var(--accent)}
.dlbtn{display:inline-flex;align-items:center;gap:6px;font:inherit;font-size:12px;font-weight:500;color:var(--muted);
  background:var(--inset);border:1px solid var(--line);border-radius:9px;padding:5px 11px;cursor:pointer;transition:.16s;white-space:nowrap}
.dlbtn:hover{color:var(--accent);border-color:var(--accent)}
/* řaditelné hlavičky tabulek */
.thsort{cursor:pointer;user-select:none;white-space:nowrap;transition:color .14s}
.thsort:hover{color:var(--text)}
.thsort .ar{font-size:9px;opacity:.65;margin-left:3px}
.brandfoot{margin-top:34px;padding-top:20px;border-top:1px solid var(--line);text-align:center}
.brandfoot img{height:46px;width:auto;opacity:.9;transition:opacity .2s, transform .2s}
.brandfoot a:hover img{opacity:1;transform:translateY(-2px)}
/* rozcestník */
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:18px;margin-top:8px}
.tile{display:flex;flex-direction:column;gap:10px;background:var(--surface);border:1px solid var(--line);border-radius:var(--radius);
  padding:22px 22px;box-shadow:var(--shadow);text-decoration:none;color:var(--text);transition:transform .2s,box-shadow .2s;position:relative}
.tile:hover{transform:translateY(-4px);box-shadow:var(--shadow-h)}
.tile.soon{opacity:.65;pointer-events:none}
.tile .ic{width:46px;height:46px;border-radius:13px;display:grid;place-items:center;font-size:22px;color:var(--accent);background:var(--accent-soft)}
.tile h3{margin:4px 0 0;font-size:18px;font-weight:640}
.tile p{margin:0;color:var(--muted);font-size:13.5px;line-height:1.55}
.tile .go{margin-top:auto;font-size:13px;color:var(--accent);font-weight:600}
.tile .badge{position:absolute;top:16px;right:16px;font-size:11px;padding:3px 9px;border-radius:999px;background:var(--inset);color:var(--muted)}
.statline{display:flex;gap:18px;flex-wrap:wrap;margin-top:6px;font-size:12.5px;color:var(--muted)}
.statline b{color:var(--text);font-weight:600}
/* modal */
.modal{position:fixed;inset:0;z-index:200;display:flex;align-items:center;justify-content:center;padding:18px}
.modal[hidden]{display:none}
.modal-bd{position:absolute;inset:0;background:rgba(13,25,30,.55)}
.modal-card{position:relative;background:var(--surface);border:1px solid var(--line);border-radius:var(--radius);max-width:640px;width:100%;max-height:84vh;display:flex;flex-direction:column;box-shadow:0 24px 70px rgba(0,0,0,.4)}
.modal-h{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:15px 18px;border-bottom:1px solid var(--line)}
.modal-h b{font-size:15.5px;font-weight:600}
.modal-c{padding:8px 18px 18px;overflow:auto}
.mtab{width:100%;border-collapse:collapse;font-size:12.5px;margin-top:8px}
.mtab th,.mtab td{padding:7px 8px;border-bottom:1px solid var(--line);text-align:right;white-space:nowrap}
.mtab th:first-child,.mtab td:first-child{text-align:left;white-space:normal}
.mtab th{color:var(--muted);font-weight:600;font-size:11.5px}
.mtab tr.total td{font-weight:680;border-top:2px solid var(--text);background:var(--surface2)}
"""

# favikona: SVG z brand/favicon (sama se přepne v tmavém režimu prohlížeče) jako data URI → funguje i offline;
# ostatní ikony (ico, apple-touch, manifest) nahrává deploy.yml z brand/favicon/ do kořene webu
_FAV_SVG = open(os.path.join(_HERE, "brand", "favicon", "favicon.svg"), encoding="utf-8").read().strip()
FAVICON_LINK = ('<link rel="icon" href="data:image/svg+xml,' + urllib.parse.quote(_FAV_SVG) + '" type="image/svg+xml">'
                '<link rel="apple-touch-icon" href="/apple-touch-icon.png"><link rel="manifest" href="/site.webmanifest">'
                '<meta name="theme-color" content="#142f3a">')

# grafy Chart.js: písmo podle CI; po načtení webových písem se překreslí
CHART_FONT_JS = ("<script>if(window.Chart){Chart.defaults.font.family=getComputedStyle(document.documentElement)"
                 ".getPropertyValue('--font-b').trim();if(document.fonts)document.fonts.ready.then(function(){"
                 "Object.values(Chart.instances||{}).forEach(function(c){c.update('none');});});}</script>")


def inject_chart_font(html):
    """Vloží CHART_FONT_JS hned za vložený Chart.js (pokud ho stránka má)."""
    i = html.find("* Chart.js v")
    if i < 0:
        return html
    j = html.find("</script>", i) + len("</script>")
    return html[:j] + CHART_FONT_JS + html[j:]


# Cloudflare Web Analytics (bez cookies) — web strelice.jaksemame.cz; token je veřejný (je v HTML každé stránky)
ANALYTICS = ("<script type='module' src='https://static.cloudflareinsights.com/beacon.min.js'"
             " data-cf-beacon='{\"token\": \"6933a7704eea40fb96f9f52c6f0e10e0\"}'></script>")


# oddělovač nad patičkou (logo a odkaz na Střeličník byly na přání odebrány)
BRANDFOOT = ('<div style="margin-top:34px;padding-top:20px;border-top:1px solid var(--line);'
             'text-align:center;color:var(--faint);font-size:12px">'
             'Občanský datový portál obce Střelice · data z veřejných zdrojů</div>')

def topbar(active):
    links = nav_html(active)
    return f'''<div class="ptop"><div class="in">
  {BRAND_HTML}
  <button class="navtoggle" id="navToggle" aria-label="Menu" aria-expanded="false">&#9776;</button>
  <nav class="pnav" id="pnav">{links}</nav>
  {SEARCH_BTN}
  <button class="iconbtn" id="themeBtn" title="Světlý/tmavý režim">◐</button>
</div></div>'''

THEME_INIT = r"""(function(){try{var t=localStorage.getItem('strelice-theme');if(t)document.documentElement.setAttribute('data-theme',t);}catch(e){}})();"""

THEME_JS = r"""
function bindTheme(after){var b=document.getElementById('themeBtn');if(!b)return;
  b.onclick=function(){var d=document.documentElement.getAttribute('data-theme')==='dark';
    document.documentElement.setAttribute('data-theme',d?'light':'dark');
    try{localStorage.setItem('strelice-theme',d?'light':'dark');}catch(e){}
    if(after)after();};}
function cssv(n){return getComputedStyle(document.documentElement).getPropertyValue(n).trim();}
function isDark(){return document.documentElement.getAttribute('data-theme')==='dark';}
(function(){var t=document.getElementById('navToggle'),n=document.getElementById('pnav');
 if(t&&n){t.addEventListener('click',function(){var o=n.classList.toggle('open');t.setAttribute('aria-expanded',o);});
 n.addEventListener('click',function(e){if(e.target.tagName==='A')n.classList.remove('open');});}})();
(function(){var els=document.querySelectorAll('.mailme');
 for(var i=0;i<els.length;i++){var a=els[i],
   m=atob(a.getAttribute('data-m')).split('').reverse().join('');
   a.href='mailto:'+m;a.textContent=m;}})();
function dlCSV(name,header,rows){
  var esc=function(c){c=(c==null?'':String(c));return /[";\n]/.test(c)?'"'+c.replace(/"/g,'""')+'"':c;};
  var csv=[header].concat(rows).map(function(r){return r.map(esc).join(';');}).join('\r\n');
  var a=document.createElement('a');
  a.href=URL.createObjectURL(new Blob([String.fromCharCode(0xFEFF)+csv],{type:'text/csv;charset=utf-8'}));
  a.download=name;document.body.appendChild(a);a.click();a.remove();
  setTimeout(function(){URL.revokeObjectURL(a.href);},500);}
"""

# --- Open Graph / náhled odkazu na sociálních sítích (FB apod.) ---
SITE = "https://strelice.jaksemame.cz"
FB_URL = "https://www.facebook.com/jaksemame"  # FB stránka projektu (odkaz v patičce)

# --- karta „Nově na Facebooku" na úvodu (fb_card) ---
FB_ICON = ('<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M18 2h-3a5 5 0 0 0-5 5v3H7v4h3v8h4v-8h3l1-4h-4V7'
           'a1 1 0 0 1 1-1h3z"/></svg>')
FB_CARD_CSS = """<style>
.fbcard{display:flex;align-items:center;gap:18px;margin:18px 0 0;padding:18px 22px;border-radius:var(--radius);text-decoration:none;
  color:var(--text);border:1px solid var(--line);box-shadow:var(--shadow);transition:transform .2s,box-shadow .2s;
  background:radial-gradient(420px 160px at 0% 0%,color-mix(in srgb,var(--amber) 16%,transparent),transparent 70%),var(--surface)}
.fbcard:hover{transform:translateY(-2px);box-shadow:var(--shadow-h)}
.fbcard .fb-ic{flex:none;width:54px;height:54px;border-radius:15px;display:grid;place-items:center;background:var(--amber);color:var(--ink)}
.fbcard .fb-ic svg{width:26px;height:26px;fill:none;stroke:currentColor;stroke-width:2;stroke-linecap:round;stroke-linejoin:round}
.fbcard .fb-tx{flex:1;min-width:0}
.fbcard .fb-k{display:block;font-size:11.5px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:var(--amber-ink);margin-bottom:3px}
.fbcard .fb-h{display:block;font-family:var(--font-d);font-size:18px;font-weight:720;line-height:1.3}
.fbcard .fb-p{display:block;margin-top:4px;font-size:13.5px;line-height:1.55;color:var(--muted)}
.fbcard .fb-go{flex:none;font-weight:700;font-size:13.5px;color:var(--accent);border:1px solid var(--line);border-radius:999px;padding:8px 16px;white-space:nowrap}
.fbcard:hover .fb-go{border-color:var(--accent)}
@media(max-width:560px){.fbcard{flex-wrap:wrap;align-items:flex-start;gap:12px 14px;padding:16px}.fbcard .fb-ic{width:44px;height:44px;border-radius:12px}
  .fbcard .fb-tx{flex-basis:calc(100% - 60px)}.fbcard .fb-h{font-size:16px}.fbcard .fb-go{margin-left:58px}}
</style>"""


def fb_card():
    """Upoutávka na FB stránku projektu (úvod portálu); CSS je součástí, stačí vložit do těla."""
    return (FB_CARD_CSS + f'<a class="fbcard" href="{FB_URL}" target="_blank" rel="noopener">'
            f'<span class="fb-ic">{FB_ICON}</span><span class="fb-tx"><span class="fb-k">Nově na Facebooku</span>'
            '<b class="fb-h">Novinky z portálu teď i na Facebooku</b>'
            '<span class="fb-p">Na stránce Jak se máme dám vědět o každé novince na portálu, o nových jednáních '
            'a o zajímavostech, které z dat obce vypadnou.</span></span>'
            '<span class="fb-go">Sledovat stránku →</span></a>')

OG_DESC = ("Otevřená data obce Střelice u Brna srozumitelně: rozpočet, investice, "
           "dotace spolkům, školství a usnesení zastupitelstva — interaktivně a pro každého.")


# --- maskot (robůtek s hlavou-grafem, maskot/*.svg z brand/build_maskot.py) ---
# Nikdy nevyskakuje sám: nápověda u grafu se otevře až kliknutím (tlačítko s hlavou robota)
# a rozbalí se v toku stránky pod nadpisem, takže nezakrývá data. Texty jen vysvětlují,
# co graf ukazuje a jak ho číst — nehodnotí.
MASCOT_DIR = "maskot/"
_mh_n = [0]


def mascot_img(name, cls="msk", alt=""):
    return f'<img class="{cls}" src="{MASCOT_DIR}{name}.svg" alt="{alt}" loading="lazy" decoding="async">'


def mascot_help(title, text, img="10-hlava-mini"):
    """Tlačítko nápovědy do .sec-h (za <h2>) + panel, který se rozbalí pod nadpisem."""
    _mh_n[0] += 1
    i = f"mh{_mh_n[0]}"
    return (f'<button type="button" class="mh-btn" aria-expanded="false" aria-controls="{i}" '
            f'title="Nápověda: {title}"><img src="{MASCOT_DIR}10-hlava-mini.svg" alt="">'
            f'<span class="sr">Nápověda: {title}</span></button>'
            f'<div class="mh-pop" id="{i}" role="region" aria-label="Nápověda: {title}" hidden>'
            f'<span class="mh-fig">{mascot_img(img)}</span><div class="mh-tx"><b class="mh-t">{title}</b>{text}</div>'
            f'<button type="button" class="mh-x" aria-label="Zavřít nápovědu">✕</button></div>')


def mascot_note(img, html, cls=""):
    """Statická bublina s robotem (prázdný stav, úvod sekce). Bez interakce, nic nepřekrývá."""
    return (f'<div class="msk-note {cls}"><span class="mh-fig">{mascot_img(img)}</span>'
            f'<div class="msk-say">{html}</div></div>')


NAV_CSS = NAV_CSS + """
.sr{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap}
.sec-h:has(.mh-btn){flex-wrap:wrap;align-items:center}
.mh-btn{flex:none;width:34px;height:34px;padding:0;border-radius:50%;border:1px solid var(--line);background:var(--msk-bg);
  cursor:pointer;display:grid;place-items:center;transition:transform .15s,border-color .15s;align-self:center}
.mh-btn img{width:24px;height:auto;display:block}
.mh-btn:hover{transform:translateY(-1px);border-color:var(--accent)}
.mh-btn:focus-visible,.mh-x:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.mh-btn[aria-expanded="true"]{border-color:var(--amber);box-shadow:0 0 0 3px color-mix(in srgb,var(--amber) 25%,transparent)}
.mh-pop{flex-basis:100%;order:9;display:flex;gap:14px;align-items:flex-start;position:relative;margin-top:4px;
  padding:14px 44px 14px 14px;border-radius:14px;background:var(--surface);border:1px solid var(--line);border-left:4px solid var(--amber);
  font-family:var(--font-b);font-size:14px;line-height:1.55;color:var(--text);font-weight:400;letter-spacing:0}
.mh-pop[hidden]{display:none}
.mh-tx .mh-t{display:block;font-family:var(--font-d);font-size:15px;margin-bottom:2px;color:var(--ink)}
.mh-tx p{margin:4px 0 0}
.mh-x{position:absolute;top:8px;right:8px;width:30px;height:30px;border-radius:8px;border:0;background:none;color:var(--muted);cursor:pointer;font-size:15px}
.mh-x:hover{color:var(--text);background:var(--inset)}
.mh-fig{flex:none;width:76px;height:76px;border-radius:18px;background:var(--msk-bg);display:grid;place-items:center;overflow:hidden}
.mh-fig .msk{width:88%;height:88%;object-fit:contain}
.msk-note{display:flex;gap:16px;align-items:center;padding:16px;border-radius:14px;background:var(--inset);border:1px dashed var(--line);color:var(--muted);font-size:14px;line-height:1.55}
.msk-note .mh-fig{width:96px;height:96px}
.msk-say b{color:var(--text)}
:root{--msk-bg:#e3eeec}
html[data-theme="dark"]{--msk-bg:#dbe7e5}
@media(max-width:560px){.mh-pop{padding:12px 40px 12px 12px;gap:10px}.mh-fig{width:56px;height:56px;border-radius:14px}
  .msk-note{padding:12px;gap:12px}.msk-note .mh-fig{width:72px;height:72px}}
"""

NAV_JS = NAV_JS + r"""
/* nápověda s maskotem: otevře se jen kliknutím, Esc / ✕ zavře a vrátí fokus na tlačítko */
(function(){
  function set(btn,open){var p=document.getElementById(btn.getAttribute('aria-controls'));if(!p)return;
    btn.setAttribute('aria-expanded',open?'true':'false');p.hidden=!open;}
  document.addEventListener('click',function(e){
    var b=e.target.closest&&e.target.closest('.mh-btn');
    if(b){set(b,b.getAttribute('aria-expanded')!=='true');return;}
    var x=e.target.closest&&e.target.closest('.mh-x');
    if(x){var p=x.closest('.mh-pop'),bt=document.querySelector('.mh-btn[aria-controls="'+p.id+'"]');if(bt){set(bt,false);bt.focus();}}
  });
  document.addEventListener('keydown',function(e){
    if(e.key!=='Escape')return;
    var p=document.activeElement&&document.activeElement.closest&&document.activeElement.closest('.mh-pop');
    var bt=p?document.querySelector('.mh-btn[aria-controls="'+p.id+'"]'):(document.activeElement&&document.activeElement.closest&&document.activeElement.closest('.mh-btn'));
    if(bt&&bt.getAttribute('aria-expanded')==='true'){set(bt,false);bt.focus();}
  });
})();
"""


def og_meta(active, title):
    """Meta značky pro hezký náhled při sdílení (obrázek og-image.png je plochý soubor v kořeni)."""
    fn = next((f for f, n in SECTIONS + EXTRA_PAGES if n == active), "index.html")
    url = SITE + "/" + ("" if fn == "index.html" else fn)
    t = (title or BRAND).replace('"', '&quot;')
    img = SITE + "/og-image.png"
    return (
        f'<link rel="canonical" href="{url}">'
        '<meta property="og:type" content="website">'
        f'<meta property="og:site_name" content="{BRAND}">'
        f'<meta property="og:title" content="{t}">'
        f'<meta property="og:description" content="{OG_DESC}">'
        f'<meta property="og:image" content="{img}">'
        '<meta property="og:image:width" content="1200">'
        '<meta property="og:image:height" content="630">'
        f'<meta property="og:url" content="{url}">'
        '<meta name="twitter:card" content="summary_large_image">'
        f'<meta name="twitter:title" content="{t}">'
        f'<meta name="twitter:description" content="{OG_DESC}">'
        f'<meta name="twitter:image" content="{img}">'
        f'<meta name="description" content="{OG_DESC}">')


def page(active, title, body, head_scripts="", body_scripts=""):
    # starý název portálu v titulcích a textech builderů → název značky (změna na jednom místě)
    title = title.replace(OLD_NAME, BRAND)
    body = body.replace(OLD_NAME, BRAND)
    head_scripts, body_scripts = inject_chart_font(head_scripts), inject_chart_font(body_scripts)
    footer = ('<footer class="footer">Data aktualizována k <b style="color:var(--muted)">' + UPDATED + '</b>'
              ' &nbsp;·&nbsp; <a href="metodika.html">Metodika a zdroje dat</a>'
              ' &nbsp;·&nbsp; <a href="odbery.html">Odběry upozornění</a>'
              ' &nbsp;·&nbsp; <a href="' + FB_URL + '" rel="noopener">Facebook</a><br>'
              'Sestavil <b style="color:var(--muted)">Radim Brener</b> ze surových CSV souborů, jednoho terminálu a hluboké víry, že veřejná data jsou vždy konzistentní 🙃 &nbsp;·&nbsp; Python &thinsp;·&thinsp; Chart.js &thinsp;·&thinsp; MONITOR SP &thinsp;·&thinsp; ČSÚ &thinsp;·&thinsp; 2025–2026</footer>')
    return f'''<!DOCTYPE html>
<html lang="cs" data-theme="dark">
<head>
<script>{THEME_INIT}</script>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
{og_meta(active, title)}
{FAVICON_LINK}
{ANALYTICS}
<style>{SHARED_CSS}</style>
{head_scripts}
</head>
<body>
{topbar(active)}
<div class="wrap">
{body}
{BRANDFOOT}
{footer}
</div>
<script>{THEME_JS}</script>
{body_scripts}
</body>
</html>'''

# rozbalovací menu: CSS a JS připojené ke sdíleným blokům
SHARED_CSS = SHARED_CSS + TYPE_CSS + NAV_CSS
THEME_JS = THEME_JS + NAV_JS

# --- jednotné barvy a ikony témat napříč portálem (Rada obce, Zastupitelstvo, Hledat, Bilance) ---
TEMA_COL = {
    "Pozemky, majetek a bydlení": "--c3",
    "Stavby, investice a územní rozvoj": "--c7",
    "Dotace a finance": "--c0",
    "Školství": "--c4",
    "Životní prostředí a odpady": "--c2",
    "Kultura, sport a spolky": "--c1",
    "Správa obce a úřad": "--c5",
    "Doprava a sítě": "--c8",
    "Sociální a zdravotní oblast": "--c6",
    "Jednání a formality": "--c9",
    "Ostatní": "--faint",
}
# témata se rozlišují jen barevnou tečkou (emoji ikony na přání odebrány); temaIco/TICO zůstávají
# kvůli builderům, které je volají, ale vrací prázdno
TEMA_JS = ("const TCOL=" + json.dumps(TEMA_COL, ensure_ascii=False) + ",TICO={};"
           "function temaName(n){return TCOL[n]||'--faint';}"
           "function temaVar(n){return 'var('+temaName(n)+')';}"
           "function temaRGB(n){return cssv(temaName(n));}"
           "function temaIco(n){return '';}")

# --- skeleton: jemný „shimmer" místo prázdných míst, než JS vykreslí data (velké stránky) ---
SKEL_CSS = """
@keyframes skel{0%{background-position:-400px 0}100%{background-position:400px 0}}
.skel{border-radius:10px;background:linear-gradient(90deg,var(--inset) 0,var(--line) 40%,var(--inset) 80%);background-size:800px 100%;animation:skel 1.3s linear infinite}
.skel-row{height:54px;margin:0 0 10px}
.skel-row.sm{height:18px;margin:10px 12px}
.chartbox:not(:has(canvas[style])){border-radius:10px;background:linear-gradient(90deg,transparent 0,var(--inset) 40%,transparent 80%);background-size:800px 100%;animation:skel 1.3s linear infinite}
@media(prefers-reduced-motion:reduce){.skel,.chartbox{animation:none!important}}
"""
SHARED_CSS = SHARED_CSS + SKEL_CSS


def skel(n=6, cls=""):
    """Zástupné řádky do kontejneru, který JS přepíše skutečným obsahem (innerHTML)."""
    return "".join(f'<div class="skel skel-row {cls}"></div>' for _ in range(n))


def skel_tr(n=8, cols=4):
    return "".join('<tr>' + f'<td colspan="{cols}"><div class="skel skel-row sm"></div></td>' + '</tr>' for _ in range(n))
