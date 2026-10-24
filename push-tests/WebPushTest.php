<?php
declare(strict_types=1);

require_once __DIR__ . '/../push/lib/WebPush.php';
require_once __DIR__ . '/../push/lib/Store.php';
require_once __DIR__ . '/lib/webpush-client.php';

Test::case('zpráva se zašifruje tak, že ji prohlížeč rozšifruje', function (): void {
    $ua = WebPush::generateVapid();
    $uaPublic = WebPush::b64urlDecode($ua['public']);
    $auth = random_bytes(16);

    $text = json_encode(['title' => 'Ochutnávka vína', 'body' => 'Přijímáme vzorky, žluťoučký kůň'], JSON_UNESCAPED_UNICODE);
    $body = WebPush::encrypt((string) $text, $uaPublic, $auth);

    Test::eq($text, webpushDecrypt($body, $ua['private_pem'], $uaPublic, $auth));
    Test::eq(4096, unpack('N', substr($body, 16, 4))[1], 'velikost záznamu v hlavičce');
    Test::eq(65, ord($body[20]), 'délka klíče odesílatele');
});

Test::case('stejná zpráva se pokaždé zašifruje jinak', function (): void {
    $ua = WebPush::generateVapid();
    $pub = WebPush::b64urlDecode($ua['public']);
    $auth = random_bytes(16);
    Test::true(WebPush::encrypt('ahoj', $pub, $auth) !== WebPush::encrypt('ahoj', $pub, $auth));
});

Test::case('šifrování odpovídá vzoru z RFC 8291 (příloha A)', function (): void {
    // Veřejný vzor: stejné vstupy musí dát stejné bajty, jinak by zprávu
    // nepřijal žádný skutečný prohlížeč.
    $uaPublic = WebPush::b64urlDecode('BCVxsr7N_eNgVRqvHtD0zTZsEc6-VV-JvLexhqUzORcxaOzi6-AYWXvTBHm4bjyPjs7Vd8pZGH6SRpkNtoIAiw4');
    $auth = WebPush::b64urlDecode('BTBZMqHH6r4Tts7J_aSIgg');
    $salt = WebPush::b64urlDecode('DGv6ra1nlYgDCS1FRnbzlw');
    $asPrivate = WebPush::b64urlDecode('yfWPiYE-n46HLnH0KqZOF1fJJU3MYrct3AELtAQ-oRw');
    $asPublic = WebPush::b64urlDecode('BP4z9KsN6nGRTbVYI_c7VJSPQTBtkgcy27mlmlMoZIIgDll6e3vCYLocInmYWAmS6TlzAC8wEqKK6PBru3jl7A8');

    // PEM z holého soukromého čísla: struktura SEC1 s vloženým veřejným klíčem.
    $sec1 = "\x30\x77\x02\x01\x01\x04\x20" . $asPrivate
        . "\xa0\x0a\x06\x08\x2a\x86\x48\xce\x3d\x03\x01\x07"
        . "\xa1\x44\x03\x42\x00" . $asPublic;
    $pem = "-----BEGIN EC PRIVATE KEY-----\n" . chunk_split(base64_encode($sec1), 64, "\n") . "-----END EC PRIVATE KEY-----\n";

    $body = WebPush::encrypt('When I grow up, I want to be a watermelon', $uaPublic, $auth, $pem, $salt);

    $expected = 'DGv6ra1nlYgDCS1FRnbzlwAAEABBBP4z9KsN6nGRTbVYI_c7VJSPQTBtkgcy27mlmlMoZIIgDll6e3vCYLocInmYWAmS6TlzAC8wEqKK6PBru3jl7A_yl95bQpu6cVPTpK4Mqgkf1CXztLVBSt2Ks3oZwbuwXPXLWyouBWLVWGNWQexSgSxsj_Qulcy4a-fN';
    Test::eq($expected, WebPush::b64urlEncode($body));
});

Test::case('hlavička VAPID je JWT podepsaný ES256 pro správný původ', function (): void {
    $vapid = WebPush::generateVapid();
    $header = WebPush::vapidHeader('https://fcm.googleapis.com/fcm/send/abc', 'mailto:a@b.cz', $vapid, 1000);

    Test::true(preg_match('/^vapid t=([\w-]+)\.([\w-]+)\.([\w-]+), k=' . preg_quote($vapid['public'], '/') . '$/', $header, $m) === 1, 'tvar');
    $claims = json_decode(WebPush::b64urlDecode($m[2]), true);
    Test::eq('https://fcm.googleapis.com', $claims['aud']);
    Test::eq(1000 + 43200, $claims['exp']);
    Test::eq('mailto:a@b.cz', $claims['sub']);
    Test::eq(64, strlen(WebPush::b64urlDecode($m[3])), 'podpis jsou dvě čísla po 32 bajtech');

    // Podpis musí ověřit veřejný klíč ze stejného páru.
    Test::eq('mailto:a@b.cz', webpushVerifyVapid($header, $vapid['public'])['sub'] ?? null);
    Test::eq(null, webpushVerifyVapid($header, WebPush::generateVapid()['public']), 'cizí klíč neověří');
});

Test::case('posílat se smí jen na https a jen na známé push služby', function (): void {
    Test::true(WebPush::endpointAllowed('https://fcm.googleapis.com/fcm/send/x'));
    Test::true(WebPush::endpointAllowed('https://updates.push.services.mozilla.com/wpush/v2/x'));
    Test::true(WebPush::endpointAllowed('https://web.push.apple.com/x'));
    Test::true(!WebPush::endpointAllowed('http://fcm.googleapis.com/x'), 'ne http');
    Test::true(!WebPush::endpointAllowed('https://evil.example.com/x'), 'ne cizí server');
    Test::true(!WebPush::endpointAllowed('https://googleapis.com.evil.com/x'), 'ne podvržená přípona');
    Test::true(!WebPush::endpointAllowed('https://localhost/x'), 'ne interní adresa');
    Test::true(!WebPush::endpointAllowed('file:///etc/passwd'));
});

Test::case('klíč VAPID se vytvoří jednou a pak se nemění', function (): void {
    $db = testDb();
    $first = WebPush::vapid($db);
    Test::eq(65, strlen(WebPush::b64urlDecode($first['public'])), 'veřejný klíč má 65 bajtů');
    Test::eq($first, WebPush::vapid($db), 'druhé čtení');
});
