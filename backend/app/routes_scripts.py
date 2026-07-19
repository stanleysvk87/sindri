from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request

from app.auth import require_auth
from app.db import get_conn
from app.import_utils import confirm_import, import_path, scan_path
from app.models import (
    ConfirmImportRequest,
    PathImportRequest,
    ScanPathRequest,
    ScriptPasteImport,
    ScriptUpdate,
)
from app.secret_scan import looks_like_it_has_a_secret

router = APIRouter(prefix="/api/scripts", tags=["scripts"], dependencies=[Depends(require_auth)])


def _row_to_dict(row):
    d = dict(row)
    if "has_possible_secret" in d:
        d["has_possible_secret"] = bool(d["has_possible_secret"])
    return d


@router.get("")
def list_scripts(host: str | None = None, tag: str | None = None, q: str | None = None):
    clauses = []
    params: list = []

    if host:
        clauses.append("host = ?")
        params.append(host)
    if tag:
        clauses.append("(',' || tags || ',') LIKE ?")
        params.append(f"%,{tag},%")
    if q:
        # Searches what the script IS, not just what it's called -- name
        # alone isn't enough when you remember the behavior but not the
        # filename you gave it eight months ago.
        clauses.append(
            "(name LIKE ? OR short_description LIKE ? OR long_description LIKE ?"
            " OR notes LIKE ? OR tags LIKE ? OR content LIKE ?)"
        )
        like = f"%{q}%"
        params.extend([like, like, like, like, like, like])

    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    sql = f"""
        SELECT id, name, host, tags, short_description, run_mode,
               has_possible_secret, updated_at
        FROM scripts
        {where}
        ORDER BY name COLLATE NOCASE
    """
    with get_conn() as conn:
        rows = conn.execute(sql, params).fetchall()
    return {"scripts": [_row_to_dict(r) for r in rows]}


@router.get("/{script_id}")
def get_script(script_id: int):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM scripts WHERE id = ?", (script_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Script not found")
    return _row_to_dict(row)


@router.patch("/{script_id}")
def update_script(script_id: int, payload: ScriptUpdate):
    fields = payload.model_dump(exclude_unset=True)
    if not fields:
        raise HTTPException(status_code=400, detail="No fields to update")

    fields["updated_at"] = datetime.now(timezone.utc).isoformat()
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    params = list(fields.values()) + [script_id]

    with get_conn() as conn:
        existing = conn.execute("SELECT id FROM scripts WHERE id = ?", (script_id,)).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Script not found")
        conn.execute(f"UPDATE scripts SET {set_clause} WHERE id = ?", params)
        row = conn.execute("SELECT * FROM scripts WHERE id = ?", (script_id,)).fetchone()
    return _row_to_dict(row)


@router.delete("/{script_id}")
def delete_script(script_id: int):
    with get_conn() as conn:
        existing = conn.execute("SELECT id FROM scripts WHERE id = ?", (script_id,)).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Script not found")
        conn.execute("DELETE FROM scripts WHERE id = ?", (script_id,))
    return {"deleted": script_id}


@router.post("/import/paste")
def import_paste(payload: ScriptPasteImport):
    now = datetime.now(timezone.utc).isoformat()
    has_secret = looks_like_it_has_a_secret(payload.content)
    with get_conn() as conn:
        cur = conn.execute(
            """
            INSERT INTO scripts
                (name, host, tags, short_description, long_description, notes,
                 content, run_mode, source_type, source_ref, has_possible_secret,
                 created_at, updated_at)
            VALUES (?, ?, ?, ?, '', '', ?, ?, 'pasted', ?, ?, ?, ?)
            """,
            (
                payload.name,
                payload.host,
                payload.tags,
                payload.short_description,
                payload.content,
                payload.run_mode,
                payload.source_ref,
                int(has_secret),
                now,
                now,
            ),
        )
        new_id = cur.lastrowid
        row = conn.execute("SELECT * FROM scripts WHERE id = ?", (new_id,)).fetchone()
    return _row_to_dict(row)


@router.post("/import/path")
def import_from_path(payload: PathImportRequest):
    """Blind import of every script file found under a path. Prefer
    /import/scan + /import/confirm when the user wants to pick which
    files to add instead of importing an entire directory."""
    try:
        result = import_path(payload.path, host=payload.host)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return result


@router.post("/import/scan")
def scan_directory(payload: ScanPathRequest):
    """Read-only preview: list script files found under a path so the UI
    can show a checklist before anything is actually added."""
    try:
        result = scan_path(payload.path)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return result


@router.post("/import/confirm")
def confirm_directory_import(payload: ConfirmImportRequest):
    """Import exactly the paths the user checked off in a prior scan."""
    if not payload.paths:
        raise HTTPException(status_code=400, detail="No paths selected")
    return confirm_import(payload.paths, host=payload.host)


@router.get("/meta/hosts")
def list_hosts():
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT DISTINCT host FROM scripts WHERE host != '' ORDER BY host"
        ).fetchall()
    return {"hosts": [r["host"] for r in rows]}
