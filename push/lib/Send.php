<?php
declare(strict_types=1);

require_once __DIR__ . '/Obec.php';
require_once __DIR__ . '/WebPush.php';
require_once __DIR__ . '/Store.php';

const PUSH_MAX_FAILURES = 10;
const PUSH_LATEST_PER_HOUR = 3;

/** Smí volající spustit rozeslání? Token porovnává v konstantním čase. */
function push_authorized(string $header, string $token): bool
{
    if ($token === '' || !str_starts_with($header, 'Bearer ')) {
        return false;
    }
    return hash_equals($token, substr($header, 7));
}

/**
 * Oznámí položky (jednání, novinky portálu), které ještě oznámené nebyly.
 *
 * Položky dodává push/feed.json, který se sestaví při nasazení (build_push.py):
 * {id, topic, title, body, url, date}, od nejnovější. Pro každý druh si server pamatuje
 * datum nejnovější položky z prvního běhu („since:<druh>") a starší nikdy neoznamuje,
 * takže první spuštění ani doplnění starého jednání do dat nepošle lavinu upozornění.
 *
 * @param list<array{id: string, topic: string, title: string, body: string, url: string, date: string}> $items
 * @param callable(array, string): array{status: int, ok: bool, gone: bool, detail: string} $sender
 * @return array{sent: int, items: int, skipped: string}
 */
function push_send(PDO $db, array $items, callable $sender, int $now): array
{
    $at = gmdate('Y-m-d H:i:s', $now);
    $items = array_values(array_filter($items, static fn ($i): bool =>
        is_array($i) && in_array($i['topic'] ?? '', PUSH_TOPICS, true) && ($i['id'] ?? '') !== '' && ($i['date'] ?? '') !== ''));
    $known = array_flip($db->query('SELECT slug FROM push_sent')->fetchAll(PDO::FETCH_COLUMN));
    $mark = $db->prepare('INSERT OR IGNORE INTO push_sent (slug, sent_at) VALUES (?, ?)');
    $getMeta = $db->prepare('SELECT value FROM push_meta WHERE key = ?');
    $setMeta = $db->prepare('INSERT OR REPLACE INTO push_meta (key, value) VALUES (?, ?)');

    $first = false;
    $fresh = [];
    foreach (PUSH_TOPICS as $topic) {
        $own = array_values(array_filter($items, static fn (array $i): bool => $i['topic'] === $topic));
        $getMeta->execute(['since:' . $topic]);
        $since = $getMeta->fetchColumn();
        if ($since === false) {
            // první běh pro tento druh: jen zapamatovat, co už je, a nic neposílat;
            // u druhu bez položek (novinky portálu) platí od včerejška, ať první novinka dojde
            $first = true;
            $dates = array_column($own, 'date');
            $setMeta->execute(['since:' . $topic, $dates === [] ? gmdate('Y-m-d', $now - 86400) : max($dates)]);
            foreach ($own as $i) {
                $mark->execute([$i['id'], $at]);
            }
            continue;
        }
        foreach ($own as $i) {
            if (!isset($known[$i['id']]) && strcmp($i['date'], (string) $since) > 0) {
                $fresh[$topic][] = $i;
            }
        }
    }
    if ($fresh === []) {
        return ['sent' => 0, 'items' => 0, 'skipped' => $first ? 'první spuštění: položky jen zapamatovány' : 'nic nového'];
    }

    $sent = 0;
    $count = 0;
    foreach ($fresh as $topic => $list) {
        // zapamatovat předem: kdyby rozeslání spadlo v půlce, nikdo nedostane totéž dvakrát
        foreach ($list as $i) {
            $mark->execute([$i['id'], $at]);
        }
        $count += count($list);
        $message = count($list) === 1 ? push_item_message($list[0]) : push_group_message($topic, $list, $now);
        $payload = (string) json_encode($message, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
        $sent += push_deliver($db, $payload, $sender, $now, $message['tag'], topic: $topic);
    }
    return ['sent' => $sent, 'items' => $count, 'skipped' => ''];
}

/**
 * Upozornění na jednu položku. Štítek začíná druhem (statistika) a je vlastní pro každou
 * položku, ať nové upozornění nepřepíše starší, které ještě visí v liště.
 *
 * @return array{title: string, body: string, url: string, tag: string}
 */
function push_item_message(array $i): array
{
    return ['title' => $i['title'], 'body' => $i['body'], 'url' => $i['url'], 'tag' => $i['id']];
}

/** Víc nových položek stejného druhu najednou: jedno souhrnné upozornění. */
function push_group_message(string $topic, array $list, int $now): array
{
    $n = count($list);
    $what = [
        'rada' => ['Rada obce', '/zapisy.html'],
        'zastupitelstvo' => ['Zastupitelstvo', '/zastupitelstvo.html'],
        'portal' => ['Novinky portálu', '/'],
    ][$topic] ?? ['Novinky', '/'];
    $title = $what[0] . ': ' . ($topic === 'portal'
        ? ($n < 5 ? "$n novinky" : "$n novinek")
        : ($n < 5 ? "$n nová jednání" : "$n nových jednání"));
    $body = mb_substr(implode(' · ', array_column($list, 'title')), 0, 240);
    return ['title' => $title, 'body' => $body, 'url' => $what[1], 'tag' => $topic . '-souhrn-' . $now];
}

/**
 * Tlačítko „Poslat mi zkušební upozornění“: pošle nejnovější položku, kterou zařízení
 * odebírá, jen tomuto zařízení. Zařízení musí server znát, nejvýš 3krát za hodinu.
 *
 * @param array<string, mixed> $in  {endpoint}
 * @return array{status: int, body: array<string, mixed>}
 */
function push_send_latest(PDO $db, array $in, array $items, callable $sender, int $now): array
{
    $endpoint = is_string($in['endpoint'] ?? null) ? trim($in['endpoint']) : '';
    $q = $db->prepare('SELECT id, topics FROM push_subscriptions WHERE endpoint = ?');
    $q->execute([$endpoint]);
    $row = $q->fetch(PDO::FETCH_ASSOC);
    if ($endpoint === '' || $row === false) {
        return ['status' => 404, 'body' => ['error' => 'Tohle zařízení server nezná. Zapněte upozornění znovu.']];
    }
    $topics = explode(',', (string) $row['topics']);
    $mine = array_values(array_filter($items, static fn ($i): bool => is_array($i) && in_array($i['topic'] ?? '', $topics, true)));
    $item = $mine[0] ?? null;
    if ($item === null) {
        return ['status' => 404, 'body' => ['error' => 'K vybraným druhům zatím nic není.']];
    }
    $id = (int) $row['id'];
    $db->prepare('DELETE FROM push_latest WHERE at <= ?')->execute([$now - 3600]);
    $count = $db->prepare('SELECT COUNT(*) FROM push_latest WHERE device_id = ?');
    $count->execute([$id]);
    if ((int) $count->fetchColumn() >= PUSH_LATEST_PER_HOUR) {
        return ['status' => 429, 'body' => ['error' => 'Zkoušku jde poslat nejvýš třikrát za hodinu.']];
    }
    $db->prepare('INSERT INTO push_latest (device_id, at) VALUES (?, ?)')->execute([$id, $now]);

    $message = push_item_message($item);
    $payload = (string) json_encode($message, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    $status = 0;
    push_deliver($db, $payload, $sender, $now, $message['tag'], $id, $status);
    return $status >= 200 && $status < 300
        ? ['status' => 200, 'body' => []]
        : ['status' => $status === 404 || $status === 410 ? 410 : 502, 'body' => ['error' => 'Push služba zprávu nepřijala. Zapněte upozornění znovu.']];
}

/**
 * Zkušební upozornění všem zařízením (ruční workflow „Zkouška upozornění“).
 *
 * @return array{sent: int}
 */
function push_test(PDO $db, callable $sender, int $now): array
{
    $tag = 'zkouska-' . $now;
    $payload = (string) json_encode([
        'title' => 'Zkušební upozornění',
        'body' => 'Tohle je jen zkouška upozornění z portálu ' . PUSH_SITE,
        'url' => '/',
        'tag' => $tag,
    ], JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    return ['sent' => push_deliver($db, $payload, $sender, $now, $tag)];
}

/** Pošle zprávu zařízením, uklidí zaniklá a zapíše výsledky do deníku. Vrací počet přijatých. */
function push_deliver(PDO $db, string $payload, callable $sender, int $now, string $tag, ?int $onlyId = null, int &$lastStatus = 0, string $topic = ''): int
{
    $at = gmdate('Y-m-d H:i:s', $now);
    $sent = 0;
    // $topic: jen zařízení, která daný druh upozornění chtějí ('' = všechna)
    $list = $db->prepare("SELECT id, endpoint, p256dh, auth, failures FROM push_subscriptions
        WHERE (? IS NULL OR id = ?) AND (? = '' OR ',' || topics || ',' LIKE '%,' || ? || ',%')");
    $list->execute([$onlyId, $onlyId, $topic, $topic]);
    $devices = $list->fetchAll(PDO::FETCH_ASSOC);
    $ok = $db->prepare('UPDATE push_subscriptions SET failures = 0, last_ok_at = ? WHERE id = ?');
    $fail = $db->prepare('UPDATE push_subscriptions SET failures = failures + 1 WHERE id = ?');
    $drop = $db->prepare('DELETE FROM push_subscriptions WHERE id = ?');

    foreach ($devices as $d) {
        try {
            $r = $sender($d, $payload);
        } catch (Throwable $e) {
            $r = ['status' => 0, 'ok' => false, 'gone' => false, 'detail' => $e->getMessage()];
        }
        $lastStatus = (int) $r['status'];
        push_log($db, 'odeslano', $tag . ' ' . (string) parse_url($d['endpoint'], PHP_URL_HOST) . ' ' . $r['status'] . ' ' . $r['detail'], $now);
        if ($r['ok']) {
            $sent++;
            $ok->execute([$at, $d['id']]);
        } elseif ($r['gone'] || (int) $d['failures'] + 1 >= PUSH_MAX_FAILURES) {
            $drop->execute([$d['id']]);
        } else {
            $fail->execute([$d['id']]);
        }
    }
    return $sent;
}
