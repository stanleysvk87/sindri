from conftest import TEST_PASSWORD


def test_login_wrong_password_rejected(client):
    resp = client.post("/api/auth/login", json={"password": "not-it"})
    assert resp.status_code == 401


def test_login_correct_password_sets_cookie(client):
    resp = client.post("/api/auth/login", json={"password": TEST_PASSWORD})
    assert resp.status_code == 200
    assert "sindri_session" in resp.cookies


def test_protected_route_requires_auth(client):
    resp = client.get("/api/scripts")
    assert resp.status_code == 401


def test_protected_route_works_after_login(auth_client):
    resp = auth_client.get("/api/scripts")
    assert resp.status_code == 200


def test_login_lockout_after_five_failures(client):
    for _ in range(5):
        resp = client.post("/api/auth/login", json={"password": "wrong"})
        assert resp.status_code == 401

    # 6th attempt -- even with the CORRECT password -- must be locked out.
    resp = client.post("/api/auth/login", json={"password": TEST_PASSWORD})
    assert resp.status_code == 429


def test_successful_login_clears_lockout_counter(client):
    for _ in range(3):
        client.post("/api/auth/login", json={"password": "wrong"})

    ok = client.post("/api/auth/login", json={"password": TEST_PASSWORD})
    assert ok.status_code == 200

    # counter should be reset -- 3 more wrong guesses should NOT lock out
    # (5 is the threshold, and the successful login above cleared history)
    for _ in range(3):
        resp = client.post("/api/auth/login", json={"password": "wrong"})
        assert resp.status_code == 401  # not 429 yet
