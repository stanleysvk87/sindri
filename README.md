# Sindri

Self-hosted katalóg skriptov — prehľadávanie (aj podľa toho, čo skript
robí, nie len podľa mena), import existujúcich skriptov (výberom z
prehľadaného priečinka, alebo vložením obsahu), voliteľné AI generovanie
a review (cez existujúce `claude`/`codex` CLI prihlásenie, alebo
Anthropic API kľúč), a ~29 vstavaných univerzálnych Linux skriptov ako
štartovací balík.

Meno po Sindrim, trpasličom kováčovi zo severskej mytológie, ktorý
vykoval Mjölnir a ďalšie legendárne artefakty pre bohov.

## Rýchly štart

```bash
cp .env.example .env   # uprav SINDRI_PASSWORD
docker compose up -d --build
```

Appka beží na `http://localhost:8420` (port nastaviteľný cez
`SINDRI_PORT` v `.env`).

## Čo appka vie

- **Katalóg**: hľadanie/filter podľa stroja a klikacích tag chipov
  (multi-select), fulltext hľadanie aj v obsahu skriptu, nielen v
  mene/popise.
- **Import**: prehľadaj priečinok (lokálny mount) a vyber, ktoré skripty
  pridať (s varovaním, ak niektorý vyzerá, že obsahuje heslo/token),
  alebo vlož obsah ručne.
- **AI generovanie/review** (voliteľné, appka funguje aj bez toho): pozri
  `docs/AI_FEATURES.md`.
- **Sandbox testovanie** (voliteľné, vypnuté defaultne): izolovaný
  jednorazový kontajner bez siete/s limitmi, pozri `docs/SANDBOX.md`.
- **Vzdialené spustenie cez SSH** (voliteľné, vypnuté defaultne):
  spustí skript na zaregistrovanom stroji, sudo heslo (ak treba) sa
  zadáva nanovo pri každom behu, nikdy sa neukladá — pozri
  `docs/REMOTE_EXEC.md`.
- **Nastavenia**: register spravovaných strojov, audit log (kto/kedy/aký
  skript/aký stroj, nikdy heslo ani plný výstup), prehľad katalógu.

## Štruktúra

- `backend/` — FastAPI + SQLite
- `frontend/` — React + Tailwind
- `docs/` — architektonické rozhodnutia a ich dôvody
- `import-sources/` — sem mountuj priečinky, ktoré appka má vedieť
  prehľadávať (pozri `import-sources/README.md`)

## Poznámka ku git politike

Tento repozitár zostáva zámerne len lokálny (žiadny GitHub remote), kým
appka nedosiahne stav, kedy je jasné rozhodnutie ísť s ňou verejne von.
