"""Regression tests for the 2026-07-21 fix: scan/import must not be able
to reach paths outside the configured import root(s)
(SINDRI_IMPORT_ALLOWED_ROOTS, default /import-sources). Before the fix,
an authenticated user could point /api/scripts/import/scan at any path
the container filesystem could see."""


def test_scan_outside_allowed_root_is_rejected(auth_client, app_env, tmp_path):
    outside = tmp_path / "definitely-not-import-sources"
    outside.mkdir()
    (outside / "secret.sh").write_text("#!/bin/bash\necho hi\n")

    resp = auth_client.post("/api/scripts/import/scan", json={"path": str(outside)})
    assert resp.status_code == 403


def test_scan_inside_allowed_root_works(auth_client, app_env):
    root = app_env["import_root"]
    (root / "hello.sh").write_text("#!/bin/bash\necho hello\n")

    resp = auth_client.post("/api/scripts/import/scan", json={"path": str(root)})
    assert resp.status_code == 200
    names = [c["name"] for c in resp.json()["candidates"]]
    assert "hello.sh" in names


def test_scan_subdirectory_of_allowed_root_works(auth_client, app_env):
    root = app_env["import_root"]
    sub = root / "nested"
    sub.mkdir()
    (sub / "deep.sh").write_text("#!/bin/bash\necho deep\n")

    resp = auth_client.post("/api/scripts/import/scan", json={"path": str(sub)})
    assert resp.status_code == 200
    names = [c["name"] for c in resp.json()["candidates"]]
    assert "deep.sh" in names


def test_confirm_import_outside_allowed_root_is_skipped_not_imported(auth_client, app_env, tmp_path):
    outside = tmp_path / "outside-again"
    outside.mkdir()
    evil = outside / "evil.sh"
    evil.write_text("#!/bin/bash\necho should-not-be-imported\n")

    resp = auth_client.post(
        "/api/scripts/import/confirm", json={"paths": [str(evil)], "host": "test"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["created"] == 0
    assert body["skipped"] == 1

    # double-check nothing actually landed in the catalog
    listing = auth_client.get("/api/scripts", params={"q": "evil.sh"}).json()
    assert listing["scripts"] == []
