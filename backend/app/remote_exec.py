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

# Cap for output that a human is going to READ in the UI (a script's
# stdout/stderr). Purely a display guard -- truncation here is expected
# and is now reported back via stdout_truncated/stderr_truncated instead
# of silently cutting the text off.
MAX_OUTPUT_CHARS = 20_000

# Cap for output that is DATA, not something to read: base64 file
# payloads for remote scan/import (app/remote_import.py). The display cap
# used to apply here too, which silently threw away every file past the
# first ~20 KB of a scan and corrupted any single file over ~15 KB on
# rescan. Sized to comfortably hold MAX_FILE_BYTES (2 MB) worth of base64
# plus a directory's worth of markers; anything past it raises instead of
# quietly returning a partial result.
MAX_TRANSFER_OUTPUT_CHARS = 64 * 1024 * 1024


class RemoteExecError(Exception):
    pass


class RemoteExecDisabledError(RemoteExecError):
    pass


class RemoteOutputTruncatedError(RemoteExecError):
    """The remote command produced more output than the caller allowed.
    Only raised on the data-transfer paths (scan/pull), where a partial
    result is worse than a hard error -- it looks like success."""


def remote_exec_enabled() -> bool:
    return os.environ.get("SINDRI_REMOTE_EXEC_ENABLED", "false").lower() == "true"


def _decode(value) -> str:
    if value is None:
        return ""
    return value.decode("utf-8", errors="replace") if isinstance(value, bytes) else value


def build_ssh_argv(machine: dict, ssh_password: str | None = None) -> tuple[list[str], dict | None]:
    """Build the SSH argv prefix (everything up to and including the
    target) plus the env the subprocess needs, honoring the machine's
    auth_type. Shared by run_remote and remote_import.push_file so a
    password-auth machine works the same way in both directions --
    push_file used to hardcode `ssh -i <key> -o BatchMode=yes`, which can
    never succeed for a machine registered with auth_type='password'
    (its ssh_key_path is empty by design)."""
    auth_type = machine.get("auth_type", "key")
    if auth_type == "password" and not ssh_password:
        raise RemoteExecError(
            "This machine uses password authentication -- an SSH password is required."
        )
    if auth_type != "password" and not machine.get("ssh_key_path"):
        raise RemoteExecError(
            "This machine has no SSH key configured -- re-register it with a mounted key."
        )

    target = f"{machine['ssh_user']}@{machine['host']}"
    ssh_opts = [
        "-o", "StrictHostKeyChecking=accept-new",
        "-o", "BatchMode=yes" if auth_type == "key" else "BatchMode=no",
        "-o", "ConnectTimeout=10",
        "-p", str(machine["port"]),
    ]

    if auth_type == "password":
        # sshpass -e reads the password from $SSHPASS -- never argv, never
        # written to disk. BatchMode must be "no" here or ssh refuses to
        # even try password auth.
        return ["sshpass", "-e", "ssh", *ssh_opts, target], {**os.environ, "SSHPASS": ssh_password}
    return ["ssh", "-i", machine["ssh_key_path"], *ssh_opts, target], None


def run_remote(
    machine: dict,
    content: str,
    sudo_password: str | None = None,
    ssh_password: str | None = None,
    max_output_chars: int = MAX_OUTPUT_CHARS,
) -> dict:
    """sudo_password is optional and off by default -- most catalog
    scripts (health checks, status reports, read-only diagnostics) don't
    need root, and forcing a sudo prompt on every single run would also
    just fail outright on any machine where sudo is gated behind
    something SSH can't satisfy at all (e.g. victus's sudo requires a
    physical touch on a FIDO2 hardware key -- there is no password path
    for it remotely, by design, and no amount of retrying here changes
    that). Pass sudo_password only when the script actually needs root
    on a machine with normal password-based sudo.

    ssh_password is for machines with auth_type='password' (no key
    mounted) -- also never persisted, entered fresh per run, same rule as
    sudo_password. Needs `sshpass` since plain openssh has no
    non-interactive password path; passed via the SSHPASS env var (`-e`),
    never as a CLI arg, so it never shows up in `ps` output.

    max_output_chars caps how much stdout/stderr is returned. The default
    is the human-readable display cap; callers moving DATA (base64 file
    payloads) pass MAX_TRANSFER_OUTPUT_CHARS. Either way the result says
    whether truncation happened -- see stdout_truncated/stderr_truncated."""
    if not remote_exec_enabled():
        raise RemoteExecDisabledError("Remote execution is disabled (SINDRI_REMOTE_EXEC_ENABLED=false).")

    ssh_base, env = build_ssh_argv(machine, ssh_password)

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
            env=env,
        )
        timed_out = False
        exit_code = proc.returncode
        stdout, stderr = proc.stdout, proc.stderr
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        exit_code = None
        stdout = _decode(exc.stdout)
        stderr = _decode(exc.stderr) + (
            f"\n[timed out after {REMOTE_EXEC_TIMEOUT_SECONDS}s -- if the target machine's sudo is "
            "bound to a physical hardware key (e.g. FIDO2), no SSH password can ever confirm it; "
            "this is not just a slow response]"
        )
    except OSError as exc:
        raise RemoteExecError(f"SSH execution failed: {exc}") from exc

    duration_ms = int((time.monotonic() - start) * 1000)

    if sudo_password:
        # Never let the password leak into what the UI shows, even though
        # -p '' should already suppress sudo's own prompt text.
        stderr = stderr.replace(sudo_password, "***")
    if ssh_password:
        stdout = stdout.replace(ssh_password, "***")
        stderr = stderr.replace(ssh_password, "***")

    stdout_truncated = len(stdout) > max_output_chars
    stderr_truncated = len(stderr) > max_output_chars

    return {
        "stdout": stdout[:max_output_chars],
        "stderr": stderr[:max_output_chars],
        "exit_code": exit_code,
        "timed_out": timed_out,
        "duration_ms": duration_ms,
        # Truncation is never silent any more: the UI can say "output was
        # cut off", and the scan/import paths turn it into a hard error
        # (see remote_import.py) instead of returning half a directory.
        "stdout_truncated": stdout_truncated,
        "stderr_truncated": stderr_truncated,
    }
