"""Alembic is now the only thing that creates schema, so it gets the same scrutiny as
application code: the revision must match the models, and all three startup states
(fresh / already-managed / pre-Alembic) must converge on head without losing data."""
import sqlalchemy as sa
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlmodel import SQLModel

from app import db as dbmod

APP_TABLES = {
    "user", "session", "group", "groupowner", "participant", "place", "night", "nightentry",
}


def _tables(engine) -> set[str]:
    return set(sa.inspect(engine).get_table_names())


def _version(engine) -> str | None:
    with engine.connect() as conn:
        if "alembic_version" not in _tables(engine):
            return None
        return conn.execute(sa.text("select version_num from alembic_version")).scalar()


def _head() -> str:
    script = ScriptDirectory.from_config(dbmod._alembic_config())
    heads = script.get_heads()
    assert len(heads) == 1, f"expected a single head, got {heads}"
    return heads[0]


def _fresh_engine(path):
    return sa.create_engine(f"sqlite:///{path}", connect_args={"check_same_thread": False})


def _run_against(monkeypatch, engine, url):
    """Point app.db at another database and run the real startup migration logic."""
    monkeypatch.setattr(dbmod.settings, "database_url", url)
    monkeypatch.setattr(dbmod, "engine", engine)
    dbmod.run_migrations()


def test_single_head():
    assert _head()


def test_session_db_is_at_head(migrated_db):
    # The suite's own database was built by init_db() -> alembic upgrade head.
    assert _version(dbmod.engine) == _head()
    assert APP_TABLES <= _tables(dbmod.engine)


def test_revision_matches_models(migrated_db):
    """The guard that keeps the initial revision honest: an autogenerate comparison
    against a DB at head must produce an empty diff, i.e. `alembic revision
    --autogenerate` would emit `pass`."""
    with dbmod.engine.connect() as conn:
        ctx = MigrationContext.configure(conn)
        diff = compare_metadata(ctx, SQLModel.metadata)
    assert diff == [], f"models and migrations have drifted: {diff}"


def test_all_seven_model_tables_are_created(tmp_path, monkeypatch):
    """Fresh DB: upgrade head creates everything, no create_all involved."""
    path = tmp_path / "fresh.db"
    engine = _fresh_engine(path)
    _run_against(monkeypatch, engine, f"sqlite:///{path}")
    assert _tables(engine) == APP_TABLES | {"alembic_version"}
    assert _version(engine) == _head()


def test_migrations_are_idempotent(tmp_path, monkeypatch):
    path = tmp_path / "again.db"
    engine = _fresh_engine(path)
    url = f"sqlite:///{path}"
    _run_against(monkeypatch, engine, url)
    _run_against(monkeypatch, engine, url)  # second boot must be a no-op
    assert _version(engine) == _head()


def test_pre_alembic_db_is_stamped_not_recreated(tmp_path, monkeypatch):
    """The prod/dev-volume case: tables exist (built by the old create_all) and hold rows,
    but there is no alembic_version. Naive `upgrade` would fail on CREATE TABLE; the data
    must survive and the DB must end up at head."""
    path = tmp_path / "legacy.db"
    engine = _fresh_engine(path)
    SQLModel.metadata.create_all(engine)
    assert _version(engine) is None

    with engine.begin() as conn:
        conn.execute(sa.text(
            "insert into user (id, username, password_hash, created_at)"
            " values (1, 'legado', 'x', '2020-01-01 00:00:00')"
        ))

    _run_against(monkeypatch, engine, f"sqlite:///{path}")

    assert _version(engine) == _head()
    with engine.connect() as conn:
        assert conn.execute(sa.text("select username from user")).scalar() == "legado"


def test_pre_alembic_db_with_legacy_extra_tables(tmp_path, monkeypatch):
    """Real dev/prod databases also carry tables from a superseded model version
    (gamevariant/stake/...). They must not confuse the detection, and must be left alone
    rather than dropped by a migration."""
    path = tmp_path / "legacy-extra.db"
    engine = _fresh_engine(path)
    SQLModel.metadata.create_all(engine)
    with engine.begin() as conn:
        conn.execute(sa.text("create table stake (id integer primary key, label varchar)"))
        conn.execute(sa.text("insert into stake (id, label) values (1, '1/2')"))

    _run_against(monkeypatch, engine, f"sqlite:///{path}")

    assert _version(engine) == _head()
    assert "stake" in _tables(engine)
    with engine.connect() as conn:
        assert conn.execute(sa.text("select label from stake")).scalar() == "1/2"


def test_session_token_hash_migration_transforms_plaintext_in_place(tmp_path, monkeypatch):
    """The security migration must upgrade a real pre-Alembic DB: one whose `session` table
    still has the old `token` column holding a *raw* token. After upgrade the column is
    `token_hash` and holds sha256(token), so the original cookie still authenticates."""
    import hashlib

    from alembic import command

    path = tmp_path / "plaintext-session.db"
    engine = _fresh_engine(path)
    url = f"sqlite:///{path}"

    # Build the *initial* schema by hand (old shape: session.token is the PK), seed a user
    # and a plaintext-token session, but leave no alembic_version — a pre-Alembic DB.
    monkeypatch.setattr(dbmod.settings, "database_url", url)
    monkeypatch.setattr(dbmod, "engine", engine)
    cfg = dbmod._alembic_config()
    command.upgrade(cfg, "1da27d86e22d")  # initial revision only: token column, not token_hash

    raw = "raw-cookie-token-xyz"
    with engine.begin() as conn:
        conn.execute(sa.text(
            "insert into user (id, username, password_hash, created_at)"
            " values (1, 'u', 'x', '2020-01-01 00:00:00')"
        ))
        conn.execute(sa.text(
            "insert into session (token, user_id, expires_at, created_at)"
            " values (:t, 1, '2099-01-01 00:00:00', '2020-01-01 00:00:00')"
        ), {"t": raw})
        # Drop the version table entirely to simulate a DB that predates Alembic: run_migrations
        # then takes the stamp-initial-then-upgrade path rather than replaying from base.
        conn.execute(sa.text("drop table alembic_version"))

    dbmod.run_migrations()

    assert _version(engine) == _head()
    with engine.connect() as conn:
        cols = {c["name"] for c in sa.inspect(engine).get_columns("session")}
        assert cols >= {"token_hash", "user_id", "expires_at"}
        assert "token" not in cols
        stored = conn.execute(sa.text("select token_hash from session")).scalar()
    assert stored != raw, "raw token must not survive the migration"
    assert stored == hashlib.sha256(raw.encode()).hexdigest(), "must be sha256(raw)"
