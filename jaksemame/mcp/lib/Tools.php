<?php
declare(strict_types=1);

/**
 * Nástroje MCP serveru. Všechny jen čtou. Výsledky jsou kompaktní JSON s odkazy na zdroje
 * (PDF zápisu, video, stránka portálu), aby model mohl každé tvrzení doložit.
 * Agregace (součty, žebříčky) dělá server, ne model.
 */
final class Tools
{
    /** Definice pro tools/list. */
    public static function definitions(): array
    {
        $obce = array_keys(Data::obce());
        $obec = ['type' => 'string', 'enum' => $obce, 'description' => 'Obec (zkratka z nástroje obce).'];
        $od = ['type' => 'string', 'description' => 'Od data: rok (2024) nebo datum (2024-05-01).'];
        $do = ['type' => 'string', 'description' => 'Do data: rok (2025) nebo datum (2025-06-30).'];
        $limit = fn(int $def, int $max) => ['type' => 'integer', 'minimum' => 1, 'maximum' => $max,
            'description' => "Kolik položek vrátit (výchozí $def, nejvýš $max)."];
        $ro = ['readOnlyHint' => true, 'destructiveHint' => false, 'idempotentHint' => true, 'openWorldHint' => false];

        $defs = [
            'obce' => [
                'title' => 'Obce a dostupná data',
                'description' => 'Seznam obcí na jaksemame.cz: co o které obci je k dispozici (zastupitelstvo, rada, '
                    . 'přepisy diskuzí, rozpočet, investice, zakázky, dotace), za jaká období, k jakému datu, '
                    . 'seznam zastupitelů a upozornění, jak data číst. Zavolej jako první.',
                'inputSchema' => ['type' => 'object', 'properties' => new stdClass()],
            ],
            'hledat' => [
                'title' => 'Hledat v jednáních',
                'description' => 'Fulltext v usneseních a zápisech zastupitelstva i rady a v přepisech diskuzí '
                    . 'ze zastupitelstva (kdo co říkal). Hledá bez diakritiky a se skloňováním, všechna slova '
                    . 'musí být v textu (když nic, zkusí aspoň některá). Vrací úryvky s odkazem na PDF, video '
                    . 'a stránku portálu. Parametr mluvci zúží diskuzi na konkrétního řečníka (jméno '
                    . 'zastupitele nebo „starosta“); u obcí bez přepisů hledá jeho jméno v textu zápisů. '
                    . 'Zkoušej i synonyma (ČOV / čistírna / kanalizace) a obecnější slova.',
                'inputSchema' => ['type' => 'object', 'properties' => [
                    'dotaz' => ['type' => 'string', 'description' => 'Hledaná slova, např. „chodník Nádražní“.'],
                    'obec' => $obec + ['description' => 'Obec; bez ní se hledá ve všech obcích.'],
                    'zdroj' => ['type' => 'string', 'enum' => ['vse', 'usneseni', 'diskuze'],
                        'description' => 'usneseni = texty usnesení a zápisů, diskuze = přepisy vystoupení, vse = obojí (výchozí).'],
                    'organ' => ['type' => 'string', 'enum' => ['ZO', 'RO'], 'description' => 'ZO = zastupitelstvo, RO = rada obce.'],
                    'mluvci' => ['type' => 'string', 'description' => 'Kdo mluvil, např. „Bartoňová“ nebo „starosta“.'],
                    'tema' => ['type' => 'string', 'description' => 'Téma usnesení, např. „Doprava“, „Školství“.'],
                    'od' => $od, 'do' => $do,
                    'limit' => $limit(10, 30),
                    'strana' => ['type' => 'integer', 'minimum' => 1, 'description' => 'Stránka výsledků (od 1).'],
                ]],
            ],
            'jednani' => [
                'title' => 'Zasedání zastupitelstva a rady',
                'description' => 'Bez id: seznam zasedání (nejnovější první) se shrnutím „V kostce“. S id: celé '
                    . 'zasedání — všechna usnesení s tématem, částkou a hlasováním (u zastupitelstva Střelic '
                    . 'i jmenovitě kdo byl proti / zdržel se), přítomnost, odkazy na PDF a video a přehled '
                    . 'u každého usnesení, zda se k němu diskutovalo. id: „ZO-29“, „RO-103“, „ZO-2026-2“ nebo „posledni“.',
                'inputSchema' => ['type' => 'object', 'required' => ['obec'], 'properties' => [
                    'obec' => $obec,
                    'id' => ['type' => 'string', 'description' => 'Zasedání: „ZO-29“, „RO-103“, „ZO-2026-2“, nebo „posledni“.'],
                    'organ' => ['type' => 'string', 'enum' => ['ZO', 'RO'], 'description' => 'ZO = zastupitelstvo (výchozí u „posledni“), RO = rada.'],
                    'rok' => ['type' => 'integer', 'description' => 'Jen zasedání v daném roce (u seznamu).'],
                    'limit' => $limit(20, 60),
                ]],
            ],
            'diskuze' => [
                'title' => 'Diskuze na zastupitelstvu',
                'description' => 'Kdo co říkal na zastupitelstvu (přepis videozáznamu, upravený do spisovné češtiny, '
                    . 'nedoslovný; občané anonymně). Diskuze se váže k usnesení: bod = číslo usnesení v zápisu '
                    . '(jak ho vrací jednani). Bez bodu vrátí přehled usnesení, ke kterým se diskutovalo. '
                    . 'rozsah „shrnuti“ = zkrácené repliky (výchozí), „cele“ = plné znění. Každý bod má odkaz '
                    . 'do videa na čas. U obcí bez přepisů je rozprava přímo v textu zápisu (nástroj jednani/hledat).',
                'inputSchema' => ['type' => 'object', 'required' => ['obec', 'jednani'], 'properties' => [
                    'obec' => $obec,
                    'jednani' => ['type' => 'string', 'description' => 'Zasedání zastupitelstva: „ZO-29“ nebo „posledni“.'],
                    'bod' => ['type' => 'integer', 'description' => 'Číslo usnesení v zápisu (z přehledu nebo z jednani).'],
                    'rozsah' => ['type' => 'string', 'enum' => ['shrnuti', 'cele']],
                    'mluvci' => ['type' => 'string', 'description' => 'Jen repliky tohoto řečníka.'],
                ]],
            ],
            'rozpocet' => [
                'title' => 'Rozpočet obce',
                'description' => 'Příjmy nebo výdaje obce z výkazu MF (MONITOR) po letech: schválený a upravený '
                    . 'rozpočet a skutečnost. Členění: celkem, druh (daňové / běžné / kapitálové…), oblast '
                    . '(doprava, školství…), paragraf (účel, např. „Silnice“), polozka (druh platby). '
                    . 'hledat filtruje názvy paragrafů a položek. Bez roku vrátí poslední dva roky.',
                'inputSchema' => ['type' => 'object', 'required' => ['obec'], 'properties' => [
                    'obec' => $obec,
                    'strana' => ['type' => 'string', 'enum' => ['vydaje', 'prijmy'], 'description' => 'Výchozí vydaje.'],
                    'cleneni' => ['type' => 'string', 'enum' => ['celkem', 'druh', 'oblast', 'paragraf', 'polozka'],
                        'description' => 'Výchozí oblast u výdajů, druh u příjmů.'],
                    'rok' => ['type' => 'integer'], 'od' => $od, 'do' => $do,
                    'hledat' => ['type' => 'string', 'description' => 'Např. „chodník“, „škola“, „odpad“.'],
                    'limit' => $limit(25, 80),
                ]],
            ],
            'investice' => [
                'title' => 'Investice obce',
                'description' => 'Kapitálové výdaje po letech (kolik obec proinvestovala) a konkrétní investiční '
                    . 'akce: stavby, nákupy pozemků a nemovitostí se zhotovitelem, částkou, datem a zdrojem. '
                    . 'Filtr podle roku, skupiny (Budovy, Komunikace, Chodníky, Voda…) nebo hledaných slov.',
                'inputSchema' => ['type' => 'object', 'required' => ['obec'], 'properties' => [
                    'obec' => $obec,
                    'rok' => ['type' => 'integer'], 'od' => $od, 'do' => $do,
                    'hledat' => ['type' => 'string'],
                    'skupina' => ['type' => 'string', 'description' => 'Skupina akcí (seznam vrací odpověď).'],
                    'min_castka' => ['type' => 'number', 'description' => 'Jen akce od této částky v Kč.'],
                    'razeni' => ['type' => 'string', 'enum' => ['castka', 'datum'], 'description' => 'Výchozí castka.'],
                    'limit' => $limit(15, 60),
                ]],
            ],
            'zakazky' => [
                'title' => 'Zakázky a dodavatelé',
                'description' => 'Komu obec platí: bez parametrů žebříček dodavatelů podle součtu zakázek (dodatky '
                    . 'se počítají do částek, ne do počtu). S dodavatelem celá historie firmy, s hledat zakázky '
                    . 'podle textu. Kde obec dodavatele neuvádí, vrací zakázky z profilu zadavatele. '
                    . 'Kdo se do soutěže přihlásil a za kolik, vrací vyberova_rizeni.',
                'inputSchema' => ['type' => 'object', 'required' => ['obec'], 'properties' => [
                    'obec' => $obec,
                    'dodavatel' => ['type' => 'string', 'description' => 'Část názvu firmy, např. „PORR“.'],
                    'hledat' => ['type' => 'string'],
                    'rok' => ['type' => 'integer'], 'od' => $od, 'do' => $do,
                    'limit' => $limit(15, 60),
                ]],
            ],
            'vyberova_rizeni' => [
                'title' => 'Výběrová řízení a nabídky',
                'description' => 'Zakázky, které obec vypsala na profilu zadavatele: kdo podal nabídku, za jakou cenu '
                    . '(bez DPH), kdo vyhrál, předpokládaná hodnota a stav. Bez filtrů přehled (stavy, počty nabídek, '
                    . 'nejčastější uchazeči) a nejnovější řízení. S firma všechna řízení, kam se firma přihlásila, '
                    . 's id detail jednoho řízení se všemi nabídkami.',
                'inputSchema' => ['type' => 'object', 'required' => ['obec'], 'properties' => [
                    'obec' => $obec,
                    'id' => ['type' => 'string', 'description' => 'Id řízení z výsledku, např. „P26V00000009“ — detail.'],
                    'firma' => ['type' => 'string', 'description' => 'Část názvu uchazeče, např. „Stavby a konstrukce“.'],
                    'hledat' => ['type' => 'string', 'description' => 'Slova v názvu zakázky nebo v názvech uchazečů.'],
                    'stav' => ['type' => 'string', 'enum' => ['zadáno', 'zrušeno', 'probíhá', 'bez výsledku']],
                    'rok' => ['type' => 'integer'], 'od' => $od, 'do' => $do,
                    'limit' => $limit(10, 40),
                ]],
            ],
            'dotace' => [
                'title' => 'Dotace spolkům',
                'description' => 'Komu obec přispívá ze svého rozpočtu: součty po letech, dotace v daném roce '
                    . 'nebo celá historie příjemce (spolku) s účelem.',
                'inputSchema' => ['type' => 'object', 'required' => ['obec'], 'properties' => [
                    'obec' => $obec,
                    'rok' => ['type' => 'integer'],
                    'prijemce' => ['type' => 'string', 'description' => 'Část názvu příjemce, např. „Sokol“.'],
                    'limit' => $limit(20, 80),
                ]],
            ],
        ];
        $out = [];
        foreach ($defs as $name => $d) {
            $out[] = ['name' => $name] + $d + ['annotations' => ['title' => $d['title']] + $ro];
        }
        return $out;
    }

    /** @return array{0: array, 1: int} data a počet výsledků pro deník */
    public static function call(string $name, array $a): array
    {
        switch ($name) {
            case 'obce': return self::obce();
            case 'hledat': return self::hledat($a);
            case 'jednani': return self::jednani($a);
            case 'diskuze': return self::diskuze($a);
            case 'rozpocet': return self::rozpocet($a);
            case 'investice': return self::investice($a);
            case 'zakazky': return self::zakazky($a);
            case 'vyberova_rizeni': return self::vyberovaRizeni($a);
            case 'dotace': return self::dotace($a);
        }
        throw new InvalidArgumentException('Neznámý nástroj: ' . $name);
    }

    // ---------------------------------------------------------------- parametry

    private static function str(array $a, string $k): string
    {
        return is_string($a[$k] ?? null) ? trim($a[$k]) : (is_numeric($a[$k] ?? null) ? (string) $a[$k] : '');
    }

    private static function int(array $a, string $k, int $def, int $min, int $max): int
    {
        $v = $a[$k] ?? null;
        return is_numeric($v) ? max($min, min($max, (int) $v)) : $def;
    }

    private static function enum(array $a, string $k, array $allowed, string $def): string
    {
        $v = self::str($a, $k);
        if ($v === '') {
            return $def;
        }
        if (!in_array($v, $allowed, true)) {
            throw new ToolError("Parametr $k musí být jedno z: " . implode(', ', $allowed) . '.');
        }
        return $v;
    }

    private static function obec(array $a): string
    {
        $o = self::str($a, 'obec');
        if ($o === '') {
            throw new ToolError('Chybí obec. Dostupné: ' . implode(', ', array_keys(Data::obce())) . '.');
        }
        Data::db($o);
        return $o;
    }

    /** @return array{0: ?string, 1: ?string} rozsah dat ISO (od, do) z parametrů rok/od/do */
    private static function range(array $a): array
    {
        $fix = function (string $v, bool $end): ?string {
            if ($v === '') {
                return null;
            }
            if (preg_match('/^\d{4}$/', $v)) {
                return $v . ($end ? '-12-31' : '-01-01');
            }
            if (preg_match('/^\d{4}-\d{2}$/', $v)) {
                return $v . ($end ? '-31' : '-01');
            }
            if (preg_match('/^\d{4}-\d{2}-\d{2}$/', $v)) {
                return $v;
            }
            throw new ToolError('Datum zadej jako rok (2024) nebo RRRR-MM-DD.');
        };
        $rok = self::str($a, 'rok');
        if ($rok !== '') {
            return [$fix($rok, false), $fix($rok, true)];
        }
        return [$fix(self::str($a, 'od'), false), $fix(self::str($a, 'do'), true)];
    }

    private static function inRange(?string $date, ?string $od, ?string $do): bool
    {
        if ($date === null || $date === '') {
            return $od === null && $do === null;
        }
        return ($od === null || $date >= $od) && ($do === null || $date <= $do);
    }

    private static function kc($v): ?int
    {
        return $v === null ? null : (int) round((float) $v);
    }

    /** Zasedání podle id / čísla / „posledni“. */
    private static function resolveJednani(string $obec, string $id, string $organ): array
    {
        $id = trim($id);
        if ($id === '' || mb_strtolower($id) === 'posledni' || mb_strtolower($id) === 'poslední') {
            $rows = Data::rows($obec, 'SELECT * FROM jednani WHERE organ = ? ORDER BY datum DESC LIMIT 1', [$organ]);
        } else {
            $cand = preg_match('/^(ZO|RO)-/i', $id) ? strtoupper(substr($id, 0, 2)) . substr($id, 2) : $organ . '-' . $id;
            $rows = Data::rows($obec, 'SELECT * FROM jednani WHERE id = ?', [$cand]);
        }
        if (!$rows) {
            throw new ToolError("Zasedání „{$id}“ v obci {$obec} není. Seznam vrátí nástroj jednani bez id.");
        }
        return $rows[0];
    }

    /** Klíče zastupitelů, na které sedí zadané jméno („Liška“ → obě Lišky). */
    private static function osobyFor(string $obec, string $mluvci): array
    {
        $m = Text::norm($mluvci);
        $keys = [];
        foreach (Data::rows($obec, 'SELECT klic, jmeno FROM osoby') as $o) {
            $hay = ' ' . Text::norm($o['jmeno'] . ' ' . $o['klic']);
            $all = true;
            foreach (explode(' ', $m) as $w) {
                if ($w !== '' && !str_contains($hay, ' ' . Text::stem($w))) {
                    $all = false;
                }
            }
            if ($all) {
                $keys[] = $o['klic'];
            }
        }
        return $keys;
    }

    private static function mluvciMatch(array $p, string $mluvci, array $keys): bool
    {
        return ($p['osoba'] !== null && in_array($p['osoba'], $keys, true))
            || str_contains(' ' . Text::norm($p['mluvci']), ' ' . Text::stem(Text::norm($mluvci)));
    }

    // ---------------------------------------------------------------- obce

    private static function obce(): array
    {
        $out = [];
        foreach (Data::obce() as $slug => $o) {
            $m = Data::meta($slug);
            $jed = [];
            foreach (Data::rows($slug, 'SELECT organ, MIN(datum) od, MAX(datum) do, COUNT(*) pocet FROM jednani GROUP BY organ') as $r) {
                $jed[$r['organ'] === 'ZO' ? 'zastupitelstvo' : 'rada'] = ['od' => $r['od'], 'do' => $r['do'], 'zasedani' => (int) $r['pocet']];
            }
            $pr = Data::rows($slug, 'SELECT COUNT(DISTINCT p.jednani_id) n, MIN(j.datum) od, MAX(j.datum) do FROM promluvy p JOIN jednani j ON j.id = p.jednani_id')[0];
            $roz = Data::rows($slug, 'SELECT MIN(rok) od, MAX(rok) do, GROUP_CONCAT(DISTINCT granularita) g FROM rozpocet')[0];
            $osoby = array_map(fn($r) => $r['jmeno'] . ($r['funkce'] ? ' — ' . $r['funkce'] : ''),
                Data::rows($slug, 'SELECT jmeno, funkce FROM osoby'));
            $out[] = array_filter([
                'obec' => $slug,
                'nazev' => $m['nazev'],
                'web' => $m['web'],
                'obyvatel' => $m['obyvatel'] ?? null,
                'okres' => $m['okres'] ?? null,
                'aktualizovano' => $m['aktualizovano'],
                'jednani' => $jed,
                'prepisy_diskuzi' => (int) $pr['n'] ? ['zasedani' => (int) $pr['n'], 'od' => $pr['od'], 'do' => $pr['do']] : 'nejsou',
                'rozpocet' => $roz['od'] ? ['od' => (int) $roz['od'], 'do' => (int) $roz['do'],
                    'detail' => str_contains((string) $roz['g'], 'polozka') ? 'paragrafy a položky' : 'jen souhrny (druh, oblast)'] : null,
                'investicni_akce' => (int) $m['pocet_akce'],
                'zakazky' => (int) $m['pocet_zakazky'],
                'vyberova_rizeni' => (int) ($m['pocet_vyberova_rizeni'] ?? 0) ?: null,
                'dotace' => (int) $m['pocet_dotace'],
                'zastupitele' => $osoby ?: null,
                'jak_cist' => $m['poznamky'] ?? null,
            ], fn($v) => $v !== null);
        }
        return [['obce' => $out], count($out)];
    }

    // ---------------------------------------------------------------- hledat

    private static function hledat(array $a): array
    {
        $dotaz = self::str($a, 'dotaz');
        $mluvci = self::str($a, 'mluvci');
        $terms = Text::terms($dotaz);
        if (!$terms && $mluvci === '') {
            throw new ToolError($dotaz === '' ? 'Zadej dotaz nebo mluvčího.' : 'Dotaz neobsahuje žádné hledatelné slovo.');
        }
        $zdroj = self::enum($a, 'zdroj', ['vse', 'usneseni', 'diskuze'], 'vse');
        $organ = self::enum($a, 'organ', ['ZO', 'RO'], '');
        $tema = Text::norm(self::str($a, 'tema'));
        [$od, $do] = self::range($a);
        $limit = self::int($a, 'limit', 10, 1, 30);
        $strana = self::int($a, 'strana', 1, 1, 1000);
        $obce = self::str($a, 'obec') !== '' ? [self::obec($a)] : array_keys(Data::obce());

        $partial = false;
        $hits = self::collect($obce, $terms, true, $zdroj, $organ, $tema, $od, $do, $mluvci);
        if (!$hits && count($terms) > 1) {
            $hits = self::collect($obce, $terms, false, $zdroj, $organ, $tema, $od, $do, $mluvci);
            $partial = (bool) $hits;
        }
        usort($hits, fn($x, $y) => [$y['_s'], $y['_d'], $x['_p']] <=> [$x['_s'], $x['_d'], $y['_p']]);
        $typy = array_count_values(array_column($hits, 'typ'));
        $page = array_slice($hits, ($strana - 1) * $limit, $limit);
        foreach ($page as &$h) {
            unset($h['_s'], $h['_d'], $h['_p']);
        }
        unset($h);
        $res = [
            'dotaz' => $dotaz,
            'celkem' => count($hits),
            'podle_typu' => $typy,
            'strana' => $strana,
            'vysledky' => $page,
        ];
        if ($partial) {
            $res['pozor'] = 'Žádný text neobsahuje všechna slova; výsledky obsahují aspoň některá (řazeno podle počtu shod).';
        }
        if (count($hits) > $strana * $limit) {
            $res['dalsi_strana'] = $strana + 1;
        }
        if (!$hits) {
            $res['tip'] = 'Nic nenalezeno. Zkus kratší nebo obecnější slovo, synonymum, jiný tvar názvu, nebo bez filtrů.';
        }
        return [$res, count($hits)];
    }

    private static function collect(array $obce, array $terms, bool $all, string $zdroj, string $organ, string $tema,
                                    ?string $od, ?string $do, string $mluvci): array
    {
        $hits = [];
        foreach ($obce as $obec) {
            $hasPrepisy = (bool) Data::value($obec, 'SELECT 1 FROM promluvy LIMIT 1');
            $where = [];
            $args = [];
            if ($terms) {
                $w = [];
                foreach ($terms as $t) {
                    $w[] = "x.norm LIKE ? ESCAPE '\\'";
                    $args[] = Text::like($t);
                }
                $where[] = '(' . implode($all ? ' AND ' : ' OR ', $w) . ')';
            }
            if ($organ !== '') {
                $where[] = 'j.organ = ?';
                $args[] = $organ;
            }
            if ($od !== null) {
                $where[] = 'j.datum >= ?';
                $args[] = $od;
            }
            if ($do !== null) {
                $where[] = 'j.datum <= ?';
                $args[] = $do;
            }
            $sqlWhere = $where ? ' WHERE ' . implode(' AND ', $where) : '';

            // usnesení: s mluvčím jen u obcí, kde je rozprava v zápisu (bez přepisů) — jméno v textu
            $nameTerms = $mluvci !== '' ? Text::terms($mluvci) : [];
            if ($zdroj !== 'diskuze' && ($mluvci === '' || !$hasPrepisy)) {
                $rows = Data::rows($obec, 'SELECT x.*, j.organ, j.cislo, j.datum, j.url_pdf FROM usneseni x '
                    . 'JOIN jednani j ON j.id = x.jednani_id' . $sqlWhere, $args);
                foreach ($rows as $r) {
                    if ($tema !== '' && !str_contains(Text::norm((string) $r['tema']), $tema)) {
                        continue;
                    }
                    if ($nameTerms && Text::hits($r['norm'], $nameTerms) < count($nameTerms)) {
                        continue;
                    }
                    $hits[] = array_filter([
                        'typ' => 'usneseni',
                        'obec' => $obec,
                        'jednani' => $r['jednani_id'],
                        'organ' => $r['organ'] === 'ZO' ? 'zastupitelstvo' : 'rada',
                        'datum' => $r['datum'],
                        'cislo_usneseni' => $r['oznaceni'] ?: (int) $r['poradi'],
                        'tema' => $r['tema'],
                        'kategorie' => $r['kategorie'],
                        'castka_kc' => self::kc($r['castka']),
                        'hlasovani' => $r['pro'] !== null ? "pro {$r['pro']}, proti {$r['proti']}, zdržel se {$r['zdrzel']}" : null,
                        'text' => Text::snippet($r['text'], $r['norm'], $terms ?: $nameTerms),
                        'pdf' => $r['url_pdf'],
                        'portal' => Data::portalLink($obec, $r['jednani_id']),
                        '_s' => $terms ? Text::hits($r['norm'], $terms) : 0, '_d' => $r['datum'], '_p' => (int) $r['poradi'],
                    ], fn($v) => $v !== null && $v !== '');
                }
            }
            if ($zdroj !== 'usneseni' && $hasPrepisy && $organ !== 'RO') {
                $keys = $mluvci !== '' ? self::osobyFor($obec, $mluvci) : [];
                $rows = Data::rows($obec, 'SELECT x.*, j.cislo, j.datum, j.video FROM promluvy x '
                    . 'JOIN jednani j ON j.id = x.jednani_id' . $sqlWhere, $args);
                foreach ($rows as $r) {
                    if ($mluvci !== '' && !self::mluvciMatch($r, $mluvci, $keys)) {
                        continue;
                    }
                    if ($tema !== '') {
                        continue;  // diskuze témata nemají
                    }
                    $hits[] = array_filter([
                        'typ' => 'diskuze',
                        'obec' => $obec,
                        'jednani' => $r['jednani_id'],
                        'organ' => 'zastupitelstvo',
                        'datum' => $r['datum'],
                        'bod' => $r['bod'] !== null ? (int) $r['bod'] : null,
                        'bod_nazev' => $r['bod_nazev'],
                        'mluvci' => $r['mluvci'],
                        'text' => Text::snippet($r['text'], $r['norm'], $terms, 420),
                        'video' => Data::videoLink($r['video'], $r['cas'] !== null ? (int) $r['cas'] : null),
                        'portal' => Data::portalLink($obec, $r['jednani_id']),
                        '_s' => $terms ? Text::hits($r['norm'], $terms) : 0, '_d' => $r['datum'], '_p' => (int) $r['poradi'],
                    ], fn($v) => $v !== null && $v !== '');
                }
            }
        }
        return $hits;
    }

    // ---------------------------------------------------------------- jednani

    private static function jednani(array $a): array
    {
        $obec = self::obec($a);
        $organ = self::enum($a, 'organ', ['ZO', 'RO'], '');
        $id = self::str($a, 'id');
        if ($id === '') {
            $where = [];
            $args = [];
            if ($organ !== '') {
                $where[] = 'organ = ?';
                $args[] = $organ;
            }
            if (self::str($a, 'rok') !== '') {
                $where[] = 'rok = ?';
                $args[] = (int) $a['rok'];
            }
            $limit = self::int($a, 'limit', 20, 1, 60);
            $rows = Data::rows($obec, 'SELECT * FROM jednani' . ($where ? ' WHERE ' . implode(' AND ', $where) : '')
                . ' ORDER BY datum DESC LIMIT ' . $limit, $args);
            $list = array_map(fn($r) => array_filter([
                'id' => $r['id'],
                'organ' => $r['organ'] === 'ZO' ? 'zastupitelstvo' : 'rada',
                'nazev' => $r['nazev'],
                'datum' => $r['datum'],
                'usneseni' => (int) $r['pocet_usneseni'],
                'v_kostce' => $r['shrnuti'],
                'prepis_diskuze' => (int) $r['pocet_replik'] > 0 ? true : null,
                'pdf' => $r['url_pdf'],
                'video' => Data::videoLink($r['video'], null),
            ], fn($v) => $v !== null && $v !== ''), $rows);
            return [['obec' => $obec, 'zasedani' => $list], count($list)];
        }

        $j = self::resolveJednani($obec, $id, $organ ?: 'ZO');
        $osoby = [];
        foreach (Data::rows($obec, 'SELECT klic, jmeno FROM osoby') as $o) {
            $osoby[$o['klic']] = $o['jmeno'];
        }
        $hlasy = [];
        foreach (Data::rows($obec, 'SELECT h.usneseni_id, h.osoba, h.hlas FROM hlasy h JOIN usneseni u ON u.id = h.usneseni_id WHERE u.jednani_id = ?', [$j['id']]) as $h) {
            $hlasy[$h['usneseni_id']][$h['hlas']][] = $osoby[$h['osoba']] ?? $h['osoba'];
        }
        // diskuze z přepisu se váže k pořadí usnesení v zápisu (bod = poradi)
        $body = [];
        foreach (Data::rows($obec, 'SELECT bod, MIN(cas) cas, COUNT(*) replik, GROUP_CONCAT(DISTINCT mluvci) kdo '
            . 'FROM promluvy WHERE jednani_id = ? GROUP BY bod', [$j['id']]) as $b) {
            $body[(int) $b['bod']] = $b;
        }
        $usn = [];
        foreach (Data::rows($obec, 'SELECT * FROM usneseni WHERE jednani_id = ? ORDER BY poradi', [$j['id']]) as $u) {
            $hl = null;
            if ($u['pro'] !== null) {
                $hl = ['pro' => (int) $u['pro'], 'proti' => (int) $u['proti'], 'zdrzel_se' => (int) $u['zdrzel']];
                foreach (['proti' => 'proti_jmenovite', 'zdrzel' => 'zdrzeli_se_jmenovite', 'nehlasoval' => 'nehlasovali'] as $k => $label) {
                    if (!empty($hlasy[$u['id']][$k])) {
                        $hl[$label] = $hlasy[$u['id']][$k];
                    }
                }
            }
            $b = $body[(int) $u['poradi']] ?? null;
            $usn[] = array_filter([
                'cislo' => $u['oznaceni'] ?: (int) $u['poradi'],
                'kategorie' => $u['kategorie'],
                'tema' => $u['tema'],
                'castka_kc' => self::kc($u['castka']),
                'hlasovani' => $hl,
                'text' => Text::cut($u['text'], 2500),
                'diskuze' => $b ? ['bod' => (int) $u['poradi'], 'replik' => (int) $b['replik'],
                    'mluvci' => explode(',', (string) $b['kdo']),
                    'video' => Data::videoLink($j['video'], $b['cas'] !== null ? (int) $b['cas'] : null)] : null,
            ], fn($v) => $v !== null && $v !== '');
        }
        $res = array_filter([
            'obec' => $obec,
            'id' => $j['id'],
            'nazev' => $j['nazev'],
            'organ' => $j['organ'] === 'ZO' ? 'zastupitelstvo' : 'rada',
            'datum' => $j['datum'],
            'v_kostce' => $j['shrnuti'],
            'pritomno' => $j['pritomno'] !== null ? (int) $j['pritomno'] : null,
            'omluveni' => $j['omluveni'] ? json_decode($j['omluveni'], true) : null,
            'pdf' => $j['url_pdf'],
            'video' => Data::videoLink($j['video'], null),
            'portal' => Data::portalLink($obec, $j['id']),
            'usneseni' => $usn,
            'tip' => $body ? 'U usnesení s diskuzí vrátí repliky nástroj diskuze (jednani, bod).' : null,
            'pozor' => $j['organ'] === 'RO' ? (Data::meta($obec)['poznamky']['jednani_ro'] ?? null) : null,
        ], fn($v) => $v !== null && $v !== '' && $v !== []);
        return [$res, count($usn)];
    }

    // ---------------------------------------------------------------- diskuze

    private static function diskuze(array $a): array
    {
        $obec = self::obec($a);
        if (!Data::value($obec, 'SELECT 1 FROM promluvy LIMIT 1')) {
            return [['obec' => $obec, 'info' => 'Pro tuto obec přepisy diskuzí nejsou. '
                . (Data::meta($obec)['poznamky']['jednani_zo'] ?? '') . ' Použij nástroj hledat (parametr mluvci) nebo jednani.'], 0];
        }
        $j = self::resolveJednani($obec, self::str($a, 'jednani'), 'ZO');
        $dostupne = fn() => array_column(Data::rows($obec, 'SELECT id FROM jednani WHERE pocet_replik > 0 ORDER BY datum DESC'), 'id');
        if ((int) $j['pocet_replik'] === 0) {
            return [['obec' => $obec, 'jednani' => $j['id'], 'info' => 'K tomuto zasedání přepis diskuze není.',
                'prepisy_jsou_k' => $dostupne()], 0];
        }
        $rozsah = self::enum($a, 'rozsah', ['shrnuti', 'cele'], 'shrnuti');
        $mluvci = self::str($a, 'mluvci');
        $keys = $mluvci !== '' ? self::osobyFor($obec, $mluvci) : [];
        $bod = self::str($a, 'bod');
        $rows = Data::rows($obec, 'SELECT * FROM promluvy WHERE jednani_id = ?' . ($bod !== '' ? ' AND bod = ?' : '')
            . ' ORDER BY poradi', $bod !== '' ? [$j['id'], (int) $bod] : [$j['id']]);
        if ($mluvci !== '') {
            $rows = array_values(array_filter($rows, fn($r) => self::mluvciMatch($r, $mluvci, $keys)));
        }
        $base = ['obec' => $obec, 'jednani' => $j['id'], 'datum' => $j['datum'],
            'pozor' => 'Přepis videozáznamu upravený do spisovné češtiny a zkrácený — nejde o doslovné citace. Občané jsou anonymní.'];

        if ($bod === '' && $mluvci === '') {
            $body = [];
            foreach ($rows as $r) {
                $k = (int) $r['bod'];
                $body[$k] ??= ['bod' => $k, 'nazev' => $r['bod_nazev'], 'replik' => 0, 'mluvci' => [],
                    'video' => Data::videoLink($j['video'], $r['cas'] !== null ? (int) $r['cas'] : null)];
                $body[$k]['replik']++;
                $body[$k]['mluvci'][$r['mluvci']] = ($body[$k]['mluvci'][$r['mluvci']] ?? 0) + 1;
            }
            return [$base + ['body' => array_map(fn($b) => array_filter($b, fn($v) => $v !== null), array_values($body)),
                'tip' => 'Repliky k bodu vrátí diskuze s parametrem bod.'], count($body)];
        }
        $len = $rozsah === 'cele' ? 100000 : 260;
        $turns = array_map(fn($r) => array_filter([
            'bod' => (int) $r['bod'],
            'mluvci' => $r['mluvci'],
            'text' => Text::cut($r['text'], $len),
        ], fn($v) => $v !== null), $rows);
        $res = $base + [
            'bod' => $bod !== '' ? (int) $bod : null,
            'nazev_bodu' => $rows[0]['bod_nazev'] ?? null,
            'video' => $rows ? Data::videoLink($j['video'], $rows[0]['cas'] !== null ? (int) $rows[0]['cas'] : null) : null,
            'rozsah' => $rozsah,
            'repliky' => $turns,
        ];
        if ($rozsah === 'shrnuti') {
            $res['tip'] = 'Repliky jsou zkrácené; plné znění vrátí rozsah „cele“.';
        }
        return [array_filter($res, fn($v) => $v !== null), count($turns)];
    }

    // ---------------------------------------------------------------- rozpocet

    private static function rozpocet(array $a): array
    {
        $obec = self::obec($a);
        $strana = self::enum($a, 'strana', ['vydaje', 'prijmy'], 'vydaje');
        $cleneni = self::enum($a, 'cleneni', ['celkem', 'druh', 'oblast', 'paragraf', 'polozka'], $strana === 'vydaje' ? 'oblast' : 'druh');
        $limit = self::int($a, 'limit', 25, 1, 80);
        $detail = (bool) Data::value($obec, "SELECT 1 FROM rozpocet WHERE granularita = 'polozka' LIMIT 1");
        if ($cleneni === 'oblast' && $strana === 'prijmy') {
            throw new ToolError('Příjmy se podle oblastí nečlení; použij cleneni druh nebo polozka.');
        }
        if (!$detail && in_array($cleneni, ['paragraf', 'polozka'], true)) {
            throw new ToolError('Tato obec má rozpočet jen v souhrnech; použij cleneni celkem, druh nebo oblast.');
        }
        $gran = $detail ? 'polozka' : ($cleneni === 'oblast' ? 'oblast' : 'druh');

        $years = array_map('intval', array_column(Data::rows($obec, 'SELECT DISTINCT rok FROM rozpocet WHERE granularita = ? ORDER BY rok', [$gran]), 'rok'));
        if (self::str($a, 'rok') !== '') {
            $sel = [(int) $a['rok']];
        } elseif (self::str($a, 'od') !== '' || self::str($a, 'do') !== '') {
            $from = (int) (self::str($a, 'od') ?: min($years));
            $to = (int) (self::str($a, 'do') ?: max($years));
            $sel = array_values(array_filter($years, fn($y) => $y >= $from && $y <= $to));
        } else {
            $sel = array_slice($years, -2);
        }
        $sel = array_values(array_intersect($sel, $years));
        if (!$sel) {
            throw new ToolError('Pro zadané roky rozpočet není. K dispozici: ' . min($years) . '–' . max($years) . '.');
        }
        $rows = Data::rows($obec, 'SELECT * FROM rozpocet WHERE granularita = ? AND strana = ? AND rok IN ('
            . implode(',', $sel) . ')', [$gran, $strana]);

        $terms = Text::terms(self::str($a, 'hledat'));
        $groups = [];
        $total = [];
        $obdobi = [];
        foreach ($rows as $r) {
            if ($terms) {
                $hay = ' ' . Text::norm(implode(' ', [$r['druh'], $r['oblast'], $r['paragraf'], $r['paragraf_nazev'], $r['polozka'], $r['polozka_nazev']]));
                if (Text::hits($hay, $terms) < count($terms)) {
                    continue;
                }
            }
            [$key, $label] = match ($cleneni) {
                'celkem' => ['celkem', 'Celkem'],
                'druh' => [$r['druh'], $r['druh']],
                'oblast' => [$r['oblast'], $r['oblast']],
                'paragraf' => [$r['paragraf'], $r['paragraf'] . ' ' . $r['paragraf_nazev']],
                'polozka' => [$r['polozka'], $r['polozka'] . ' ' . $r['polozka_nazev']],
            };
            if ($key === null || $key === '') {
                continue;
            }
            $y = (int) $r['rok'];
            $obdobi[$y] = $r['obdobi'];
            $groups[$key] ??= ['nazev' => $label, 'roky' => []];
            foreach (['schvaleny', 'upraveny', 'skutecnost'] as $c) {
                $groups[$key]['roky'][$y][$c] = ($groups[$key]['roky'][$y][$c] ?? 0) + (float) $r[$c];
                $total[$y][$c] = ($total[$y][$c] ?? 0) + (float) $r[$c];
            }
        }
        // řadit podle posledního celého roku (průběžný rok by pořadí zkresloval)
        $full = array_keys(array_filter($obdobi, fn($o) => str_ends_with((string) $o, '-12')));
        $last = $full ? max($full) : max(array_keys($obdobi) ?: $sel);
        uasort($groups, fn($x, $y) => ($y['roky'][$last]['skutecnost'] ?? 0) <=> ($x['roky'][$last]['skutecnost'] ?? 0));
        $round = function (array $roky): array {
            $o = [];
            ksort($roky);
            foreach ($roky as $y => $v) {
                $o[(string) $y] = array_map(fn($x) => (int) round($x), $v);
            }
            return $o;
        };
        $out = array_map(fn($g) => ['nazev' => $g['nazev'], 'roky' => $round($g['roky'])], array_slice(array_values($groups), 0, $limit));
        $stav = [];
        foreach ($obdobi as $y => $o) {
            $stav[(string) $y] = str_ends_with((string) $o, '-12') ? 'celý rok' : 'průběžně k ' . substr((string) $o, 5) . '/' . $y . ' (skutečnost není za celý rok)';
        }
        ksort($stav);
        $m = Data::meta($obec);
        $res = array_filter([
            'obec' => $obec,
            'strana' => $strana === 'vydaje' ? 'výdaje' : 'příjmy',
            'cleneni' => $cleneni,
            'hledat' => self::str($a, 'hledat') ?: null,
            'obdobi' => $stav,
            'celkem' => $round($total),
            'polozky' => $cleneni === 'celkem' ? null : $out,
            'dalsich_polozek' => count($groups) > $limit ? count($groups) - $limit : null,
            'obyvatel' => $m['obyvatel'] ?? null,
            'jednotky' => 'Kč; schvaleny = schválený rozpočet, upraveny = po rozpočtových opatřeních, skutecnost = skutečně vybráno/utraceno',
            'zdroj' => $m['poznamky']['rozpocet'] ?? null,
            'portal' => $m['web'] . '/rozpocet.html',
        ], fn($v) => $v !== null);
        return [$res, count($groups)];
    }

    // ---------------------------------------------------------------- investice

    private static function investice(array $a): array
    {
        $obec = self::obec($a);
        [$od, $do] = self::range($a);
        $terms = Text::terms(self::str($a, 'hledat'));
        $skupina = Text::norm(self::str($a, 'skupina'));
        $min = (float) ($a['min_castka'] ?? 0);
        $limit = self::int($a, 'limit', 15, 1, 60);
        $razeni = self::enum($a, 'razeni', ['castka', 'datum'], 'castka');

        $kap = array_map(fn($r) => ['rok' => (int) $r['rok'], 'kapitalove_vydaje' => self::kc($r['kapitalove']),
            'vydaje_celkem' => self::kc($r['vydaje']),
            'podil_investic' => $r['vydaje'] ? round($r['kapitalove'] / $r['vydaje'] * 100) . ' %' : null],
            Data::rows($obec, 'SELECT * FROM kapitalove ORDER BY rok'));

        $all = Data::rows($obec, 'SELECT * FROM akce');
        $skupiny = array_count_values(array_filter(array_column($all, 'skupina')));
        arsort($skupiny);
        $rows = array_values(array_filter($all, function ($r) use ($od, $do, $terms, $skupina, $min) {
            $date = $r['datum'] ?: ($r['rok'] ? $r['rok'] . '-07-01' : null);
            return ($od === null && $do === null || self::inRange($date, $od, $do))
                && (!$terms || Text::hits($r['norm'], $terms) === count($terms))
                && ($skupina === '' || str_contains(Text::norm((string) $r['skupina']), $skupina))
                && (float) $r['castka'] >= $min;
        }));
        usort($rows, $razeni === 'datum'
            ? fn($x, $y) => [$y['datum'] ?? '', $y['rok']] <=> [$x['datum'] ?? '', $x['rok']]
            : fn($x, $y) => (float) $y['castka'] <=> (float) $x['castka']);
        $sum = array_sum(array_map(fn($r) => (float) $r['castka'], $rows));
        $akce = array_map(fn($r) => array_filter([
            'datum' => $r['datum'] ?: null,
            'rok' => (int) $r['rok'],
            'castka_kc' => self::kc($r['castka']),
            'nazev' => $r['nazev'],
            'skupina' => $r['skupina'],
            'zhotovitel' => $r['zhotovitel'],
            'text' => $r['nazev'] && $r['nazev'] === $r['text'] ? null : Text::cut($r['text'], 500),
            'jednani' => $r['jednani_id'],
            'zdroj' => $r['zdroj'],
            'odkaz' => $r['url'],
        ], fn($v) => $v !== null && $v !== ''), array_slice($rows, 0, $limit));
        $m = Data::meta($obec);
        return [[
            'obec' => $obec,
            'kapitalove_vydaje_po_letech' => $kap,
            'akce' => ['celkem' => count($rows), 'soucet_kc' => (int) round($sum), 'zobrazeno' => count($akce), 'seznam' => $akce],
            'skupiny' => $skupiny,
            'pozor' => 'Kapitálové výdaje jsou skutečnost z rozpočtu; akce jsou rozhodnutí (smlouvy, nákupy) s částkou z usnesení '
                . 'nebo z profilu zadavatele — součty se proto nekryjí. ' . ($m['poznamky']['castky'] ?? ''),
            'portal' => $m['web'] . '/investice.html',
        ], count($rows)];
    }

    // ---------------------------------------------------------------- zakazky

    private static function zakazky(array $a): array
    {
        $obec = self::obec($a);
        [$od, $do] = self::range($a);
        $limit = self::int($a, 'limit', 15, 1, 60);
        $dod = Text::norm(self::str($a, 'dodavatel'));
        $terms = Text::terms(self::str($a, 'hledat'));
        $rows = array_values(array_filter(Data::rows($obec, 'SELECT * FROM zakazky'),
            fn($r) => ($od === null && $do === null || self::inRange($r['datum'], $od, $do))
                && ($dod === '' || str_contains(Text::norm((string) $r['dodavatel']), $dod))
                && (!$terms || Text::hits($r['norm'], $terms) === count($terms))));
        $hasDod = (bool) Data::value($obec, 'SELECT 1 FROM zakazky WHERE dodavatel IS NOT NULL LIMIT 1');
        $m = Data::meta($obec);
        $item = fn($r) => array_filter([
            'datum' => $r['datum'],
            'dodavatel' => $r['dodavatel'],
            'castka_kc' => self::kc($r['castka']),
            'dodatek' => $r['dodatek'] ? true : null,
            'text' => Text::cut($r['text'], 450),
            'jednani' => $r['jednani_id'],
            'odkaz' => $r['url'],
        ], fn($v) => $v !== null && $v !== '');
        $res = ['obec' => $obec, 'pozor' => $m['poznamky']['zakazky'] ?? null, 'portal' => $m['web'] . '/zakazky.html'];

        $poLetech = [];
        foreach ($rows as $r) {
            $poLetech[(string) $r['rok']] = ($poLetech[(string) $r['rok']] ?? 0) + (int) round((float) $r['castka']);
        }
        ksort($poLetech);
        $res['soucet_po_letech_kc'] = $poLetech;

        if ($hasDod && $dod === '' && !$terms) {
            $firmy = [];
            foreach ($rows as $r) {
                $f = &$firmy[$r['dodavatel']];
                $f ??= ['dodavatel' => $r['dodavatel'], 'soucet_kc' => 0, 'zakazek' => 0, 'dodatku' => 0, 'roky' => []];
                $f['soucet_kc'] += (int) round((float) $r['castka']);
                $f[$r['dodatek'] ? 'dodatku' : 'zakazek']++;
                $f['roky'][$r['rok']] = true;
                unset($f);
            }
            usort($firmy, fn($x, $y) => $y['soucet_kc'] <=> $x['soucet_kc']);
            foreach ($firmy as &$f) {
                ksort($f['roky']);
                $f['roky'] = implode(', ', array_keys($f['roky']));
            }
            unset($f);
            $res += ['dodavatelu' => count($firmy), 'zebricek' => array_slice($firmy, 0, $limit),
                'tip' => 'Historii firmy vrátí zakazky s parametrem dodavatel.'];
            return [$res, count($firmy)];
        }
        usort($rows, $dod !== ''
            ? fn($x, $y) => strcmp((string) $y['datum'], (string) $x['datum'])
            : fn($x, $y) => (float) $y['castka'] <=> (float) $x['castka']);
        $res += ['celkem' => count($rows), 'soucet_kc' => array_sum($poLetech),
            'zakazky' => array_map($item, array_slice($rows, 0, $limit))];
        return [array_filter($res, fn($v) => $v !== null), count($rows)];
    }

    // ---------------------------------------------------------------- vyberova_rizeni

    private static function vyberovaRizeni(array $a): array
    {
        $obec = self::obec($a);
        $m = Data::meta($obec);
        $res = ['obec' => $obec, 'pozor' => $m['poznamky']['vyberova_rizeni'] ?? null,
            'portal' => $m['web'] . '/zakazky.html#vypsane'];
        if (!(int) ($m['pocet_vyberova_rizeni'] ?? 0)) {
            return [$res + ['info' => 'Pro tuto obec výběrová řízení s nabídkami nejsou. Zakázky vrací nástroj zakazky.'], 0];
        }
        $nab = [];
        foreach (Data::rows($obec, 'SELECT * FROM nabidky') as $n) {
            $nab[$n['rizeni_id']][] = $n;
        }
        $offer = fn(array $n) => array_filter([
            'firma' => $n['firma'], 'ico' => $n['ico'], 'cena_kc' => self::kc($n['cena']),
            'vybrana' => $n['vybrana'] ? true : null, 'vyloucena' => $n['vyloucen'] ? true : null,
        ], fn($v) => $v !== null && $v !== '');
        $byPrice = function (array $list): array {
            usort($list, fn($x, $y) => ($x['cena'] === null) <=> ($y['cena'] === null) ?: (float) $x['cena'] <=> (float) $y['cena']);
            return $list;
        };
        $item = fn(array $r, bool $offers) => array_filter([
            'id' => $r['id'], 'datum' => $r['datum'], 'nazev' => $r['nazev'], 'druh' => $r['druh'],
            'postup' => $r['postup'], 'stav' => $r['stav'],
            'predpokladana_hodnota_kc' => self::kc($r['predpokladana_hodnota']),
            'lhuta_nabidek' => $r['stav'] === 'probíhá' ? $r['lhuta'] : null,
            'pocet_nabidek' => (int) $r['pocet_nabidek'],
            'vybrana_firma' => $r['dodavatel'], 'cena_kc' => self::kc($r['cena']),
            'nabidky' => $offers && isset($nab[$r['id']]) ? array_map($offer, $byPrice($nab[$r['id']])) : null,
            'odkaz' => $r['url'],
        ], fn($v) => $v !== null && $v !== '');

        $id = self::str($a, 'id');
        if ($id !== '') {
            $r = Data::rows($obec, 'SELECT * FROM vyberova_rizeni WHERE id = ?', [$id])[0] ?? null;
            if (!$r) {
                throw new ToolError("Řízení $id neexistuje. Id vrací vyberova_rizeni bez parametru id.");
            }
            $out = $item($r, true);
            if ($r['cena'] && $r['predpokladana_hodnota']) {
                $out['cena_proti_predpokladane_hodnote'] = round((float) $r['cena'] / (float) $r['predpokladana_hodnota'] * 100) . ' %';
            }
            return [$res + ['rizeni' => $out], 1];
        }

        [$od, $do] = self::range($a);
        $limit = self::int($a, 'limit', 10, 1, 40);
        $firma = Text::norm(self::str($a, 'firma'));
        $terms = Text::terms(self::str($a, 'hledat'));
        $stav = self::str($a, 'stav');
        $rows = array_values(array_filter(Data::rows($obec, 'SELECT * FROM vyberova_rizeni ORDER BY datum DESC'),
            fn($r) => ($od === null && $do === null || self::inRange($r['datum'], $od, $do))
                && ($stav === '' || $r['stav'] === $stav)
                && (!$terms || Text::hits($r['norm'], $terms) === count($terms))));

        if ($firma !== '') {
            $hit = fn(array $n) => str_contains(Text::norm($n['firma']), $firma);
            $list = [];
            $vyhry = 0;
            foreach ($rows as $r) {
                $own = array_values(array_filter($nab[$r['id']] ?? [], $hit));
                if (!$own) {
                    continue;
                }
                $all = $byPrice($nab[$r['id']]);
                $poradi = array_search($own[0], $all, true) + 1;
                $vyhry += $own[0]['vybrana'] ? 1 : 0;
                $list[] = array_filter([
                    'id' => $r['id'], 'datum' => $r['datum'], 'nazev' => $r['nazev'], 'stav' => $r['stav'],
                    'firma' => $own[0]['firma'], 'nabidka_kc' => self::kc($own[0]['cena']),
                    'vybrana' => (bool) $own[0]['vybrana'],
                    'poradi_podle_ceny' => $own[0]['cena'] !== null ? "$poradi. z " . count($all) : null,
                    'vybrana_firma' => $own[0]['vybrana'] ? null : $r['dodavatel'],
                    'cena_vybrane_kc' => $own[0]['vybrana'] ? null : self::kc($r['cena']),
                    'odkaz' => $r['url'],
                ], fn($v) => $v !== null && $v !== '');
            }
            // hledá se částí názvu → víc různých firem; ať model vidí, o koho jde
            $firmy = array_count_values(array_column($list, 'firma'));
            arsort($firmy);
            return [$res + ['firma' => self::str($a, 'firma'), 'nalezene_firmy' => count($firmy) > 1 ? $firmy : null,
                'nabidek' => count($list), 'vybrana' => $vyhry,
                'rizeni' => array_slice($list, 0, $limit)], count($list)];
        }

        if (!$terms && $stav === '' && $od === null && $do === null) {
            $stavy = array_count_values(array_column($rows, 'stav'));
            $zad = array_filter($rows, fn($r) => $r['stav'] === 'zadáno' && $r['pocet_nabidek'] > 0);
            $uchazeci = [];
            foreach ($nab as $list) {
                foreach ($list as $n) {
                    $u = &$uchazeci[Text::norm($n['firma'])];
                    $u ??= ['firma' => $n['firma'], 'nabidek' => 0, 'vybrana' => 0];
                    $u['nabidek']++;
                    $u['vybrana'] += $n['vybrana'];
                    unset($u);
                }
            }
            usort($uchazeci, fn($x, $y) => [$y['nabidek'], $y['vybrana']] <=> [$x['nabidek'], $x['vybrana']]);
            $postupy = array_count_values(array_filter(array_column($rows, 'postup')));
            arsort($postupy);
            $res['prehled'] = [
                'rizeni' => count($rows), 'od' => min(array_filter(array_column($rows, 'datum')) ?: [null]),
                'stavy' => $stavy, 'postupy' => $postupy ?: null,
                's_uvedenymi_nabidkami' => count(array_filter($rows, fn($r) => $r['pocet_nabidek'] > 0)),
                'prumer_nabidek_u_zadanych' => $zad ? round(array_sum(array_column($zad, 'pocet_nabidek')) / count($zad), 1) : null,
                'zadanych_s_jedinou_nabidkou' => count(array_filter($zad, fn($r) => (int) $r['pocet_nabidek'] === 1)),
                'nejcastejsi_uchazeci' => array_slice($uchazeci, 0, 10),
            ];
            $res['tip'] = 'Nabídky jednoho řízení vrátí parametr id, účast firmy parametr firma.';
        }
        $res += ['celkem' => count($rows), 'rizeni' => array_map(fn($r) => $item($r, true), array_slice($rows, 0, $limit))];
        return [array_filter($res, fn($v) => $v !== null), count($rows)];
    }

    // ---------------------------------------------------------------- dotace

    private static function dotace(array $a): array
    {
        $obec = self::obec($a);
        $limit = self::int($a, 'limit', 20, 1, 80);
        $all = Data::rows($obec, 'SELECT * FROM dotace');
        $poLetech = [];
        foreach ($all as $r) {
            $y = (string) $r['rok'];
            $poLetech[$y] ??= ['soucet_kc' => 0, 'dotaci' => 0];
            $poLetech[$y]['soucet_kc'] += (int) round((float) $r['castka']);
            $poLetech[$y]['dotaci']++;
        }
        ksort($poLetech);
        $item = fn($r) => array_filter(['rok' => (int) $r['rok'], 'prijemce' => $r['prijemce'], 'castka_kc' => self::kc($r['castka']),
            'ucel' => Text::cut((string) $r['ucel'], 400), 'odkaz' => $r['url']], fn($v) => $v !== null && $v !== '');
        $res = ['obec' => $obec, 'po_letech' => $poLetech, 'portal' => Data::meta($obec)['web'] . '/dotace.html'];

        $pr = Text::norm(self::str($a, 'prijemce'));
        $rok = self::str($a, 'rok');
        if ($pr !== '' || $rok !== '') {
            $rows = array_values(array_filter($all, fn($r) => ($pr === '' || str_contains(' ' . Text::norm($r['prijemce']), ' ' . Text::stem($pr)))
                && ($rok === '' || (int) $r['rok'] === (int) $rok)));
            usort($rows, $pr !== ''
                ? fn($x, $y) => [$y['rok'], (float) $y['castka']] <=> [$x['rok'], (float) $x['castka']]
                : fn($x, $y) => (float) $y['castka'] <=> (float) $x['castka']);
            $res += ['celkem' => count($rows), 'soucet_kc' => (int) round(array_sum(array_column($rows, 'castka'))),
                'dotace' => array_map($item, array_slice($rows, 0, $limit))];
            return [$res, count($rows)];
        }
        $prij = [];
        foreach ($all as $r) {
            $p = &$prij[$r['prijemce']];
            $p ??= ['prijemce' => $r['prijemce'], 'soucet_kc' => 0, 'dotaci' => 0];
            $p['soucet_kc'] += (int) round((float) $r['castka']);
            $p['dotaci']++;
            unset($p);
        }
        usort($prij, fn($x, $y) => $y['soucet_kc'] <=> $x['soucet_kc']);
        $res += ['nejvetsi_prijemci' => array_slice($prij, 0, $limit),
            'tip' => 'Dotace jednoho roku vrátí parametr rok, historii spolku parametr prijemce.'];
        return [$res, count($prij)];
    }
}
