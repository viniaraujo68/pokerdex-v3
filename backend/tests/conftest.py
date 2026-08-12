"""Shared test setup.

The app reads its DB URL from settings at import time, so the environment has to be
rewritten *before* anything under `app.` is imported — that is why the env block below
sits at module top level rather than inside a fixture.

One temp SQLite file is used for the whole session and is migrated with Alembic (the same
code path production uses). Tests therefore share a database: every helper mints unique
names so tests stay independent without paying for a per-test schema rebuild.
"""
import itertools
import os
import sys
import tempfile
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_ROOT))

TEST_DB_DIR = tempfile.mkdtemp(prefix="pokerdex-pytest-")
TEST_DB_PATH = os.path.join(TEST_DB_DIR, "test.db")
os.environ["POKERDEX_DATABASE_URL"] = f"sqlite:///{TEST_DB_PATH}"
os.environ["POKERDEX_CORS_ORIGINS"] = ""
os.environ["POKERDEX_COOKIE_SECURE"] = "false"
# Off by default so the ~200 requests the suite makes don't trip the per-IP buckets
# (TestClient always looks like the same client). tests/test_ratelimit.py opts back in.
os.environ["POKERDEX_RATE_LIMIT_ENABLED"] = "false"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import event  # noqa: E402

from app import ratelimit  # noqa: E402
from app.config import settings  # noqa: E402
from app.db import engine, init_db  # noqa: E402
from app.main import app  # noqa: E402

PASSWORD = "senha123"
_seq = itertools.count(1)


def unique(prefix: str) -> str:
    return f"{prefix}{next(_seq)}"


@pytest.fixture(scope="session", autouse=True)
def migrated_db():
    """Build the session database through Alembic, exactly like app startup does."""
    assert settings.database_url == f"sqlite:///{TEST_DB_PATH}", settings.database_url
    init_db()
    yield TEST_DB_PATH


@pytest.fixture
def client() -> TestClient:
    """Anonymous client (fresh cookie jar, so no session leaks between tests)."""
    return TestClient(app)


class Api:
    """Thin wrapper over TestClient: one logged-in user plus the create helpers every
    test needs. Asserts on the happy path so tests only assert what they are about."""

    def __init__(self, username: str | None = None):
        self.client = TestClient(app)
        self.username = username or unique("user")
        r = self.client.post(
            "/api/auth/register", json={"username": self.username, "password": PASSWORD}
        )
        assert r.status_code == 201, r.text
        self.user_id = r.json()["id"]

    # --- passthroughs ---
    def get(self, url, **kw):
        return self.client.get(url, **kw)

    def post(self, url, **kw):
        return self.client.post(url, **kw)

    def put(self, url, **kw):
        return self.client.put(url, **kw)

    def patch(self, url, **kw):
        return self.client.patch(url, **kw)

    def delete(self, url, **kw):
        return self.client.delete(url, **kw)

    # --- factories ---
    def group(self, name: str | None = None, **extra) -> int:
        r = self.post("/api/groups", json={"name": name or unique("Grupo "), **extra})
        assert r.status_code == 201, r.text
        self.last_group = r.json()
        return r.json()["id"]

    def participant(self, group_id: int, name: str | None = None) -> int:
        r = self.post(f"/api/groups/{group_id}/participants",
                      json={"name": name or unique("Jogador ")})
        assert r.status_code == 201, r.text
        return r.json()["id"]

    def place(self, group_id: int, name: str | None = None) -> int:
        r = self.post(f"/api/groups/{group_id}/places", json={"name": name or unique("Local ")})
        assert r.status_code == 201, r.text
        return r.json()["id"]

    def night(self, group_id: int, date: str, entries: list[dict], place_id: int | None = None):
        body = {"date": date, "entries": entries}
        if place_id is not None:
            body["place_id"] = place_id
        r = self.post(f"/api/groups/{group_id}/nights", json=body)
        assert r.status_code == 201, r.text
        return r.json()


def entry(participant_id: int, buy_in: int, cash_out: int) -> dict:
    return {"participant_id": participant_id, "buy_in_cents": buy_in, "cash_out_cents": cash_out}


@pytest.fixture
def api() -> Api:
    """A registered+logged-in user."""
    return Api()


@pytest.fixture
def other_api() -> Api:
    """A second, unrelated user — for the cross-tenant authz checks."""
    return Api()


@pytest.fixture
def group(api) -> int:
    return api.group()


class QueryCounter:
    """Counts SQL statements issued on the app engine inside the `with` block."""

    def __init__(self):
        self.count = 0
        self.statements: list[str] = []

    def _on_exec(self, conn, cursor, statement, params, context, executemany):
        self.count += 1
        self.statements.append(statement)

    def __enter__(self):
        self.count = 0
        self.statements.clear()
        event.listen(engine, "before_cursor_execute", self._on_exec)
        return self

    def __exit__(self, *exc):
        event.remove(engine, "before_cursor_execute", self._on_exec)
        return False


@pytest.fixture
def queries() -> QueryCounter:
    return QueryCounter()


@pytest.fixture
def rate_limits():
    """Turn the per-IP limiter on for one test and leave no counters behind."""
    ratelimit.reset()
    ratelimit.limiter.enabled = True
    yield ratelimit.limiter
    ratelimit.limiter.enabled = False
    ratelimit.reset()
