"""The login lockout is documented as per-IP, and behind the bundled
nginx container it wasn't: every request reached the backend from the
proxy's own container address, so five wrong passwords from any one
client on the LAN locked the owner out of every device (429) for 15
minutes. The forwarded header is now honored -- but only from a peer
listed in SINDRI_TRUSTED_PROXIES, otherwise anyone could simply invent
an address per attempt and never be locked out at all.

TestClient reports its peer as the literal string "testclient", so
these tests set that as the trusted proxy where they want the forwarded
header believed.
"""

from conftest import TEST_PASSWORD


def _fail_login(client, headers=None):
    return client.post("/api/auth/login", json={"password": "wrong"}, headers=headers or {})


def test_forwarded_ip_is_ignored_when_the_peer_is_not_a_trusted_proxy(client, monkeypatch):
    monkeypatch.setenv("SINDRI_TRUSTED_PROXIES", "")

    # Five failures, each claiming a different client address. With the
    # header untrusted they all land in the same bucket -> locked out.
    for i in range(5):
        assert _fail_login(client, {"X-Real-IP": f"10.0.0.{i}"}).status_code == 401

    resp = client.post(
        "/api/auth/login",
        json={"password": TEST_PASSWORD},
        headers={"X-Real-IP": "10.0.0.99"},
    )
    assert resp.status_code == 429


def test_lockout_is_per_client_ip_behind_a_trusted_proxy(client, monkeypatch):
    monkeypatch.setenv("SINDRI_TRUSTED_PROXIES", "testclient")

    attacker = {"X-Real-IP": "192.168.1.66"}
    for _ in range(5):
        assert _fail_login(client, attacker).status_code == 401

    # The attacker's own address is locked...
    assert (
        client.post("/api/auth/login", json={"password": TEST_PASSWORD}, headers=attacker).status_code
        == 429
    )

    # ...but the owner, on a different address, is not. This is the whole
    # point of the finding: previously this returned 429 too.
    owner = {"X-Real-IP": "192.168.1.10"}
    resp = client.post("/api/auth/login", json={"password": TEST_PASSWORD}, headers=owner)
    assert resp.status_code == 200


def test_x_forwarded_for_takes_the_original_client(client, monkeypatch):
    monkeypatch.setenv("SINDRI_TRUSTED_PROXIES", "testclient")

    chain = {"X-Forwarded-For": "203.0.113.7, 172.30.0.2"}
    for _ in range(5):
        assert _fail_login(client, chain).status_code == 401

    assert (
        client.post("/api/auth/login", json={"password": TEST_PASSWORD}, headers=chain).status_code
        == 429
    )
    other = {"X-Forwarded-For": "203.0.113.8, 172.30.0.2"}
    assert (
        client.post("/api/auth/login", json={"password": TEST_PASSWORD}, headers=other).status_code
        == 200
    )


def test_cidr_entry_matches_a_proxy_inside_the_network(app_env, monkeypatch):
    monkeypatch.setenv("SINDRI_TRUSTED_PROXIES", "172.16.0.0/12,127.0.0.1")
    import sys

    for name in list(sys.modules):
        if name == "app" or name.startswith("app."):
            del sys.modules[name]
    from app.auth import _is_trusted_proxy

    assert _is_trusted_proxy("172.30.0.2") is True
    assert _is_trusted_proxy("127.0.0.1") is True
    assert _is_trusted_proxy("192.168.1.44") is False
    assert _is_trusted_proxy("") is False
