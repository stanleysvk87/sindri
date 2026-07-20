"""Content version history for scripts -- a snapshot of the OLD content
is taken right before it gets overwritten (manual edit, rescan-from-
source, or restoring an older version itself), so nothing is ever lost
even without an explicit "save version" step. Deliberately minimal: no
diffing/compression here, that's the frontend's job (lib/diff.js) --
this module is just snapshot/list/fetch."""

from datetime import datetime, timezone

from app.db import get_conn


def snapshot(script_id: int, content: str, source: str):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO script_versions (script_id, content, source, created_at) VALUES (?, ?, ?, ?)",
            (script_id, content, source, datetime.now(timezone.utc).isoformat()),
        )


def list_for_script(script_id: int, limit: int = 50) -> list[dict]:
    # content itself is excluded here on purpose -- a script with many
    # revisions shouldn't mean shipping every historical blob just to
    # render a list. get_version() fetches one in full, on demand.
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id, script_id, source, created_at, length(content) AS content_length"
            " FROM script_versions WHERE script_id = ? ORDER BY id DESC LIMIT ?",
            (script_id, limit),
        ).fetchall()
    return [dict(r) for r in rows]


def get_version(version_id: int) -> dict | None:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM script_versions WHERE id = ?", (version_id,)).fetchone()
    return dict(row) if row else None
