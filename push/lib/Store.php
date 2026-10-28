<?php
declare(strict_types=1);

/**
 * Úložiště upozornění: SQLite v push/data/. Složka není v dist/, takže ji nasazení
 * nikdy nepřepíše ani nesmaže, a .htaccess k ní zakazuje přístup z webu.
 */
final class Store
{
    public static function open(string $dataDir): PDO
    {
        if (!is_dir($dataDir) && !mkdir($dataDir, 0700, true) && !is_dir($dataDir)) {
            throw new RuntimeException('Složka pro data upozornění nejde vytvořit.');
        }
        $guard = $dataDir . DIRECTORY_SEPARATOR . '.htaccess';
        if (!is_file($guard)) {
            file_put_contents($guard, "Require all denied\n");
        }
        $db = new PDO('sqlite:' . $dataDir . DIRECTORY_SEPARATOR . 'push.sqlite');
        $db->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
        $db->exec('PRAGMA busy_timeout = 5000');
        $db->exec(<<<'SQL'
            -- Jeden řádek. Klíč VAPID se vytvoří při prvním použití a už se nemění,
            -- jinak by přestala platit všechna předplatná.
            CREATE TABLE IF NOT EXISTS push_vapid (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                public_key TEXT NOT NULL,
                private_pem TEXT NOT NULL
            );
            -- O zařízení jen adresa push služby, jeho dva klíče a data. Žádná IP ani jméno.
            CREATE TABLE IF NOT EXISTS push_subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                endpoint TEXT NOT NULL UNIQUE,
                p256dh TEXT NOT NULL,
                auth TEXT NOT NULL,
                created_at TEXT NOT NULL,
                last_ok_at TEXT NULL,
                failures INTEGER NOT NULL DEFAULT 0,
                topics TEXT NOT NULL DEFAULT ''
            );
            -- Položky (jednání, novinky portálu), které už byly oznámené nebo byly na webu před zapnutím.
            CREATE TABLE IF NOT EXISTS push_sent (
                slug TEXT PRIMARY KEY,
                sent_at TEXT NOT NULL
            );
            -- since:<druh> = datum nejnovější položky při zapnutí upozornění; starší se neoznamují.
            CREATE TABLE IF NOT EXISTS push_meta (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            -- Deník doručování pro hledání chyb: co odpověděla push služba a co ohlásil
            -- service worker v prohlížeči. Bez adres zařízení.
            CREATE TABLE IF NOT EXISTS push_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                at INTEGER NOT NULL,
                event TEXT NOT NULL,
                detail TEXT NOT NULL
            );
            -- Kdy si zařízení poslalo zkušební upozornění tlačítkem (nejvýš 3krát za hodinu).
            CREATE TABLE IF NOT EXISTS push_latest (
                device_id INTEGER NOT NULL,
                at INTEGER NOT NULL
            );
            -- Trvalé počty po dnech pro statistiku (deník push_log drží jen 200 záznamů).
            CREATE TABLE IF NOT EXISTS push_counts (
                day TEXT NOT NULL,
                kind TEXT NOT NULL,
                n INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (day, kind)
            );
            -- Omezení registrací: otisk IP (s datem, ne IP samotná) a čas, drží se hodinu.
            CREATE TABLE IF NOT EXISTS push_rate (
                ip_hash TEXT NOT NULL,
                at INTEGER NOT NULL
            );
            SQL);
        // jednou: doplnit statistiku ze stávajících dat; celé najednou, ať chyba nenechá půlku
        if (!$db->query("SELECT 1 FROM push_meta WHERE key = 'counts_backfilled'")->fetchColumn()) {
            $db->beginTransaction();
            try {
                $db->exec('DELETE FROM push_counts');
                push_counts_backfill($db);
                $db->prepare("INSERT OR REPLACE INTO push_meta (key, value) VALUES ('counts_backfilled', ?)")->execute([gmdate('c')]);
                $db->commit();
            } catch (Throwable $e) {
                $db->rollBack();
                throw $e;
            }
        }
        // jednou: nový druh „zakazky" (10/2026) dostanou zařízení, která odebírala všechny
        // dosavadní druhy obce (nic si neodškrtla); ostatní si ho mohou zapnout sama
        if (in_array('zakazky', PUSH_TOPICS, true)
            && !$db->query("SELECT 1 FROM push_meta WHERE key = 'topic_zakazky_added'")->fetchColumn()) {
            $all = implode(' AND ', array_map(fn(string $t): string => "',' || topics || ',' LIKE '%,$t,%'",
                array_diff(PUSH_TOPICS, ['zakazky'])));
            $db->exec("UPDATE push_subscriptions SET topics = topics || ',zakazky'
                WHERE $all AND ',' || topics || ',' NOT LIKE '%,zakazky,%'");
            $db->prepare("INSERT OR REPLACE INTO push_meta (key, value) VALUES ('topic_zakazky_added', ?)")->execute([gmdate('c')]);
        }
        return $db;
    }
}

/** Den v pražském čase pro statistiku. */
function push_day(int $ts): string
{
    return (new DateTimeImmutable('@' . $ts))->setTimezone(new DateTimeZone('Europe/Prague'))->format('Y-m-d');
}

/**
 * Co se z události v deníku počítá do statistiky: přihlášení nového zařízení, odhlášení,
 * upozornění přijaté push službou (podle druhu), nedoručené, zaniklé zařízení a zobrazené.
 *
 * @return list<string>
 */
function push_count_kinds(string $event, string $detail): array
{
    if ($event === 'prihlaseni') {
        return str_starts_with($detail, 'nove') ? ['prihlaseni'] : [];
    }
    if ($event === 'odhlaseni') {
        return ['odhlaseni'];
    }
    if ($event === 'sw-shown') {
        return ['zobrazeno'];
    }
    if ($event !== 'odeslano') {
        return [];
    }
    $parts = explode(' ', $detail);
    $status = (int) ($parts[2] ?? 0);
    if ($status >= 200 && $status < 300) {
        // štítek začíná druhem upozornění: „rada-103", „zastupitelstvo-souhrn-…", „portal-volby"
        $head = explode('-', $parts[0] ?? '')[0];
        $topic = defined('PUSH_TOPICS') && in_array($head, PUSH_TOPICS, true) ? $head : 'zkouska';
        return ['odeslano', 'odeslano:' . $topic];
    }
    return $status === 404 || $status === 410 ? ['nedoruceno', 'zaniklo'] : ['nedoruceno'];
}

function push_count(PDO $db, string $kind, int $ts): void
{
    // bez ON CONFLICT: na hostingu může být starší SQLite, která ho neumí
    $day = push_day($ts);
    $up = $db->prepare('UPDATE push_counts SET n = n + 1 WHERE day = ? AND kind = ?');
    $up->execute([$day, $kind]);
    if ($up->rowCount() === 0) {
        $db->prepare('INSERT OR IGNORE INTO push_counts (day, kind, n) VALUES (?, ?, 1)')->execute([$day, $kind]);
    }
}

/** Jednou při zavedení statistiky: přihlášení ze stávajících zařízení a zbytek z deníku. */
function push_counts_backfill(PDO $db): void
{
    foreach ($db->query('SELECT created_at FROM push_subscriptions')->fetchAll(PDO::FETCH_COLUMN) as $created) {
        push_count($db, 'prihlaseni', (int) strtotime($created . ' UTC'));
    }
    foreach ($db->query("SELECT at, event, detail FROM push_log WHERE event <> 'prihlaseni' ORDER BY id")->fetchAll(PDO::FETCH_ASSOC) as $r) {
        foreach (push_count_kinds($r['event'], $r['detail']) as $kind) {
            push_count($db, $kind, (int) $r['at']);
        }
    }
}

/** Zápis do deníku doručování (bez adres zařízení); drží posledních 200 záznamů. */
function push_log(PDO $db, string $event, string $detail, int $now): void
{
    $db->prepare('INSERT INTO push_log (at, event, detail) VALUES (?, ?, ?)')
        ->execute([$now, $event, mb_substr($detail, 0, 200)]);
    foreach (push_count_kinds($event, $detail) as $kind) {
        push_count($db, $kind, $now);
    }
    $db->exec('DELETE FROM push_log WHERE id NOT IN (SELECT id FROM push_log ORDER BY id DESC LIMIT 200)');
}

/** @return list<array{at: string, event: string, detail: string}>  od nejnovějšího */
function push_log_read(PDO $db, int $limit): array
{
    $q = $db->prepare('SELECT at, event, detail FROM push_log ORDER BY id DESC LIMIT ?');
    $q->bindValue(1, $limit, PDO::PARAM_INT);
    $q->execute();
    return array_map(
        static fn (array $r): array => ['at' => gmdate('Y-m-d H:i:s', (int) $r['at']) . ' UTC', 'event' => $r['event'], 'detail' => $r['detail']],
        $q->fetchAll(PDO::FETCH_ASSOC)
    );
}
