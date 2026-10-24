<?php
declare(strict_types=1);

require_once __DIR__ . '/../push/lib/Api.php';

/** Předplatné, jaké vrací PushSubscription.toJSON(). */
function sampleSub(string $endpoint = 'https://fcm.googleapis.com/fcm/send/abc'): array
{
    return [
        'endpoint' => $endpoint,
        'keys' => [
            'p256dh' => WebPush::generateVapid()['public'],
            'auth' => WebPush::b64urlEncode(random_bytes(16)),
        ],
    ];
}

function subCount(PDO $db): int
{
    return (int) $db->query('SELECT COUNT(*) FROM push_subscriptions')->fetchColumn();
}

Test::case('veřejný klíč pro prohlížeč', function (): void {
    $db = testDb();
    $r = push_api($db, 'key', [], '1.2.3.4', 1000);
    Test::eq(200, $r['status']);
    Test::eq(WebPush::vapid($db)['public'], $r['body']['public_key']);
});

Test::case('přihlášení uloží zařízení a druhé přihlášení ho nezdvojí', function (): void {
    $db = testDb();
    $sub = sampleSub();
    Test::eq(201, push_api($db, 'subscribe', $sub, '1.2.3.4', 1000)['status']);
    Test::eq(1, subCount($db));
    $sub['keys']['auth'] = WebPush::b64urlEncode(random_bytes(16));
    Test::eq(201, push_api($db, 'subscribe', $sub, '1.2.3.4', 1001)['status']);
    Test::eq(1, subCount($db), 'stejný endpoint');
    Test::eq($sub['keys']['auth'], $db->query('SELECT auth FROM push_subscriptions')->fetchColumn(), 'nové klíče');
});

Test::case('cizí adresa push služby se odmítne', function (): void {
    $db = testDb();
    Test::eq(422, push_api($db, 'subscribe', sampleSub('http://evil.example/x'), '1.2.3.4', 1000)['status']);
    Test::eq(422, push_api($db, 'subscribe', sampleSub('https://evil.example/x'), '1.2.3.4', 1000)['status']);
    Test::eq(0, subCount($db));
});

Test::case('špatné klíče zařízení se odmítnou', function (): void {
    $db = testDb();
    $sub = sampleSub();
    $sub['keys']['p256dh'] = WebPush::b64urlEncode(random_bytes(30));
    Test::eq(422, push_api($db, 'subscribe', $sub, '1.2.3.4', 1000)['status']);
    $sub = sampleSub();
    unset($sub['keys']['auth']);
    Test::eq(422, push_api($db, 'subscribe', $sub, '1.2.3.4', 1000)['status']);
    Test::eq(0, subCount($db));
});

Test::case('z jedné IP nejvýš 5 přihlášení za hodinu', function (): void {
    $db = testDb();
    for ($i = 0; $i < 5; $i++) {
        Test::eq(201, push_api($db, 'subscribe', sampleSub("https://fcm.googleapis.com/fcm/send/$i"), '1.2.3.4', 1000 + $i)['status']);
    }
    Test::eq(429, push_api($db, 'subscribe', sampleSub('https://fcm.googleapis.com/fcm/send/6'), '1.2.3.4', 1010)['status']);
    Test::eq(201, push_api($db, 'subscribe', sampleSub('https://fcm.googleapis.com/fcm/send/7'), '5.6.7.8', 1010)['status'], 'jiná IP');
    Test::eq(201, push_api($db, 'subscribe', sampleSub('https://fcm.googleapis.com/fcm/send/8'), '1.2.3.4', 1000 + 3601)['status'], 'po hodině');
    Test::true(!str_contains((string) json_encode($db->query('SELECT * FROM push_rate')->fetchAll()), '1.2.3.4'), 'IP se neukládá');
});

Test::case('nejvýš 5000 předplatných celkem', function (): void {
    $db = testDb();
    $db->beginTransaction();
    $ins = $db->prepare("INSERT INTO push_subscriptions (endpoint, p256dh, auth, created_at) VALUES (?, 'x', 'y', 'z')");
    for ($i = 0; $i < PUSH_MAX_SUBSCRIPTIONS; $i++) {
        $ins->execute(["https://fcm.googleapis.com/fcm/send/n$i"]);
    }
    $db->commit();
    Test::eq(429, push_api($db, 'subscribe', sampleSub(), '1.2.3.4', 1000)['status']);
    $known = sampleSub('https://fcm.googleapis.com/fcm/send/n1');
    Test::eq(201, push_api($db, 'subscribe', $known, '1.2.3.4', 1000)['status'], 'známé zařízení si smí obnovit klíče');
});

Test::case('odhlášení zařízení smaže', function (): void {
    $db = testDb();
    $sub = sampleSub();
    push_api($db, 'subscribe', $sub, '1.2.3.4', 1000);
    Test::eq(204, push_api($db, 'unsubscribe', ['endpoint' => $sub['endpoint']], '1.2.3.4', 1001)['status']);
    Test::eq(0, subCount($db));
});

Test::case('neznámá akce je 404', function (): void {
    Test::eq(404, push_api(testDb(), 'smaz-vse', [], '1.2.3.4', 1000)['status']);
});

Test::case('klíč zařízení musí být skutečný bod křivky', function (): void {
    $db = testDb();
    $sub = sampleSub();
    $sub['keys']['p256dh'] = WebPush::b64urlEncode("\x04" . random_bytes(64));
    Test::eq(422, push_api($db, 'subscribe', $sub, '1.2.3.4', 1000)['status']);
});

Test::case('celkem nejvýš 200 nových zařízení za hodinu', function (): void {
    $db = testDb();
    $db->beginTransaction();
    $ins = $db->prepare('INSERT INTO push_rate (ip_hash, at) VALUES (?, ?)');
    for ($i = 0; $i < PUSH_MAX_NEW_PER_HOUR; $i++) {
        $ins->execute(["ip$i", 1000]);
    }
    $db->commit();
    Test::eq(429, push_api($db, 'subscribe', sampleSub(), '9.9.9.9', 1010)['status']);
    Test::eq(201, push_api($db, 'subscribe', sampleSub(), '9.9.9.9', 1000 + 3601)['status'], 'po hodině');
});

Test::case('push služby jen ze seznamu, ne jiné služby stejných firem', function (): void {
    Test::true(!WebPush::endpointAllowed('https://storage.googleapis.com/x'), 'Google Storage');
    Test::true(!WebPush::endpointAllowed('https://evil.mozilla.com/x'), 'jiná služba Mozilly');
    Test::true(WebPush::endpointAllowed('https://wns2-par02p.notify.windows.com/w/?token=x'), 'Edge');
});

Test::case('service worker hlásí, že zpráva došla a upozornění se zobrazilo', function (): void {
    $db = testDb();
    Test::eq(204, push_api($db, 'seen', ['tag' => 'zkouska-5000', 'stage' => 'shown'], '1.2.3.4', 1000)['status']);
    Test::eq(204, push_api($db, 'seen', ['tag' => 'zkouska-5000', 'stage' => 'error', 'detail' => str_repeat('x', 500)], '1.2.3.4', 1001)['status']);
    Test::eq(422, push_api($db, 'seen', ['tag' => 'x', 'stage' => 'smaz'], '1.2.3.4', 1002)['status']);
    $rows = push_log_read($db, 10);
    Test::eq(2, count($rows));
    Test::eq('sw-error', $rows[0]['event']);
    Test::true(strlen($rows[0]['detail']) <= 220, 'zkrácený text');
});

Test::case('nové zařízení si vybere druhy upozornění, bez výběru všechny druhy', function (): void {
    $db = testDb();
    $a = sampleSub('https://fcm.googleapis.com/fcm/send/a');
    Test::eq(['rada', 'zastupitelstvo', 'portal'], push_api($db, 'subscribe', $a, '1.2.3.4', 1000)['body']['topics']);
    $b = sampleSub('https://fcm.googleapis.com/fcm/send/b') + ['topics' => ['rada', 'zastupitelstvo', 'nesmysl']];
    Test::eq(['rada', 'zastupitelstvo'], push_api($db, 'subscribe', $b, '1.2.3.4', 1001)['body']['topics']);
});

Test::case('obnovení bez výběru druhů nechá původní výběr, s výběrem ho změní', function (): void {
    $db = testDb();
    $a = sampleSub('https://fcm.googleapis.com/fcm/send/a');
    push_api($db, 'subscribe', $a + ['topics' => ['zastupitelstvo']], '1.2.3.4', 1000);
    Test::eq(['zastupitelstvo'], push_api($db, 'subscribe', $a, '1.2.3.4', 1001)['body']['topics'], 'stránka jen ověřuje přihlášení');
    Test::eq(['rada'], push_api($db, 'subscribe', $a + ['topics' => ['rada']], '1.2.3.4', 1002)['body']['topics']);
    Test::eq(422, push_api($db, 'subscribe', $a + ['topics' => []], '1.2.3.4', 1003)['status'], 'aspoň jeden druh; jinak vypnout');
});

Test::case('přehled odběrů: počty, druhy, prohlížeče a zařízení bez adres', function (): void {
    $db = testDb();
    $ins = $db->prepare('INSERT INTO push_subscriptions (endpoint, p256dh, auth, created_at, last_ok_at, failures, topics) VALUES (?, ?, ?, ?, ?, ?, ?)');
    $ins->execute(['https://fcm.googleapis.com/fcm/send/tajne1', 'k', 'a', '2026-10-21 22:30:00', '2026-10-23 08:00:00', 0, 'rada,zastupitelstvo,portal']);
    $ins->execute(['https://updates.push.services.mozilla.com/wpush/v2/tajne2', 'k', 'a', '2026-10-23 07:00:00', null, 2, 'zastupitelstvo']);
    $r = push_api($db, 'stats', [], '1.2.3.4', 1000);
    Test::eq(200, $r['status']);
    $b = $r['body'];
    Test::eq(2, $b['total']);
    Test::eq(['rada' => 1, 'zastupitelstvo' => 2, 'portal' => 1], $b['topics']);
    Test::eq(['Chrome nebo Android' => 1, 'Firefox' => 1], $b['services']);
    Test::eq('2026-10-22', $b['devices'][0]['since'], 'datum přihlášení v pražském čase');
    Test::eq(['rada', 'zastupitelstvo', 'portal'], $b['devices'][0]['topics']);
    Test::eq('2026-10-23', $b['devices'][0]['last_ok']);
    Test::eq(null, $b['devices'][1]['last_ok']);
    Test::eq(2, $b['devices'][1]['failures']);
    Test::eq([['date' => '2026-10-22', 'n' => 1], ['date' => '2026-10-23', 'n' => 1]], $b['by_day']);
    Test::true(!str_contains((string) json_encode($b), 'tajne'), 'žádné adresy zařízení');
});

Test::case('statistika po dnech: přihlášení, odhlášení a doručená upozornění podle druhu', function (): void {
    $db = testDb();
    $day1 = strtotime('2026-10-22 10:00:00 UTC');
    $day2 = strtotime('2026-10-23 10:00:00 UTC');
    push_log($db, 'prihlaseni', 'nove zarizeni 1 fcm.googleapis.com', $day1);
    push_log($db, 'prihlaseni', 'obnoveno zarizeni 1', $day1);  // obnovení se nepočítá
    push_log($db, 'odeslano', 'rada-a fcm.googleapis.com 201 ', $day1);
    push_log($db, 'odeslano', 'zastupitelstvo-2026-10-24 fcm.googleapis.com 201 ', $day2);
    push_log($db, 'odeslano', 'portal-1 fcm.googleapis.com 410 gone', $day2);
    push_log($db, 'sw-shown', 'zastupitelstvo-2026-10-24', $day2);
    push_log($db, 'odhlaseni', 'fcm.googleapis.com', $day2);
    $s = push_stats($db, $day2);
    Test::eq(['prihlaseni' => 1, 'odhlaseni' => 1, 'odeslano' => 2, 'nedoruceno' => 1, 'zobrazeno' => 1], $s['totals']);
    Test::eq(['rada' => 1, 'zastupitelstvo' => 1, 'portal' => 0, 'zkouska' => 0], $s['sent_by_topic']);
    Test::eq(30, count($s['daily']), 'posledních 30 dní');
    $last = $s['daily'][29];
    Test::eq('2026-10-23', $last['date']);
    Test::eq(['date' => '2026-10-23', 'prihlaseni' => 0, 'odhlaseni' => 1, 'odeslano' => 1, 'nedoruceno' => 1, 'zobrazeno' => 1, 'subscribers' => 0], $last);
    Test::eq(1, $s['daily'][28]['prihlaseni']);
    // zpětně od dnešního počtu (0): 23. 10. jeden odhlášený a jeden zaniklý (410), 22. 10. tedy 2
    Test::eq(2, $s['daily'][28]['subscribers'], 'počet odběratelů na konci dne');
});

Test::case('dopočítání statistiky proběhne i u databáze, kde tabulka počtů už je (z neúspěšného prvního pokusu)', function (): void {
    $dir = sys_get_temp_dir() . DIRECTORY_SEPARATOR . 'jaksemame-push-' . bin2hex(random_bytes(6));
    mkdir($dir);
    $db = Store::open($dir);
    $db->prepare("INSERT INTO push_subscriptions (endpoint, p256dh, auth, created_at) VALUES ('https://fcm.googleapis.com/x', 'k', 'a', '2026-10-22 10:00:00')")->execute();
    // stav po neúspěšném prvním pokusu: tabulka je, příznak dopočítání chybí
    $db->exec("DELETE FROM push_meta WHERE key = 'counts_backfilled'");
    $db->exec('DELETE FROM push_counts');
    $db = Store::open($dir);
    Test::eq(1, push_stats($db, strtotime('2026-10-23 10:00:00 UTC'))['totals']['prihlaseni']);
    $db = Store::open($dir);
    Test::eq(1, push_stats($db, strtotime('2026-10-23 10:00:00 UTC'))['totals']['prihlaseni'], 'podruhé se nepřičte');
});

Test::case('před prvním zaznamenaným dnem nebyl žádný odběratel', function (): void {
    $db = testDb();
    $db->prepare("INSERT INTO push_subscriptions (endpoint, p256dh, auth, created_at) VALUES ('https://fcm.googleapis.com/x', 'k', 'a', '2026-10-22 10:00:00')")->execute();
    push_log($db, 'odhlaseni', 'fcm.googleapis.com', strtotime('2026-10-22 09:00:00 UTC'));
    push_log($db, 'prihlaseni', 'nove zarizeni 1 fcm.googleapis.com', strtotime('2026-10-22 10:00:00 UTC'));
    push_log($db, 'odeslano', 'zkouska-1 fcm.googleapis.com 201 ', strtotime('2026-10-21 19:00:00 UTC'));
    $daily = push_stats($db, strtotime('2026-10-23 10:00:00 UTC'))['daily'];
    $by = array_column($daily, 'subscribers', 'date');
    Test::eq(1, $by['2026-10-21'], 'první den s doručením');
    Test::eq(0, $by['2026-10-20']);
    Test::eq(0, $by['2026-09-24']);
});
