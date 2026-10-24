<?php
declare(strict_types=1);

// Přihlášení k upozornění: GET ?a=key|stats, POST ?a=subscribe|unsubscribe|seen|latest.
require_once __DIR__ . '/lib/Api.php';

header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store');
header('X-Robots-Tag: noindex');

$action = is_string($_GET['a'] ?? null) ? $_GET['a'] : '';
$method = $_SERVER['REQUEST_METHOD'] ?? 'GET';
$in = [];

if (!in_array($action, ['key', 'stats'], true)) {  // čtení jde přes GET, změny jen POST
    $type = strtolower((string) ($_SERVER['CONTENT_TYPE'] ?? ''));
    $raw = (string) file_get_contents('php://input', false, null, 0, 4097);
    if ($method !== 'POST' || !str_starts_with($type, 'application/json') || strlen($raw) > 4096) {
        http_response_code(400);
        echo json_encode(['error' => 'Špatný požadavek.']);
        exit;
    }
    $decoded = json_decode($raw, true);
    $in = is_array($decoded) ? $decoded : [];
}

// Web jede přes CDN WEDOSu, takže REMOTE_ADDR je adresa CDN. Skutečného návštěvníka
// připisuje CDN na konec X-Forwarded-For; co je před ním, mohl podvrhnout klient.
// I tak platí strop nových zařízení za hodinu a celkem.
$hops = array_values(array_filter(array_map('trim', explode(',', (string) ($_SERVER['HTTP_X_FORWARDED_FOR'] ?? '')))));
$forwarded = $hops === [] ? '' : $hops[count($hops) - 1];
$ip = $forwarded !== '' ? $forwarded : (string) ($_SERVER['REMOTE_ADDR'] ?? '');

try {
    $db = Store::open(__DIR__ . '/data');
    if ($action === 'latest') {
        // tlačítko „Poslat mi zkušební upozornění“: jen tomuto zařízení
        require_once __DIR__ . '/lib/Send.php';
        $feed = json_decode((string) @file_get_contents(__DIR__ . '/feed.json'), true);
        $result = push_send_latest(
            $db,
            $in,
            is_array($feed) ? $feed : [],
            static fn (array $sub, string $payload): array => WebPush::send($db, $sub, $payload, PUSH_SUBJECT),
            time()
        );
    } else {
        $result = push_api($db, $action, $in, $ip, time());
    }
} catch (Throwable $e) {
    error_log('push api: ' . $e->getMessage());
    $result = ['status' => 500, 'body' => ['error' => 'Na serveru se něco pokazilo.']];
}

http_response_code($result['status']);
if ($result['status'] !== 204) {
    echo json_encode($result['body'], JSON_UNESCAPED_UNICODE);
}
