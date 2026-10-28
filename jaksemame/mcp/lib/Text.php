<?php
declare(strict_types=1);

/**
 * Hledání bez diakritiky a se skloňováním. Texty v datech mají sloupec `norm`
 * (vyrábí mcp_export.py): malá písmena bez diakritiky, interpunkce jako mezera,
 * na začátku mezera, znak po znaku stejně dlouhý jako text. Hledá se od začátku slova
 * zkráceným kmenem („chodníky“ → „ chodnik“), takže projde i „chodníku“, „chodníků“.
 */
final class Text
{
    private const FOLD = [
        'á' => 'a', 'ä' => 'a', 'ą' => 'a', 'č' => 'c', 'ć' => 'c', 'ď' => 'd', 'é' => 'e', 'ě' => 'e',
        'ę' => 'e', 'ë' => 'e', 'í' => 'i', 'ľ' => 'l', 'ĺ' => 'l', 'ł' => 'l', 'ň' => 'n', 'ń' => 'n',
        'ó' => 'o', 'ô' => 'o', 'ö' => 'o', 'ő' => 'o', 'ř' => 'r', 'ŕ' => 'r', 'š' => 's', 'ś' => 's',
        'ť' => 't', 'ú' => 'u', 'ů' => 'u', 'ü' => 'u', 'ű' => 'u', 'ý' => 'y', 'ž' => 'z', 'ź' => 'z',
        'ż' => 'z',
    ];

    /** Slova, podle kterých hledat nemá smysl. */
    private const STOP = [
        'a', 'i', 'o', 'u', 'v', 've', 'na', 'se', 'si', 'z', 'ze', 'k', 'ke', 's', 'do', 'od', 'po',
        'pro', 'za', 'je', 'to', 'ta', 'ten', 'co', 'kdo', 'jak', 'kdy', 'kde', 'proc', 'ktery', 'ktera',
        'ktere', 'nebo', 'ale', 'by', 'byl', 'byla', 'bylo', 'jsou', 'obec', 'obce', 'obci',
    ];

    public static function norm(string $s): string
    {
        $s = strtr(mb_strtolower($s, 'UTF-8'), self::FOLD);
        return trim((string) preg_replace('/[^\p{L}\p{N}]+/u', ' ', $s));
    }

    /** Hledané kmeny z dotazu (nejvýš 8): dlouhá slova bez koncovky, čísla celá. */
    public static function terms(string $q): array
    {
        $out = [];
        foreach (explode(' ', self::norm($q)) as $w) {
            if ($w === '' || in_array($w, self::STOP, true) || (mb_strlen($w) < 2 && !ctype_digit($w))) {
                continue;
            }
            $out[] = self::stem($w);
        }
        return array_slice(array_values(array_unique($out)), 0, 8);
    }

    public static function stem(string $w): string
    {
        $n = mb_strlen($w);
        if (ctype_digit($w) || $n < 5) {
            return $w;
        }
        if ($n >= 7) {
            return mb_substr($w, 0, $n - 2);
        }
        // krátká slova jen bez koncové samohlásky („škola“ → „skol“); „prvek“ zůstane, jinak by chytal „první“
        return preg_match('/[aeiouy]$/', $w) ? mb_substr($w, 0, $n - 1) : $w;
    }

    /** Vzor pro LIKE nad sloupcem norm: kmen od začátku slova. */
    public static function like(string $term): string
    {
        return '% ' . addcslashes($term, '%_\\') . '%';
    }

    /** Kolik kmenů se v normalizovaném textu najde od začátku slova. */
    public static function hits(string $norm, array $terms): int
    {
        $n = 0;
        foreach ($terms as $t) {
            if (str_contains($norm, ' ' . $t)) {
                $n++;
            }
        }
        return $n;
    }

    /**
     * Úryvek kolem prvního nálezu. `norm` začíná mezerou navíc, takže nález „ kmen“
     * na pozici p v norm je v původním textu na pozici p.
     */
    public static function snippet(string $text, string $norm, array $terms, int $len = 320): string
    {
        if (mb_strlen($text) <= $len) {
            return $text;
        }
        $pos = null;
        foreach ($terms as $t) {
            $p = mb_strpos($norm, ' ' . $t);
            if ($p !== false && ($pos === null || $p < $pos)) {
                $pos = $p;
            }
        }
        $start = max(0, ($pos ?? 0) - 100);
        if ($start > 0) {
            $space = mb_strpos($text, ' ', $start);
            $start = $space !== false && $space < $start + 30 ? $space + 1 : $start;
        }
        $cut = mb_substr($text, $start, $len);
        $space = mb_strrpos($cut, ' ');
        if ($start + $len < mb_strlen($text) && $space !== false && $space > $len - 40) {
            $cut = mb_substr($cut, 0, $space);
        }
        return ($start > 0 ? '…' : '') . $cut . ($start + mb_strlen($cut) < mb_strlen($text) ? '…' : '');
    }

    public static function cut(string $text, int $len): string
    {
        return mb_strlen($text) <= $len ? $text : rtrim(mb_substr($text, 0, $len)) . '…';
    }
}
