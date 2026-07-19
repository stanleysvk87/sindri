import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

DB_PATH = Path(os.environ.get("SINDRI_DB_PATH", "./data/scripts.db")).resolve()

SCHEMA = """
CREATE TABLE IF NOT EXISTS scripts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    host TEXT NOT NULL DEFAULT '',
    tags TEXT NOT NULL DEFAULT '',
    short_description TEXT NOT NULL DEFAULT '',
    long_description TEXT NOT NULL DEFAULT '',
    notes TEXT NOT NULL DEFAULT '',
    content TEXT NOT NULL DEFAULT '',
    run_mode TEXT NOT NULL DEFAULT '',
    source_type TEXT NOT NULL DEFAULT 'pasted',
    source_ref TEXT NOT NULL DEFAULT '',
    has_possible_secret INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_scripts_host ON scripts(host);
CREATE INDEX IF NOT EXISTS idx_scripts_source_ref ON scripts(source_ref);

CREATE TABLE IF NOT EXISTS sessions (
    token TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL
);

-- Tracks which built-in template names have ever been seeded, so a
-- template is inserted exactly once ever -- a restart never resurrects
-- one the user deliberately deleted, and never re-seeds one they
-- renamed.
CREATE TABLE IF NOT EXISTS seed_state (
    template_name TEXT PRIMARY KEY,
    seeded_at TEXT NOT NULL
);

-- Generic key/value overrides editable from Settings (currently just AI
-- provider mode + API key) -- takes priority over the env var default
-- when present, so a UI change doesn't require redeploying the
-- container. Absence of a key means "use the env var".
CREATE TABLE IF NOT EXISTS app_settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

-- auth_type 'key' -> ssh_key_path is a path already mounted from the
-- host (see ssh_keys.py). auth_type 'password' -> ssh_key_path stays
-- empty; the SSH password itself is NEVER stored here, same rule as the
-- sudo password -- entered fresh in the UI on every run.
CREATE TABLE IF NOT EXISTS machines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    host TEXT NOT NULL,
    port INTEGER NOT NULL DEFAULT 22,
    ssh_user TEXT NOT NULL,
    auth_type TEXT NOT NULL DEFAULT 'key',
    ssh_key_path TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);

-- No secrets/output here on purpose -- audit trail is "who ran what,
-- where, when, what exit code", not a transcript that could itself leak
-- whatever the script printed.
CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    action TEXT NOT NULL,
    script_id INTEGER,
    script_name TEXT NOT NULL DEFAULT '',
    detail TEXT NOT NULL DEFAULT ''
);
"""


def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with get_conn() as conn:
        conn.executescript(SCHEMA)
    _migrate()
    seed_templates()


def _migrate():
    """Small ad-hoc migrations for columns added after a table already
    existed in the wild -- SQLite has no `ADD COLUMN IF NOT EXISTS`, so
    check pragma table_info first. Kept minimal on purpose: this is a
    single-tenant app with one DB file, not a project that needs a real
    migration framework yet."""
    with get_conn() as conn:
        existing_cols = {row["name"] for row in conn.execute("PRAGMA table_info(machines)")}
        if "auth_type" not in existing_cols:
            conn.execute("ALTER TABLE machines ADD COLUMN auth_type TEXT NOT NULL DEFAULT 'key'")


def seed_templates():
    from datetime import datetime, timezone

    from app.templates_seed import SEED_TEMPLATES

    now = datetime.now(timezone.utc).isoformat()
    with get_conn() as conn:
        already_seeded = {
            r["template_name"]
            for r in conn.execute("SELECT template_name FROM seed_state").fetchall()
        }
        for tmpl in SEED_TEMPLATES:
            if tmpl["name"] in already_seeded:
                continue
            conn.execute(
                """
                INSERT INTO scripts
                    (name, host, tags, short_description, long_description, notes,
                     content, run_mode, source_type, source_ref, has_possible_secret,
                     created_at, updated_at)
                VALUES (?, '', ?, ?, ?, '', ?, ?, 'template', '', 0, ?, ?)
                """,
                (
                    tmpl["name"],
                    tmpl["tags"],
                    tmpl["short_description"],
                    tmpl["long_description"],
                    tmpl["content"],
                    tmpl["run_mode"],
                    now,
                    now,
                ),
            )
            conn.execute(
                "INSERT INTO seed_state (template_name, seeded_at) VALUES (?, ?)",
                (tmpl["name"], now),
            )


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()
