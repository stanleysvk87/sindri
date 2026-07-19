from datetime import datetime, timezone

from app.db import get_conn


def log_action(action: str, script_id: int | None = None, script_name: str = "", detail: str = ""):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO audit_log (created_at, action, script_id, script_name, detail)"
            " VALUES (?, ?, ?, ?, ?)",
            (datetime.now(timezone.utc).isoformat(), action, script_id, script_name, detail),
        )


def recent(limit: int = 100) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM audit_log ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
    return [dict(r) for r in rows]


def for_script(script_id: int, limit: int = 50) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM audit_log WHERE script_id = ? ORDER BY id DESC LIMIT ?",
            (script_id, limit),
        ).fetchall()
    return [dict(r) for r in rows]
