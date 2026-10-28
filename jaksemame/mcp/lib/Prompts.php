<?php
declare(strict_types=1);

/** Hotové dotazy, které klienti nabízejí jako příkazy (v Claude třeba přes „+“ → jaksemame). */
final class Prompts
{
    public static function definitions(): array
    {
        $obec = ['name' => 'obec', 'description' => 'Obec: ' . implode(', ', array_keys(Data::obce())), 'required' => true];
        return [
            ['name' => 'posledni_zastupitelstvo', 'title' => 'Co se řešilo na posledním zastupitelstvu',
                'description' => 'Shrnutí posledního zasedání: rozhodnutí, peníze, sporná hlasování a diskuze.',
                'arguments' => [$obec]],
            ['name' => 'tema_v_obci', 'title' => 'Jak se v obci řešilo téma',
                'description' => 'Vývoj tématu v čase: usnesení, diskuze, peníze a kdo co říkal.',
                'arguments' => [$obec, ['name' => 'tema', 'description' => 'Např. „chodníky“, „ČOV“, „školka“.', 'required' => true]]],
            ['name' => 'hospodareni_obce', 'title' => 'Jak obec hospodaří',
                'description' => 'Příjmy, výdaje, investice a největší akce za zvolený rok.',
                'arguments' => [$obec, ['name' => 'rok', 'description' => 'Rok (výchozí poslední celý).', 'required' => false]]],
        ];
    }

    public static function get(string $name, array $args): array
    {
        $obec = (string) ($args['obec'] ?? '');
        if (!Data::exists($obec)) {
            throw new InvalidArgumentException('Neznámá obec; dostupné: ' . implode(', ', array_keys(Data::obce())) . '.');
        }
        $nazev = Data::meta($obec)['nazev'];
        switch ($name) {
            case 'posledni_zastupitelstvo':
                $text = "Shrň poslední zasedání zastupitelstva obce $nazev. Použij nástroj jednani (obec \"$obec\", id \"posledni\"). "
                    . 'Napiš: kdy se konalo, co nejdůležitějšího schválilo (hlavně peníze, stavby, pozemky), která hlasování '
                    . 'nebyla jednomyslná a kdo byl proti, a pokud je přepis diskuze, o čem se nejvíc mluvilo (nástroj diskuze). '
                    . 'Ke každé věci dej odkaz na zdroj.';
                break;
            case 'tema_v_obci':
                $tema = trim((string) ($args['tema'] ?? ''));
                if ($tema === '') {
                    throw new InvalidArgumentException('Chybí téma.');
                }
                $text = "Jak se v obci $nazev řešilo téma „{$tema}“? Prohledej usnesení i diskuze (nástroj hledat, obec \"$obec\"; "
                    . 'zkus i synonyma), seřaď to v čase, uveď rozhodnutí, částky a hlasování, a co k tomu říkali zastupitelé. '
                    . 'Odděl fakta od výkladu a ke každému faktu dej odkaz na zdroj.';
                break;
            case 'hospodareni_obce':
                $rok = trim((string) ($args['rok'] ?? ''));
                $kdy = $rok !== '' ? "v roce $rok" : 'v posledním celém roce';
                $text = "Jak obec $nazev hospodařila $kdy? Použij nástroje rozpocet (příjmy podle druhu, výdaje podle oblasti), "
                    . 'investice a zakazky (obec "' . $obec . '"). Uveď celkové příjmy a výdaje, saldo, na co šlo nejvíc peněz, '
                    . 'největší investiční akce a srovnání s předchozím rokem. Částky zaokrouhli na miliony a uveď zdroj.';
                break;
            default:
                throw new InvalidArgumentException('Neznámý prompt: ' . $name);
        }
        return ['messages' => [['role' => 'user', 'content' => ['type' => 'text', 'text' => $text]]]];
    }
}
