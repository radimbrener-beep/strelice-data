<?php
declare(strict_types=1);

require_once __DIR__ . '/../push/lib/Send.php';

/** Položka feedu (jednání nebo novinka portálu). */
function item(string $topic, string $id, string $date, string $title = 'Nadpis'): array
{
    return ['id' => "$topic-$id", 'topic' => $topic, 'title' => $title, 'body' => "Text $id", 'url' => "/x.html?$id", 'date' => $date];
}

function addDevice(PDO $db, string $endpoint, string $topics = 'rada,zastupitelstvo,portal', int $failures = 0): void
{
    $db->prepare("INSERT INTO push_subscriptions (endpoint, p256dh, auth, created_at, failures, topics) VALUES (?, 'k', 'a', 'z', ?, ?)")
        ->execute([$endpoint, $failures, $topics]);
}

/** Atrapa odesílání: zapíše, co by se poslalo, a vrátí zadaný stav. */
function fakeSender(array &$log, int $status = 201): callable
{
    return function (array $sub, string $payload) use (&$log, $status): array {
        $log[] = ['endpoint' => $sub['endpoint'], 'payload' => json_decode($payload, true)];
        return ['status' => $status, 'ok' => $status < 300, 'gone' => in_array($status, [404, 410], true), 'detail' => ''];
    };
}

$now = strtotime('2026-10-24 10:00:00 UTC');

Test::case('první běh jen zapamatuje jednání a nepošle nic', function () use ($now): void {
    $db = testDb();
    addDevice($db, 'https://fcm.googleapis.com/a');
    $log = [];
    $r = push_send($db, [item('rada', '103', '2026-10-14'), item('zastupitelstvo', '29', '2026-09-17')], fakeSender($log), $now);
    Test::eq(0, $r['sent']);
    Test::eq([], $log);
    Test::true(str_starts_with($r['skipped'], 'první'), 'hlášení prvního běhu');
});

Test::case('nové jednání dostanou jen zařízení, která ten druh chtějí', function () use ($now): void {
    $db = testDb();
    addDevice($db, 'https://fcm.googleapis.com/rada', 'rada');
    addDevice($db, 'https://fcm.googleapis.com/zo', 'zastupitelstvo');
    $log = [];
    $old = [item('rada', '103', '2026-10-14'), item('zastupitelstvo', '29', '2026-09-17')];
    push_send($db, $old, fakeSender($log), $now);
    $r = push_send($db, [item('rada', '104', '2026-10-28', 'Rada obce č. 104'), ...$old], fakeSender($log), $now + 60);
    Test::eq(1, $r['sent']);
    Test::eq(['https://fcm.googleapis.com/rada'], array_column($log, 'endpoint'));
    Test::eq('Rada obce č. 104', $log[0]['payload']['title']);
    Test::eq('rada-104', $log[0]['payload']['tag'], 'štítek začíná druhem, vlastní pro jednání');
    Test::eq('/x.html?104', $log[0]['payload']['url']);
});

Test::case('stejné jednání se neoznámí dvakrát', function () use ($now): void {
    $db = testDb();
    addDevice($db, 'https://fcm.googleapis.com/a');
    $log = [];
    push_send($db, [item('rada', '103', '2026-10-14')], fakeSender($log), $now);
    push_send($db, [item('rada', '104', '2026-10-28'), item('rada', '103', '2026-10-14')], fakeSender($log), $now + 1);
    push_send($db, [item('rada', '104', '2026-10-28'), item('rada', '103', '2026-10-14')], fakeSender($log), $now + 2);
    Test::eq(1, count($log));
});

Test::case('doplněné starší jednání se neoznamuje', function () use ($now): void {
    $db = testDb();
    addDevice($db, 'https://fcm.googleapis.com/a');
    $log = [];
    push_send($db, [item('rada', '103', '2026-10-14')], fakeSender($log), $now);
    $r = push_send($db, [item('rada', '103', '2026-10-14'), item('rada', '50', '2024-05-01')], fakeSender($log), $now + 1);
    Test::eq(0, $r['sent']);
    Test::eq([], $log);
});

Test::case('víc nových jednání stejného druhu = jedno souhrnné upozornění', function () use ($now): void {
    $db = testDb();
    addDevice($db, 'https://fcm.googleapis.com/a');
    $log = [];
    push_send($db, [item('rada', '103', '2026-10-14')], fakeSender($log), $now);
    push_send($db, [item('rada', '105', '2026-11-11', 'RO 105'), item('rada', '104', '2026-10-28', 'RO 104'), item('rada', '103', '2026-10-14')], fakeSender($log), $now + 1);
    Test::eq(1, count($log));
    Test::eq('Rada obce: 2 nová jednání', $log[0]['payload']['title']);
    Test::eq('RO 105 · RO 104', $log[0]['payload']['body']);
    Test::eq('/zapisy.html', $log[0]['payload']['url']);
});

Test::case('první novinka portálu dojde, i když jich při zapnutí nebylo', function () use ($now): void {
    $db = testDb();
    addDevice($db, 'https://fcm.googleapis.com/a', 'portal');
    $log = [];
    push_send($db, [item('rada', '103', '2026-10-14')], fakeSender($log), $now);
    $r = push_send($db, [item('portal', 'volby', '2026-10-24', 'Nová sekce Volby'), item('rada', '103', '2026-10-14')], fakeSender($log), $now + 1);
    Test::eq(1, $r['sent']);
    Test::eq('Nová sekce Volby', $log[0]['payload']['title']);
});

Test::case('neznámý druh ani položka bez data se neposílá', function () use ($now): void {
    $db = testDb();
    addDevice($db, 'https://fcm.googleapis.com/a');
    $log = [];
    push_send($db, [], fakeSender($log), $now);
    $r = push_send($db, [item('svoz', 'x', '2026-10-25'), ['id' => 'rada-9', 'topic' => 'rada', 'title' => 't', 'body' => '', 'url' => '/', 'date' => '']], fakeSender($log), $now + 1);
    Test::eq(0, $r['sent']);
});

Test::case('zaniklé zařízení (410) se smaže, dočasná chyba ne', function () use ($now): void {
    $db = testDb();
    addDevice($db, 'https://fcm.googleapis.com/a');
    $log = [];
    push_send($db, [item('rada', '103', '2026-10-14')], fakeSender($log), $now);
    push_send($db, [item('rada', '104', '2026-10-28'), item('rada', '103', '2026-10-14')], fakeSender($log, 500), $now + 1);
    Test::eq(1, (int) $db->query('SELECT COUNT(*) FROM push_subscriptions')->fetchColumn(), 'po 500 zůstává');
    push_send($db, [item('rada', '105', '2026-11-11'), item('rada', '104', '2026-10-28')], fakeSender($log, 410), $now + 2);
    Test::eq(0, (int) $db->query('SELECT COUNT(*) FROM push_subscriptions')->fetchColumn(), 'po 410 smazáno');
});

Test::case('zkušební upozornění všem zařízením', function () use ($now): void {
    $db = testDb();
    addDevice($db, 'https://fcm.googleapis.com/a');
    addDevice($db, 'https://fcm.googleapis.com/b', 'portal');
    $log = [];
    Test::eq(2, push_test($db, fakeSender($log), $now)['sent']);
    Test::true(str_starts_with($log[0]['payload']['tag'], 'zkouska-'));
});

Test::case('tlačítko zkoušky: nejnovější položka z druhů zařízení, nejvýš 3krát za hodinu', function () use ($now): void {
    $db = testDb();
    addDevice($db, 'https://fcm.googleapis.com/moje', 'zastupitelstvo');
    $feed = [item('rada', '103', '2026-10-14', 'RO'), item('zastupitelstvo', '29', '2026-09-17', 'ZO 29')];
    $log = [];
    Test::eq(200, push_send_latest($db, ['endpoint' => 'https://fcm.googleapis.com/moje'], $feed, fakeSender($log), $now)['status']);
    Test::eq('ZO 29', $log[0]['payload']['title'], 'jen odebíraný druh');
    push_send_latest($db, ['endpoint' => 'https://fcm.googleapis.com/moje'], $feed, fakeSender($log), $now + 1);
    push_send_latest($db, ['endpoint' => 'https://fcm.googleapis.com/moje'], $feed, fakeSender($log), $now + 2);
    Test::eq(429, push_send_latest($db, ['endpoint' => 'https://fcm.googleapis.com/moje'], $feed, fakeSender($log), $now + 3)['status']);
    Test::eq(404, push_send_latest($db, ['endpoint' => 'https://fcm.googleapis.com/cizi'], $feed, fakeSender($log), $now)['status']);
});

Test::case('deník a statistika počítají odeslání podle druhu ze štítku', function () use ($now): void {
    $db = testDb();
    addDevice($db, 'https://fcm.googleapis.com/a');
    $log = [];
    push_send($db, [item('rada', '103', '2026-10-14')], fakeSender($log), $now);
    push_send($db, [item('rada', '104', '2026-10-28'), item('rada', '103', '2026-10-14')], fakeSender($log), $now + 1);
    $s = push_stats($db, $now + 1);
    Test::eq(1, $s['sent_by_topic']['rada']);
    Test::eq(0, $s['sent_by_topic']['zastupitelstvo']);
});
