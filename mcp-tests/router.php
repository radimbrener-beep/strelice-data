<?php
// Lokální server: php -S localhost:8790 mcp-tests/router.php  → http://localhost:8790/mcp
$path = parse_url($_SERVER['REQUEST_URI'], PHP_URL_PATH);
if ($path === '/mcp' || $path === '/mcp/') {
    require __DIR__ . '/../jaksemame/mcp/index.php';
    return true;
}
http_response_code(404);
echo 'Jen /mcp';
