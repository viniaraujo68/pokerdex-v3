"""Per-IP rate limiting on the credential and public endpoints.

Every test here takes the `rate_limits` fixture, which enables the limiter and clears its
counters; the rest of the suite runs with it disabled. Because slowapi's limiter is global
process state these tests must not run in parallel — hence the `ratelimit` mark.
"""
import pytest

from conftest import PASSWORD, Api, unique

pytestmark = pytest.mark.ratelimit

LOGIN_LIMIT = 5
REGISTER_LIMIT = 3
PUBLIC_LIMIT = 30


def login_body(username="qualquer-um", password=PASSWORD):
    return {"username": username, "password": password}


def test_configured_limits_match_expectations():
    """Pin the policy so a config edit can't silently loosen it."""
    from app.config import settings

    assert settings.rate_limit_login == f"{LOGIN_LIMIT}/minute"
    assert settings.rate_limit_register == f"{REGISTER_LIMIT}/minute"
    assert settings.rate_limit_public == f"{PUBLIC_LIMIT}/minute"


def test_limiter_is_disabled_for_the_rest_of_the_suite():
    """Sanity check on the fixture contract: without `rate_limits`, limits are off."""
    from app import ratelimit

    assert ratelimit.limiter.enabled is False


def test_login_is_limited_after_five_attempts(rate_limits, client):
    codes = [client.post("/api/auth/login", json=login_body()).status_code
             for _ in range(LOGIN_LIMIT + 2)]
    assert codes[:LOGIN_LIMIT] == [401] * LOGIN_LIMIT
    assert codes[LOGIN_LIMIT:] == [429, 429], codes


def test_rate_limited_response_is_429_with_pt_br_detail(rate_limits, client):
    for _ in range(LOGIN_LIMIT):
        client.post("/api/auth/login", json=login_body())
    r = client.post("/api/auth/login", json=login_body())
    assert r.status_code == 429
    assert r.json()["detail"] == {
        "code": "rate_limited",
        "message": "Muitas tentativas. Aguarde um momento e tente novamente.",
    }
    assert r.headers["Retry-After"] == "60"


def test_successful_logins_also_count_toward_the_limit(rate_limits):
    """A valid password must not be a free pass, otherwise one known account could be used
    to keep probing forever. (Api() only charges the separate register bucket.)"""
    api = Api()
    codes = [api.post("/api/auth/login", json=login_body(api.username)).status_code
             for _ in range(LOGIN_LIMIT + 1)]
    assert codes == [200] * LOGIN_LIMIT + [429], codes


def test_register_is_limited_after_three_attempts(rate_limits, client):
    codes = []
    for _ in range(REGISTER_LIMIT + 1):
        codes.append(client.post(
            "/api/auth/register", json={"username": unique("flood"), "password": PASSWORD}
        ).status_code)
    assert codes[:REGISTER_LIMIT] == [201] * REGISTER_LIMIT
    assert codes[REGISTER_LIMIT] == 429, codes


def test_login_and_register_have_separate_buckets(rate_limits, client):
    """Exhausting register must not lock a legitimate user out of login."""
    for _ in range(REGISTER_LIMIT + 1):
        client.post("/api/auth/register", json={"username": unique("sep"), "password": PASSWORD})
    assert client.post("/api/auth/login", json=login_body()).status_code == 401


def test_public_directory_is_limited_at_thirty(rate_limits, client):
    codes = [client.get("/api/public").status_code for _ in range(PUBLIC_LIMIT + 1)]
    assert codes[:PUBLIC_LIMIT] == [200] * PUBLIC_LIMIT
    assert codes[PUBLIC_LIMIT] == 429, codes[-3:]


def test_public_detail_shares_one_bucket_across_slugs(rate_limits):
    """Endpoint-keyed buckets: walking different slugs must not reset the allowance."""
    api = Api()
    slugs = []
    for i in range(3):
        api.group(unique("Publico RL "), visibility="public")
        slugs.append(api.last_group["slug"])
    rate_limits.reset()  # don't charge the setup requests to the public bucket

    client = api.client
    codes = []
    for i in range(PUBLIC_LIMIT + 1):
        codes.append(client.get(f"/api/public/{slugs[i % len(slugs)]}").status_code)
    assert codes[:PUBLIC_LIMIT] == [200] * PUBLIC_LIMIT
    assert codes[PUBLIC_LIMIT] == 429, codes[-3:]


def test_authenticated_endpoints_are_not_rate_limited(rate_limits):
    """Only the credential and public surfaces are limited; normal app use is not."""
    api = Api()
    gid = api.group()
    codes = {api.get(f"/api/groups/{gid}/nights").status_code for _ in range(40)}
    assert codes == {200}


def test_counters_reset_releases_the_limit(rate_limits, client):
    """Proxy for the window expiring, without sleeping 60s in the test suite."""
    for _ in range(LOGIN_LIMIT + 1):
        client.post("/api/auth/login", json=login_body())
    assert client.post("/api/auth/login", json=login_body()).status_code == 429
    rate_limits.reset()
    assert client.post("/api/auth/login", json=login_body()).status_code == 401


def client_from_ip(ip: str):
    """TestClient hardcodes the peer address, so wrap the app and rewrite scope["client"]
    — the same field uvicorn's --proxy-headers handling populates from X-Forwarded-For."""
    from fastapi.testclient import TestClient

    from app.main import app

    async def with_ip(scope, receive, send):
        if scope["type"] == "http":
            scope = dict(scope, client=(ip, 1234))
        await app(scope, receive, send)

    return TestClient(with_ip)


def test_limiter_keys_on_client_ip(rate_limits):
    """Two different source IPs must get independent buckets — the reason uvicorn runs
    with --proxy-headers/--forwarded-allow-ips behind the edge proxy."""
    a = client_from_ip("10.0.0.1")
    b = client_from_ip("10.0.0.2")
    for _ in range(LOGIN_LIMIT):
        assert a.post("/api/auth/login", json=login_body()).status_code == 401
    assert a.post("/api/auth/login", json=login_body()).status_code == 429
    # b is a different IP and still has its full allowance.
    assert b.post("/api/auth/login", json=login_body()).status_code == 401
