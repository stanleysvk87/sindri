from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.audit import for_script, log_action
from app.auth import require_auth
from app.db import get_conn
from app.import_utils import confirm_import, import_path, scan_path
from app.machines import create_machine, get_machine, list_machines
from app.models import (
    BulkTagRequest,
    ConfirmImportRequest,
    PathImportRequest,
    PushBackRequest,
    RemoteConfirmImportRequest,
    RemoteExecAllRequest,
    RemoteExecRequest,
    RemoteScanRequest,
    ScanPathRequest,
    ScriptPasteImport,
    ScriptUpdate,
)
from app.remote_exec import RemoteExecError, run_remote
from app.remote_import import pull_file, push_file, scan_remote_path
from app.secret_scan import looks_like_it_has_a_secret

router = APIRouter(prefix="/api/scripts", tags=["scripts"], dependencies=[Depends(require_auth)])


def _resolve_remote_source(script) -> tuple[dict, str]:
    """Parse a remote_import script's source_ref (shape:
    ssh://<machine_name><absolute_path>) back into a machine row + path,
    for the push/rescan routes that infer the target from where a script
    was originally pulled from."""
    if script["source_type"] != "remote_import" or not script["source_ref"].startswith("ssh://"):
        raise HTTPException(status_code=400, detail="Tento skript nepochádza z remote importu.")
    rest = script["source_ref"][len("ssh://") :]
    machine_name, _, path_part = rest.partition("/")
    path = "/" + path_part
    with get_conn() as conn:
        machine_row = conn.execute("SELECT * FROM machines WHERE name = ?", (machine_name,)).fetchone()
    if not machine_row:
        raise HTTPException(
            status_code=404,
            detail=f"Pôvodný stroj '{machine_name}' už nie je zaregistrovaný.",
        )
    return dict(machine_row), path


def _row_to_dict(row):
    d = dict(row)
    if "has_possible_secret" in d:
        d["has_possible_secret"] = bool(d["has_possible_secret"])
    if "is_favorite" in d:
        d["is_favorite"] = bool(d["is_favorite"])
    if "works_everywhere" in d:
        d["works_everywhere"] = bool(d["works_everywhere"])
    return d


@router.get("")
def list_scripts(
    host: str | None = None,
    tag: list[str] = Query(default=[]),
    q: str | None = None,
    favorite: bool = False,
):
    clauses = []
    params: list = []

    if host:
        clauses.append("host = ?")
        params.append(host)
    if favorite:
        clauses.append("is_favorite = 1")
    if tag:
        # OR across selected tag chips -- "docker" + "network" means
        # "either category", the way a category filter is normally read,
        # not "must have both tags at once".
        tag_clause = " OR ".join(["(',' || tags || ',') LIKE ?"] * len(tag))
        clauses.append(f"({tag_clause})")
        params.extend(f"%,{t},%" for t in tag)
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
               has_possible_secret, is_favorite, works_everywhere, updated_at
        FROM scripts
        {where}
        ORDER BY is_favorite DESC, name COLLATE NOCASE
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


@router.get("/{script_id}/history")
def script_history(script_id: int, limit: int = 50):
    return {"entries": for_script(script_id, limit)}


@router.post("/{script_id}/favorite")
def toggle_favorite(script_id: int):
    with get_conn() as conn:
        row = conn.execute("SELECT is_favorite FROM scripts WHERE id = ?", (script_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Script not found")
        new_value = 0 if row["is_favorite"] else 1
        conn.execute("UPDATE scripts SET is_favorite = ? WHERE id = ?", (new_value, script_id))
    return {"is_favorite": bool(new_value)}


@router.post("/{script_id}/duplicate")
def duplicate_script(script_id: int):
    """A fresh, independent copy -- always source_type='pasted' with no
    source_ref, even if the original was imported, so editing/deleting
    the copy can never touch the original file on disk or its remote
    machine (no source to push/rescan back to)."""
    with get_conn() as conn:
        script = conn.execute("SELECT * FROM scripts WHERE id = ?", (script_id,)).fetchone()
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")

    now = datetime.now(timezone.utc).isoformat()
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO scripts
               (name, host, tags, short_description, long_description, notes, content,
                run_mode, source_type, source_ref, has_possible_secret, is_favorite,
                created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pasted', '', ?, 0, ?, ?)""",
            (
                f"{script['name']} (kópia)",
                script["host"],
                script["tags"],
                script["short_description"],
                script["long_description"],
                script["notes"],
                script["content"],
                script["run_mode"],
                script["has_possible_secret"],
                now,
                now,
            ),
        )
        row = conn.execute("SELECT * FROM scripts WHERE id = ?", (cur.lastrowid,)).fetchone()
    log_action("duplicate", cur.lastrowid, row["name"], f"from_id={script_id}")
    return _row_to_dict(row)


@router.patch("/{script_id}")
def update_script(script_id: int, payload: ScriptUpdate):
    fields = payload.model_dump(exclude_unset=True)
    if not fields:
        raise HTTPException(status_code=400, detail="No fields to update")

    if "content" in fields:
        fields["has_possible_secret"] = int(looks_like_it_has_a_secret(fields["content"]))
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
        existing = conn.execute("SELECT id, name FROM scripts WHERE id = ?", (script_id,)).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Script not found")
        conn.execute("DELETE FROM scripts WHERE id = ?", (script_id,))
    log_action("delete", script_id, existing["name"])
    return {"deleted": script_id}


@router.post("/{script_id}/remote-exec")
def remote_exec(script_id: int, payload: RemoteExecRequest):
    with get_conn() as conn:
        script = conn.execute("SELECT * FROM scripts WHERE id = ?", (script_id,)).fetchone()
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")

    saved_machine_id = None
    if payload.machine_id is not None:
        machine = get_machine(payload.machine_id)
        if not machine:
            raise HTTPException(status_code=404, detail="Machine not found")
        machine_label = machine["name"]
        saved_machine_id = machine["id"]
    elif payload.connection is not None:
        # Ad-hoc: no saved machine, connection details typed in for this
        # one run. Never touches the machines table unless save_as_name
        # is set, and even then the password itself is never part of
        # what gets saved (create_machine has no password field at all).
        c = payload.connection
        machine = {
            "host": c.host,
            "port": c.port,
            "ssh_user": c.ssh_user,
            "auth_type": c.auth_type,
            "ssh_key_path": c.ssh_key_path,
        }
        machine_label = f"{c.ssh_user}@{c.host}"
    else:
        raise HTTPException(status_code=400, detail="machine_id alebo connection je povinné")

    try:
        result = run_remote(machine, script["content"], payload.sudo_password, payload.ssh_password)
    except RemoteExecError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    if payload.connection is not None and payload.connection.save_as_name:
        saved = create_machine(
            payload.connection.save_as_name,
            payload.connection.host,
            payload.connection.port,
            payload.connection.ssh_user,
            payload.connection.auth_type,
            payload.connection.ssh_key_path,
        )
        saved_machine_id = saved["id"]
        result["saved_machine_id"] = saved_machine_id

    exit_display = "timeout" if result["timed_out"] else result["exit_code"]
    log_action(
        "remote_exec",
        script_id,
        script["name"],
        f"machine={machine_label} exit_code={exit_display} sudo={'yes' if payload.sudo_password else 'no'}",
    )
    return result


@router.post("/{script_id}/remote-exec-all")
def remote_exec_all(script_id: int, payload: RemoteExecAllRequest):
    """Run this script on every registered machine, one after another --
    only registered machines (no ad-hoc connection: "run everywhere"
    only makes sense against the fleet you already track), same sudo
    password reused across all of them since it's never stored either
    way. Failures on one machine don't stop the rest -- each result is
    reported independently."""
    with get_conn() as conn:
        script = conn.execute("SELECT * FROM scripts WHERE id = ?", (script_id,)).fetchone()
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")

    machines = list_machines()
    if not machines:
        raise HTTPException(status_code=400, detail="Žiadny spravovaný stroj nie je zaregistrovaný.")

    results = []
    for machine in machines:
        try:
            result = run_remote(machine, script["content"], payload.sudo_password, None)
            exit_display = "timeout" if result["timed_out"] else result["exit_code"]
        except RemoteExecError as exc:
            result = {"error": str(exc)}
            exit_display = "error"
        results.append({"machine_id": machine["id"], "machine_name": machine["name"], **result})
        log_action(
            "remote_exec",
            script_id,
            script["name"],
            f"machine={machine['name']} exit_code={exit_display} sudo={'yes' if payload.sudo_password else 'no'} (run-all)",
        )
    return {"results": results}


@router.post("/{script_id}/push")
def push_script(script_id: int, payload: PushBackRequest):
    """Write this script's current content to a machine -- either back
    to where a remote_import script came from (source_ref parsed
    automatically), or to any registered machine + path for scripts that
    didn't originate remotely ("deploy this catalog script somewhere\").
    Always explicit, always a fresh click -- never triggered by saving
    an edit."""
    with get_conn() as conn:
        script = conn.execute("SELECT * FROM scripts WHERE id = ?", (script_id,)).fetchone()
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")

    machine_id = payload.machine_id
    target_path = payload.target_path

    if machine_id is None or target_path is None:
        try:
            machine, target_path = _resolve_remote_source(script)
        except HTTPException as exc:
            if exc.status_code == 400:
                raise HTTPException(
                    status_code=400,
                    detail="machine_id a target_path sú povinné pre skripty, ktoré nepochádzajú z remote importu.",
                ) from exc
            raise
    else:
        machine = get_machine(machine_id)
        if not machine:
            raise HTTPException(status_code=404, detail="Machine not found")

    try:
        result = push_file(machine, target_path, script["content"])
    except RemoteExecError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    log_action("push", script_id, script["name"], f"machine={machine['name']} path={target_path}")
    return result


@router.post("/{script_id}/rescan")
def rescan_script(script_id: int):
    """Re-read this script's content from wherever it was originally
    imported from (local_import: mounted path, remote_import: SSH pull)
    and, if the source has drifted since import, update the stored copy.
    The opposite direction of /push -- source of truth flows in, not out."""
    with get_conn() as conn:
        script = conn.execute("SELECT * FROM scripts WHERE id = ?", (script_id,)).fetchone()
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")

    if script["source_type"] == "local_import":
        source_path = Path(script["source_ref"])
        if not source_path.is_file():
            raise HTTPException(status_code=404, detail=f"Zdrojový súbor {source_path} už na disku neexistuje.")
        try:
            new_content = source_path.read_text(errors="replace")
        except OSError as exc:
            raise HTTPException(status_code=503, detail=f"Súbor sa nepodarilo prečítať: {exc}") from exc
    elif script["source_type"] == "remote_import":
        machine, path = _resolve_remote_source(script)
        try:
            new_content = pull_file(machine, path)
        except RemoteExecError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
    else:
        raise HTTPException(status_code=400, detail="Tento skript nepochádza z importu, niet z čoho ho obnoviť.")

    changed = new_content != script["content"]
    if changed:
        with get_conn() as conn:
            conn.execute(
                "UPDATE scripts SET content = ?, has_possible_secret = ?, updated_at = ? WHERE id = ?",
                (
                    new_content,
                    int(looks_like_it_has_a_secret(new_content)),
                    datetime.now(timezone.utc).isoformat(),
                    script_id,
                ),
            )
            row = conn.execute("SELECT * FROM scripts WHERE id = ?", (script_id,)).fetchone()
        log_action("rescan", script_id, script["name"], "changed=yes")
        return {"changed": True, "script": _row_to_dict(row)}

    log_action("rescan", script_id, script["name"], "changed=no")
    return {"changed": False, "script": _row_to_dict(script)}


@router.post("/bulk-tag")
def bulk_tag(payload: BulkTagRequest):
    """Add and/or remove tags across many scripts at once -- the
    catalog's multi-select checkboxes feed this. Tags are stored as a
    plain comma-separated string per script (same shape EditableField
    already edits one at a time), so this just does the same
    add-to-set/remove-from-set per row, in bulk."""
    add_tags = {t.strip() for t in payload.add.split(",") if t.strip()}
    remove_tags = {t.strip() for t in payload.remove.split(",") if t.strip()}
    if not add_tags and not remove_tags:
        raise HTTPException(status_code=400, detail="Zadaj aspoň jeden tag na pridanie alebo odstránenie.")

    updated = 0
    with get_conn() as conn:
        for script_id in payload.ids:
            row = conn.execute("SELECT tags FROM scripts WHERE id = ?", (script_id,)).fetchone()
            if not row:
                continue
            current = {t.strip() for t in row["tags"].split(",") if t.strip()}
            new_tags = ",".join(sorted((current | add_tags) - remove_tags))
            conn.execute(
                "UPDATE scripts SET tags = ?, updated_at = ? WHERE id = ?",
                (new_tags, datetime.now(timezone.utc).isoformat(), script_id),
            )
            updated += 1

    log_action("bulk_tag", None, "", f"ids={len(payload.ids)} add={payload.add!r} remove={payload.remove!r} updated={updated}")
    return {"updated": updated}


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
                 works_everywhere, created_at, updated_at)
            VALUES (?, ?, ?, ?, '', '', ?, ?, 'pasted', ?, ?, ?, ?, ?)
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
                int(payload.works_everywhere),
                now,
                now,
            ),
        )
        new_id = cur.lastrowid
        row = conn.execute("SELECT * FROM scripts WHERE id = ?", (new_id,)).fetchone()
    log_action("create_paste", new_id, payload.name)
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
    result = confirm_import(payload.paths, host=payload.host)
    log_action("bulk_import", None, "", f"host={payload.host} {result}")
    return result


@router.post("/import/remote-scan")
def scan_remote(payload: RemoteScanRequest):
    """Read-only preview over SSH, mirrors /import/scan for local paths.
    Content is fetched in this same call (unlike the local scan, which
    defers reading to confirm) so confirming doesn't need a second SSH
    round trip per file."""
    machine = get_machine(payload.machine_id)
    if not machine:
        raise HTTPException(status_code=404, detail="Machine not found")
    with get_conn() as conn:
        known_refs = {
            r["source_ref"]
            for r in conn.execute(
                "SELECT source_ref FROM scripts WHERE source_type = 'remote_import'"
            ).fetchall()
        }
    try:
        return scan_remote_path(machine, payload.path, known_refs)
    except RemoteExecError as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@router.post("/import/remote-confirm")
def confirm_remote_import(payload: RemoteConfirmImportRequest):
    if not payload.items:
        raise HTTPException(status_code=400, detail="No items selected")
    machine = get_machine(payload.machine_id)
    if not machine:
        raise HTTPException(status_code=404, detail="Machine not found")

    now = datetime.now(timezone.utc).isoformat()
    created = 0
    updated = 0
    with get_conn() as conn:
        for item in payload.items:
            source_ref = f"ssh://{machine['name']}{item.path}"
            has_secret = looks_like_it_has_a_secret(item.content)
            existing = conn.execute(
                "SELECT id FROM scripts WHERE source_ref = ? AND source_type = 'remote_import'",
                (source_ref,),
            ).fetchone()
            if existing:
                conn.execute(
                    "UPDATE scripts SET content = ?, has_possible_secret = ?, updated_at = ? WHERE id = ?",
                    (item.content, int(has_secret), now, existing["id"]),
                )
                updated += 1
            else:
                conn.execute(
                    """
                    INSERT INTO scripts
                        (name, host, tags, short_description, long_description, notes,
                         content, run_mode, source_type, source_ref, has_possible_secret,
                         created_at, updated_at)
                    VALUES (?, ?, '', '', '', '', ?, '', 'remote_import', ?, ?, ?, ?)
                    """,
                    (
                        item.path.rsplit("/", 1)[-1],
                        payload.host,
                        item.content,
                        source_ref,
                        int(has_secret),
                        now,
                        now,
                    ),
                )
                created += 1
    result = {"created": created, "updated": updated}
    log_action("remote_import", None, "", f"machine={machine['name']} {result}")
    return result


@router.get("/meta/hosts")
def list_hosts():
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT DISTINCT host FROM scripts WHERE host != '' ORDER BY host"
        ).fetchall()
    return {"hosts": [r["host"] for r in rows]}


@router.get("/meta/tags")
def list_tags():
    with get_conn() as conn:
        rows = conn.execute("SELECT tags FROM scripts WHERE tags != ''").fetchall()
    tags: set[str] = set()
    for row in rows:
        tags.update(t.strip() for t in row["tags"].split(",") if t.strip())
    return {"tags": sorted(tags)}
