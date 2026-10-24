<?php
declare(strict_types=1);

// Rozeslání upozornění na nová jednání a novinky portálu. Volá ho GitHub Actions po nasazení:
//   POST /push/send.php  s hlavičkou Authorization: Bearer <PUSH_TOKEN>
// Ruční workflow „Zkouška upozornění“ volá ?mode=test (zkušební upozornění všem)
// a ?mode=log (počet zařízení a posledních 40 záznamů deníku doručování).
require_once __DIR__ . '/lib/Send.php';

header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store');
header('X-Robots-Tag: noindex');

// config.local.php vytváří workflow z GitHub secretu; v repozitáři není.
$config = is_file(__DIR__ . '/config.local.php') ? require __DIR__ . '/config.local.php' : [];
$token = is_array($config) && is_string($config['token'] ?? null) ? $config['token'] : '';
if ($token === '') {
    http_response_code(503);
    echo json_encode(['error' => 'Rozesílání není nastavené.']);
    exit;
}

$header = (string) ($_SERVER['HTTP_AUTHORIZATION'] ?? $_SERVER['REDIRECT_HTTP_AUTHORIZATION'] ?? '');
if (($_SERVER['REQUEST_METHOD'] ?? '') !== 'POST' || !push_authorized($header, $token)) {
    http_response_code(403);
    echo json_encode(['error' => 'Přístup odepřen.']);
    exit;
}

$sender = static fn (PDO $db): callable =>
    static fn (array $sub, string $payload): array => WebPush::send($db, $sub, $payload, PUSH_SUBJECT);
$mode = is_string($_GET['mode'] ?? null) ? $_GET['mode'] : '';

set_time_limit(300);
try {
    $db = Store::open(__DIR__ . '/data');
    if ($mode === 'test') {
        $result = push_test($db, $sender($db), time());
    } elseif ($mode === 'log') {
        $count = (int) $db->query('SELECT COUNT(*) FROM push_subscriptions')->fetchColumn();
        $result = ['zarizeni' => $count, 'sqlite' => $db->query('SELECT sqlite_version()')->fetchColumn(), 'denik' => push_log_read($db, 40)];
    } else {
        $feed = json_decode((string) @file_get_contents(__DIR__ . '/feed.json'), true);
        if (!is_array($feed)) {
            http_response_code(500);
            echo json_encode(['error' => 'Chybí push/feed.json.']);
            exit;
        }
        $result = push_send($db, $feed, $sender($db), time());
    }
    echo json_encode($result, JSON_UNESCAPED_UNICODE | JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES);
} catch (Throwable $e) {
    error_log('push send: ' . $e->getMessage());
    http_response_code(500);
    echo json_encode(['error' => 'Rozeslání selhalo.']);
}
