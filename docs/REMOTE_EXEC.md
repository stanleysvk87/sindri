# Remote execution — implementované 2026-07-19

Spustí obsah katalogizovaného skriptu na registrovanom stroji cez SSH.
Vypnuté defaultne (`SINDRI_REMOTE_EXEC_ENABLED=false`) — appka bez toho
funguje plnohodnotne, toto je jediná funkcia, ktorá reálne mení stav na
inom stroji, nie len číta/testuje izolovane (na rozdiel od
`docs/SANDBOX.md`, ktorý beží v zahoditeľnom kontajneri bez následkov).

Pôvodne (viď git história tohto súboru) bol tento zápis len zámer s
vypnutým placeholder tlačidlom — po explicitnej žiadosti usera je teraz
reálne implementované, s presne tými podmienkami, čo boli vopred
stanovené (sudo heslo nanovo pri každom spustení, žiadne uloženie).

## Bezpečnostné vlastnosti (over v `backend/app/remote_exec.py`)

- **Vždy len na vopred zaregistrovaný stroj** — nikdy na cestu/IP
  zadanú narýchlo pri spustení. Register v `backend/app/machines.py`
  (Nastavenia → Spravované stroje).
- **SSH kľúč vždy len namontovaný z hostiteľa** — appka kľúč nikdy
  negeneruje ani neukladá jeho obsah. `backend/app/ssh_keys.py` len
  vypíše, ktoré kľúče sú na namontovanej ceste (`GET
  /api/machines/available-keys`), formulár na pridanie stroja z nich
  vyberá.
- **Sudo heslo (ak sa použije) sa zadáva nanovo pri KAŽDOM spustení**,
  nikdy sa neukladá — ani v DB, ani v audit logu. Posiela sa cez SSH
  na `sudo -S` cez stdin (nie ako argument príkazu), takže sa nikdy
  neobjaví vo výpise procesov (`ps`) na hociktorej strane.
- **Sudo je voliteľné, nie vynútené na každé spustenie** — väčšina
  katalogizovaných skriptov (health checky, stavové výpisy) nepotrebuje
  root. Vynucovať sudo heslo vždy by navyše na niektorých strojoch
  vôbec nefungovalo (pozri nižšie).
- `SSH BatchMode=yes` — SSH klient nikdy sám nespadne do interaktívneho
  promptu, na ktorý by appka nemala čo odpovedať (zlyhá rýchlo namiesto
  zaseknutia).
- Timeout 60s, žiadny hang navždy.
- Audit log (`backend/app/audit.py`) zaznamená kto/kedy/aký skript/aký
  stroj/exit kód — **nikdy heslo, nikdy plný výstup** (výstup môže
  obsahovať citlivé dáta z cieľového stroja).

## Dôležitý reálny nález pri testovaní

Pri testovaní proti victusu (kde je sudo fyzicky viazané na FIDO2
hardvérový kľúč, nie heslo — pozri `CLAUDE.md`) sa potvrdilo: **heslom
sa fyzicky-viazané sudo cez SSH vôbec nedá potvrdiť**, žiadna zmena v
appke to nezmení, je to zámerná vlastnosť takto nastaveného stroja.
Overené priamo proti victusu:

- Bez sudo (`bash -s` priamo) — funguje spoľahlivo, rýchlo (~0.5s).
- So zlým/chýbajúcim heslom — `sudo -S` zlyhá čisto s "incorrect
  password attempts", **skript sa nikdy nespustí**, appka to korektne
  nahlási, žiadny hang, žiadny pád.
- Správne heslo na stroji s klasickým password-based sudo (napr. opi) —
  toto si over sám priamo cez appku, keď budeš mať heslo poruke. Nie je
  to niečo, čo by táto session mala/mohla overiť namiesto teba (heslo sa
  nikam nezadáva okrem tvojho vlastného prehliadača).

## Čo appka nerobí (zámerne)

- Neuchováva históriu spustení s plným výstupom (len metadata v audit
  logu).
- Nespúšťa nič automaticky/naplánovane — vždy explicitný klik + potvrdenie.
- Nerieši viac používateľov/rolí — appka má zatiaľ jedno zdieľané heslo,
  takže "kto spustil čo" je momentálne len časová stopa v audit logu, nie
  identita.
