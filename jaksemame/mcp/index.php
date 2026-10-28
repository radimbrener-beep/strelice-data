<?php
declare(strict_types=1);

// MCP server jaksemame.cz/mcp — Streamable HTTP bez stavu: POST s JSON-RPC → JSON odpověď.
// GET z prohlížeče ukáže krátký návod; klient, který chce SSE stream, dostane 405 (stream nenabízíme).

define('MCP_ROOT', __DIR__);
if (is_file(__DIR__ . '/config.local.php')) {
    require __DIR__ . '/config.local.php';
}
require_once __DIR__ . '/lib/Text.php';
require_once __DIR__ . '/lib/Data.php';
require_once __DIR__ . '/lib/Log.php';
require_once __DIR__ . '/lib/Tools.php';
require_once __DIR__ . '/lib/Prompts.php';
require_once __DIR__ . '/lib/Mcp.php';

// veřejná data bez přihlášení → jakýkoli původ (webové klienty MCP volají z prohlížeče)
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: POST, GET, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type, Accept, Mcp-Session-Id, Mcp-Protocol-Version, Last-Event-ID');
header('Access-Control-Max-Age: 86400');
header('Cache-Control: no-store');
header('X-Robots-Tag: noindex');

$method = $_SERVER['REQUEST_METHOD'] ?? 'GET';
if ($method === 'OPTIONS') {
    http_response_code(204);
    exit;
}
if ($method === 'GET' && !str_contains((string) ($_SERVER['HTTP_ACCEPT'] ?? ''), 'text/event-stream')) {
    header('Content-Type: text/html; charset=utf-8');
    readfile(__DIR__ . '/info.html');
    exit;
}
if ($method !== 'POST') {
    header('Allow: POST, OPTIONS');
    http_response_code(405);
    exit;
}

header('Content-Type: application/json; charset=utf-8');
$reply = function (int $status, $body): void {
    http_response_code($status);
    echo json_encode($body, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    exit;
};

// Web jede přes CDN WEDOSu: skutečného klienta připisuje CDN na konec X-Forwarded-For.
$hops = array_values(array_filter(array_map('trim', explode(',', (string) ($_SERVER['HTTP_X_FORWARDED_FOR'] ?? '')))));
$ip = $hops ? $hops[count($hops) - 1] : (string) ($_SERVER['REMOTE_ADDR'] ?? '');
if (Log::overLimit($ip)) {
    header('Retry-After: 60');
    $reply(429, Mcp::error(null, -32000, 'Příliš mnoho dotazů za minutu, zkus to prosím za chvíli.'));
}

$raw = (string) file_get_contents('php://input', false, null, 0, 65537);
if (strlen($raw) > 65536) {
    $reply(413, Mcp::error(null, -32600, 'Požadavek je příliš velký.'));
}
$msg = json_decode($raw, true);
if ($msg === null && trim($raw) !== 'null') {
    $reply(400, Mcp::error(null, -32700, 'Neplatný JSON.'));
}
$client = mb_substr((string) ($_SERVER['HTTP_USER_AGENT'] ?? ''), 0, 80) ?: null;

// dávka (starší verze protokolu); array_is_list() až od PHP 8.1, Wedos má 8.0
if (is_array($msg) && $msg && array_keys($msg) === range(0, count($msg) - 1)) {
    $out = array_values(array_filter(array_map(fn($m) => Mcp::handle($m, $client), array_slice($msg, 0, 20))));
    if (!$out) {
        http_response_code(202);
        exit;
    }
    $reply(200, $out);
}
$out = Mcp::handle($msg, $client);
if ($out === null) {
    http_response_code(202);  // notifikace nebo odpověď klienta
    exit;
}
$reply(200, $out);
