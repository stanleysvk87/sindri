# Sindri

Self-hosted script catalog — search (by what a script does, not just its
name), import existing scripts (pick from a scanned folder, or paste
content), optional AI generation and review (via an existing `claude`/
`codex` CLI login, or an Anthropic API key), and **~119 built-in scripts/
references as a starter kit** (~29 generic Linux admin scripts + a
~90-entry cheatsheet spanning Docker, systemd, git, network diagnostics,
Windows/PowerShell, macOS, Python, databases, and more). The UI is
bilingual (Slovak/English, toggle in the header).

Named after Sindri, the dwarven blacksmith from Norse mythology who
forged Mjölnir and other legendary artifacts for the gods.

<p float="left">
  <img src="docs/screenshots/catalog.png" width="49%" alt="Script catalog" />
  <img src="docs/screenshots/script-detail.png" width="49%" alt="Script detail view" />
</p>
<p float="left">
  <img src="docs/screenshots/catalog-en.png" width="49%" alt="Catalog view, English UI" />
</p>

## Quick start

```bash
cp .env.example .env   # set SINDRI_PASSWORD
docker compose up -d --build
```

The app runs on `http://localhost:8420` (port configurable via
`SINDRI_PORT` in `.env`). Optional features (AI, sandbox, remote
execution) each have their own enable steps — see `docs/AI_FEATURES.md`,
`docs/SANDBOX.md`, `docs/REMOTE_EXEC.md`.

## What it does

- **Catalog**: search/filter by machine and clickable tag chips
  (multi-select), fulltext search that includes script content (not just
  name/description), reference collections (cheatsheet/pentest) group
  into collapsible categories, syntax highlighting in content view.
- **Import**: scan a folder (local mount) and pick which scripts to add
  (with a warning if one looks like it contains a hardcoded password/
  token), or paste content manually — both paths also work over SSH
  against a registered remote machine.
- **AI generate/review** (optional, the app works fully without it): see
  `docs/AI_FEATURES.md`.
- **Sandbox testing** (optional, off by default): isolated, throwaway
  container with no network/hard limits — see `docs/SANDBOX.md`.
- **Remote execution over SSH** (optional, off by default): runs a
  script on a registered machine (individually or on all of them at
  once); the sudo password (if needed) is entered fresh on every run and
  is never stored — see `docs/REMOTE_EXEC.md`.
- **Push back**: overwrites the source file on a registered machine with
  the current catalog content (the reverse of import).
- **Content history and rollback**: every content change (manual edit,
  restore from source, AI rewrite) is snapshotted as a version before
  being overwritten; diff against the current content and one-click
  restore, nothing is ever lost.
- **Restore from source with a diff**: for imported scripts, shows
  exactly what changed since import (added/removed lines), not just a
  yes/no "changed" flag.
- **Orphaned-record detection**: checks whether the source file of an
  imported script still exists (locally directly, remotely over SSH if
  remote execution is enabled).
- **Schedule-vs-reality check**: compares the catalog's "run mode" field
  against the actual `crontab`/systemd timer setup on registered
  machines — surfaces drift between what the catalog claims and what
  actually runs.
- **Tag management**: a dedicated page to rename/delete a tag across the
  whole catalog in one place, not just per script.
- **Catalog export**: the entire catalog content as a downloadable JSON
  file.
- **Login brute-force lockout**: 5 failed attempts / 15 min locks out
  that IP address.
- **Settings**: managed machine registry, paginated audit log (who/when/
  which script/which machine, never the password or full output),
  catalog overview.

## Structure

- `backend/` — FastAPI + SQLite
- `frontend/` — React + Tailwind, a lightweight custom i18n
  (`frontend/src/i18n/`)
- `docs/` — architectural decisions and the reasoning behind them
- `import-sources/` — mount folders here that the app should be able to
  scan (see `import-sources/README.md`)

## License

Apache License 2.0 — see [`LICENSE`](./LICENSE).

## Note on git history

This repository was deliberately local-only for a long time (no GitHub
remote). The conscious decision to put it on GitHub landed on
2026-07-20.
