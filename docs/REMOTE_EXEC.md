# Remote execution — planned, not built

Zámer: raz vedieť spustiť katalogizovaný skript na diaľku priamo z UI,
nie len skopírovať a spustiť ručne v termináli. Zapísané 2026-07-19 na
základe požiadavky usera — **explicitne ako budúca, zatiaľ vypnutá
funkcia**, nie niečo na implementáciu teraz.

## Prečo to (zatiaľ) neexistuje

Pri návrhu tohto projektu sme si overili architektúru Heimdallu
(MidgardOps), ktorý má na presne tento problém — spúšťanie príkazov na
spravovaných strojoch — už poriadne premyslený bezpečnostný model:
`actions/safe_subprocess.py` tam vynucuje pevný, ručne recenzovaný
zoznam povolených spustiteľných príkazov, `shell=False`, žiadnu shell
interpretáciu, timeouty, orezaný výstup. Nikdy nespúšťa "ľubovoľný text,
ktorý niekto vložil do databázy" — len vopred definované, parametrizované
akcie (napr. `docker restart <id>`, `systemctl restart <service>`).

Tento katalóg skriptov je z podstaty iný prípad: obsahuje presne
"ľubovoľný text, ktorý niekto vložil" (importom alebo paste). Spustiť to
na diaľku jedným klikom z web UI by bola úplne iná dôveryhodnostná
hranica než čokoľvek v Heimdalli — v podstate primitívum na vzdialené
spustenie kódu. To sa nemá robiť narýchlo/mimochodom.

## Čo je pripravené už teraz

- `GET /api/settings` vracia `remote_exec_enabled` (default `false`,
  cez `SINDRI_REMOTE_EXEC_ENABLED` env var) — **žiadny kód, ktorý by
  túto hodnotu využil na skutočné spustenie, zatiaľ neexistuje.**
- Frontend zobrazí tlačidlo "Spustiť na diaľku" ako trvalo disabled s
  tooltipom, prečo (pozri nižšie), bez ohľadu na hodnotu flagu — flag je
  len na to, aby sa dal neskôr vedome zapnúť súbežne s implementáciou,
  nie na to, aby si ho niekto omylom nastavil na `true` a čakal že to
  niečo urobí.

## Čo by to vyžadovalo pred reálnou implementáciou

1. Explicitné overenie sudo hesla pri KAŽDOM spustení (nie len raz pri
   prihlásení do appky) — presne to user pri zadaní požadoval.
2. Vlastný, ručne recenzovaný spôsob spustenia (žiadny `shell=True`,
   žiadny priamy `subprocess` nad ľubovoľným DB textom) — inšpirovať sa
   `safe_subprocess.py` z Heimdallu, ideálne ako zdieľaný/portovaný kód
   pri neskoršom napojení na MidgardOps.
3. Audit log každého spustenia (kto, kedy, aký skript, aký výstup).
4. Rozhodnutie, na ktorom stroji sa to reálne vykoná (SSH z appky? Agent
   ako Heimdallov `midgard_agent`? To je architektonická otázka na
   samostatné doriešenie, nie súčasť tohto zápisu.)

Toto je vedomé budúce rozhodnutie, nie automatický "zapneme keď bude
čas" krok.
