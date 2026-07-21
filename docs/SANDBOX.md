# Sandbox execution — how and why

**Test in sandbox** runs a script's content in a one-off, isolated
Docker container and returns stdout/stderr/exit code. Off by default
(`SINDRI_SANDBOX_ENABLED=false`) — the app is fully functional without
it, this is an optional feature.

## Enabling it — 3 steps, not 1

1. `SINDRI_SANDBOX_ENABLED=true` in `.env`.
2. Uncomment `/var/run/docker.sock:/var/run/docker.sock` in
   `docker-compose.yml`.
3. **Set `SINDRI_DOCKER_GID` in `.env`** to the GID of the `docker`
   group on THIS host (`getent group docker | cut -d: -f3` — this
   differs machine to machine, we've seen both 995 and 136 on two real
   deployments). Without this step, even with the mount uncommented,
   the app fails with `PermissionError(13, 'Permission denied')` when
   touching `docker.sock` — the backend runs as non-root UID 1000
   (`backend/Dockerfile`), which without an explicit `group_add` is not
   a member of the host's `docker` group even though it can see the
   socket via the bind mount.

Check via `GET /api/sandbox/status` — `{"available": true}` means all 3
steps are in place.

**This is NOT the same as "Run remotely"** (see `docs/REMOTE_EXEC.md`).
The key difference: a sandbox run is one-off and disposable — no access
to real data/network/services, no lasting effect. That's what makes it
safe to implement as a real feature instead of just a stated intent.

## Isolation per run

Every run is a fresh container with (see `backend/app/sandbox.py`):

- `network_disabled` — no network access at all.
- `mem_limit=128m`, `memswap_limit=128m` — a hard cap, no extra swap.
  Exceeding it triggers an OOM kill (exit code 137).
- `nano_cpus=500_000_000` (0.5 CPU) — limited compute.
- `pids_limit=50` — a fork bomb stops at the process limit instead of
  growing unbounded.
- `read_only=True` + `tmpfs /tmp` (16MB, `noexec,nosuid`) — writes are
  only possible to a scratch `/tmp`, nowhere else, and nothing there can
  be executed as a binary.
- `cap_drop=["ALL"]` + `security_opt=["no-new-privileges"]` — no extra
  Linux capabilities, no privilege escalation.
- `user="65534:65534"` (nobody) — never root inside the container.
- 15s timeout (`container.wait(timeout=...)`); if exceeded, the
  container is killed explicitly (`container.kill()`), not just left
  running in the background.
- `container.remove(force=True)` in a `finally` block — no containers
  pile up even if an earlier step fails.

All 8 properties above were verified before deployment with direct
tests against a real Docker daemon (not just code review): non-root
execution, network blocked (a `wget` attempt failed), writing outside
`/tmp` failed with "Read-only file system", writing to `/tmp` worked, a
30s run was killed at ~15s and the container was cleaned up, a fork
bomb was stopped by `pids_limit` within 1s instead of overwhelming the
host, and a 500MB allocation against the 128m limit ended in an OOM
kill (exit 137, no leftover container).

## What the isolation does NOT solve — an important trade-off

The app's backend needs access to the host's `/var/run/docker.sock` to
be able to spin up these "sibling" containers (Docker-outside-of-Docker).
**Whoever has access to `docker.sock` has practically root-equivalent
access to the host** — that's a property of the backend deployment
itself, not of any individual sandbox run. Because of that:

- The mount is commented out by default in `docker-compose.yml`, same
  as `SINDRI_SANDBOX_ENABLED=false`.
- Only enable this on a host where you trust the app's backend (and
  anything that might end up inside it — e.g. via a dependency
  vulnerability) to have that level of access.
- The app itself (the auth password, the HTTP endpoints) doesn't give a
  logged-in user anything beyond running scripts in an isolated
  container — but the security of the whole setup lives and dies with
  who can reach the backend process.

## Image choice by script type

Detected from the first line (shebang) — `python` in the shebang →
`python:3.12-slim`, otherwise `bash:5`. Can be forced explicitly
(`script_type` in the request) if detection fails.

## An important limitation — the sandbox is not a copy of the host

`bash:5`/`python:3.12-slim` are **minimal** images — just bash/python
plus coreutils, nothing more. Scripts that call system tools like
`journalctl`, `systemctl`, `docker`, `ss`, `ip`, or anything that
assumes a running systemd/network/real host files, will fail in the
sandbox with "command not found" or empty output — **this is not an app
bug, nor a bug in the script**, just a consequence of the sandbox being
deliberately bare and offline (see above). The exit code for a run like
that is still often `0` (bash keeps going after "command not found"
unless the script has `set -e`), so "EXIT 0" in the output header does
not mean the script did what it was supposed to — always read the
actual stdout/stderr text underneath it.

The sandbox is good for checking a script's **logic/safety** (syntax,
dangerous commands, what the script attempts to do), not for a full
simulation of running on a specific machine — that's what "Run
remotely" (`docs/REMOTE_EXEC.md`) is for, which runs directly on a real
registered machine with all of its tools available.
