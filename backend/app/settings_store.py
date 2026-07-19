"""Tiny key/value override store for Settings-editable config (right now
just AI provider mode/API key). A stored key wins over the matching env
var; no stored key falls back to the env var default -- same shape as
Muninn's settings_store."""

from app.db import get_conn


def get_setting(key: str, default: str = "") -> str:
    with get_conn() as conn:
        row = conn.execute("SELECT value FROM app_settings WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else default


def set_setting(key: str, value: str) -> None:
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO app_settings (key, value) VALUES (?, ?)"
            " ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )


def delete_setting(key: str) -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM app_settings WHERE key = ?", (key,))
