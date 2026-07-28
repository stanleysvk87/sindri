"""Logging out and changing the password must kill the session
server-side. Both used to be cosmetic: logout only deleted the browser's
copy of the cookie and set_password only wrote a new hash, so a token
someone had copied stayed valid for the rest of its 14-day TTL --
including for remote execution."""

from conftest import TEST_PASSWORD


def _token(client):
    return client.cookies.get("sindri_session")


def test_logout_invalidates_the_token_server_side(auth_client):
    stolen = _token(auth_client)
    assert stolen

    assert auth_client.post("/api/auth/logout").status_code == 200

    # Replay the token the way a thief would: fresh cookie header, no
    # dependence on the client's own cookie jar.
    resp = auth_client.get("/api/scripts", cookies={"sindri_session": stolen})
    assert resp.status_code == 401


def test_password_change_invalidates_other_sessions(client, auth_client):
    stolen = _token(auth_client)

    resp = auth_client.put(
        "/api/settings/account",
        json={"current_password": TEST_PASSWORD, "new_password": "a-new-longer-password"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["sessions_invalidated"] is True

    assert auth_client.get("/api/scripts", cookies={"sindri_session": stolen}).status_code == 401


def test_password_change_keeps_the_caller_logged_in(auth_client):
    resp = auth_client.put(
        "/api/settings/account",
        json={"current_password": TEST_PASSWORD, "new_password": "a-new-longer-password"},
    )
    assert resp.status_code == 200

    # The caller got a fresh cookie back, so changing your own password
    # doesn't log you out of your own browser.
    assert auth_client.get("/api/scripts").status_code == 200
    assert _token(auth_client) is not None
