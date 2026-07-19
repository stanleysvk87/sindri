# Sandbox execution — ako a prečo

**Testovať v sandboxe** spustí obsah skriptu v jednorazovom, izolovanom
Docker kontajneri a vráti stdout/stderr/exit code. Vypnuté defaultne
(`SINDRI_SANDBOX_ENABLED=false`) — appka bez toho funguje plnohodnotne,
je to voliteľná funkcia.

**Toto NIE JE to isté ako "Spustiť na diaľku"** (ten placeholder ostáva
natrvalo disabled, pozri `docs/REMOTE_EXEC.md`). Kľúčový rozdiel:
sandbox beh je jednorazový a zahoditeľný — žiadny prístup k reálnym
dátam/sieti/službám, žiadny trvalý dopad. Preto sa to dá bezpečne
implementovať ako reálnu funkciu, nie len zapísaný zámer.

## Izolácia jedného behu

Každý beh je nový kontajner s (over v `backend/app/sandbox.py`):

- `network_disabled` — žiadny sieťový prístup vôbec.
- `mem_limit=128m`, `memswap_limit=128m` — tvrdý strop, žiadny swap
  navyše. Prekročenie = OOM kill (exit code 137).
- `nano_cpus=500_000_000` (0.5 CPU) — obmedzený výpočtový výkon.
- `pids_limit=50` — fork bomba sa zastaví na limite procesov, nie
  neobmedzene rastie.
- `read_only=True` + `tmpfs /tmp` (16MB, `noexec,nosuid`) — zápis je
  možný len do dočasného `/tmp`, nikde inde, a nič odtiaľ sa nedá
  spustiť ako binárka.
- `cap_drop=["ALL"]` + `security_opt=["no-new-privileges"]` — žiadne
  Linux capabilities navyše, žiadna eskalácia oprávnení.
- `user="65534:65534"` (nobody) — nikdy root vnútri kontajnera.
- Timeout 15s (`container.wait(timeout=...)`), pri prekročení sa
  kontajner explicitne zabije (`container.kill()`), nie len necháva
  bežať na pozadí.
- `container.remove(force=True)` vo `finally` bloku — žiadne kontajnery
  sa nehromadia, aj keby predchádzajúce kroky zlyhali.

Všetkých 8 vyššie uvedených vlastností bolo pred nasadením overených
priamymi testami proti reálnemu Docker daemonovi (nie len code review):
non-root beh, blokovaná sieť (pokus o `wget` zlyhal), zápis mimo `/tmp`
zlyhal na "Read-only file system", zápis do `/tmp` fungoval, timeout
zabil 30s beh presne po ~15s a kontajner sa upratal, fork bomba sa
zastavila na `pids_limit` do 1s namiesto zahltenia hostiteľa, alokácia
500MB pri limite 128m skončila OOM killom (exit 137, žiadny leftover
kontajner).

## Čo izolácia NERIEŠI — dôležitý trade-off

Backend appky potrebuje prístup k `/var/run/docker.sock` hostiteľa, aby
vedel spúšťať tieto "sesterské" kontajnery (Docker-outside-of-Docker).
**Kto má prístup k `docker.sock`, má prakticky root ekvivalent na
hostiteľovi** — to je vlastnosť samotného backend deploymentu, nie
jednotlivého sandbox behu. Preto:

- Mount je v `docker-compose.yml` zakomentovaný defaultne, rovnako ako
  `SINDRI_SANDBOX_ENABLED=false`.
- Odomkni to len na hostiteľovi, kde dôveruješ tomu, že backend appky
  (a čokoľvek, čo by sa doňho prípadne dostalo — napr. cez zraniteľnosť
  v závislosti) má túto úroveň prístupu.
- Appka samotná (auth heslo, HTTP endpointy) nedáva používateľovi nič
  navyše nad rámec spúšťania skriptov v izolovanom kontajneri — ale
  bezpečnosť tohto celku stojí a padá s tým, kto sa vie dostať k
  backend procesu.

## Voľba image podľa typu skriptu

Detekcia z prvého riadku (shebang) — `python` v shebangu → `python:3.12-
slim`, inak `bash:5`. Dá sa vynútiť explicitne (`script_type` v
requeste), keby detekcia zlyhala.
