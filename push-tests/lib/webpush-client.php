<?php
declare(strict_types=1);

/**
 * Strana prohlížeče pro testy Web Push: rozšifrování zprávy podle RFC 8291
 * a ověření podpisu VAPID. Je psaná odděleně od app/WebPush.php, aby test
 * nesrovnával kód sám se sebou.
 */

require_once __DIR__ . '/../../push/lib/WebPush.php';

function webpushDecrypt(string $body, string $uaPrivatePem, string $uaPublic, string $authSecret): string
{
    $salt = substr($body, 0, 16);
    $idLen = ord($body[20]);
    $asPublic = substr($body, 21, $idLen);
    $rest = substr($body, 21 + $idLen);
    $cipher = substr($rest, 0, -16);
    $tag = substr($rest, -16);

    $der = (string) hex2bin('3059301306072a8648ce3d020106082a8648ce3d030107034200') . $asPublic;
    $peer = openssl_pkey_get_public("-----BEGIN PUBLIC KEY-----\n" . chunk_split(base64_encode($der), 64, "\n") . "-----END PUBLIC KEY-----\n");
    $shared = openssl_pkey_derive($peer, openssl_pkey_get_private($uaPrivatePem), 32);

    $prk = hash_hkdf('sha256', $shared, 32, "WebPush: info\0" . $uaPublic . $asPublic, $authSecret);
    $cek = hash_hkdf('sha256', $prk, 16, "Content-Encoding: aes128gcm\0", $salt);
    $nonce = hash_hkdf('sha256', $prk, 12, "Content-Encoding: nonce\0", $salt);

    $plain = openssl_decrypt($cipher, 'aes-128-gcm', $cek, OPENSSL_RAW_DATA, $nonce, $tag);
    return $plain === false ? '' : rtrim($plain, "\x02");
}

/**
 * Ověří hlavičku Authorization: vapid t=…, k=… proti veřejnému klíči serveru.
 *
 * @return array<string, mixed>|null  claimy, když podpis sedí
 */
function webpushVerifyVapid(string $header, string $expectedPublic): ?array
{
    if (preg_match('/^vapid t=([\w-]+)\.([\w-]+)\.([\w-]+), k=([\w-]+)$/', $header, $m) !== 1 || $m[4] !== $expectedPublic) {
        return null;
    }

    $raw = WebPush::b64urlDecode($m[3]);
    if (strlen($raw) !== 64) {
        return null;
    }
    $enc = static function (string $n): string {
        $n = ltrim($n, "\0");
        if ($n === '' || (ord($n[0]) & 0x80)) {
            $n = "\0" . $n;
        }
        return "\x02" . chr(strlen($n)) . $n;
    };
    $body = $enc(substr($raw, 0, 32)) . $enc(substr($raw, 32));
    $der = "\x30" . chr(strlen($body)) . $body;

    $pub = WebPush::b64urlDecode($m[4]);
    $spki = "-----BEGIN PUBLIC KEY-----\n"
        . chunk_split(base64_encode((string) hex2bin('3059301306072a8648ce3d020106082a8648ce3d030107034200') . $pub), 64, "\n")
        . "-----END PUBLIC KEY-----\n";

    if (openssl_verify($m[1] . '.' . $m[2], $der, $spki, OPENSSL_ALGO_SHA256) !== 1) {
        return null;
    }
    $claims = json_decode(WebPush::b64urlDecode($m[2]), true);
    return is_array($claims) ? $claims : null;
}
