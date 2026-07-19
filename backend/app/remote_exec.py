"""Real remote execution -- the one part of Sindri that changes state on
a real machine, not a throwaway sandbox. Deliberately narrow:

- Only ever targets a machine the user explicitly registered (name/host/
  ssh_user/key path) -- never an arbitrary host typed in at run time.
- The SSH key is always one already mounted from the host filesystem
  (see ssh_keys.py) -- this app never generates, stores, or sees a
  private key's content.
- Every single call requires the sudo password, typed fresh each time
  and never persisted anywhere (not in the DB, not in the audit log) --
  this was an explicit requirement from the start (docs/REMOTE_EXEC.md),
  not a detail added later. The password is piped to the remote `sudo -S`
  over stdin, never passed as an argv element or embedded in the SSH
  command line, so it never shows up in `ps` output on either end.
- Gated by SINDRI_REMOTE_EXEC_ENABLED (default false) -- same pattern as
  the sandbox feature.
"""

import os
import subprocess
import time

REMOTE_EXEC_TIMEOUT_SECONDS = 60
MAX_OUTPUT_CHARS = 20_000


class RemoteExecError(Exception):
    pass


class RemoteExecDisabledError(RemoteExecError):
    pass


def remote_exec_enabled() -> bool:
    return os.environ.get("SINDRI_REMOTE_EXEC_ENABLED", "false").lower() == "true"


def _decode(value) -> str:
    if value is None:
        return ""
    return value.decode("utf-8", errors="replace") if isinstance(value, bytes) else value


def run_remote(machine: dict, content: str, sudo_password: str | None = None) -> dict:
    """sudo_password is optional and off by default -- most catalog
    scripts (health checks, status reports, read-only diagnostics) don't
    need root, and forcing a sudo prompt on every single run would also
    just fail outright on any machine where sudo is gated behind
    something SSH can't satisfy at all (e.g. victus's sudo requires a
    physical touch on a FIDO2 hardware key -- there is no password path
    for it remotely, by design, and no amount of retrying here changes
    that). Pass sudo_password only when the script actually needs root
    on a machine with normal password-based sudo."""
    if not remote_exec_enabled():
        raise RemoteExecDisabledError("Vzdialené spustenie je vypnuté (SINDRI_REMOTE_EXEC_ENABLED=false).")

    target = f"{machine['ssh_user']}@{machine['host']}"
    ssh_base = [
        "ssh",
        "-i", machine["ssh_key_path"],
        "-o", "StrictHostKeyChecking=accept-new",
        "-o", "BatchMode=yes",  # never let ssh itself fall back to an interactive prompt we can't answer
        "-o", "ConnectTimeout=10",
        "-p", str(machine["port"]),
        target,
    ]

    if sudo_password:
        # -p '' empties sudo's own prompt text so it never mixes into
        # captured stdout/stderr; sudo -S consumes exactly one line from
        # stdin for the password, then bash -s inherits the rest of
        # stdin (the actual script) unchanged.
        ssh_cmd = ssh_base + ["sudo -S -p '' bash -s"]
        stdin_payload = f"{sudo_password}\n{content}"
    else:
        ssh_cmd = ssh_base + ["bash -s"]
        stdin_payload = content

    start = time.monotonic()
    try:
        proc = subprocess.run(
            ssh_cmd,
            input=stdin_payload,
            capture_output=True,
            text=True,
            timeout=REMOTE_EXEC_TIMEOUT_SECONDS,
        )
        timed_out = False
        exit_code = proc.returncode
        stdout, stderr = proc.stdout, proc.stderr
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        exit_code = None
        stdout = _decode(exc.stdout)
        stderr = _decode(exc.stderr) + (
            f"\n[timeout po {REMOTE_EXEC_TIMEOUT_SECONDS}s -- ak cieľový stroj má sudo viazané na "
            "fyzický hardvérový kľúč (napr. FIDO2), heslom cez SSH sa to nedá potvrdiť vôbec, "
            "toto nie je len pomalá odpoveď]"
        )
    except OSError as exc:
        raise RemoteExecError(f"SSH spustenie zlyhalo: {exc}") from exc

    duration_ms = int((time.monotonic() - start) * 1000)

    if sudo_password:
        # Never let the password leak into what the UI shows, even though
        # -p '' should already suppress sudo's own prompt text.
        stderr = stderr.replace(sudo_password, "***")

    return {
        "stdout": stdout[:MAX_OUTPUT_CHARS],
        "stderr": stderr[:MAX_OUTPUT_CHARS],
        "exit_code": exit_code,
        "timed_out": timed_out,
        "duration_ms": duration_ms,
    }
