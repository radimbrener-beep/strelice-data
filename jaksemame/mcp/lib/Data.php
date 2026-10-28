<?php
declare(strict_types=1);

/**
 * Registr obcí (obce.json) a jejich data. Každá obec má vlastní SQLite z build_mcp.py
 * svého repa; na webu leží v mcp/data/<obec>.sqlite. Lokálně jde cestu přepsat
 * v config.local.php: define('MCP_DATA', ['strelice' => 'C:/…/strelice.sqlite']).
 * Novou obec přidáš záznamem v obce.json a nahráním jejího souboru, server se nemění.
 */
final class Data
{
    private static ?array $obce = null;
    /** @var array<string, PDO> */
    private static array $db = [];
    /** @var array<string, array> */
    private static array $meta = [];

    /** Obce, jejichž data jsou opravdu k dispozici: [slug => záznam z registru]. */
    public static function obce(): array
    {
        if (self::$obce === null) {
            $list = json_decode((string) file_get_contents(MCP_ROOT . '/obce.json'), true) ?: [];
            self::$obce = [];
            foreach ($list as $o) {
                if (is_file(self::path($o['obec']))) {
                    self::$obce[$o['obec']] = $o;
                }
            }
        }
        return self::$obce;
    }

    public static function path(string $obec): string
    {
        $local = defined('MCP_DATA') ? MCP_DATA : [];
        return $local[$obec] ?? MCP_ROOT . '/data/' . $obec . '.sqlite';
    }

    public static function exists(string $obec): bool
    {
        return isset(self::obce()[$obec]);
    }

    public static function db(string $obec): PDO
    {
        if (!self::exists($obec)) {
            throw new ToolError('Neznámá obec „' . $obec . '“. Dostupné: ' . implode(', ', array_keys(self::obce())) . '.');
        }
        if (!isset(self::$db[$obec])) {
            $db = new PDO('sqlite:' . self::path($obec), null, null,
                [PDO::SQLITE_ATTR_OPEN_FLAGS => PDO::SQLITE_OPEN_READONLY]);
            $db->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
            $db->setAttribute(PDO::ATTR_DEFAULT_FETCH_MODE, PDO::FETCH_ASSOC);
            self::$db[$obec] = $db;
        }
        return self::$db[$obec];
    }

    /** Metadata obce z tabulky meta; JSON hodnoty dekódované. */
    public static function meta(string $obec): array
    {
        if (!isset(self::$meta[$obec])) {
            $m = [];
            foreach (self::db($obec)->query('SELECT klic, hodnota FROM meta') as $r) {
                $v = json_decode($r['hodnota'], true);
                $m[$r['klic']] = $v === null && $r['hodnota'] !== 'null' ? $r['hodnota'] : $v;
            }
            self::$meta[$obec] = $m;
        }
        return self::$meta[$obec];
    }

    public static function rows(string $obec, string $sql, array $args = []): array
    {
        $st = self::db($obec)->prepare($sql);
        $st->execute($args);
        return $st->fetchAll();
    }

    public static function value(string $obec, string $sql, array $args = [])
    {
        $st = self::db($obec)->prepare($sql);
        $st->execute($args);
        return $st->fetchColumn();
    }

    /** Odkaz na jednání na portálu obce (stránka zastupitelstva nebo rady rozbalená na zasedání). */
    public static function portalLink(string $obec, string $jednaniId): string
    {
        $web = self::meta($obec)['web'];
        [$organ, $rest] = explode('-', $jednaniId, 2) + [1 => ''];
        return $web . ($organ === 'RO' ? '/zapisy.html?ro=' : '/zastupitelstvo.html?zo=') . rawurlencode($rest);
    }

    public static function videoLink(?string $vid, ?int $t): ?string
    {
        return $vid ? 'https://youtu.be/' . rawurlencode($vid) . ($t ? '?t=' . $t : '') : null;
    }
}

/** Chyba, kterou má vidět model (špatný parametr, chybějící data) — ne pád serveru. */
final class ToolError extends RuntimeException
{
}
