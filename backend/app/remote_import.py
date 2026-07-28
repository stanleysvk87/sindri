"""Pull scripts from a directory on a registered machine over SSH,
mirroring import_utils.py's local scan+confirm shape as closely as
possible so the frontend/UX is the same either way. Reuses
remote_exec.run_remote for the actual SSH call instead of inventing a
second transport -- "scanning" here is just "running a script that
prints file listings", the exact same primitive already used for
everything else.

Content is base64-encoded on the remote side and decoded here, not
transferred as raw text between markers -- avoids any chance of a
script's own content colliding with our delimiter lines.
"""

import base64
import shlex
import subprocess
import time

from app.remote_exec import (
    MAX_TRANSFER_OUTPUT_CHARS,
    RemoteExecError,
    RemoteOutputTruncatedError,
    build_ssh_argv,
    remote_exec_enabled,
    run_remote,
)
from app.secret_scan import looks_like_it_has_a_secret

FILE_START = "===SINDRI_FILE_START==="
FILE_END = "===SINDRI_FILE_END==="
MAX_FILE_BYTES = 2 * 1024 * 1024


def _list_script_command(path: str) -> str:
    quoted = shlex.quote(path)
    return f"""
find {quoted} -type f \\( -name '*.sh' -o -name '*.py' \\) ! -name '*.bak*' 2>/dev/null | while IFS= read -r f; do
  size=$(wc -c < "$f" 2>/dev/null || echo 0)
  if [ "$size" -gt {MAX_FILE_BYTES} ]; then continue; fi
  printf '%s\\n' "{FILE_START}"
  printf '%s\\n' "$f"
  base64 "$f" | tr -d '\\n'
  printf '\\n%s\\n' "{FILE_END}"
done
"""


def _parse_files(output: str) -> tuple[list[dict], list[dict]]:
    """Returns (files, skipped). Nothing is dropped silently any more:
    a block that can't be parsed or decoded (truncated transfer, binary
    junk, a marker line inside a file) comes back in `skipped` with a
    reason, so the caller can surface it instead of quietly returning a
    shorter list than the directory actually contains."""
    files: list[dict] = []
    skipped: list[dict] = []
    for block in output.split(FILE_START)[1:]:
        complete = FILE_END in block
        # each split chunk starts with the newline right after the
        # marker line -- strip exactly that one before splitting into
        # path/content, or lines[0] is an empty string, not the path.
        body = block.split(FILE_END, 1)[0].lstrip("\n")
        lines = body.split("\n", 1)
        path = lines[0].strip() if lines else ""
        if len(lines) != 2 or not path:
            skipped.append({"path": path, "reason": "unparseable block"})
            continue
        if not complete:
            skipped.append({"path": path, "reason": "incomplete transfer (output cut off)"})
            continue
        b64 = lines[1].strip()
        try:
            content = base64.b64decode(b64).decode("utf-8", errors="replace")
        except Exception as exc:
            skipped.append({"path": path, "reason": f"base64 decode failed: {exc}"})
            continue
        files.append({"path": path, "content": content})
    return files, skipped


def _guess_short_description(content: str) -> str:
    lines = content.splitlines()
    idx = 1 if lines and lines[0].startswith("#!") else 0
    for line in lines[idx : idx + 6]:
        stripped = line.strip()
        if stripped.startswith("#"):
            text = stripped.lstrip("#").strip()
            if text:
                return text[:200]
        elif stripped:
            break
    return ""


def scan_remote_path(
    machine: dict, path: str, known_refs: set[str], ssh_password: str | None = None
) -> dict:
    try:
        result = run_remote(
            machine,
            _list_script_command(path),
            None,
            ssh_password,
            # Every file in the directory streams through this one stdout
            # as base64. Under the 20 KB display cap that meant a scan of
            # a real script folder returned HTTP 200 with only the first
            # couple of files and no error at all.
            max_output_chars=MAX_TRANSFER_OUTPUT_CHARS,
        )
    except RemoteExecError as exc:
        raise RemoteExecError(f"Could not scan {path} on {machine.get('host')}: {exc}") from exc
    if result["timed_out"]:
        raise RemoteExecError("Scan timed out -- the directory is probably too large.")
    if result["exit_code"] not in (0, None):
        raise RemoteExecError(result["stderr"][:500] or "Scan failed.")
    if result["stdout_truncated"]:
        raise RemoteOutputTruncatedError(
            f"Scan output exceeded {MAX_TRANSFER_OUTPUT_CHARS} characters and was cut off -- "
            "scan a smaller directory instead of importing a partial, silently incomplete result."
        )

    files, skipped = _parse_files(result["stdout"])
    candidates = []
    for f in files:
        source_ref = f"ssh://{machine.get('name', machine.get('host'))}{f['path']}"
        candidates.append(
            {
                "path": f["path"],
                "name": f["path"].rsplit("/", 1)[-1],
                "short_description": _guess_short_description(f["content"]),
                "size": len(f["content"]),
                "has_possible_secret": looks_like_it_has_a_secret(f["content"]),
                "already_imported": source_ref in known_refs,
                "content": f["content"],
            }
        )
    return {"scanned_dir": path, "candidates": candidates, "skipped": skipped}


def pull_file(machine: dict, remote_path: str, ssh_password: str | None = None) -> str:
    """Read a single file's current content from `machine` over SSH --
    the reverse of push_file, used by the "rescan/refresh from source"
    button to check whether a remote_import script's source has drifted
    since it was imported. Base64 over stdout for the same reason as
    scan_remote_path: no delimiter/content collision risk."""
    quoted_path = shlex.quote(remote_path)
    result = run_remote(
        machine,
        f"base64 {quoted_path}",
        None,
        ssh_password,
        # Same reason as scan_remote_path: this is a base64 payload, not
        # text to read. Under the display cap any file over ~15 KB came
        # back chopped mid-base64 and failed to decode, which surfaced as
        # "could not decode content" -- indistinguishable from a corrupt
        # source file.
        max_output_chars=MAX_TRANSFER_OUTPUT_CHARS,
    )
    if result["timed_out"]:
        raise RemoteExecError("Reading from the source timed out.")
    if result["exit_code"] not in (0, None):
        raise RemoteExecError(result["stderr"][:500] or f"Could not read {remote_path}.")
    if result["stdout_truncated"]:
        raise RemoteOutputTruncatedError(
            f"{remote_path} is larger than the {MAX_TRANSFER_OUTPUT_CHARS}-character transfer "
            "limit -- refusing to store a truncated copy."
        )
    try:
        return base64.b64decode(result["stdout"].strip()).decode("utf-8", errors="replace")
    except Exception as exc:
        raise RemoteExecError(f"Could not decode the content of {remote_path}: {exc}") from exc


def remote_file_exists(machine: dict, remote_path: str, ssh_password: str | None = None) -> bool:
    """Cheap existence check over SSH, used by the orphaned-source scan --
    avoids pulling the whole file just to find out whether it's still
    there."""
    quoted_path = shlex.quote(remote_path)
    result = run_remote(
        machine, f"test -f {quoted_path} && echo EXISTS || echo MISSING", None, ssh_password
    )
    if result["timed_out"]:
        raise RemoteExecError("The file existence check timed out.")
    return "EXISTS" in result["stdout"]


def push_file(
    machine: dict, remote_path: str, content: str, ssh_password: str | None = None
) -> dict:
    """Write `content` to `remote_path` on `machine` over SSH -- the
    other direction of scan_remote_path, for "edit here, send it back"
    (docs/REMOTE_EXEC.md's push/pull round trip). Base64 over stdin, same
    reasoning as scan: avoids any quoting/escaping hazard from the
    script's own content, this time on the way out instead of in.
    Kept separate from run_remote rather than overloading its "run this
    as a script" contract with a second, different meaning -- but it
    shares build_ssh_argv, so key and password machines behave
    identically in both directions."""
    if not remote_exec_enabled():
        raise RemoteExecError("Remote execution is disabled (SINDRI_REMOTE_EXEC_ENABLED=false).")

    quoted_path = shlex.quote(remote_path)
    remote_cmd = f"base64 -d > {quoted_path}"
    b64 = base64.b64encode(content.encode()).decode()

    # Shared with run_remote so auth_type='password' machines work here
    # too -- this used to hardcode `ssh -i <key> -o BatchMode=yes`, which
    # can only ever fail for a machine registered without a key.
    ssh_base, env = build_ssh_argv(machine, ssh_password)
    ssh_cmd = ssh_base + [remote_cmd]

    start = time.monotonic()
    try:
        proc = subprocess.run(
            ssh_cmd, input=b64, capture_output=True, text=True, timeout=30, env=env
        )
    except subprocess.TimeoutExpired as exc:
        raise RemoteExecError(f"Writing to {machine['host']} timed out: {exc}") from exc
    except OSError as exc:
        raise RemoteExecError(f"SSH write failed: {exc}") from exc

    duration_ms = int((time.monotonic() - start) * 1000)
    if proc.returncode != 0:
        stderr = proc.stderr or ""
        if ssh_password:
            stderr = stderr.replace(ssh_password, "***")
        raise RemoteExecError(stderr[:500] or "Writing to the target machine failed.")
    return {"path": remote_path, "duration_ms": duration_ms}
