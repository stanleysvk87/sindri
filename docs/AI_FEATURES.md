# AI generovanie a review — ako to funguje

Dve funkcie: **Vygenerovať cez AI** (popíšeš čo skript má robiť, dostaneš
draft do formulára — nič sa neuloží automaticky, vždy si to skontroluješ
predtým, než klikneš "Pridať do katalógu") a **Skontrolovať cez AI**
(pošle obsah existujúceho skriptu na review — heslá/tokeny natvrdo v
kóde, nebezpečné príkazy, chýbajúce quotovanie).

Obe sú **voliteľné** — appka funguje plnohodnotne aj bez nich (katalóg,
scan/paste import, šablóny). `GET /api/ai/status` vracia
`{"available": false}`, ak nie je nič nakonfigurované, a UI potom tie
tlačidlá jednoducho neukáže.

## Architektúra — prevzaté z Muninn `ai_engine`

Rovnaký vzor ako v `~/muninn/backend/app/ai_engine/`: `AIProvider`
protokol s jednou metódou (`complete(prompt) -> str`), tri implementácie
v poradí priority (`SINDRI_AI_PROVIDER_MODE=auto`):

1. **`claude` CLI** (`shutil.which("claude")`) — spúšťa `claude -p
   <prompt> --output-format json` ako subprocess (`shell=False`, pevný
   argv, timeout 120s). Používa existujúce prihlásenie na hostiteľovi,
   žiadny extra náklad nad rámec toho, čo už platíš za Claude Code/
   subscription.
2. **`codex` CLI** (`shutil.which("codex")`) — `codex exec <prompt> -s
   read-only --skip-git-repo-check --ephemeral -o <tmpfile>`, rovnaká
   logika.
3. **Anthropic API** (`SINDRI_ANTHROPIC_API_KEY`) — priamy
   `anthropic.Anthropic().messages.create(...)` call, fallback pre hosty
   bez CLI.

Detekcia je automatická (`shutil.which`), nič netreba ručne prepínať,
pokiaľ nechceš vynútiť konkrétny provider cez `SINDRI_AI_PROVIDER_MODE`.

## Docker — prečo sú CLI mounty v `docker-compose.yml` zakomentované

CLI providery fungujú len vtedy, keď backend kontajner reálne vidí
`claude`/`codex` binárku AJ jej prihlásenie (`~/.claude`, `~/.codex`).
To znamená bind-mount osobných auth súborov z hostiteľa do kontajnera —
citlivé, a **funguje to len na hostiteľovi, kde je CLI reálne
nainštalované a prihlásené** (nie na "hocijakom Linuxe", preto je to
mimo defaultu):

- `~/.claude` a `~/.claude.json` ako `:ro` — claude CLI ich pri `-p`
  režime len číta.
- `~/.codex` **bez** `:ro` — codex zapisuje session/app-server stav pri
  každom volaní, `:ro` mount by zlyhal na "Read-only file system".
- Samotná binárka (`claude`/`codex`) sa mountuje z hostiteľa, nie
  inštaluje do image — jednoduchšie ako replikovať inštaláciu vo vnútri
  kontajnera.
- Kontajner beží ako non-root (UID 1000) — niektoré CLI auth flow sa
  správajú inak/odmietajú fungovať pod rootom.

Na hostiteľoch bez nainštalovaného CLI (typický "cudzí" Linux server)
appka jednoducho beží ďalej bez AI funkcií, alebo nastav
`SINDRI_ANTHROPIC_API_KEY` pre API-key fallback bez potreby CLI mountov.

## Bezpečnosť promptov

`ai_engine/prompts.py` stavia prompty len z textu, ktorý appka sama
kontroluje (popis od používateľa pre generovanie, obsah skriptu pre
review) — žiadne `--add-dir`/nástroje s prístupom na disk mimo toho, čo
je explicitne v prompte. Model nikdy nedostane prístup k spúšťaniu
príkazov ani k iným súborom na hostiteľovi cez tento endpoint.
