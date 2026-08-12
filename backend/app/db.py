from collections.abc import Generator
from pathlib import Path

from sqlalchemy import event, inspect
from sqlalchemy.engine import Engine
from sqlmodel import Session, SQLModel, create_engine

from .config import settings

BACKEND_ROOT = Path(__file__).resolve().parent.parent

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args)


@event.listens_for(Engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):
    """Enable WAL (concurrent reads) and enforce foreign keys on every SQLite connection."""
    if settings.database_url.startswith("sqlite"):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        # SQLite serializes writers; without this a concurrent write raises
        # "database is locked" immediately instead of waiting its turn.
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.close()


def _alembic_config():
    from alembic.config import Config

    cfg = Config(str(BACKEND_ROOT / "alembic.ini"))
    # Absolute paths: the app may be started from any working directory, so neither the
    # script location nor env.py's `from app import models` can rely on cwd.
    cfg.set_main_option("script_location", str(BACKEND_ROOT / "alembic"))
    cfg.set_main_option("prepend_sys_path", str(BACKEND_ROOT))
    cfg.set_main_option("sqlalchemy.url", settings.database_url.replace("%", "%%"))
    # Don't let alembic's fileConfig() rip out uvicorn's log handlers (see env.py).
    cfg.attributes["configure_logger"] = False
    return cfg


def run_migrations() -> None:
    """Bring the database to `head`, whatever state it starts in.

    Three cases have to work, and the discriminator is which tables already exist:

    * fresh DB (nothing at all)      -> upgrade head creates every table.
    * Alembic-managed DB             -> upgrade head applies whatever is pending.
    * pre-Alembic DB (dev/prod vols) -> the app's tables are already there but there is
      no alembic_version row, so `upgrade` would try to CREATE TABLE over them. Stamp
      first, then upgrade so any later revisions still run.
    """
    from alembic import command
    from alembic.script import ScriptDirectory

    from . import models  # noqa: F401  (register tables on SQLModel.metadata)

    existing = set(inspect(engine).get_table_names())
    cfg = _alembic_config()

    if "alembic_version" not in existing and existing & set(SQLModel.metadata.tables):
        # Stamp the *initial* revision rather than `head`: a legacy DB matches the first
        # revision's schema, so stamping head would permanently skip revisions 2..n.
        bases = ScriptDirectory.from_config(cfg).get_bases()
        command.stamp(cfg, bases[0] if len(bases) == 1 else "head")

    command.upgrade(cfg, "head")


def init_db() -> None:
    """Called from the app lifespan. Schema now comes from Alembic, never create_all."""
    run_migrations()


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
