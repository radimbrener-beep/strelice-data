<?php
declare(strict_types=1);

/**
 * Protokol MCP (JSON-RPC 2.0) bez stavu: každý POST se vyřídí sám, žádné sezení ani SSE.
 * Server nabízí nástroje (Tools) a pár hotových promptů; jen čte.
 */
final class Mcp
{
    public const VERSIONS = ['2025-11-25', '2025-06-18', '2025-03-26', '2024-11-05'];

    public const INSTRUCTIONS = <<<'TXT'
        Data občanského portálu jaksemame.cz o obcích (zatím Střelice a Ostopovice u Brna): usnesení
        a zápisy zastupitelstva a rady, přepisy diskuzí ze zastupitelstva, rozpočet, investice, zakázky
        a dotace spolkům. Portál provozuje soukromá osoba, ne obec — nejde o oficiální stanovisko obce.

        Pravidla odpovědí:
        1. Odpovídej česky, pokud uživatel nepíše jinak.
        2. Fakta ber jen z výsledků nástrojů. U každého faktu uveď datum a zdroj (odkaz na PDF zápisu,
           video nebo stránku portálu z výsledku). Když data nestačí, řekni to; nic nedomýšlej.
        3. Odděl fakta od vlastního výkladu. Buď politicky neutrální, nehodnoť lidi ani kandidátky;
           hlasování a vystoupení zastupitelů popisuj věcně.
        4. Přepisy diskuzí jsou upravené a zkrácené, ne doslovné — necituj je jako přesná slova.
           Občané jsou anonymní a soukromé osoby v zápisech mají jen iniciály; nepokoušej se je identifikovat.
        5. Částky z usnesení jsou vytažené automaticky; u důležitých odkaž na PDF k ověření.

        Postup: nástroj obce řekne, co je o které obci k dispozici. Pak hledat (fulltext v usneseních
        i diskuzích, s filtrem mluvci pro „kdo co říkal“), jednani (celé zasedání), diskuze (repliky
        k bodu), rozpocet, investice, zakazky, vyberova_rizeni (kdo se do soutěže přihlásil a za kolik),
        dotace. Při hledání zkoušej synonyma a obecnější slova.
        TXT;

    /** Odpověď na jednu zprávu; null u notifikace (bez odpovědi). */
    public static function handle($msg, ?string $client): ?array
    {
        if (!is_array($msg) || ($msg['jsonrpc'] ?? null) !== '2.0' || !is_string($msg['method'] ?? null)) {
            if (is_array($msg) && !isset($msg['method']) && (isset($msg['result']) || isset($msg['error']))) {
                return null;  // odpověď klienta na náš požadavek — žádné neposíláme
            }
            return self::error($msg['id'] ?? null, -32600, 'Neplatný požadavek JSON-RPC.');
        }
        $id = $msg['id'] ?? null;
        $isNotification = !array_key_exists('id', $msg);
        $method = $msg['method'];
        $params = is_array($msg['params'] ?? null) ? $msg['params'] : [];

        if ($isNotification) {
            return null;
        }
        switch ($method) {
            case 'initialize':
                $want = is_string($params['protocolVersion'] ?? null) ? $params['protocolVersion'] : '';
                $info = $params['clientInfo'] ?? [];
                Log::call('initialize', null, null, null, 0,
                    trim(($info['name'] ?? '') . ' ' . ($info['version'] ?? '')) ?: $client, null);
                return self::result($id, [
                    'protocolVersion' => in_array($want, self::VERSIONS, true) ? $want : self::VERSIONS[0],
                    'capabilities' => ['tools' => ['listChanged' => false], 'prompts' => ['listChanged' => false]],
                    'serverInfo' => ['name' => 'jaksemame', 'title' => 'Jak se máme — data obcí', 'version' => '1.0.0',
                        'websiteUrl' => 'https://jaksemame.cz/mcp'],
                    'instructions' => self::INSTRUCTIONS,
                ]);
            case 'ping':
                return self::result($id, new stdClass());
            case 'tools/list':
                return self::result($id, ['tools' => Tools::definitions()]);
            case 'tools/call':
                return self::callTool($id, $params, $client);
            case 'prompts/list':
                return self::result($id, ['prompts' => Prompts::definitions()]);
            case 'prompts/get':
                try {
                    return self::result($id, Prompts::get((string) ($params['name'] ?? ''), (array) ($params['arguments'] ?? [])));
                } catch (InvalidArgumentException $e) {
                    return self::error($id, -32602, $e->getMessage());
                }
            case 'resources/list':
                return self::result($id, ['resources' => []]);
            case 'resources/templates/list':
                return self::result($id, ['resourceTemplates' => []]);
        }
        return self::error($id, -32601, 'Neznámá metoda: ' . $method);
    }

    private static function callTool($id, array $params, ?string $client): array
    {
        $name = (string) ($params['name'] ?? '');
        $args = is_array($params['arguments'] ?? null) ? $params['arguments'] : [];
        $t0 = microtime(true);
        try {
            [$data, $count] = Tools::call($name, $args);
            Log::call('tools/call', $name, $args, $count, (int) ((microtime(true) - $t0) * 1000), $client, null);
            return self::result($id, [
                'content' => [['type' => 'text', 'text' => json_encode($data, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES)]],
                'structuredContent' => $data,
            ]);
        } catch (InvalidArgumentException $e) {
            Log::call('tools/call', $name, $args, null, 0, $client, $e->getMessage());
            return self::error($id, -32602, $e->getMessage());
        } catch (ToolError $e) {
            Log::call('tools/call', $name, $args, 0, (int) ((microtime(true) - $t0) * 1000), $client, $e->getMessage());
            return self::result($id, ['content' => [['type' => 'text', 'text' => $e->getMessage()]], 'isError' => true]);
        } catch (Throwable $e) {
            error_log('MCP ' . $name . ': ' . $e->getMessage());
            Log::call('tools/call', $name, $args, null, 0, $client, get_class($e) . ': ' . $e->getMessage());
            return self::result($id, ['content' => [['type' => 'text', 'text' => 'Chyba serveru při čtení dat, zkus to prosím znovu.']], 'isError' => true]);
        }
    }

    public static function result($id, $result): array
    {
        return ['jsonrpc' => '2.0', 'id' => $id, 'result' => $result];
    }

    public static function error($id, int $code, string $message): array
    {
        return ['jsonrpc' => '2.0', 'id' => $id, 'error' => ['code' => $code, 'message' => $message]];
    }
}
