<?php
declare(strict_types=1);

// Testy MCP serveru bez webového serveru: php mcp-tests/run.php
// Potřebují lokální data (python build_mcp.py v obou repech) a jaksemame/mcp/config.local.php.

define('MCP_ROOT', __DIR__ . '/../jaksemame/mcp');
define('MCP_LOG_DIR', sys_get_temp_dir() . '/mcp-tests-log');
require MCP_ROOT . '/config.local.php';
foreach (['Text', 'Data', 'Log', 'Tools', 'Prompts', 'Mcp'] as $f) {
    require_once MCP_ROOT . "/lib/$f.php";
}

$fail = 0;
$n = 0;
function ok(bool $cond, string $what): void
{
    global $fail, $n;
    $n++;
    if (!$cond) {
        $fail++;
        echo "CHYBA: $what\n";
    }
}
function call(string $tool, array $args): array
{
    $r = Mcp::handle(['jsonrpc' => '2.0', 'id' => 1, 'method' => 'tools/call', 'params' => ['name' => $tool, 'arguments' => $args]], 'test');
    return $r['result'];
}

// hledání: kmeny, diakritika, úryvek
ok(Text::terms('Chodníky v ulici Nádražní') === ['chodni', 'ulic', 'nadraz'], 'kmeny dotazu');
ok(Text::stem('prvek') === 'prvek', 'krátké slovo bez samohlásky na konci zůstane celé');
ok(Text::norm('ČOV „Střelice“') === 'cov strelice', 'normalizace');

// protokol
$init = Mcp::handle(['jsonrpc' => '2.0', 'id' => 1, 'method' => 'initialize', 'params' => ['protocolVersion' => '2025-06-18']], 'test');
ok($init['result']['protocolVersion'] === '2025-06-18', 'initialize vrací verzi klienta');
$init = Mcp::handle(['jsonrpc' => '2.0', 'id' => 1, 'method' => 'initialize', 'params' => ['protocolVersion' => '1999-01-01']], 'test');
ok($init['result']['protocolVersion'] === Mcp::VERSIONS[0], 'neznámá verze → nejnovější');
ok(Mcp::handle(['jsonrpc' => '2.0', 'method' => 'notifications/initialized'], 'test') === null, 'notifikace bez odpovědi');
ok(Mcp::handle(['jsonrpc' => '2.0', 'id' => 2, 'method' => 'nic'], 'test')['error']['code'] === -32601, 'neznámá metoda');
$tools = Mcp::handle(['jsonrpc' => '2.0', 'id' => 3, 'method' => 'tools/list'], 'test')['result']['tools'];
ok(count($tools) === 9, '9 nástrojů');
ok(array_reduce($tools, fn($c, $t) => $c && $t['annotations']['readOnlyHint'] === true, true), 'všechny nástroje jen čtou');

// obce a registr
$o = call('obce', [])['structuredContent']['obce'];
ok(array_column($o, 'obec') === ['strelice', 'ostopovice'], 'obě obce v registru');
ok($o[1]['prepisy_diskuzi'] === 'nejsou', 'Ostopovice bez přepisů');

// hledat
$h = call('hledat', ['dotaz' => 'skatepark', 'obec' => 'strelice'])['structuredContent'];
ok($h['celkem'] > 0 && isset($h['podle_typu']['diskuze'], $h['podle_typu']['usneseni']), 'skatepark v usneseních i diskuzi');
$h = call('hledat', ['dotaz' => 'čistírna', 'mluvci' => 'Bartoňová', 'obec' => 'strelice'])['structuredContent'];
ok($h['celkem'] >= 1 && $h['vysledky'][0]['mluvci'] === 'Eva Bartoňová', 'filtr mluvčího');
ok(str_contains($h['vysledky'][0]['video'], 'youtu.be/') && str_contains($h['vysledky'][0]['video'], '?t='), 'odkaz do videa na čas');
$h = call('hledat', ['dotaz' => 'kanalizace', 'obec' => 'ostopovice'])['structuredContent'];
ok($h['celkem'] > 0 && $h['vysledky'][0]['obec'] === 'ostopovice', 'hledání v Ostopovicích');
ok(call('hledat', ['dotaz' => 'a'])['isError'] ?? false, 'dotaz bez slov → chyba pro model');

// jednani
$j = call('jednani', ['obec' => 'strelice', 'id' => 'ZO-29'])['structuredContent'];
ok(count($j['usneseni']) === 31, 'ZO 29 má 31 usnesení');
// 1. usnesení ZO 29: pro 3, proti 11 — kdo byl proti, vrací jmenovitě
$hl = $j['usneseni'][0]['hlasovani'];
ok($hl['pro'] === 3 && count($hl['proti_jmenovite']) === 11 && in_array('Radim Brener', $hl['proti_jmenovite'], true), 'jmenovité hlasování u ZO 29');
$j = call('jednani', ['obec' => 'ostopovice', 'id' => 'posledni'])['structuredContent'];
ok($j['id'] === 'ZO-2026-2' && str_ends_with($j['portal'], '?zo=2026-2'), 'poslední ZO Ostopovic + odkaz na portál');
ok(call('jednani', ['obec' => 'strelice', 'id' => 'RO-103'])['structuredContent']['organ'] === 'rada', 'rada obce');

// diskuze: váže se k usnesení
$d = call('diskuze', ['obec' => 'strelice', 'jednani' => 'ZO-12', 'bod' => 11])['structuredContent'];
ok(str_contains($d['nazev_bodu'], 'memorandum') && count($d['repliky']) > 1, 'diskuze k usnesení o memorandu ČOV');
ok(isset(call('diskuze', ['obec' => 'ostopovice', 'jednani' => 'posledni'])['structuredContent']['info']), 'Ostopovice: diskuze odkáže jinam');

// peníze
$r = call('rozpocet', ['obec' => 'strelice', 'rok' => 2025, 'cleneni' => 'celkem'])['structuredContent'];
ok(abs($r['celkem']['2025']['skutecnost'] - 92874207) < 10, 'výdaje Střelic 2025 sedí s investice.html');
$r = call('rozpocet', ['obec' => 'ostopovice', 'rok' => 2025, 'cleneni' => 'celkem'])['structuredContent'];
ok($r['celkem']['2025']['skutecnost'] === 140052799, 'výdaje Ostopovic 2025');
ok(call('rozpocet', ['obec' => 'ostopovice', 'cleneni' => 'paragraf'])['isError'] ?? false, 'Ostopovice nemají paragrafy');
$z = call('zakazky', ['obec' => 'strelice'])['structuredContent'];
ok($z['zebricek'][0]['dodavatel'] === 'MATYÁŠ s.r.o.', 'největší dodavatel Střelic');
// výběrová řízení z profilu zadavatele
$v = call('vyberova_rizeni', ['obec' => 'strelice'])['structuredContent'];
ok($v['prehled']['rizeni'] >= 76 && isset($v['rizeni'][0]['nabidky']), 'řízení: přehled + nejnovější s nabídkami');
$v = call('vyberova_rizeni', ['obec' => 'strelice', 'id' => 'P26V00000007'])['structuredContent']['rizeni'] ?? [];
$vit = array_values(array_filter($v['nabidky'] ?? [], fn($n) => $n['vybrana'] ?? false));
ok(count($v['nabidky'] ?? []) >= 2 && count($vit) === 1, 'detail řízení: nabídky a právě jedna vybraná');
$v = call('vyberova_rizeni', ['obec' => 'strelice', 'firma' => 'imos'])['structuredContent'];
ok($v['nabidek'] >= 1 && $v['vybrana'] >= 1, 'účast firmy v řízeních');
$v = call('vyberova_rizeni', ['obec' => 'ostopovice', 'id' => 'P24V00006421'])['structuredContent']['rizeni'] ?? [];
ok(($v['vybrana_firma'] ?? '') === 'PORR a.s.' && count($v['nabidky']) === 3, 'Ostopovice: Lipová 2024, 3 nabídky, vyhrál PORR');
ok(call('vyberova_rizeni', ['obec' => 'strelice', 'id' => 'X'])['isError'] ?? false, 'neznámé řízení → chyba pro model');
$i = call('investice',['obec' => 'strelice', 'hledat' => 'MŠ', 'min_castka' => 20000000])['structuredContent'];
ok($i['akce']['celkem'] >= 1, 'investice: novostavba MŠ');
$t = call('dotace', ['obec' => 'strelice', 'prijemce' => 'sokol'])['structuredContent'];
ok($t['celkem'] >= 5, 'dotace Sokolu po letech');

echo $fail ? "\n$fail z $n testů selhalo\n" : "Všech $n testů prošlo.\n";
exit($fail ? 1 : 0);
