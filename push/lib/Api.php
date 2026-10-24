<?php
declare(strict_types=1);

require_once __DIR__ . '/Obec.php';
require_once __DIR__ . '/WebPush.php';
require_once __DIR__ . '/Store.php';

const PUSH_MAX_SUBSCRIPTIONS = 5000;
const PUSH_MAX_PER_IP_HOUR = 5;
const PUSH_MAX_NEW_PER_HOUR = 200;

/**
 * Přihlášení a odhlášení zařízení. Bez HTTP, ať jde testovat; obal je v api.php.
 * Registraci může volat kdokoli, proto se ověřuje adresa push služby, klíče
 * a počet nových zařízení z jedné IP i celkem.
 *
 * @param array<string, mixed> $in  tělo požadavku (JSON)
 * @return array{status: int, body: array<string, mixed>}
 */
function push_api(PDO $db, string $action, array $in, string $ip, int $now): array
{
    if ($action === 'stats') {
        return ['status' => 200, 'body' => push_stats($db, $now)];
    }

    if ($action === 'key') {
        return ['status' => 200, 'body' => ['public_key' => WebPush::vapid($db)['public']]];
    }

    $endpoint = is_string($in['endpoint'] ?? null) ? trim($in['endpoint']) : '';

    if ($action === 'seen') {
        // service worker hlásí, co se se zprávou stalo v prohlížeči (pro hledání chyb)
        $stage = is_string($in['stage'] ?? null) ? $in['stage'] : '';
        if (!in_array($stage, ['push', 'shown', 'error'], true)) {
            return ['status' => 422, 'body' => ['error' => 'Neznámý stav.']];
        }
        $tag = is_string($in['tag'] ?? null) ? mb_substr($in['tag'], 0, 80) : '';
        $detail = is_string($in['detail'] ?? null) ? mb_substr($in['detail'], 0, 120) : '';
        push_log($db, 'sw-' . $stage, trim($tag . ' ' . $detail), $now);
        return ['status' => 204, 'body' => []];
    }

    if ($action === 'unsubscribe') {
        $db->prepare('DELETE FROM push_subscriptions WHERE endpoint = ?')->execute([$endpoint]);
        push_log($db, 'odhlaseni', (string) parse_url($endpoint, PHP_URL_HOST), $now);
        return ['status' => 204, 'body' => []];
    }

    if ($action !== 'subscribe') {
        return ['status' => 404, 'body' => ['error' => 'Neznámá akce.']];
    }

    $keys = is_array($in['keys'] ?? null) ? $in['keys'] : [];
    $p256dh = is_string($keys['p256dh'] ?? null) ? $keys['p256dh'] : '';
    $auth = is_string($keys['auth'] ?? null) ? $keys['auth'] : '';

    if ($endpoint === '' || strlen($endpoint) > 1000 || !WebPush::endpointAllowed($endpoint)) {
        return ['status' => 422, 'body' => ['error' => 'Adresa push služby není povolená.']];
    }
    $pub = WebPush::b64urlDecode($p256dh);
    $secret = WebPush::b64urlDecode($auth);
    if (!WebPush::validPublicKey($pub) || strlen($secret) < 16 || strlen($secret) > 64) {
        return ['status' => 422, 'body' => ['error' => 'Chybí klíče zařízení.']];
    }

    // Výběr druhů: bez něj (stránka jen ověřuje přihlášení) zůstává, jak byl.
    $topics = null;
    if (array_key_exists('topics', $in)) {
        $topics = array_values(array_intersect(PUSH_TOPICS, is_array($in['topics']) ? $in['topics'] : []));
        if ($topics === []) {
            return ['status' => 422, 'body' => ['error' => 'Vyberte aspoň jeden druh upozornění, nebo upozornění vypněte.']];
        }
    }

    $at = gmdate('Y-m-d H:i:s', $now);
    $known = $db->prepare('SELECT id FROM push_subscriptions WHERE endpoint = ?');
    $known->execute([$endpoint]);
    $id = $known->fetchColumn();

    if ($id !== false) {
        // Stejný prohlížeč si obnovil klíče.
        $db->prepare('UPDATE push_subscriptions SET p256dh = ?, auth = ?, failures = 0, topics = COALESCE(?, topics) WHERE id = ?')
            ->execute([$p256dh, $auth, $topics === null ? null : implode(',', $topics), $id]);
        push_log($db, 'prihlaseni', 'obnoveno zarizeni ' . $id, $now);
        return ['status' => 201, 'body' => ['topics' => push_topics_of($db, (int) $id)]];
    }

    // IP se neukládá, jen její otisk s datem; po hodině se maže.
    $ipHash = hash('sha256', $ip . '|' . gmdate('Y-m-d', $now));
    $db->prepare('DELETE FROM push_rate WHERE at <= ?')->execute([$now - 3600]);
    $recent = $db->prepare('SELECT COUNT(*) FROM push_rate WHERE ip_hash = ?');
    $recent->execute([$ipHash]);
    $all = (int) $db->query('SELECT COUNT(*) FROM push_rate')->fetchColumn();
    if ((int) $recent->fetchColumn() >= PUSH_MAX_PER_IP_HOUR || $all >= PUSH_MAX_NEW_PER_HOUR) {
        return ['status' => 429, 'body' => ['error' => 'Příliš mnoho přihlášení, zkuste to později.']];
    }
    if ((int) $db->query('SELECT COUNT(*) FROM push_subscriptions')->fetchColumn() >= PUSH_MAX_SUBSCRIPTIONS) {
        return ['status' => 429, 'body' => ['error' => 'Upozornění teď nejde zapnout.']];
    }

    $db->prepare('INSERT INTO push_subscriptions (endpoint, p256dh, auth, created_at, topics) VALUES (?, ?, ?, ?, ?)')
        ->execute([$endpoint, $p256dh, $auth, $at, implode(',', $topics ?? PUSH_TOPICS)]);
    $newId = (int) $db->lastInsertId();
    $db->prepare('INSERT INTO push_rate (ip_hash, at) VALUES (?, ?)')->execute([$ipHash, $now]);
    push_log($db, 'prihlaseni', 'nove zarizeni ' . $newId . ' ' . (string) parse_url($endpoint, PHP_URL_HOST), $now);
    return ['status' => 201, 'body' => ['topics' => push_topics_of($db, $newId)]];
}

/** @return list<string> */
function push_topics_of(PDO $db, int $id): array
{
    $q = $db->prepare('SELECT topics FROM push_subscriptions WHERE id = ?');
    $q->execute([$id]);
    return array_values(array_filter(explode(',', (string) $q->fetchColumn())));
}

/**
 * Přehled odběrů (?a=stats): kolik zařízení, kdy se přihlásila, co odebírají
 * a přes jakou push službu. Bez adres a klíčů zařízení, takže ho smí vidět kdokoli.
 *
 * @return array<string, mixed>
 */
function push_stats(PDO $db, ?int $now = null): array
{
    $now ??= time();
    $zone = new DateTimeZone('Europe/Prague');
    $day = static function (?string $utc) use ($zone): ?string {
        if ($utc === null || $utc === '') {
            return null;
        }
        return (new DateTimeImmutable($utc, new DateTimeZone('UTC')))->setTimezone($zone)->format('Y-m-d');
    };
    $services = [
        'fcm.googleapis.com' => 'Chrome nebo Android',
        'push.services.mozilla.com' => 'Firefox',
        'push.apple.com' => 'Safari (iPhone, iPad, Mac)',
        'notify.windows.com' => 'Edge ve Windows',
    ];
    $service = static function (string $endpoint) use ($services): string {
        $host = (string) parse_url($endpoint, PHP_URL_HOST);
        foreach ($services as $suffix => $name) {
            if ($host === $suffix || str_ends_with($host, '.' . $suffix)) {
                return $name;
            }
        }
        return 'Jiný prohlížeč';
    };

    $rows = $db->query('SELECT endpoint, created_at, last_ok_at, failures, topics FROM push_subscriptions ORDER BY created_at, id')
        ->fetchAll(PDO::FETCH_ASSOC);
    $topics = array_fill_keys(PUSH_TOPICS, 0);
    $byService = [];
    $byDay = [];
    $devices = [];
    foreach ($rows as $n => $r) {
        $own = array_values(array_intersect(PUSH_TOPICS, explode(',', (string) $r['topics'])));
        foreach ($own as $t) {
            $topics[$t]++;
        }
        $svc = $service((string) $r['endpoint']);
        $byService[$svc] = ($byService[$svc] ?? 0) + 1;
        $since = $day((string) $r['created_at']);
        $byDay[$since] = ($byDay[$since] ?? 0) + 1;
        $devices[] = [
            'no' => $n + 1, 'since' => $since, 'service' => $svc, 'topics' => $own,
            'last_ok' => $day($r['last_ok_at']), 'failures' => (int) $r['failures'],
        ];
    }
    ksort($byDay);

    // trvalé počty po dnech: součty, posledních 30 dní a počet odběratelů na konci dne
    $counts = [];
    foreach ($db->query('SELECT day, kind, n FROM push_counts')->fetchAll(PDO::FETCH_ASSOC) as $c) {
        $counts[$c['day']][$c['kind']] = (int) $c['n'];
    }
    $kinds = ['prihlaseni', 'odhlaseni', 'odeslano', 'nedoruceno', 'zobrazeno'];
    $totals = array_fill_keys($kinds, 0);
    $sentByTopic = array_fill_keys([...PUSH_TOPICS, 'zkouska'], 0);
    foreach ($counts as $kindsOfDay) {
        foreach ($kinds as $k) {
            $totals[$k] += $kindsOfDay[$k] ?? 0;
        }
        foreach (array_keys($sentByTopic) as $t) {
            $sentByTopic[$t] += $kindsOfDay['odeslano:' . $t] ?? 0;
        }
    }
    $today = new DateTimeImmutable(push_day($now), $zone);
    $daily = [];
    $subscribers = count($rows);
    for ($i = 0; $i < 30; $i++) {
        $d = $today->modify("-$i day")->format('Y-m-d');
        $c = $counts[$d] ?? [];
        $daily[] = ['date' => $d] + array_combine($kinds, array_map(static fn ($k) => $c[$k] ?? 0, $kinds)) + ['subscribers' => $subscribers];
        // zpětně: před tímto dnem bylo o přihlášené méně a o odhlášené a zaniklé víc
        $subscribers -= ($c['prihlaseni'] ?? 0) - ($c['odhlaseni'] ?? 0) - ($c['zaniklo'] ?? 0);
        $subscribers = max($subscribers, 0);
    }
    $daily = array_reverse($daily);
    // před prvním zaznamenaným dnem upozornění ještě nikdo neodebíral
    $first = $counts === [] ? null : min(array_keys($counts));
    foreach ($daily as &$row) {
        if ($first !== null && $row['date'] < $first) {
            $row['subscribers'] = 0;
        }
    }
    unset($row);

    return [
        'totals' => $totals,
        'sent_by_topic' => $sentByTopic,
        'daily' => $daily,
        'total' => count($rows),
        'topics' => $topics,
        'services' => $byService,
        'by_day' => array_map(static fn ($d, $c) => ['date' => $d, 'n' => $c], array_keys($byDay), $byDay),
        'devices' => $devices,
    ];
}
