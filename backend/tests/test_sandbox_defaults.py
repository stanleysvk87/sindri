def test_sandbox_disabled_by_default(auth_client):
    resp = auth_client.get("/api/sandbox/status")
    assert resp.status_code == 200
    assert resp.json()["available"] is False


def test_sandbox_run_rejected_when_disabled(auth_client):
    resp = auth_client.post(
        "/api/sandbox/run", json={"content": "#!/bin/bash\necho hi\n", "script_type": "bash"}
    )
    assert resp.status_code in (400, 403, 503)


def test_health_endpoint_needs_no_auth(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
