# -*- coding: utf-8 -*-
"""Pravidlova (keyword) klasifikace bodu usneseni Rady obce do tematickych
oblasti. Deterministicke, offline. Kazde tema ma seznam vzoru (regex nad
textem zbavenym diakritiky). Skore = pocet ruznych vzoru, ktere se trefi;
vyhrava nejvyssi skore, pri shode mensi 'priorita' (specifictejsi tema).
Bez trefy -> 'Ostatni'.

Taxonomie: 9 sirsich oblasti + Ostatni."""
import re
import unicodedata


def fold(s):
    return "".join(c for c in unicodedata.normalize("NFD", (s or "").lower())
                    if unicodedata.category(c) != "Mn")


# tema: (priorita, [vzory]) ; mensi priorita = vyhrava pri shode skore
THEMES = {
    "Školství": (1, [
        r"\bskoly\b", r"\bskole\b", r"\bskolu\b", r"matersk\w* skol", r"zakladni skol",
        r"umelec\w* skol", r"\bskolk", r"\bzus\b", r"\bms\b", r"\bzs\b", r"druzin",
        r"\bzaci\b", r"\bzaku\b", r"\bzakum\b", r"\bzaky\b", r"skolni jideln",
        r"skolstvi", r"\bpedagog", r"matersk\w* skolk", r"deti do skol", r"skolsk\w* rad",
    ]),
    "Sociální a zdravotní oblast": (2, [
        r"socialn", r"pecovatelsk", r"\bcharit", r"zdravotn", r"\bsenior", r"handicap",
        r"domov pro", r"\bhospic", r"ran\w* pece", r"\bocr\b", r"klub senior",
        r"pomoc\w* v hmotne nouzi", r"senior taxi", r"diakoni",
    ]),
    "Kultura, sport a spolky": (3, [
        r"\bspolek", r"\bspolku", r"\bspolkem", r"\bspolky", r"\bakce\b", r"\bakci\b",
        r"\bhody\b", r"\bhodu\b", r"\bples", r"\bkultur", r"\bsport", r"\btj\b",
        r"\bsokol", r"\bsdh\b", r"\bhasic", r"knihovn", r"\bkoncert", r"\bsoutez",
        r"\bvystav\w* (?:obraz|prac|del)", r"festival", r"\bhrist", r"detsk\w* hrist",
        r"myslivc", r"zahradkar", r"cerven\w* kriz", r"\borchestr", r"staveni maj",
        r"\bmaje\b", r"\bvyroci", r"farnost", r"\bkostel", r"telovychov", r"\bchasa\b",
    ]),
    "Životní prostředí a odpady": (4, [
        # voda + zivotni prostredi
        r"\bstudn", r"vodni dilo", r"\bvrt\b", r"\bvrtan", r"podzemni vod", r"povrchov\w* vod",
        r"nakladani\w*\s+\w*\s*vod", r"\bkacen", r"\bzelen", r"zivotniho prostred",
        r"zivotni prostred", r"\brybnik", r"\bpotok", r"\bpovod", r"vodopravn",
        r"\bvysadb", r"\bstrom", r"odpadni vod", r"cistirn", r"\bkanaliz",
        r"vegetac", r"\bdosadb", r"\bzapach", r"ovocn\w* strom",
        # odpady
        r"\bodpad", r"\bsvoz", r"kontejner", r"sbern\w* dvur", r"sbern\w* mist",
        r"popelnic", r"separac", r"\btrideni odpad", r"\bskladk", r"biologick\w* rozlozit",
        r"komunaln\w* odpad", r"\bekokom", r"komposter", r"\bkelimk", r"zpetny odber",
    ]),
    "Doprava a sítě": (5, [
        # doprava
        r"\bdoprav", r"dopravni znacen", r"\bzastavk", r"\bautobus", r"\bparkov",
        r"\bsilnic", r"prechod pro chodce", r"\bmhd\b", r"\bids\b", r"\bcyklo",
        r"dopravni obsluz", r"\bzelezni", r"\bzel\. ", r"\bprejezd", r"\bkordis\b",
        r"\blinka\b", r"\blinky\b", r"\blinku\b", r"jizdni rad", r"objizd",
        # site / energetika
        r"\beg\.?\s?d\b", r"\be\.?on\b", r"\bcez\b", r"pripojk", r"\bnn\b", r"\bvn\b",
        r"kabelov\w* veden", r"\bplyn", r"\belektr", r"distribu\w* soustav", r"\bcetin\b",
        r"telekomunik", r"\boptick", r"trafostanic", r"veden\w* nizk\w* napet",
        r"veden\w* vysok\w* napet", r"\bvodafone", r"\bnapeti\b",
    ]),
    "Dotace a finance": (6, [
        r"\bdotac", r"prispevek", r"prispevku", r"prispevk", r"individualni dotac",
        r"rozpoctov\w* opatren", r"\brozpoct", r"\brozpocet", r"financni\w* dar",
        r"\bdar\b", r"\bdaru\b", r"darovaci", r"\bpujck", r"refundac", r"zaverecn\w* ucet",
        r"\bfaktur", r"verejn\w* sbirk", r"\bzaloh", r"penezit\w* dar", r"\bvefa\b",
        r"\bgrant", r"poskytnuti dotac",
    ]),
    "Stavby, investice a územní rozvoj": (7, [
        # stavby a investice
        r"\bstavb", r"vystavb", r"rekonstrukc", r"\boprav\w", r"projektov\w* dokumentac",
        r"stavebn\w* urad", r"stavebn\w* povolen", r"stavebn\w* rizen", r"spolecn\w* rizen",
        r"\bchodnik", r"\bkomunikac", r"vodovod", r"verejn\w* osvetlen", r"\bpristavb",
        r"\bzakazk", r"vyberov\w* rizen", r"\binvestic", r"demolic", r"\bzhotoven",
        r"\bzhotovitel", r"novostavb", r"rodinn\w* dum", r"rodinn\w* domu", r"\bbudov\w",
        r"\bnastavb", r"stavebn\w* zamer", r"realizac\w* stavb", r"\bdotace na rekonstr",
        # uzemni planovani a rozvoj
        r"uzemni\w* plan", r"uzemniho planu", r"uzemnimu planu", r"zmen\w*\s+uzemn",
        r"zmen\w* up\b", r"\bzmenu up\b", r"regulacni plan", r"uzemni studie",
        r"uzemne\s*planovac", r"uzemniho rozvoje", r"program rozvoje obce",
        r"zasad\w* uzemniho rozvoje",
    ]),
    "Pozemky, majetek a bydlení": (8, [
        # pozemky a majetek
        r"\bpozemek", r"\bpozemku", r"\bpozemky", r"\bpozemc", r"\bparcel", r"\bp\. ?c\.",
        r"\bk\. ?u\.", r"vecn\w* bremen", r"\bsluzebnost", r"\bodkoup", r"\bkoupe\b",
        r"\bprodej", r"\bsmen\w* pozemk", r"\bpronaj", r"\bnajem", r"\bvypujck",
        r"kupni smlouv", r"\bsmen\b", r"predkupni", r"smlouv\w* o smlouv\w* budouc",
        r"bezuplatn\w* prevod", r"\bnakup pozemk", r"\bvecneho bremene", r"\bmajetk",
        # bydleni
        r"\bbyt\b", r"\bbytu\b", r"\bbyty\b", r"\bbyte\b", r"\bbytov", r"\bdps\b",
        r"dum s pecovatelsk", r"najem\w* bytu", r"prideleni bytu", r"pridelovani bytu",
        r"\bnajemnik", r"bytov\w* fond",
    ]),
    "Správa obce a úřad": (9, [
        # sprava, urad, provoz
        r"program\b[\w ]{0,20}zastupitelstv", r"program\b[\w ]{0,20}zasedani",
        r"jednaci rad", r"\bsmernic", r"\bkomis\w", r"\bvybor\b", r"\bvyboru\b",
        r"zamestnan", r"pracovni\w* pozic", r"pracovni\w* mist", r"pracovni\w* pomer",
        r"\bmzd", r"\bodmen", r"organizacni rad", r"inventarizac", r"\bkronik",
        r"\bgdpr\b", r"svobodn\w* pristup", r"106/1999", r"verejn\w* vyhlask",
        r"vyrocni zprav", r"datov\w* schrank", r"\bpetice", r"obecne zavazn",
        r"narizeni obce", r"\bovem\b", r"\bauditu?\b", r"poskytnuti informac",
        r"webov\w* strank", r"kamerov", r"kamer\w* v obci", r"zpravodaj",
        r"\bmatrik", r"deratizac", r"reklamn\w* predmet", r"logem obce",
        r"oznacovani ulic", r"cislovani budov", r"orientacn\w* cisl", r"\bzapis z\b",
        r"poptavkov\w* rizen", r"\bvolb\w", r"komunaln\w* volb",
        # verejny poradek a souziti
        r"\bstiznost", r"prestupk", r"\bprestupek", r"verejn\w* poradek",
        r"obcansk\w* souzit", r"vandal", r"\bhluk", r"ruseni nocniho", r"\bpes\b",
        r"\bpsa\b", r"\bpsi\b", r"\bpsu\b", r"obtezovan", r"sousedsk\w* spor",
    ]),
}

# kompilace
_COMPILED = []
for _name, (_pri, _pats) in THEMES.items():
    _COMPILED.append((_name, _pri, [re.compile(p) for p in _pats]))

OSTATNI = "Ostatní"
# poradi pro zobrazeni (chipy, barvy) — zhruba dle velikosti, Ostatni nakonec
ORDER = [
    "Pozemky, majetek a bydlení",
    "Stavby, investice a územní rozvoj",
    "Dotace a finance",
    "Školství",
    "Životní prostředí a odpady",
    "Kultura, sport a spolky",
    "Správa obce a úřad",
    "Doprava a sítě",
    "Sociální a zdravotní oblast",
    OSTATNI,
]


def classify(text):
    f = fold(text)
    cands = []
    for name, pri, pats in _COMPILED:
        score = sum(1 for p in pats if p.search(f))
        if score > 0:
            cands.append((score, -pri, name))
    if not cands:
        return OSTATNI
    cands.sort(reverse=True)
    return cands[0][2]
