<?php
declare(strict_types=1);

/**
 * Web Push bez knihoven: šifrování zprávy (RFC 8291, aes128gcm), podpis
 * serveru (VAPID, RFC 8292) a odeslání. Stačí k tomu openssl a curl,
 * takže to jede i na sdíleném hostingu bez Composeru.
 */
final class WebPush
{
    /** Hlavička DER struktury SubjectPublicKeyInfo pro veřejný klíč P-256. */
    private const SPKI_PREFIX = '3059301306072a8648ce3d020106082a8648ce3d030107034200';

    /** Kam smí server posílat. Adresu předplatného dodává prohlížeč, ale ověřit se musí. */
    private const ALLOWED_HOSTS = [
        'fcm.googleapis.com',          // Chrome, Android (FCM)
        'push.services.mozilla.com',   // Firefox
        'push.apple.com',              // Safari
        'notify.windows.com',          // Edge na Windows
    ];

    public static function b64urlEncode(string $raw): string
    {
        return rtrim(strtr(base64_encode($raw), '+/', '-_'), '=');
    }

    public static function b64urlDecode(string $text): string
    {
        $raw = base64_decode(strtr($text, '-_', '+/') . str_repeat('=', (4 - strlen($text) % 4) % 4), true);
        return $raw === false ? '' : $raw;
    }

    /** Je to veřejný klíč P-256, který openssl přijme (ne jen 65 bajtů s 0x04 na začátku)? */
    public static function validPublicKey(string $raw): bool
    {
        return strlen($raw) === 65 && $raw[0] === "\x04" && openssl_pkey_get_public(self::spkiPem($raw)) !== false;
    }

    /** Smí se na tuhle adresu posílat? Jen https a jen známé služby. */
    public static function endpointAllowed(string $endpoint): bool
    {
        $parts = parse_url($endpoint);
        if (!is_array($parts) || !isset($parts['host'])) {
            return false;
        }
        if (self::allowAnyEndpoint()) {
            return in_array($parts['scheme'] ?? '', ['http', 'https'], true);
        }
        if (($parts['scheme'] ?? '') !== 'https') {
            return false;
        }
        $host = strtolower((string) $parts['host']);
        foreach (self::ALLOWED_HOSTS as $allowed) {
            if ($host === $allowed || str_ends_with($host, '.' . $allowed)) {
                return true;
            }
        }
        return false;
    }

    /** Jen pro testy a vývoj; z configu ani z webu se to zapnout nedá. */
    private static function allowAnyEndpoint(): bool
    {
        return getenv('JAKSEMAME_PUSH_ALLOW_ANY') === '1';
    }

    /**
     * Nový klíčový pár VAPID.
     *
     * @return array{public: string, private_pem: string}
     */
    public static function generateVapid(): array
    {
        [$pem, $public] = self::newEcKey();
        return ['public' => self::b64urlEncode($public), 'private_pem' => $pem];
    }

    /**
     * Klíč serveru; při prvním použití ho vytvoří a uloží.
     *
     * @return array{public: string, private_pem: string}
     */
    public static function vapid(PDO $db): array
    {
        $read = static function () use ($db): ?array {
            $row = $db->query('SELECT public_key, private_pem FROM push_vapid WHERE id = 1')->fetch(PDO::FETCH_ASSOC);
            return $row === false ? null : $row;
        };
        $row = $read();
        if ($row === null) {
            $new = self::generateVapid();
            // Dva současné první požadavky: druhý nevloží nic a přečte ten první.
            $db->prepare('INSERT OR IGNORE INTO push_vapid (id, public_key, private_pem) VALUES (1, ?, ?)')
                ->execute([$new['public'], $new['private_pem']]);
            $row = $read();
        }
        return ['public' => (string) $row['public_key'], 'private_pem' => (string) $row['private_pem']];
    }

    /**
     * Zašifruje zprávu pro jedno předplatné.
     *
     * Náhodné vstupy jdou předat zvenku jen kvůli testu se vzorem z RFC 8291.
     *
     * @param string $uaPublic  veřejný klíč prohlížeče, 65 bajtů
     * @param string $authSecret  tajemství předplatného, 16 bajtů
     * @param ?string $asPrivatePem  klíč odesílatele (jednorázový)
     * @param ?string $salt  16 bajtů
     * @return string  tělo požadavku
     */
    public static function encrypt(
        string $payload,
        string $uaPublic,
        string $authSecret,
        ?string $asPrivatePem = null,
        ?string $salt = null
    ): string {
        if (strlen($uaPublic) !== 65 || $uaPublic[0] !== "\x04" || strlen($authSecret) < 16) {
            throw new InvalidArgumentException('Neplatné předplatné.');
        }

        if ($asPrivatePem === null) {
            [$asPrivatePem, $asPublic] = self::newEcKey();
        } else {
            $asPublic = self::publicFromPem($asPrivatePem);
        }
        $salt ??= random_bytes(16);

        $peer = openssl_pkey_get_public(self::spkiPem($uaPublic));
        $own = openssl_pkey_get_private($asPrivatePem);
        if ($peer === false || $own === false) {
            throw new RuntimeException('Klíč se nepodařilo načíst.');
        }
        $shared = openssl_pkey_derive($peer, $own, 32);
        if ($shared === false) {
            throw new RuntimeException('Dohoda klíče selhala.');
        }

        $prk = hash_hkdf('sha256', $shared, 32, "WebPush: info\0" . $uaPublic . $asPublic, $authSecret);
        $cek = hash_hkdf('sha256', $prk, 16, "Content-Encoding: aes128gcm\0", $salt);
        $nonce = hash_hkdf('sha256', $prk, 12, "Content-Encoding: nonce\0", $salt);

        // Jeden záznam; bajt 0x02 na konci značí poslední záznam.
        $tag = '';
        $cipher = openssl_encrypt($payload . "\x02", 'aes-128-gcm', $cek, OPENSSL_RAW_DATA, $nonce, $tag, '', 16);
        if ($cipher === false) {
            throw new RuntimeException('Šifrování selhalo.');
        }

        return $salt . pack('N', 4096) . chr(strlen($asPublic)) . $asPublic . $cipher . $tag;
    }

    /**
     * Hlavička Authorization podle VAPID.
     *
     * @param array{public: string, private_pem: string} $vapid
     */
    public static function vapidHeader(string $endpoint, string $subject, array $vapid, ?int $now = null): string
    {
        $parts = parse_url($endpoint);
        $audience = ($parts['scheme'] ?? 'https') . '://' . ($parts['host'] ?? '')
            . (isset($parts['port']) ? ':' . $parts['port'] : '');

        $head = self::b64urlEncode((string) json_encode(['typ' => 'JWT', 'alg' => 'ES256']));
        $claims = self::b64urlEncode((string) json_encode([
            'aud' => $audience,
            'exp' => ($now ?? time()) + 12 * 3600,
            'sub' => $subject,
        ], JSON_UNESCAPED_SLASHES));

        $signed = $head . '.' . $claims;
        $key = openssl_pkey_get_private($vapid['private_pem']);
        if ($key === false || !openssl_sign($signed, $der, $key, OPENSSL_ALGO_SHA256)) {
            throw new RuntimeException('Podpis VAPID selhal.');
        }

        return 'vapid t=' . $signed . '.' . self::b64urlEncode(self::derToRaw($der)) . ', k=' . $vapid['public'];
    }

    /**
     * Pošle zprávu jednomu zařízení.
     *
     * @param array{endpoint: string, p256dh: string, auth: string} $sub
     * @return array{status: int, ok: bool, gone: bool, detail: string}
     */
    public static function send(PDO $db, array $sub, string $payload, string $subject, int $ttl = 86400): array
    {
        if (!self::endpointAllowed($sub['endpoint'])) {
            return ['status' => 0, 'ok' => false, 'gone' => true, 'detail' => 'adresa push služby není povolená'];
        }

        $body = self::encrypt($payload, self::b64urlDecode($sub['p256dh']), self::b64urlDecode($sub['auth']));

        $ch = curl_init($sub['endpoint']);
        curl_setopt_array($ch, [
            CURLOPT_POST => true,
            CURLOPT_POSTFIELDS => $body,
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_TIMEOUT => 15,
            CURLOPT_CONNECTTIMEOUT => 8,
            CURLOPT_FOLLOWLOCATION => false,
            CURLOPT_PROTOCOLS => self::allowAnyEndpoint() ? (CURLPROTO_HTTP | CURLPROTO_HTTPS) : CURLPROTO_HTTPS,
            CURLOPT_HTTPHEADER => [
                'Content-Encoding: aes128gcm',
                'Content-Type: application/octet-stream',
                'TTL: ' . $ttl,
                // S „normal“ Android v úsporném režimu (Doze) zprávu drží, dokud se telefon
                // neprobudí, takže upozornění na nový článek může dorazit pozdě nebo vůbec.
                'Urgency: high',
                'Authorization: ' . self::vapidHeader($sub['endpoint'], $subject, self::vapid($db)),
            ],
        ]);
        $response = curl_exec($ch);
        $status = (int) curl_getinfo($ch, CURLINFO_RESPONSE_CODE);
        $detail = $response === false ? curl_error($ch) : substr(trim((string) $response), 0, 200);
        curl_close($ch);

        return [
            'status' => $status,
            'ok' => $status >= 200 && $status < 300,
            // 404 a 410: předplatné je pryč (odinstalovaný prohlížeč, odvolané povolení).
            'gone' => $status === 404 || $status === 410,
            // Co o chybě řekla push služba; pomůže při hledání příčiny.
            'detail' => $detail,
        ];
    }

    /** @return array{0: string, 1: string}  [PEM soukromého klíče, veřejný klíč 65 bajtů] */
    private static function newEcKey(): array
    {
        $opts = ['curve_name' => 'prime256v1', 'private_key_type' => OPENSSL_KEYTYPE_EC];
        $key = openssl_pkey_new($opts);

        // Openssl bez konfiguračního souboru (typicky PHP na Windows) klíč nevytvoří.
        // Stačí mu prázdná konfigurace, tak ji podstrčíme.
        if ($key === false) {
            $conf = sys_get_temp_dir() . DIRECTORY_SEPARATOR . 'jaksemame-openssl-' . md5(__FILE__) . '.cnf';
            if (!is_file($conf)) {
                file_put_contents($conf, "[req]\ndefault_bits = 2048\ndistinguished_name = dn\n[dn]\n");
            }
            $opts['config'] = $conf;
            $key = openssl_pkey_new($opts);
        }

        if ($key === false || !openssl_pkey_export($key, $pem, null, isset($opts['config']) ? ['config' => $opts['config']] : [])) {
            throw new RuntimeException('Nepodařilo se vytvořit klíč (openssl).');
        }
        return [$pem, self::publicFromPem($pem)];
    }

    private static function publicFromPem(string $pem): string
    {
        $key = openssl_pkey_get_private($pem);
        $ec = $key === false ? false : openssl_pkey_get_details($key);
        if ($ec === false || !isset($ec['ec']['x'], $ec['ec']['y'])) {
            throw new RuntimeException('Klíč se nepodařilo přečíst.');
        }
        return "\x04" . str_pad($ec['ec']['x'], 32, "\0", STR_PAD_LEFT) . str_pad($ec['ec']['y'], 32, "\0", STR_PAD_LEFT);
    }

    private static function spkiPem(string $rawPublic): string
    {
        $der = (string) hex2bin(self::SPKI_PREFIX) . $rawPublic;
        return "-----BEGIN PUBLIC KEY-----\n" . chunk_split(base64_encode($der), 64, "\n") . "-----END PUBLIC KEY-----\n";
    }

    /** Podpis ECDSA z openssl je DER; JWT chce dvě 32bajtová čísla za sebou. */
    private static function derToRaw(string $der): string
    {
        $pos = 2;
        if (ord($der[1]) & 0x80) {
            $pos += ord($der[1]) & 0x7f;
        }
        $out = '';
        for ($i = 0; $i < 2; $i++) {
            $len = ord($der[$pos + 1]);
            $int = substr($der, $pos + 2, $len);
            $pos += 2 + $len;
            $out .= str_pad(ltrim($int, "\0"), 32, "\0", STR_PAD_LEFT);
        }
        return $out;
    }
}
