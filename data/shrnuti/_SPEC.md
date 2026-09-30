# Shrnutí zasedání — zadání pro jazykový model

Cíl: u každého zasedání Zastupitelstva (ZO) a jednání Rady obce (RO) Střelice krátké
shrnutí **„co se rozhodlo"** pro běžného občana, zobrazené nad seznamem usnesení.

## Vstup
- ZO: `dataset_ZO.json` (seznam zasedání; `cislo_zasedani`, `datum_text`, `body[].text`, `body[].kategorie`, `body[].castka`, `body[].hlasovani` [pro, proti, zdržel])
- RO: `dataset_RO.json` (stejná struktura, bez hlasování)

## Výstup
JSON soubor `{ "<číslo zasedání>": "<shrnutí>", ... }` (UTF-8, klíče jako řetězce).

## Pravidla
1. **2–4 věty, cca 35–70 slov.** Česky, srozumitelně, bez úředního žargonu
   („schválilo smlouvu o dílo" → „zadalo stavbu…").
2. **Jen fakta z textu usnesení.** Nic nedomýšlet, nehodnotit, žádná přídavná jména typu
   „důležitý", „kontroverzní", „úspěšný". Neutrální tón — web je nestranný.
3. **Priorita:** peníze a stavby (zakázky, investice, nákupy pozemků/nemovitostí, rozpočet,
   úvěry, dotace), pak vyhlášky/pravidla, pak ostatní. Vynechat procedurální body
   (program, ověřovatelé, návrhová komise, „bere na vědomí zprávu o činnosti rady",
   běžná rozpočtová opatření — ta jen souhrnně, pokud nic jiného není).
4. **Částky** zaokrouhlit a psát lidsky: „za 1,4 mil. Kč", „přes 27 mil. Kč",
   „za 220 tis. Kč". Uvádět, zda bez DPH, jen pokud to text říká a je to podstatné.
5. **Firmy** jmenovat lze (právnické osoby). **Fyzické osoby NEJMENOVAT** (kupující,
   prodávající, nájemci, žadatelé → „soukromý vlastník", „žadatel", „manželé").
   Funkce obce (starosta, rada) ano, jména zastupitelů ne.
6. **Hlasování (jen ZO):** pokud bylo u věcného bodu nejednomyslné (někdo proti / zdržel),
   lze stručně zmínit „(schváleno 12:2)" — jen u podstatných bodů, bez jmen.
7. Když je zasedání čistě formální / krátké, stačí jedna věta.
8. Nepoužívat odrážky ani markdown, jen souvislý text. Nezačínat „Na zasedání…" pokaždé —
   rovnou k věci („Zastupitelstvo schválilo rozpočet na rok 2024 … ").
