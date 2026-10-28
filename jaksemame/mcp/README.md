# MCP server jaksemame.cz/mcp/

Server pro AI asistenty (Claude, ChatGPT…) nad daty všech obcí na jaksemame.cz. Jen čte.
Protokol MCP přes Streamable HTTP **bez stavu**: POST s JSON-RPC → JSON odpověď, bez sezení a bez SSE.
PHP 8.0+ (Wedos má 8.0, takže nic z 8.1 jako `array_is_list`) a PDO SQLite, stejně jako `push/`.

## Jak to funguje

- `obce.json`: registr obcí. Nová obec = záznam sem + soubor `data/<obec>.sqlite`. Kód serveru se nemění.
- Data vyrábí `build_mcp.py` v repu každé obce (Střelice: `rozpocet/`, Ostopovice: `ostopovice/`).
  Formát popisuje `mcp_export.py` (formát v1, kopie v obou repech). Běží **po** buildu stránek,
  protože čte data vložená do `investice.html` a `zakazky.html`.
- `lib/Tools.php`: 9 nástrojů (`obce`, `hledat`, `jednani`, `diskuze`, `rozpocet`, `investice`,
  `zakazky`, `vyberova_rizeni`, `dotace`). `lib/Prompts.php`: 3 hotové dotazy. `lib/Mcp.php`: protokol a pravidla pro model.
- Hledání (`lib/Text.php`): bez diakritiky, kmeny od začátku slova, LIKE nad sloupcem `norm`.
  FTS5 se nepoužívá, protože ho Wedos nemusí mít a dat je málo (jednotky tisíc řádků, odpověď do 20 ms).
- Diskuze z přepisů se váže k **pořadí usnesení v zápisu** (`index` v `prepisy/N.json`), ne k číslu bodu programu.
- `lib/Log.php`: deník `log/mcp.sqlite`. Ukládá nástroj, parametry, počet výsledků, dobu a klienta.
  IP adresu neukládá; limit 60 volání za minutu počítá z otisku IP s denní solí. Záznamy se mažou po 90 dnech.

## Lokálně

```
python build_mcp.py                          # v rozpocet/ i v ostopovice/
php -S localhost:8790 mcp-tests/router.php   # http://localhost:8790/mcp
php mcp-tests/run.php                        # testy bez serveru
python mcp-tests/call.py hledat '{"dotaz":"skatepark"}'
```

`config.local.php` (není v gitu) přesměruje cesty k datům na buildy obou rep.

## Nasazení

- **Kód serveru** nasazuje `deploy.yml` repa Střelic spolu s rozcestníkem do `/www/domains/jaksemame.cz/mcp/`
  (jen `index.php`, `info.html`, `obce.json`, `.htaccess`, `lib/`; ne `config.local.php` ani `log/`).
- **Data:** každé repo v CI spustí `build_mcp.py` a nahraje svůj `mcp/<obec>.sqlite` do `…/jaksemame.cz/mcp/data/`
  (Střelice s rozcestníkem, Ostopovice vlastním krokem jen se svým souborem, aby sync nesmazal cizí data).
  Automatické kontroly obou rep po změně spouštějí `deploy.yml`, takže data MCP jsou stejně čerstvá jako web.
- **Adresa je `https://jaksemame.cz/mcp/` s lomítkem.** Bez lomítka to na Wedosu nejde (ověřeno 28. 10. 2026):
  složku bez lomítka přesměruje 302 s prázdnou adresou ještě před `.htaccess` a interní přepis (`RewriteRule`)
  vrací 500 — stejně jako dřív u čistých URL portálu. Klienti MCP přesměrování POSTu nenásledují.
- **Nečitelné z webu:** `data/` a `log/` mají `Require all denied`, `mcp/.htaccess` blokuje `lib/`, `*.sqlite`, `*.json`.
- Co server ukládá, popisuje `info.html` a sekce „AI asistenti (MCP server)“ v metodice obou portálů.
