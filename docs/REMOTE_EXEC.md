# Remote execution — implemented 2026-07-19

Runs a catalogued script's content on a registered machine over SSH.
Off by default (`SINDRI_REMOTE_EXEC_ENABLED=false`) — the app is fully
functional without it. This is the only feature that actually changes
state on another machine, rather than just reading/testing in isolation
(unlike `docs/SANDBOX.md`, which runs in a throwaway container with no
lasting effect).

## Security properties (see `backend/app/remote_exec.py`)

- **Always against a pre-registered machine** — never a path/IP typed in
  ad hoc at run time. Registry in `backend/app/machines.py` (Settings →
  Managed machines).
- **SSH key is always just mounted from the host** — the app never
  generates or stores key material itself. `backend/app/ssh_keys.py`
  only lists which keys exist at the mounted path (`GET
  /api/machines/available-keys`); the "add machine" form picks from
  that list.
- **The sudo password (if used) is entered fresh on EVERY run**, never
  stored — not in the DB, not in the audit log. It's sent over SSH via
  `sudo -S` on stdin (not as a command argument), so it never shows up
  in a process listing (`ps`) on either side.
- **Sudo is optional, not forced on every run** — most catalogued
  scripts (health checks, status dumps) don't need root. Forcing a sudo
  password on every run would also simply fail on some machines (see
  below).
- `SSH BatchMode=yes` — the SSH client never falls into an interactive
  prompt the app has no way to answer (fails fast instead of hanging).
- 60s timeout, no indefinite hang.
- Audit log (`backend/app/audit.py`) records who/when/which script/which
  machine/exit code — **never the password, never the full output**
  (output can contain sensitive data from the target machine).

## An important real finding from testing

Testing against a machine where sudo is physically bound to a FIDO2
hardware key (not a password) confirmed: **hardware-bound sudo simply
cannot be satisfied with a password over SSH** — no change in the app
changes that, it's an intentional property of that machine's setup.
Verified directly against it:

- Without sudo (`bash -s` directly) — works reliably, fast (~0.5-1.8s).
- **A quirk worth knowing**: the very first connection to a new machine
  (while the container is still establishing `~/.ssh/known_hosts`) can
  eat the entire timeout once. A second attempt right after was fast and
  reliable — if the first run against a new machine looks stuck, retry
  it before assuming something else is wrong.
- With a wrong/missing password — `sudo -S` fails cleanly with
  "incorrect password attempts", **the script never runs**, the app
  reports it correctly, no hang, no crash.
- Correct password on a machine with classic password-based sudo — try
  this yourself directly through the app once you have the password
  handy. Not something that could be verified from the outside (the
  password is never entered anywhere except your own browser).

## What the app deliberately does not do

- Doesn't keep a run history with full output (only metadata in the
  audit log).
- Doesn't run anything automatically/on a schedule — always an explicit
  click + confirmation.
- Doesn't handle multiple users/roles — the app currently has one shared
  password, so "who ran what" is just a timestamp trail in the audit
  log, not an identity.
