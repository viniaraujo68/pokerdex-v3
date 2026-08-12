"""Registration, login, session cookie and the timing-equalization guarantee."""
import time

import pytest

from conftest import PASSWORD, Api, unique


def test_register_sets_session_cookie_and_returns_user(client):
    name = unique("novo")
    r = client.post("/api/auth/register", json={"username": name, "password": PASSWORD})
    assert r.status_code == 201
    assert r.json()["username"] == name
    assert "pokerdex_session" in client.cookies
    # The cookie must not be readable by JS.
    assert "httponly" in r.headers["set-cookie"].lower()


def test_register_duplicate_username_is_409(client):
    name = unique("dup")
    assert client.post("/api/auth/register", json={"username": name, "password": PASSWORD}).status_code == 201
    r = client.post("/api/auth/register", json={"username": name, "password": PASSWORD})
    assert r.status_code == 409
    assert r.json()["detail"]["code"] == "username_taken"
    assert r.json()["detail"]["message"] == "Nome de usuário já existe"


@pytest.mark.parametrize(
    "body",
    [
        {"username": "ab", "password": PASSWORD},          # username too short
        {"username": "validname", "password": "12345"},    # password too short
        {"username": "validname"},                         # no password
    ],
)
def test_register_validation_is_422(client, body):
    assert client.post("/api/auth/register", json=body).status_code == 422


def test_me_requires_a_session(client):
    assert client.get("/api/auth/me").status_code == 401


def test_login_logout_roundtrip(api):
    assert api.get("/api/auth/me").json()["username"] == api.username
    assert api.post("/api/auth/logout").status_code == 204
    assert api.get("/api/auth/me").status_code == 401
    r = api.post("/api/auth/login", json={"username": api.username, "password": PASSWORD})
    assert r.status_code == 200
    assert api.get("/api/auth/me").json()["username"] == api.username


def test_login_rejects_unknown_user_and_wrong_password_identically(client):
    existing = Api().username
    miss = client.post("/api/auth/login", json={"username": "naoexiste-xyz", "password": PASSWORD})
    bad = client.post("/api/auth/login", json={"username": existing, "password": "erradaaaa"})
    assert miss.status_code == 401 and bad.status_code == 401
    # Identical bodies: nothing reveals whether the account exists.
    assert miss.json() == bad.json()
    assert miss.json()["detail"]["code"] == "invalid_credentials"


def test_expired_session_is_rejected(api):
    """A session past expires_at must 401 and be cleaned up, not silently accepted."""
    from datetime import timedelta

    from sqlmodel import Session as DBSession

    from app.db import engine
    from app.models import UserSession, utcnow
    from app.security import hash_token

    token = api.client.cookies["pokerdex_session"]
    token_hash = hash_token(token)
    with DBSession(engine) as db:
        row = db.get(UserSession, token_hash)
        row.expires_at = utcnow() - timedelta(seconds=1)
        db.add(row)
        db.commit()

    assert api.get("/api/auth/me").status_code == 401
    with DBSession(engine) as db:
        assert db.get(UserSession, token_hash) is None


def test_invalid_session_token_is_rejected(client):
    client.cookies.set("pokerdex_session", "nao-e-um-token-valido")
    assert client.get("/api/auth/me").status_code == 401


@pytest.mark.timing
def test_login_timing_does_not_leak_account_existence(client):
    """The unknown-user path burns a dummy argon2 verify, so its latency must sit in the
    same ballpark as a real wrong-password check. Wall-clock based: see the `timing` mark."""
    existing = Api().username

    def median_of(fn, n=5):
        samples = []
        for _ in range(n):
            start = time.perf_counter()
            fn()
            samples.append(time.perf_counter() - start)
        return sorted(samples)[n // 2]

    miss = median_of(lambda: client.post(
        "/api/auth/login", json={"username": "naoexiste-abc", "password": PASSWORD}))
    wrong = median_of(lambda: client.post(
        "/api/auth/login", json={"username": existing, "password": "erradaaaa"}))
    ratio = miss / wrong
    assert 0.4 < ratio < 2.5, f"timing side channel: miss={miss:.4f}s wrong-pw={wrong:.4f}s"


# --------------------------------------------------------------------------------------
# Session tokens are hashed at rest
# --------------------------------------------------------------------------------------
def test_session_token_is_stored_hashed_not_raw(api):
    """The DB must hold sha256(cookie), never the raw cookie value."""
    from sqlmodel import Session as DBSession
    from sqlmodel import select

    from app.db import engine
    from app.models import UserSession
    from app.security import hash_token

    raw = api.client.cookies["pokerdex_session"]
    with DBSession(engine) as db:
        rows = db.exec(select(UserSession).where(UserSession.user_id == api.user_id)).all()
    stored = {r.token_hash for r in rows}
    assert raw not in stored, "raw token must not be persisted"
    assert hash_token(raw) in stored, "stored value must be sha256(cookie)"


def test_valid_cookie_still_authenticates_after_hashing(api):
    """Round-trip: the raw cookie the client holds resolves to the hashed row."""
    assert api.get("/api/auth/me").json()["username"] == api.username


# --------------------------------------------------------------------------------------
# Change password
# --------------------------------------------------------------------------------------
def _sessions_for(user_id):
    from sqlmodel import Session as DBSession
    from sqlmodel import select

    from app.db import engine
    from app.models import UserSession

    with DBSession(engine) as db:
        return db.exec(select(UserSession).where(UserSession.user_id == user_id)).all()


def test_change_password_rejects_wrong_current(api):
    r = api.post("/api/auth/change-password",
                 json={"current_password": "senha-errada", "new_password": "novasenha1"})
    assert r.status_code == 401
    assert r.json()["detail"]["code"] == "invalid_credentials"
    # Password unchanged: the original still logs in.
    from fastapi.testclient import TestClient

    from app.main import app
    c = TestClient(app)
    assert c.post("/api/auth/login",
                  json={"username": api.username, "password": PASSWORD}).status_code == 200


def test_change_password_validates_new_password(api):
    r = api.post("/api/auth/change-password",
                 json={"current_password": PASSWORD, "new_password": "123"})
    assert r.status_code == 422  # same min-length rule as registration


def test_change_password_accepts_right_current_and_keeps_current_session(api):
    new_pw = "novaSenha123"
    r = api.post("/api/auth/change-password",
                 json={"current_password": PASSWORD, "new_password": new_pw})
    assert r.status_code == 204
    # The caller's own session survives the change.
    assert api.get("/api/auth/me").status_code == 200
    # New password works; old one no longer does.
    from fastapi.testclient import TestClient

    from app.main import app
    c = TestClient(app)
    assert c.post("/api/auth/login",
                  json={"username": api.username, "password": PASSWORD}).status_code == 401
    assert c.post("/api/auth/login",
                  json={"username": api.username, "password": new_pw}).status_code == 200


def test_change_password_revokes_other_sessions(api):
    from fastapi.testclient import TestClient

    from app.main import app

    # A second, independent login for the same user.
    other = TestClient(app)
    assert other.post("/api/auth/login",
                      json={"username": api.username, "password": PASSWORD}).status_code == 200
    assert other.get("/api/auth/me").status_code == 200

    r = api.post("/api/auth/change-password",
                 json={"current_password": PASSWORD, "new_password": "outraSenha9"})
    assert r.status_code == 204

    # The other device is booted; the caller keeps working.
    assert other.get("/api/auth/me").status_code == 401
    assert api.get("/api/auth/me").status_code == 200
    assert len(_sessions_for(api.user_id)) == 1


# --------------------------------------------------------------------------------------
# Log out everywhere
# --------------------------------------------------------------------------------------
def test_logout_all_kills_current_and_all_sessions(api):
    from fastapi.testclient import TestClient

    from app.main import app

    other = TestClient(app)
    assert other.post("/api/auth/login",
                      json={"username": api.username, "password": PASSWORD}).status_code == 200

    r = api.post("/api/auth/logout-all")
    assert r.status_code == 204
    # Both the caller and the other device are logged out; no rows remain.
    assert api.get("/api/auth/me").status_code == 401
    assert other.get("/api/auth/me").status_code == 401
    assert _sessions_for(api.user_id) == []
