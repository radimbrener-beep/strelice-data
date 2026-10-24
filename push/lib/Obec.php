<?php
declare(strict_types=1);

// Nastavení upozornění pro tento portál (každá obec má vlastní kopii tohoto souboru).
// define() místo const: testy si hodnoty nastaví předem (push-tests/run.php).

/** Název portálu do zkušebního upozornění. */
defined('PUSH_SITE') || define('PUSH_SITE', 'Jak se máme, Střelice?');
/** Kontakt pro push služby (VAPID „sub"): adresa webu, žádný e-mail. */
defined('PUSH_SUBJECT') || define('PUSH_SUBJECT', 'https://strelice.jaksemame.cz');
/** Druhy upozornění: nová jednání rady, zastupitelstva a ručně ohlášené novinky portálu. */
defined('PUSH_TOPICS') || define('PUSH_TOPICS', ['rada', 'zastupitelstvo', 'portal']);
