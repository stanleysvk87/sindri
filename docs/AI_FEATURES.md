# AI generation and review — how it works

Two features: **Generate via AI** (describe what the script should do,
get a draft into the form — nothing is saved automatically, you always
review it before clicking "Add to catalog") and **Review via AI**
(sends an existing script's content off for review — hardcoded
passwords/tokens, dangerous commands, missing quoting).

Both are **optional** — the app is fully functional without them
(catalog, scan/paste import, templates). `GET /api/ai/status` returns
`{"available": false}` if nothing is configured, and the UI simply
hides those buttons.

## Architecture — carried over from Muninn's `ai_engine`

Same pattern as `~/muninn/backend/app/ai_engine/`: an `AIProvider`
protocol with a single method (`complete(prompt) -> str`), three
implementations tried in priority order (`SINDRI_AI_PROVIDER_MODE=auto`):

1. **`claude` CLI** (`shutil.which("claude")`) — runs `claude -p
   <prompt> --output-format json` as a subprocess (`shell=False`, fixed
   argv, 120s timeout). Uses the existing login on the host, no extra
   cost beyond what you already pay for Claude Code/subscription.
2. **`codex` CLI** (`shutil.which("codex")`) — `codex exec <prompt> -s
   read-only --skip-git-repo-check --ephemeral -o <tmpfile>`, same
   logic.
3. **Anthropic API** (`SINDRI_ANTHROPIC_API_KEY`) — a direct
   `anthropic.Anthropic().messages.create(...)` call, a fallback for
   hosts without either CLI.

Detection is automatic (`shutil.which`), nothing to switch manually
unless you want to force a specific provider via
`SINDRI_AI_PROVIDER_MODE`.

## Docker — the CLI mounts in `docker-compose.yml`

CLI providers only work when the backend container can actually see the
`claude`/`codex` binary AND its login state (`~/.claude`, `~/.codex`).
That means bind-mounting personal auth files from the host into the
container — sensitive, and **only works on a host where the CLI is
actually installed and logged in** (not on "any Linux box"), which is
why these mounts are worth understanding before you deploy elsewhere:

- `~/.claude` and `~/.claude.json` as `:ro` — the claude CLI only reads
  these in `-p` mode.
- `~/.codex` **without** `:ro` — codex writes session/app-server state
  on every call, a `:ro` mount would fail with "Read-only file system".
- The binary itself (`claude`/`codex`) is mounted from the host rather
  than installed into the image — simpler than replicating the install
  inside the container.
- The container runs as non-root (UID 1000) — some CLI auth flows
  behave differently or refuse to run as root.

On hosts without the CLI installed, these mounts point at paths that
don't exist yet — Docker will bind-mount them as empty directories
rather than error out, so the app still starts, just without CLI-backed
AI (set `SINDRI_ANTHROPIC_API_KEY` instead for the API-key fallback with
no CLI mounts needed). If that empty-directory side effect bothers you,
comment these five volume lines out entirely; the app works the same
either way with AI simply reported as unavailable.

## Prompt safety

`ai_engine/prompts.py` builds prompts only from text the app itself
controls (the user's description for generation, the script's content
for review) — no `--add-dir` or tools with disk access beyond what's
explicitly in the prompt. The model never gets the ability to run
commands or reach other files on the host through this endpoint.
