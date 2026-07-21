import sys

import pytest

TEST_PASSWORD = "test-password-for-pytest-only"


@pytest.fixture()
def app_env(tmp_path, monkeypatch):
    """Isolated env for every test: a throwaway SQLite file, a known
    password, and every optional feature (remote exec/sandbox) off
    unless a specific test turns one on. Set before importing app.main,
    since db.py/auth.py read these env vars at import/call time."""
    db_path = tmp_path / "test.db"
    import_root = tmp_path / "import-sources"
    import_root.mkdir()
    ssh_keys_dir = tmp_path / "ssh-host"
    ssh_keys_dir.mkdir()
    (ssh_keys_dir / "id_ed25519").write_text(
        "-----BEGIN OPENSSH PRIVATE KEY-----\nfake-test-key-not-real\n-----END OPENSSH PRIVATE KEY-----\n"
    )
    monkeypatch.setenv("SINDRI_DB_PATH", str(db_path))
    monkeypatch.setenv("SINDRI_PASSWORD", TEST_PASSWORD)
    monkeypatch.setenv("SINDRI_REMOTE_EXEC_ENABLED", "false")
    monkeypatch.setenv("SINDRI_SANDBOX_ENABLED", "false")
    monkeypatch.setenv("SINDRI_IMPORT_ALLOWED_ROOTS", str(import_root))
    monkeypatch.setenv("SINDRI_SSH_KEYS_DIR", str(ssh_keys_dir))
    monkeypatch.delenv("SINDRI_ANTHROPIC_API_KEY", raising=False)
    yield {
        "db_path": db_path,
        "import_root": import_root,
        "ssh_keys_dir": ssh_keys_dir,
        "valid_key_path": str(ssh_keys_dir / "id_ed25519"),
    }


@pytest.fixture()
def client(app_env):
    # app.db.DB_PATH / app.ssh_keys.SSH_KEYS_DIR are module-level
    # constants read ONCE from the environment at import time. Python
    # caches imports across tests in the same process, so without
    # dropping the app.* modules from sys.modules here, every test after
    # the first would silently keep reusing the FIRST test's temp DB/
    # keys dir instead of its own -- e.g. login-lockout counters bleeding
    # across supposedly-isolated tests. Force a fresh import every time.
    for name in list(sys.modules):
        if name == "app" or name.startswith("app."):
            del sys.modules[name]

    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as c:
        yield c


@pytest.fixture()
def auth_client(client):
    resp = client.post("/api/auth/login", json={"password": TEST_PASSWORD})
    assert resp.status_code == 200, resp.text
    return client
