<?php
declare(strict_types=1);

/**
 * Deník volání a omezení četnosti. Ukládá se, co server opravdu dostane: název nástroje,
 * jeho parametry (to, co model hledal), počet výsledků, dobu a typ klienta. Otázku uživatele
 * server nevidí. IP adresa se neukládá: pro limit se z ní dělá otisk s denně měněnou solí,
 * takže návštěvníka nejde sledovat přes dny. Záznamy starší 90 dní se mažou.
 */
final class Log
{
    private const KEEP_DAYS = 90;
    private const PER_MINUTE = 60;

    private static ?PDO $db = null;

    private static function db(): PDO
    {
        if (self::$db === null) {
            $dir = defined('MCP_LOG_DIR') ? MCP_LOG_DIR : MCP_ROOT . '/log';
            if (!is_dir($dir) && !mkdir($dir, 0700, true) && !is_dir($dir)) {
                throw new RuntimeException('Složka deníku nejde vytvořit.');
            }
            if (!is_file($dir . '/.htaccess')) {
                file_put_contents($dir . '/.htaccess', "Require all denied\n");
            }
            $db = new PDO('sqlite:' . $dir . '/mcp.sqlite');
            $db->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
            $db->exec('PRAGMA busy_timeout = 3000');
            $db->exec(<<<'SQL'
                CREATE TABLE IF NOT EXISTS volani (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    kdy TEXT NOT NULL,
                    metoda TEXT NOT NULL,
                    nastroj TEXT NULL,
                    obec TEXT NULL,
                    parametry TEXT NULL,
                    vysledku INTEGER NULL,
                    ms INTEGER NULL,
                    klient TEXT NULL,
                    chyba TEXT NULL
                );
                CREATE INDEX IF NOT EXISTS volani_kdy ON volani (kdy);
                CREATE TABLE IF NOT EXISTS limit_okna (
                    otisk TEXT NOT NULL,
                    minuta INTEGER NOT NULL,
                    pocet INTEGER NOT NULL,
                    PRIMARY KEY (otisk, minuta)
                );
                CREATE TABLE IF NOT EXISTS sul (den TEXT PRIMARY KEY, hodnota TEXT NOT NULL);
                SQL);
            self::$db = $db;
        }
        return self::$db;
    }

    /** true = klient přetáhl limit volání za minutu. */
    public static function overLimit(string $ip): bool
    {
        try {
            $db = self::db();
            $day = gmdate('Y-m-d');
            $db->prepare('INSERT OR IGNORE INTO sul VALUES (?, ?)')->execute([$day, bin2hex(random_bytes(16))]);
            $salt = (string) $db->query("SELECT hodnota FROM sul WHERE den = '$day'")->fetchColumn();
            $key = substr(hash('sha256', $salt . $ip), 0, 16);
            $min = intdiv(time(), 60);
            $db->prepare('INSERT INTO limit_okna VALUES (?, ?, 1) ON CONFLICT (otisk, minuta) DO UPDATE SET pocet = pocet + 1')
                ->execute([$key, $min]);
            $st = $db->prepare('SELECT pocet FROM limit_okna WHERE otisk = ? AND minuta = ?');
            $st->execute([$key, $min]);
            if (random_int(1, 50) === 1) {
                $db->prepare('DELETE FROM limit_okna WHERE minuta < ?')->execute([$min - 5]);
                $db->prepare('DELETE FROM sul WHERE den < ?')->execute([gmdate('Y-m-d', time() - 2 * 86400)]);
            }
            return (int) $st->fetchColumn() > self::PER_MINUTE;
        } catch (Throwable $e) {
            return false;  // deník nesmí shodit odpovědi
        }
    }

    public static function call(string $method, ?string $tool, ?array $args, ?int $results, int $ms, ?string $client, ?string $error): void
    {
        try {
            $db = self::db();
            $obec = is_string($args['obec'] ?? null) ? $args['obec'] : null;
            $db->prepare('INSERT INTO volani (kdy, metoda, nastroj, obec, parametry, vysledku, ms, klient, chyba) VALUES (?,?,?,?,?,?,?,?,?)')
                ->execute([gmdate('Y-m-d\TH:i:s\Z'), $method, $tool, $obec,
                    $args ? mb_substr(json_encode($args, JSON_UNESCAPED_UNICODE), 0, 2000) : null,
                    $results, $ms, $client ? mb_substr($client, 0, 80) : null,
                    $error ? mb_substr($error, 0, 300) : null]);
            if (random_int(1, 200) === 1) {
                $db->prepare('DELETE FROM volani WHERE kdy < ?')->execute([gmdate('Y-m-d', time() - self::KEEP_DAYS * 86400)]);
            }
        } catch (Throwable $e) {
            // deník nesmí shodit odpovědi
        }
    }
}
