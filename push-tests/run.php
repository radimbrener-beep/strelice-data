<?php
declare(strict_types=1);

// Spouštěč testů upozornění bez PHPUnit: php push-tests/run.php

// testy počítají se všemi druhy upozornění, ať jsou stejné pro každou obec
define('PUSH_SITE', 'Testovací portál');
define('PUSH_SUBJECT', 'https://example.cz');
define('PUSH_TOPICS', ['rada', 'zastupitelstvo', 'portal']);
final class Test
{
    public static int $failed = 0;
    public static int $passed = 0;

    public static function case(string $name, callable $fn): void
    {
        try {
            $fn();
            self::$passed++;
            echo "  ok    $name\n";
        } catch (Throwable $e) {
            self::$failed++;
            echo "  CHYBA $name\n        " . $e->getMessage() . "\n";
        }
    }

    public static function eq(mixed $expected, mixed $actual, string $what = ''): void
    {
        if ($expected !== $actual) {
            throw new RuntimeException(($what !== '' ? "$what: " : '') . 'čekáno ' . var_export($expected, true) . ', je ' . var_export($actual, true));
        }
    }

    public static function true(bool $value, string $what = 'podmínka'): void
    {
        if (!$value) {
            throw new RuntimeException("$what neplatí");
        }
    }
}

/** Čerstvá databáze v dočasné složce. */
function testDb(): PDO
{
    $dir = sys_get_temp_dir() . DIRECTORY_SEPARATOR . 'jaksemame-push-' . bin2hex(random_bytes(6));
    mkdir($dir);
    return Store::open($dir);
}

foreach (glob(__DIR__ . '/*Test.php') ?: [] as $file) {
    echo basename($file) . "\n";
    require $file;
}
echo "\n" . Test::$passed . ' prošlo, ' . Test::$failed . " selhalo\n";
exit(Test::$failed > 0 ? 1 : 0);
