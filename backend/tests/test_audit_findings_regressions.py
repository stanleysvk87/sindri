"""Regression tests for the smaller correctness findings from the
2026-07-28 audit. One test per finding, named after what actually broke.
"""

import subprocess

import pytest
from conftest import TEST_PASSWORD


class FakeCompletedProcess:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


# --- one dangling symlink used to make a whole directory unscannable ---


def test_dangling_symlink_skips_only_that_entry(auth_client, app_env):
    root = app_env["import_root"]
    (root / "real.sh").write_text("#!/bin/bash\necho real\n")
    (root / "stale.sh").symlink_to(root / "gone.sh")  # target never created

    resp = auth_client.post("/api/scripts/import/scan", json={"path": str(root)})
    assert resp.status_code == 200, resp.text
    names = [c["name"] for c in resp.json()["candidates"]]
    assert names == ["real.sh"]


# --- search treated user input as a LIKE pattern ---


def test_search_does_not_treat_underscore_as_a_wildcard(auth_client):
    for name in ("xv_probe.sh", "xvXprobe.sh"):
        auth_client.post("/api/scripts/import/paste", json={"name": name, "content": "#!/bin/sh\n"})

    found = auth_client.get("/api/scripts", params={"q": "xv_probe"}).json()["scripts"]
    assert [s["name"] for s in found] == ["xv_probe.sh"]


def test_search_for_percent_does_not_match_everything(auth_client):
    auth_client.post("/api/scripts/import/paste", json={"name": "plain.sh", "content": "#!/bin/sh\n"})
    auth_client.post(
        "/api/scripts/import/paste", json={"name": "pct.sh", "content": "df | awk '{print $5}' # 100%\n"}
    )

    found = {s["name"] for s in auth_client.get("/api/scripts", params={"q": "%"}).json()["scripts"]}
    total = {s["name"] for s in auth_client.get("/api/scripts").json()["scripts"]}

    # "%" now means a literal percent sign, so it hits only scripts that
    # actually contain one -- it used to match the entire catalog.
    assert "pct.sh" in found
    assert "plain.sh" not in found
    assert found < total


# --- duplicate silently dropped works_everywhere ---


def test_duplicate_preserves_works_everywhere(auth_client):
    created = auth_client.post(
        "/api/scripts/import/paste",
        json={"name": "portable.sh", "content": "#!/bin/sh\n", "works_everywhere": True},
    ).json()
    assert created["works_everywhere"] is True

    copy = auth_client.post(f"/api/scripts/{created['id']}/duplicate").json()
    assert copy["works_everywhere"] is True

    everywhere = auth_client.get("/api/scripts", params={"everywhere": "true"}).json()["scripts"]
    assert {s["id"] for s in everywhere} == {created["id"], copy["id"]}


# --- ad-hoc remote exec validated the key allowlist AFTER running ---


def test_adhoc_remote_exec_rejects_unmounted_key_before_running(auth_client, app_env, monkeypatch):
    monkeypatch.setenv("SINDRI_REMOTE_EXEC_ENABLED", "true")
    ran = {"called": False}

    def fake_run(cmd, **kwargs):
        ran["called"] = True
        return FakeCompletedProcess(stdout="pwned\n")

    monkeypatch.setattr(subprocess, "run", fake_run)

    created = auth_client.post(
        "/api/scripts/import/paste", json={"name": "x.sh", "content": "#!/bin/sh\necho hi\n"}
    ).json()

    resp = auth_client.post(
        f"/api/scripts/{created['id']}/remote-exec",
        json={
            "connection": {
                "host": "1.2.3.4",
                "ssh_user": "u",
                "auth_type": "key",
                "ssh_key_path": "/etc/passwd",  # readable, but not a mounted key
            }
        },
    )
    assert resp.status_code == 400
    assert ran["called"] is False, "the script ran before the key allowlist was checked"


# --- machine names are identifiers, not free text ---


def test_machine_name_must_be_unique_and_slash_free(auth_client, app_env):
    key = app_env["valid_key_path"]
    base = {"host": "1.2.3.4", "ssh_user": "u", "auth_type": "key", "ssh_key_path": key}

    assert auth_client.post("/api/machines", json={**base, "name": "prod"}).status_code == 200

    dup = auth_client.post("/api/machines", json={**base, "name": "prod"})
    assert dup.status_code == 400

    slashed = auth_client.post("/api/machines", json={**base, "name": "prod/eu"})
    assert slashed.status_code == 400


# --- blind bulk import was the one write path with no audit trail ---


def test_blind_path_import_is_audit_logged(auth_client, app_env):
    (app_env["import_root"] / "a.sh").write_text("#!/bin/bash\necho a\n")

    resp = auth_client.post(
        "/api/scripts/import/path", json={"path": str(app_env["import_root"]), "host": "opi"}
    )
    assert resp.status_code == 200, resp.text

    entries = auth_client.get("/api/settings/audit-log").json()["entries"]
    assert any(e["action"] == "bulk_import" for e in entries)


# --- provider_mode typos silently behaved like "auto" ---


def test_invalid_provider_mode_is_rejected(auth_client):
    assert auth_client.put("/api/settings/ai", json={"provider_mode": "claude-cli"}).status_code == 400
    assert auth_client.put("/api/settings/ai", json={"provider_mode": "auto"}).status_code == 200
    assert auth_client.get("/api/settings/ai").json()["provider_mode"] == "auto"


# --- CORS was hardcoded on in production ---


def test_cors_is_off_unless_explicitly_configured(client, monkeypatch):
    resp = client.get("/api/health", headers={"Origin": "http://localhost:5173"})
    assert "access-control-allow-origin" not in {k.lower() for k in resp.headers}


# --- "auto" never actually fell through to the next provider ---


def test_provider_chain_falls_through_on_unavailable(app_env, monkeypatch):
    import sys

    for name in list(sys.modules):
        if name == "app" or name.startswith("app."):
            del sys.modules[name]

    from app import ai_engine
    from midgard_ai_engine import ProviderUnavailableError

    class RateLimited:
        name = "claude_cli"

        def complete(self, prompt):
            raise ProviderUnavailableError("429 rate limit")

    class Working:
        name = "anthropic_api"

        def complete(self, prompt):
            return "generated"

    monkeypatch.setattr(ai_engine, "get_provider_chain", lambda: [RateLimited(), Working()])
    assert ai_engine.complete("hi") == ("generated", "anthropic_api")


def test_provider_chain_reports_when_every_provider_is_unavailable(app_env, monkeypatch):
    import sys

    for name in list(sys.modules):
        if name == "app" or name.startswith("app."):
            del sys.modules[name]

    from app import ai_engine
    from midgard_ai_engine import AIEngineError, ProviderUnavailableError

    class Dead:
        name = "codex_cli"

        def complete(self, prompt):
            raise ProviderUnavailableError("no such file or directory")

    monkeypatch.setattr(ai_engine, "get_provider_chain", lambda: [Dead()])
    with pytest.raises(AIEngineError):
        ai_engine.complete("hi")


# --- password-auth machines could never be pushed to ---


def test_push_to_password_machine_uses_sshpass_not_a_missing_key(app_env, monkeypatch):
    monkeypatch.setenv("SINDRI_REMOTE_EXEC_ENABLED", "true")
    from app import remote_import

    captured = {}

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        captured["env"] = kwargs.get("env") or {}
        return FakeCompletedProcess(returncode=0)

    monkeypatch.setattr(subprocess, "run", fake_run)

    machine = {"name": "pw", "ssh_user": "u", "host": "h", "port": 22,
               "ssh_key_path": "", "auth_type": "password"}
    remote_import.push_file(machine, "/tmp/x.sh", "#!/bin/sh\n", ssh_password="pw-secret")

    assert captured["cmd"][0] == "sshpass"
    assert "-i" not in captured["cmd"]
    assert captured["env"].get("SSHPASS") == "pw-secret"
    assert "pw-secret" not in " ".join(captured["cmd"])


def test_push_to_password_machine_without_password_says_so(app_env, monkeypatch):
    monkeypatch.setenv("SINDRI_REMOTE_EXEC_ENABLED", "true")
    from app import remote_import
    from app.remote_exec import RemoteExecError

    machine = {"name": "pw", "ssh_user": "u", "host": "h", "port": 22,
               "ssh_key_path": "", "auth_type": "password"}
    with pytest.raises(RemoteExecError, match="password"):
        remote_import.push_file(machine, "/tmp/x.sh", "#!/bin/sh\n")


# --- codex left a temp file behind on every timeout ---


def test_codex_cleans_up_its_temp_file_on_timeout(app_env, monkeypatch):
    from pathlib import Path

    from midgard_ai_engine import CodexCLIProvider, ProviderUnavailableError

    created = []
    real_named_temp = __import__("tempfile").NamedTemporaryFile

    def tracking_temp(*args, **kwargs):
        handle = real_named_temp(*args, **kwargs)
        created.append(Path(handle.name))
        return handle

    monkeypatch.setattr("midgard_ai_engine.cli_runner.tempfile.NamedTemporaryFile", tracking_temp)

    def fake_run(cmd, **kwargs):
        raise subprocess.TimeoutExpired(cmd, 120)

    monkeypatch.setattr(subprocess, "run", fake_run)

    with pytest.raises(ProviderUnavailableError):
        CodexCLIProvider().complete("hi")

    assert created, "test did not observe the temp file being created"
    assert not created[0].exists(), "codex temp file leaked on the timeout path"


# --- password change keeps working with the new password ---


def test_new_password_works_after_change(auth_client, client):
    auth_client.put(
        "/api/settings/account",
        json={"current_password": TEST_PASSWORD, "new_password": "a-new-longer-password"},
    )
    auth_client.post("/api/auth/logout")
    assert auth_client.post("/api/auth/login", json={"password": TEST_PASSWORD}).status_code == 401
    assert (
        auth_client.post("/api/auth/login", json={"password": "a-new-longer-password"}).status_code
        == 200
    )


# --- rescan grew an optional body (SSH password for password machines);
# --- the UI still calls it with no body at all


def test_rescan_still_works_without_a_request_body(auth_client, app_env):
    src = app_env["import_root"] / "r.sh"
    src.write_text("#!/bin/bash\necho v1\n")
    auth_client.post("/api/scripts/import/path", json={"path": str(app_env["import_root"])})
    scripts = auth_client.get("/api/scripts").json()["scripts"]
    script_id = next(s["id"] for s in scripts if s["name"] == "r.sh")

    src.write_text("#!/bin/bash\necho v2\n")
    resp = auth_client.post(f"/api/scripts/{script_id}/rescan")
    assert resp.status_code == 200, resp.text
    assert resp.json()["changed"] is True
