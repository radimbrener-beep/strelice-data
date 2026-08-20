# Specifikace: čištění přepisů jednání zastupitelstva (ZO)

Vytváříš REDAKČNĚ VYČIŠTĚNÝ přepis diskuze z jednání zastupitelstva obce Střelice
z automatických YouTube titulků, rozsekaný po bodech, se jmény mluvčích.

## Vstup a výstup
- VSTUP: `data/prepisy/zo{N}_raw.json` — pole `body`, každý bod má: `index`, `start` (s),
  `usneseni` (OFICIÁLNÍ ověřené znění), `hlasovani` ([pro,proti,zdržel] nebo null),
  `raw` (surový auto-přepis diskuze — obsahuje chyby přepisu).
- VZOR kvality a schéma: `prepisy/_styl_vzor.json` (hotové kvalitní zasedání).
- VÝSTUP: `prepisy/{N}.json`, striktní JSON UTF-8, schéma:
```
{"cislo_zasedani": N, "vid": "…", "body": [
  {"index": 3, "start": 601, "turns": [
    {"who": "Starosta", "role": "s", "text": "…"},
    {"who": "Eva Bartoňová", "role": "z", "text": "…"}
  ]}
]}
```
- `role`: "s" = předsedající/starosta/místostarosta, "z" = zastupitel(ka),
  "o" = občan/veřejnost, "k" = návrhová komise.
- `vid` vezmi ze vstupu. Pořadí bodů dle `index`, `start` zkopíruj 1:1.

## Pravidla čištění (KVALITA JE KLÍČOVÁ — žádné nesmysly)
1. **Fakta ber z `usneseni` a `hlasovani`, NE z `raw`.** Auto-přepis komolí čísla, IČO
   a názvy firem (např. „Jubokar" = JUBOCAR spol. s r.o.; „Aquasis/i2534447" = AQUASYS,
   IČ 25344447). Když se v diskuzi zmiňuje částka/firma/IČO/parcela, použij správný tvar
   z `usneseni`. NIKDY nevymýšlej fakta, jména ani čísla.
2. **Diskuzi z `raw` přepiš do čitelné spisovné češtiny:** oprav přeřeky a chyby přepisu,
   odstraň vycpávky („eh", „prostě", opakování, falešné začátky), ale zůstaň VĚRNÝ obsahu —
   nic nepřidávej, neinterpretuj, nehodnoť.
3. **Když je úsek `raw` tak zkomolený, že mu nerozumíš, radši ho stručně parafrázuj nebo
   vynech — NIKDY nefabuluj.** Nejisté datum/název/číslo raději vynech než hádej.
4. Slučuj po sobě jdoucí repliky téhož mluvčího. Buď stručný a čitelný. U velmi dlouhých
   bodů (diskuze „různé" na konci) obsah věrně zhušťuj do parafrází.
5. Procedurální bod bez reálné diskuze (jen „doporučuji vzít na vědomí, kdo je pro")
   shrň do 1–2 replik (uvedení + výsledek), ať není prázdný.

## Kdo mluví (přiřazení mluvčích)
- Předsedající uděluje slovo jménem („Otevírám diskuzi. Eva Bartoňová.") — podle toho
  přiřaď. Předsedající = `who:"Starosta"`; jeho zástupce, kterému předává slovo
  (rozpočet, investice) = `who:"Místostarosta"`; čtení návrhu usnesení = `who:"Návrhová komise"`
  (pokud je jmenován zastupitel, uveď jméno s rolí "k").
- **ZASTUPITELÉ — uváděj plným jménem, role "z":**
  Jiří Vašulín, Petra Zoubková, Vojtěch Liška, Jan Dlapka, Helena Fialová,
  Robert Ströbinger, Alois Liška, Eva Bartoňová, Martin Klíma, Radim Brener,
  Jan Pernikář, Petr Rozsíval, Josef Tichý, Zuzana Hloušková, David Dvořák, **Smištík**.
  (Smištík je zastupitel/náhradník — křestní jméno neznámé, uváděj „pan Smištík".
  Obecné pravidlo: KDOKOLI, jehož příjmení je v tomto seznamu, je zastupitel a jmenuje se.)
- **Občané z pléna (NEJSOU v seznamu výše): ANONYMIZUJ** jako `who:"Občan"` / `"Občanka"`,
  role "o". Odstraň jejich příjmení i z řeči ostatních (např. „Pane Adamíku" → „Pane…"
  nebo oslovení vynech). Vynech i vedlejší křestní jména z pléna.
- Když mluvčí není osloven jménem a nejde určit, NEHÁDEJ — buď dotaz shrň neutrálně do
  odpovědi předsedajícího, nebo použij `who:"Občan"` jen je-li zřejmé, že jde o veřejnost.

Na konci vrať ve své odpovědi: číslo zasedání, počet bodů, počet replik a upozornění na
jakékoli nejistoty (zkomolené úseky, nejisté přiřazení mluvčího). Nespouštěj git.
