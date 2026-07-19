from datetime import datetime, timezone

from app.db import get_conn


def list_machines() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM machines ORDER BY name").fetchall()
    return [dict(r) for r in rows]


def get_machine(machine_id: int) -> dict | None:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM machines WHERE id = ?", (machine_id,)).fetchone()
    return dict(row) if row else None


def create_machine(
    name: str, host: str, port: int, ssh_user: str, auth_type: str, ssh_key_path: str = ""
) -> dict:
    now = datetime.now(timezone.utc).isoformat()
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO machines (name, host, port, ssh_user, auth_type, ssh_key_path, created_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)",
            (name, host, port, ssh_user, auth_type, ssh_key_path, now),
        )
        row = conn.execute("SELECT * FROM machines WHERE id = ?", (cur.lastrowid,)).fetchone()
    return dict(row)


def delete_machine(machine_id: int) -> bool:
    with get_conn() as conn:
        existing = conn.execute("SELECT id FROM machines WHERE id = ?", (machine_id,)).fetchone()
        if not existing:
            return False
        conn.execute("DELETE FROM machines WHERE id = ?", (machine_id,))
    return True
