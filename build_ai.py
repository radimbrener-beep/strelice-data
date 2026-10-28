#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Rubrika Ptejte se AI (ai.html) — srozumitelně pro laiky: co je MCP server
jaksemame.cz/mcp/, k čemu je dobrý, ukázka rozhovoru, příklady otázek a návod na připojení.
Technický popis serveru: jaksemame/mcp/README.md. Ostopovice mají kopii s vlastními příklady
(maskota vkládá inline, protože jejich repo složku maskot/ nemá)."""
import sys
import portal_common as pc
sys.stdout.reconfigure(encoding="utf-8")

MCP_URL = "https://jaksemame.cz/mcp/"
OBEC = "Střelice"
MASKOT = open("maskot/01-uvitani.svg", encoding="utf-8").read()

# ikony (stroke = currentColor, barvu dává CSS)
_I = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{}</svg>'
ICON = {
    "clovek": _I.format('<circle cx="12" cy="8" r="4"/><path d="M4 21c1.5-4 4.5-6 8-6s6.5 2 8 6"/>'),
    "chat": _I.format('<path d="M4 5h16v11H9l-5 4z"/><path d="M8 9h8M8 12h5"/>'),
    "zasuvka": _I.format('<path d="M9 3v5M15 3v5"/><path d="M6 8h12v3a6 6 0 0 1-12 0z"/><path d="M12 17v4"/>'),
    "data": _I.format('<ellipse cx="12" cy="5" rx="7" ry="3"/><path d="M5 5v14c0 1.7 3.1 3 7 3s7-1.3 7-3V5"/><path d="M5 12c0 1.7 3.1 3 7 3s7-1.3 7-3"/>'),
    "hlas": _I.format('<path d="M4 20h16"/><path d="M6 20V10h4v10M14 20V4h4v16"/>'),
    "penize": _I.format('<circle cx="12" cy="12" r="9"/><path d="M15 9.5c-.5-1-1.6-1.5-3-1.5-1.7 0-3 .8-3 2s1.3 1.7 3 2 3 .9 3 2.1-1.3 1.9-3 1.9c-1.4 0-2.6-.6-3-1.6M12 6.5v11"/>'),
    "zakazka": _I.format('<path d="M4 20l7-7"/><path d="M13 4l7 7-3 3-7-7z"/><path d="M10 7l7 7"/>'),
    "odkaz": _I.format('<path d="M10 14l10-10M14 4h6v6"/><path d="M20 14v6H4V4h6"/>'),
}

# příklady otázek: co si o obci můžete nechat dohledat (odpovídají datům, která server má)
PRIKLADY = [
    ("hlas", "Zastupitelstvo a rada", [
        "Co se řešilo na posledním zastupitelstvu ve Střelicích?",
        "Jak se hlasovalo o novém územním plánu a kdo byl proti?",
        "O čem se na zastupitelstvu diskutovalo v souvislosti s kanalizací?",
        "Co rada obce schválila za poslední měsíc?",
    ]),
    ("penize", "Peníze obce", [
        "Kolik Střelice loni vybraly na daních a za co nejvíc utratily?",
        "Jaké velké investice obec za poslední roky dělala a kolik stály?",
        "Kolik dostávají od obce spolky a který nejvíc?",
    ]),
    ("zakazka", "Zakázky", [
        "Kdo se přihlásil do soutěže na skatepark a za kolik?",
        "Které firmy od obce dostávají nejvíc zakázek?",
        "U kterých zakázek přišla jen jedna nabídka?",
    ]),
]
# ukázka rozhovoru — odpověď odpovídá skutečným datům (profil zadavatele, srpen 2026)
UKAZKA_Q = "Kdo se přihlásil do soutěže na skatepark a za kolik?"
UKAZKA_A = ('Zakázku <b>„V 00923 – Skatepark“</b> obec vypsala 28. 8. 2026 s předpokládanou hodnotou '
            '1 950 000 Kč. Přišla do ní <b>jediná nabídka</b> — od firmy Zdeněk Kotyza za <b>1 948 000 Kč</b> '
            'bez DPH — a ta byla vybrána. Zastupitelstvo smlouvu schválilo 17. 9. 2026.')
UKAZKA_ZDROJE = [("Profil zadavatele", "zakazky.html#vypsane"), ("Zastupitelstvo č. 29", "zastupitelstvo.html?zo=29")]

FLOW = [("clovek", "Vy", "ptáte se běžnou větou"), ("chat", "AI asistent", "Claude, ChatGPT…"),
        ("zasuvka", "MCP server", "jaksemame.cz/mcp/"), ("data", "Data portálu", "zápisy, rozpočet, zakázky")]
SIPKA = '<svg class="ai-arrow" viewBox="0 0 40 16" aria-hidden="true"><path d="M2 8h32M28 3l6 5-6 5" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>'
flow = SIPKA.join(f'<div class="ai-node"><span class="ai-ico c{i}">{ICON[k]}</span><b>{t}</b><span>{s}</span></div>'
                  for i, (k, t, s) in enumerate(FLOW))

priklady = "".join(
    f'<div class="panel ai-q"><h3><span class="ai-ico sm">{ICON[ik]}</span>{nadpis}</h3><ul>'
    + "".join(f"<li>„{q}“</li>" for q in otazky) + "</ul></div>"
    for ik, nadpis, otazky in PRIKLADY)

zdroje = "".join(f'<a class="ai-src" href="{u}">{ICON["odkaz"]}{t}</a>' for t, u in UKAZKA_ZDROJE)

body = f'''<header class="hero ai-hero">
  <div class="ai-hero-tx">
    <h1>Ptejte se AI na {OBEC}</h1>
    <p>Místo proklikávání tabulek se můžete zeptat svého AI asistenta (Claude, ChatGPT a další) normální větou — třeba „co se řešilo na posledním zastupitelstvu?“. Asistent si odpověď dohledá v datech tohoto portálu a připojí odkaz, kde si ji ověříte.</p>
    <div class="chips"><span class="chip">zdarma</span><span class="chip">bez registrace na portálu</span><span class="chip">data jen ke čtení</span></div>
  </div>
  <div class="ai-hero-fig" aria-hidden="true">{MASKOT}</div>
</header>

<section>
  <div class="sec-h"><h2>Jak to vypadá</h2><span class="hint">ukázka rozhovoru</span></div>
  <div class="panel ai-chat">
    <div class="ai-msg me"><span class="ai-av">{ICON["clovek"]}</span><div class="ai-bub">{UKAZKA_Q}</div></div>
    <div class="ai-msg bot"><span class="ai-av">{ICON["chat"]}</span><div class="ai-bub">
      <div class="ai-tool">{ICON["zasuvka"]} Hledám v datech jaksemame.cz…</div>
      <p>{UKAZKA_A}</p><div class="ai-srcs">{zdroje}</div></div></div>
  </div>
  <p class="note">Ilustrační ukázka — skutečná odpověď se liší podle asistenta, ale údaje bere ze stejných dat.</p>
</section>

<section>
  <div class="sec-h"><h2>Co to je</h2></div>
  <div class="panel">
    <div class="ai-flow">{flow}</div>
    <p>AI asistenti sami o obci skoro nic nevědí — znají jen to, co se kdysi naučili z internetu, a zápisy ze zastupitelstva nebo rozpočet obce mezi tím nejsou. <b>MCP server</b> je něco jako zásuvka, přes kterou se asistent k datům portálu připojí. Když se pak zeptáte, asistent si sám vyhledá, co potřebuje — zápisy, hlasování, rozpočet, zakázky — a odpoví z toho.</p>
    <p class="note">MCP (Model Context Protocol) je otevřený standard, který používá většina AI asistentů. Server jen čte stejná data, jaká vidíte na tomto portálu, a aktualizuje se spolu s ním.</p>
  </div>
</section>

<section>
  <div class="sec-h"><h2>Na co se můžete zeptat</h2><span class="hint">příklady, ptát se můžete i jinak</span></div>
  <div class="ai-grid">{priklady}</div>
  <p class="note">Asistent zvládne i navazující otázky („a jak to bylo předloni?“), porovnání se sousedními Ostopovicemi nebo shrnutí delšího období. Neví ale nic, co v datech portálu není — třeba co se říkalo mimo zasedání.</p>
</section>

<section>
  <div class="sec-h"><h2>Jak ho připojit</h2><span class="hint">jednou, zabere to asi minutu</span></div>
  <div class="panel">
    <p>Adresa serveru <span class="note" style="margin:0">(i s lomítkem na konci)</span>:</p>
    <div class="ai-url"><code id="mcpUrl">{MCP_URL}</code><button type="button" class="morebtn" id="copyUrl">Zkopírovat</button></div>
    <ol class="ai-steps">
      <li><span class="ai-n">1</span><div><b>Claude</b> (claude.ai i aplikace): Nastavení → <i>Konektory</i> → <i>Přidat vlastní konektor</i>. Jako název napište třeba „Jak se máme“, jako adresu vložte adresu výše a potvrďte. V konverzaci pak konektor zapnete v nabídce nástrojů (ikona pod polem pro psaní).</div></li>
      <li><span class="ai-n">2</span><div><b>ChatGPT</b>: v nastavení <i>Aplikace a konektory</i> přidejte vlastní konektor (MCP server) s adresou výše. Tahle možnost zatím není ve všech tarifech.</div></li>
      <li><span class="ai-n">3</span><div><b>Jiný asistent</b>: přidejte „vzdálený MCP server“ typu <i>Streamable HTTP</i> s adresou výše, bez přihlašování.</div></li>
    </ol>
    <p class="note">Názvy položek v nastavení se mohou podle verze aplikace trochu lišit a dostupnost vlastních konektorů závisí na tarifu daného asistenta. Pak se už jen zeptejte — například „Co nového ve Střelicích řešilo zastupitelstvo?“.</p>
  </div>
</section>

<section>
  <div class="sec-h"><h2>Na co dát pozor</h2></div>
  <div class="panel">
    <table class="mtab"><tbody>
      <tr><td><b>Odpověď píše asistent</b></td><td>ne tento portál — může něco zjednodušit nebo splést. U důležitých věcí si otevřete odkaz, který k odpovědi připojí (zápis, video, stránku portálu); rozhoduje vždy originální dokument.</td></tr>
      <tr><td><b>Přepisy diskuzí</b></td><td>jsou upravené a zkrácené, ne doslovné — necitujte je jako přesná slova.</td></tr>
      <tr><td><b>Neoficiální zdroj</b></td><td>portál i server provozuje občan, ne obec; data pocházejí z veřejných zápisů a výkazů.</td></tr>
      <tr><td><b>Soukromí</b></td><td>server nevidí vaši otázku ani IP adresu — jen to, co si u něj asistent vyhledá (např. hledané slovo). Podrobnosti v <a href="metodika.html" style="color:var(--accent)">metodice</a>.</td></tr>
    </tbody></table>
    <p class="note">Technický popis a seznam nástrojů je přímo na <a href="{MCP_URL}" target="_blank" rel="noopener" style="color:var(--accent)">{MCP_URL}</a>. Nefunguje vám připojení? Napište: {pc.MAIL_LINK}</p>
  </div>
</section>'''

CSS = '''<style>
.ai-hero{display:flex;gap:24px;align-items:center}
.ai-hero-tx{flex:1;min-width:0}
.ai-hero-fig{flex:none;width:170px;height:170px;border-radius:28px;background:var(--msk-bg,#e3eeec);display:grid;place-items:center}
.ai-hero-fig svg{width:88%;height:88%}
.ai-ico{display:inline-grid;place-items:center;width:46px;height:46px;border-radius:14px;background:color-mix(in srgb,var(--accent) 14%,transparent);color:var(--accent)}
.ai-ico svg{width:24px;height:24px}
.ai-ico.c1{background:color-mix(in srgb,var(--c0) 16%,transparent);color:var(--c0)}
.ai-ico.c2{background:color-mix(in srgb,var(--amber) 18%,transparent);color:var(--amber)}
.ai-ico.c3{background:color-mix(in srgb,var(--c3) 16%,transparent);color:var(--c3)}
.ai-ico.sm{width:30px;height:30px;border-radius:9px;margin-right:9px;vertical-align:middle}
.ai-ico.sm svg{width:17px;height:17px}
.ai-flow{display:flex;align-items:flex-start;justify-content:space-between;gap:6px;margin:4px 0 16px}
.ai-node{flex:1 1 0;display:flex;flex-direction:column;align-items:center;text-align:center;gap:5px;min-width:0}
.ai-node b{font-family:var(--font-d);font-size:14.5px}
.ai-node span:not(.ai-ico){font-size:12px;color:var(--muted)}
.ai-arrow{flex:none;width:34px;margin-top:15px;color:var(--faint)}
.ai-chat{display:flex;flex-direction:column;gap:14px}
.ai-msg{display:flex;gap:10px;align-items:flex-start;max-width:640px}
.ai-msg.me{flex-direction:row-reverse;align-self:flex-end}
.ai-av{flex:none;display:grid;place-items:center;width:34px;height:34px;border-radius:50%;background:var(--inset);color:var(--muted);border:1px solid var(--line)}
.ai-av svg{width:18px;height:18px}
.ai-msg.bot .ai-av{background:color-mix(in srgb,var(--accent) 14%,transparent);color:var(--accent);border-color:transparent}
.ai-bub{padding:11px 14px;border-radius:16px;line-height:1.55;font-size:14.5px}
.ai-msg.me .ai-bub{background:var(--accent);color:#fff;border-top-right-radius:4px}
.ai-msg.bot .ai-bub{background:var(--inset);border:1px solid var(--line);border-top-left-radius:4px}
.ai-bub p{margin:6px 0 8px}
.ai-tool{display:flex;gap:6px;align-items:center;font-size:12px;color:var(--muted)}
.ai-tool svg{width:14px;height:14px}
.ai-srcs{display:flex;flex-wrap:wrap;gap:6px}
.ai-src{display:inline-flex;gap:5px;align-items:center;font-size:12px;padding:3px 10px;border-radius:999px;border:1px solid var(--line);background:var(--surface);color:var(--accent);text-decoration:none}
.ai-src svg{width:12px;height:12px}
.ai-src:hover{border-color:var(--accent)}
.ai-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:14px}
.ai-q h3{margin:0 0 8px;font-size:15px;display:flex;align-items:center}
.ai-q ul{margin:0;padding-left:18px;line-height:1.6;color:var(--muted)}
.ai-url{display:flex;flex-wrap:wrap;gap:10px;align-items:center;margin:4px 0 14px}
.ai-url code{font-size:15px;padding:8px 12px;border-radius:10px;background:var(--inset);border:1px solid var(--line);word-break:break-all}
.ai-url .morebtn{margin:0}
.ai-steps{list-style:none;padding:0;margin:0;display:flex;flex-direction:column;gap:10px;line-height:1.6}
.ai-steps li{display:flex;gap:12px;align-items:flex-start}
.ai-n{flex:none;display:grid;place-items:center;width:28px;height:28px;border-radius:50%;background:var(--accent);color:#fff;font-weight:700;font-size:13px}
.panel p{line-height:1.6}
.mtab th,.mtab td{text-align:left;white-space:normal;vertical-align:top}
.mtab td:first-child{width:26%}
@media(max-width:640px){
  .ai-hero{flex-direction:column-reverse;align-items:flex-start}
  .ai-hero-fig{width:110px;height:110px;border-radius:20px}
  .ai-flow{flex-wrap:wrap;justify-content:center;row-gap:14px}
  .ai-node{flex:0 0 40%}
  .ai-arrow{display:none}
  .mtab td:first-child{width:auto}
}
</style>'''

SCRIPT = '''<script>
document.getElementById('copyUrl').onclick=function(){var b=this,t=document.getElementById('mcpUrl').textContent;
  (navigator.clipboard?navigator.clipboard.writeText(t):Promise.reject()).then(function(){b.textContent='Zkopírováno ✓';},
  function(){var r=document.createRange();r.selectNodeContents(document.getElementById('mcpUrl'));var s=getSelection();s.removeAllRanges();s.addRange(r);});
  setTimeout(function(){b.textContent='Zkopírovat';},2500);};
</script>'''

open("ai.html", "w", encoding="utf-8").write(
    pc.page("Ptejte se AI", "Ptejte se AI — " + pc.BRAND, body, head_scripts=CSS, body_scripts=SCRIPT))
print("HOTOVO: ai.html")
