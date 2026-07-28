from datetime import datetime, timezone

from app.db import get_conn
from app.ssh_keys import to_host_path


def _with_host_path(row: dict) -> dict:
    row["ssh_key_path_host"] = to_host_path(row["ssh_key_path"]) if row["ssh_key_path"] else ""
    return row


def list_machines() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM machines ORDER BY name").fetchall()
    return [_with_host_path(dict(r)) for r in rows]


def get_machine(machine_id: int) -> dict | None:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM machines WHERE id = ?", (machine_id,)).fetchone()
    return dict(row) if row else None


class MachineNameError(ValueError):
    pass


def validate_machine_name(name: str) -> str:
    """A machine's NAME is an identifier, not a label: imported scripts
    record their origin as `ssh://<name><absolute path>` and every
    push/rescan resolves the target by parsing that string back apart.
    So the name must be non-empty, unique, and must not contain '/' --
    a slash makes the parser split in the wrong place and silently
    resolve to a different machine (or none)."""
    name = name.strip()
    if not name:
        raise MachineNameError("Machine name is required.")
    if "/" in name:
        raise MachineNameError(
            "Machine name must not contain '/' -- it is used as an identifier in "
            "imported scripts' source references."
        )
    with get_conn() as conn:
        existing = conn.execute(
            "SELECT id FROM machines WHERE name = ? COLLATE NOCASE", (name,)
        ).fetchone()
    if existing:
        raise MachineNameError(f"A machine named '{name}' is already registered.")
    return name


def create_machine(
    name: str, host: str, port: int, ssh_user: str, auth_type: str, ssh_key_path: str = ""
) -> dict:
    name = validate_machine_name(name)
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
