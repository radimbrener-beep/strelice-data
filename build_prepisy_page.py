#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generuje NEVEŘEJNOU (neodkazovanou, noindex) stránku 'prepisy-zo.html' —
odkaz, ze kterého lze stáhnout plné přepisy diskuze jednotlivých zasedání
zastupitelstva jako čitelný .txt (i vše najednou). Texty jsou předsestavené
v Pythonu a vložené do stránky; stažení řeší prohlížeč (Blob) → jeden
samostatný soubor bez potřeby serveru. Není v hlavním menu (SECTIONS)."""
import sys, json, glob, os, datetime
import portal_common as pc
sys.stdout.reconfigure(encoding="utf-8")

zo = {m["cislo_zasedani"]: m for m in json.load(open("dataset_ZO.json", encoding="utf-8"))}

def fmt_d(iso):
    p = (iso or "").split("-")
    return f"{int(p[2])}. {int(p[1])}. {p[0]}" if len(p) == 3 else (iso or "")

def mmss(s):
    s = int(s or 0)
    return f"{s // 60}:{s % 60:02d}"

SEP = "─" * 60
DISCLAIMER = ("Redakčně upravený přepis z automatických titulků videozáznamu — orientační, "
              "NENÍ doslovný ani úřední záznam. Závazné je usnesení a originální zápis.\n"
              "Zastupitelé jsou uvedeni jménem, občané z pléna anonymizováni.")

def build_text(cislo, pj):
    m = zo.get(cislo, {})
    body_ds = m.get("body", [])
    vid = pj.get("vid")
    L = []
    L.append("PŘEPIS JEDNÁNÍ ZASTUPITELSTVA OBCE STŘELICE")
    L.append(f"{cislo}. zasedání — {fmt_d(m.get('datum',''))}")
    if vid:
        L.append(f"Videozáznam: https://youtu.be/{vid}")
    L.append("")
    L.append(DISCLAIMER)
    L.append("")
    for b in pj.get("body", []):
        idx = b.get("index")
        ds = body_ds[idx] if isinstance(idx, int) and idx < len(body_ds) else {}
        kat = (ds.get("kategorie") or "").upper()
        usn = ds.get("text") or ""
        head = f"Bod {idx}"
        if b.get("start") is not None:
            head += f"  [{mmss(b['start'])}]"
        if kat:
            head += f"  — {kat}"
        L.append(SEP)
        L.append(head)
        if usn:
            L.append(f"Usnesení: {usn}")
        L.append("")
        for t in b.get("turns", []):
            who = t.get("who", "").strip()
            txt = t.get("text", "").strip()
            L.append(f"  {who}: {txt}")
        L.append("")
    L.append(SEP)
    L.append(f"Zdroj: videozáznam obce (YouTube @tvstreliceubrna) + ověřená data portálu jakzijistrelice.cz.")
    return "\n".join(L)

# načti všechny přepisy
meetings = []
for fp in sorted(glob.glob("prepisy/*.json"), key=lambda p: int(os.path.basename(p).split(".")[0]) if os.path.basename(p).split(".")[0].isdigit() else 0):
    base = os.path.basename(fp)
    if base.startswith("_"):
        continue
    pj = json.load(open(fp, encoding="utf-8"))
    c = pj.get("cislo_zasedani")
    if c is None:
        continue
    txt = build_text(c, pj)
    nturns = sum(len(b.get("turns", [])) for b in pj.get("body", []))
    meetings.append({"c": c, "datum": zo.get(c, {}).get("datum", ""),
                     "datum_text": fmt_d(zo.get(c, {}).get("datum", "")),
                     "vid": pj.get("vid"), "body": len(pj.get("body", [])),
                     "turns": nturns, "txt": txt})
meetings.sort(key=lambda x: x["c"], reverse=True)

TEXTS = {str(m["c"]): m["txt"] for m in meetings}
today = datetime.date.today().isoformat()

rows = "".join(
    f'''<div class="dlrow">
      <div class="dlmeta"><span class="dlnum">ZO {m['c']}</span>
        <span class="dldate">{m['datum_text']}</span>
        <span class="dlsub">{m['body']} bodů · {m['turns']} replik</span></div>
      <div class="dlact">
        {'<a class="dlyt" href="https://youtu.be/'+m['vid']+'" target="_blank" rel="noopener">▶ záznam</a>' if m['vid'] else ''}
        <button class="dlbtn" data-c="{m['c']}">⬇ Stáhnout .txt</button>
      </div>
    </div>''' for m in meetings)

total_turns = sum(m["turns"] for m in meetings)

body = f'''<header class="hero">
  <h1>Přepisy jednání zastupitelstva <span style="font-size:16px;font-weight:500;color:var(--muted)">· ke stažení</span></h1>
  <p>Plné přepisy diskuze z jednotlivých zasedání Zastupitelstva obce Střelice (ze záznamů na YouTube). Stáhni si jedno zasedání, nebo vše najednou jako textový soubor.</p>
  <div class="chips"><span class="chip">{len(meetings)} zasedání · {total_turns} replik</span><span class="chip">formát .txt</span><span class="chip">neveřejná stránka</span></div>
</header>

<section><div class="panel">
  <p class="pnote">⚠️ <b>Orientační přepis.</b> Vznikl z automatických titulků a byl redakčně upraven do čitelné podoby — není doslovný ani úřední záznam. Závazné je usnesení a originální zápis na <a href="https://www.streliceubrna.cz" target="_blank" rel="noopener" style="color:var(--accent)">streliceubrna.cz</a>. Zastupitelé jsou uvedeni jménem, občané z pléna anonymizováni. Tato stránka není součástí menu portálu.</p>
  <div class="dlall"><button class="dlbtn big" id="dlAll">⬇ Stáhnout vše (jeden soubor)</button></div>
  <div class="dllist">{rows}</div>
</div></section>'''

CSS = '''<style>
.pnote{font-size:12.5px;color:var(--muted);line-height:1.6;margin:0 0 14px;padding:12px 15px;background:var(--inset);
  border:1px solid var(--line);border-left:3px solid var(--accent);border-radius:12px}
.pnote b{color:var(--text)}
.dlall{margin:0 0 16px}
.dllist{display:flex;flex-direction:column}
.dlrow{display:flex;align-items:center;gap:14px;flex-wrap:wrap;padding:12px 4px;border-bottom:1px solid var(--line)}
.dllist .dlrow:last-child{border-bottom:0}
.dlmeta{display:flex;align-items:baseline;gap:12px;flex-wrap:wrap;flex:1;min-width:200px}
.dlnum{font-weight:700;color:var(--accent);font-size:14.5px;min-width:52px}
.dldate{font-size:13.5px;color:var(--text);font-variant-numeric:tabular-nums}
.dlsub{font-size:12px;color:var(--faint)}
.dlact{display:flex;align-items:center;gap:8px;margin-left:auto}
.dlbtn{border:1px solid var(--line);background:var(--accent-soft);color:var(--accent);font:inherit;font-size:13px;
  font-weight:600;padding:7px 14px;border-radius:10px;cursor:pointer;white-space:nowrap;transition:.16s}
.dlbtn:hover{border-color:var(--accent)}
.dlbtn.big{font-size:14px;padding:11px 20px}
.dlyt{font-size:12px;color:#e23b2e;text-decoration:none;font-weight:600;padding:6px 10px;border:1px solid var(--line);
  border-radius:10px;white-space:nowrap}
.dlyt:hover{border-color:#e23b2e}
@media(max-width:560px){.dlact{margin-left:0;width:100%}.dlbtn{flex:1}}
</style>'''

data_json = json.dumps(TEXTS, ensure_ascii=False)
scripts = '<script>const TEXTS=' + data_json + ''';
const TODAY=''' + json.dumps(today) + ''';
function dl(name, text){
  const blob=new Blob([text],{type:'text/plain;charset=utf-8'});
  const url=URL.createObjectURL(blob);
  const a=document.createElement('a'); a.href=url; a.download=name;
  document.body.appendChild(a); a.click(); a.remove();
  setTimeout(()=>URL.revokeObjectURL(url), 1500);
}
document.querySelectorAll('.dlbtn[data-c]').forEach(b=>b.onclick=()=>{
  const c=b.dataset.c; dl('Prepis_ZO_'+c+'_Strelice.txt', TEXTS[c]);
});
document.getElementById('dlAll').onclick=()=>{
  const keys=Object.keys(TEXTS).map(Number).sort((a,b)=>a-b);
  const all=keys.map(k=>TEXTS[k]).join('\\n\\n\\n'+'='.repeat(60)+'\\n\\n\\n');
  const head='PŘEPISY JEDNÁNÍ ZASTUPITELSTVA OBCE STŘELICE\\nStaženo z jakzijistrelice.cz · '+TODAY+'\\nOrientační přepisy z videozáznamů, redakčně upravené. Nejsou úředním záznamem.\\n\\n\\n';
  dl('Prepisy_ZO_Strelice_vse.txt', head+all);
};
bindTheme();
</script>'''

html = pc.page("", "Přepisy zastupitelstva ke stažení — Jak žijí Střelice", body,
               head_scripts=CSS + '<meta name="robots" content="noindex,nofollow">',
               body_scripts=scripts)
open("prepisy-zo.html", "w", encoding="utf-8").write(html)
print(f"HOTOVO: prepisy-zo.html — {len(meetings)} zasedání, {total_turns} replik, {len(html)//1024} kB")
