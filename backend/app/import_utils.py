import os
from datetime import datetime, timezone
from pathlib import Path

from app.db import get_conn
from app.secret_scan import looks_like_it_has_a_secret

SCRIPT_EXTENSIONS = {".sh", ".py"}
SKIP_DIR_NAMES = {
    ".git", "node_modules", "__pycache__", ".venv", "venv",
    "dist", "build", ".pytest_cache",
}
MAX_FILE_BYTES = 2 * 1024 * 1024

# Local scan/import is only ever supposed to reach paths the operator
# deliberately bind-mounted for this purpose (docker-compose.yml's
# import-sources volume, see import-sources/README.md -- extra folders
# are documented as extra mounts nested under the same /import-sources
# prefix). Without this check, an authenticated user could point
# scan_path/confirm_import at any path the container filesystem can see
# (e.g. /app, or the read-only ~/.ssh / ~/.claude mounts used by other
# features) -- the .sh/.py extension filter narrows what comes back, but
# containment should be enforced up front, not left to that filter alone.
IMPORT_ALLOWED_ROOTS = tuple(
    Path(p).resolve()
    for p in os.environ.get("SINDRI_IMPORT_ALLOWED_ROOTS", "/import-sources").split(":")
    if p
)


class ImportPathNotAllowedError(Exception):
    pass


def _ensure_allowed_root(root: Path) -> None:
    if not any(root == allowed or allowed in root.parents for allowed in IMPORT_ALLOWED_ROOTS):
        raise ImportPathNotAllowedError(
            f"{root} is outside the allowed import root(s) "
            f"({', '.join(str(r) for r in IMPORT_ALLOWED_ROOTS)})"
        )


def _iter_script_files(root: Path):
    for path in sorted(root.rglob("*")):
        if path.is_dir():
            continue
        if any(part in SKIP_DIR_NAMES for part in path.parts):
            continue
        if path.suffix not in SCRIPT_EXTENSIONS:
            continue
        if ".bak" in path.name:
            continue
        if path.stat().st_size > MAX_FILE_BYTES:
            continue
        yield path


def _guess_short_description(content: str) -> str:
    lines = content.splitlines()
    idx = 0
    if lines and lines[0].startswith("#!"):
        idx = 1
    for line in lines[idx : idx + 6]:
        stripped = line.strip()
        if stripped.startswith("#"):
            text = stripped.lstrip("#").strip()
            if text:
                return text[:200]
        elif stripped:
            break
    return ""


def _already_imported_paths(conn) -> set[str]:
    rows = conn.execute(
        "SELECT source_ref FROM scripts WHERE source_type = 'local_import'"
    ).fetchall()
    return {r["source_ref"] for r in rows}


def scan_path(root_path: str) -> dict:
    """Read-only: list script files found under a directory, without
    importing anything. Lets the UI show a checklist so the user picks
    which ones actually get added to the catalog."""
    root = Path(root_path).expanduser().resolve()
    _ensure_allowed_root(root)
    if not root.exists() or not root.is_dir():
        raise FileNotFoundError(f"{root} does not exist or is not a directory")

    candidates = []
    with get_conn() as conn:
        known = _already_imported_paths(conn)

    for file_path in _iter_script_files(root):
        try:
            content = file_path.read_text(encoding="utf-8", errors="strict")
        except (UnicodeDecodeError, OSError):
            continue

        source_ref = str(file_path)
        candidates.append(
            {
                "path": source_ref,
                "name": file_path.name,
                "short_description": _guess_short_description(content),
                "size": file_path.stat().st_size,
                "has_possible_secret": looks_like_it_has_a_secret(content),
                "already_imported": source_ref in known,
            }
        )

    return {"scanned_dir": str(root), "candidates": candidates}


def _upsert_file(conn, file_path: Path, host: str, now: str) -> str:
    """Returns 'created', 'updated', or 'skipped'."""
    try:
        content = file_path.read_text(encoding="utf-8", errors="strict")
    except (UnicodeDecodeError, OSError):
        return "skipped"

    source_ref = str(file_path)
    has_secret = looks_like_it_has_a_secret(content)
    existing = conn.execute(
        "SELECT id FROM scripts WHERE source_ref = ? AND source_type = 'local_import'",
        (source_ref,),
    ).fetchone()

    if existing:
        conn.execute(
            "UPDATE scripts SET content = ?, has_possible_secret = ?, updated_at = ? WHERE id = ?",
            (content, int(has_secret), now, existing["id"]),
        )
        return "updated"

    conn.execute(
        """
        INSERT INTO scripts
            (name, host, tags, short_description, long_description, notes,
             content, run_mode, source_type, source_ref, has_possible_secret,
             created_at, updated_at)
        VALUES (?, ?, '', ?, '', '', ?, '', 'local_import', ?, ?, ?, ?)
        """,
        (
            file_path.name,
            host,
            _guess_short_description(content),
            content,
            source_ref,
            int(has_secret),
            now,
            now,
        ),
    )
    return "created"


def import_path(root_path: str, host: str = "") -> dict:
    """Scan a directory and import every script file found, blind (no
    picking). Re-importing an already-known path (matched by absolute
    source_ref) refreshes `content`/`has_possible_secret`/`updated_at`
    only -- user-edited fields (short_description, long_description,
    notes, tags, host, run_mode) are preserved, never overwritten."""
    root = Path(root_path).expanduser().resolve()
    _ensure_allowed_root(root)
    if not root.exists() or not root.is_dir():
        raise FileNotFoundError(f"{root} does not exist or is not a directory")

    counts = {"created": 0, "updated": 0, "skipped": 0}
    now = datetime.now(timezone.utc).isoformat()

    with get_conn() as conn:
        for file_path in _iter_script_files(root):
            counts[_upsert_file(conn, file_path, host, now)] += 1

    return {**counts, "scanned_dir": str(root)}


def confirm_import(paths: list[str], host: str = "") -> dict:
    """Import exactly the given file paths (from a prior scan_path
    selection), same upsert-preserving-edits semantics as import_path."""
    counts = {"created": 0, "updated": 0, "skipped": 0}
    now = datetime.now(timezone.utc).isoformat()

    with get_conn() as conn:
        for raw_path in paths:
            file_path = Path(raw_path).expanduser().resolve()
            try:
                _ensure_allowed_root(file_path.parent)
            except ImportPathNotAllowedError:
                counts["skipped"] += 1
                continue
            if not file_path.is_file():
                counts["skipped"] += 1
                continue
            counts[_upsert_file(conn, file_path, host, now)] += 1

    return counts
