"""Regression tests for the 2026-07-21 fix: POST /api/machines must
reject an ssh_key_path that isn't one of the keys actually mounted from
the host (GET /api/machines/available-keys), instead of trusting
whatever the client sends -- the dropdown in the UI was previously the
only thing enforcing this."""


def test_add_machine_with_unmounted_key_path_rejected(auth_client):
    resp = auth_client.post(
        "/api/machines",
        json={
            "name": "fake",
            "host": "1.2.3.4",
            "ssh_user": "x",
            "auth_type": "key",
            "ssh_key_path": "/etc/passwd",
        },
    )
    assert resp.status_code == 400


def test_add_machine_with_actually_mounted_key_succeeds(auth_client, app_env):
    resp = auth_client.post(
        "/api/machines",
        json={
            "name": "real",
            "host": "1.2.3.4",
            "ssh_user": "x",
            "auth_type": "key",
            "ssh_key_path": app_env["valid_key_path"],
        },
    )
    assert resp.status_code == 200, resp.text


def test_add_machine_password_auth_does_not_require_key_path(auth_client):
    resp = auth_client.post(
        "/api/machines",
        json={
            "name": "pw-machine",
            "host": "1.2.3.4",
            "ssh_user": "x",
            "auth_type": "password",
        },
    )
    assert resp.status_code == 200, resp.text


def test_available_keys_lists_only_mounted_keys(auth_client, app_env):
    resp = auth_client.get("/api/machines/available-keys")
    assert resp.status_code == 200
    assert resp.json()["keys"] == [app_env["valid_key_path"]]
