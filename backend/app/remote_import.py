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

from app.remote_exec import RemoteExecError, remote_exec_enabled, run_remote
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


def _parse_files(output: str) -> list[dict]:
    files = []
    for block in output.split(FILE_START)[1:]:
        # each split chunk starts with the newline right after the
        # marker line -- strip exactly that one before splitting into
        # path/content, or lines[0] is an empty string, not the path.
        body = block.split(FILE_END, 1)[0].lstrip("\n")
        lines = body.split("\n", 1)
        if len(lines) != 2:
            continue
        path = lines[0].strip()
        b64 = lines[1].strip()
        if not path:
            continue
        try:
            content = base64.b64decode(b64).decode("utf-8", errors="replace")
        except Exception:
            continue
        files.append({"path": path, "content": content})
    return files


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


def scan_remote_path(machine: dict, path: str, known_refs: set[str]) -> dict:
    try:
        result = run_remote(machine, _list_script_command(path), None)
    except RemoteExecError as exc:
        raise RemoteExecError(f"Nepodarilo sa prehľadať {path} na {machine.get('host')}: {exc}") from exc
    if result["timed_out"]:
        raise RemoteExecError("Prehľadávanie vypršalo (timeout) -- priečinok je asi príliš veľký.")
    if result["exit_code"] not in (0, None):
        raise RemoteExecError(result["stderr"][:500] or "Prehľadávanie zlyhalo.")

    candidates = []
    for f in _parse_files(result["stdout"]):
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
    return {"scanned_dir": path, "candidates": candidates}


def pull_file(machine: dict, remote_path: str) -> str:
    """Read a single file's current content from `machine` over SSH --
    the reverse of push_file, used by the "rescan/refresh from source"
    button to check whether a remote_import script's source has drifted
    since it was imported. Base64 over stdout for the same reason as
    scan_remote_path: no delimiter/content collision risk."""
    quoted_path = shlex.quote(remote_path)
    result = run_remote(machine, f"base64 {quoted_path}", None)
    if result["timed_out"]:
        raise RemoteExecError("Čítanie zo zdroja vypršalo (timeout).")
    if result["exit_code"] not in (0, None):
        raise RemoteExecError(result["stderr"][:500] or f"Súbor {remote_path} sa nepodarilo prečítať.")
    try:
        return base64.b64decode(result["stdout"].strip()).decode("utf-8", errors="replace")
    except Exception as exc:
        raise RemoteExecError(f"Obsah {remote_path} sa nepodarilo dekódovať: {exc}") from exc


def remote_file_exists(machine: dict, remote_path: str) -> bool:
    """Cheap existence check over SSH, used by the orphaned-source scan --
    avoids pulling the whole file just to find out whether it's still
    there."""
    quoted_path = shlex.quote(remote_path)
    result = run_remote(machine, f"test -f {quoted_path} && echo EXISTS || echo MISSING", None)
    if result["timed_out"]:
        raise RemoteExecError("Kontrola existencie súboru vypršala (timeout).")
    return "EXISTS" in result["stdout"]


def push_file(machine: dict, remote_path: str, content: str) -> dict:
    """Write `content` to `remote_path` on `machine` over SSH -- the
    other direction of scan_remote_path, for "edit here, send it back"
    (docs/REMOTE_EXEC.md's push/pull round trip). Base64 over stdin, same
    reasoning as scan: avoids any quoting/escaping hazard from the
    script's own content, this time on the way out instead of in.
    Reuses run_remote's timeout/auth-type "auto (docs/REMOTE_EXEC.md)"
    handling isn't needed here -- this is a small enough primitive to
    keep separate rather than overload run_remote's "run this as a
    script" contract with a second, different meaning."""
    if not remote_exec_enabled():
        raise RemoteExecError("Vzdialené spustenie je vypnuté (SINDRI_REMOTE_EXEC_ENABLED=false).")

    quoted_path = shlex.quote(remote_path)
    remote_cmd = f"base64 -d > {quoted_path}"
    b64 = base64.b64encode(content.encode()).decode()

    target = f"{machine['ssh_user']}@{machine['host']}"
    ssh_cmd = [
        "ssh",
        "-i", machine["ssh_key_path"],
        "-o", "StrictHostKeyChecking=accept-new",
        "-o", "BatchMode=yes",
        "-o", "ConnectTimeout=10",
        "-p", str(machine["port"]),
        target,
        remote_cmd,
    ]

    start = time.monotonic()
    try:
        proc = subprocess.run(ssh_cmd, input=b64, capture_output=True, text=True, timeout=30)
    except subprocess.TimeoutExpired as exc:
        raise RemoteExecError(f"Zápis na {machine['host']} vypršal (timeout): {exc}") from exc
    except OSError as exc:
        raise RemoteExecError(f"SSH zápis zlyhal: {exc}") from exc

    duration_ms = int((time.monotonic() - start) * 1000)
    if proc.returncode != 0:
        raise RemoteExecError(proc.stderr[:500] or "Zápis na cieľový stroj zlyhal.")
    return {"path": remote_path, "duration_ms": duration_ms}
