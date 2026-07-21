"""End-to-end check that a sudo password used in a real remote-exec call
never ends up in the audit log -- docs/REMOTE_EXEC.md's "never the
password, not in the DB, not in the audit log" claim. SSH itself is
mocked (see test_remote_exec_safety.py for the transport-level checks);
this test is about what routes_scripts.py chooses to pass to
log_action()."""

import subprocess


class FakeCompletedProcess:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def test_remote_exec_audit_log_never_contains_sudo_password(auth_client, app_env, monkeypatch):
    monkeypatch.setenv("SINDRI_REMOTE_EXEC_ENABLED", "true")

    def fake_run(cmd, **kwargs):
        return FakeCompletedProcess(returncode=0, stdout="hi\n", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    created = auth_client.post(
        "/api/scripts/import/paste",
        json={"name": "audit-test.sh", "content": "#!/bin/bash\necho hi\n"},
    ).json()

    secret = "s3cr3t-sudo-pw-should-never-be-logged"
    resp = auth_client.post(
        f"/api/scripts/{created['id']}/remote-exec",
        json={
            "connection": {
                "host": "1.2.3.4",
                "ssh_user": "u",
                "auth_type": "key",
                "ssh_key_path": "",
            },
            "sudo_password": secret,
        },
    )
    assert resp.status_code == 200, resp.text

    # imported here, not at module level -- app.db is re-imported fresh
    # per test by the `client` fixture (see conftest.py), so a
    # module-level import here would bind to a stale get_conn from
    # whichever test happened to trigger the first import.
    from app.db import get_conn

    with get_conn() as conn:
        rows = conn.execute("SELECT detail FROM audit_log").fetchall()
    all_details = " ".join(r["detail"] for r in rows)
    assert secret not in all_details
