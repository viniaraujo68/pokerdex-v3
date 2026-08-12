"""hash session tokens at rest

The `session` table used to store the raw cookie token as its primary key, so a DB leak was
a full account takeover. We now store sha256(token) instead: the raw token stays only in the
httpOnly cookie, and each request hashes the cookie and looks the row up by hash.

Column `token` is renamed to `token_hash`, and existing rows are transformed in place
(sha256 of the raw value they currently hold). Because the transform is exactly what the app
now applies to an incoming cookie, every already-issued cookie keeps working after this
migration — nobody is logged out.

The upgrade is defensive about which shape it finds: a database created by the pre-Alembic
`create_all` path now reflects the *current* model and therefore already has `token_hash`.
In that case there is nothing to rename and the values are assumed already hashed, so we skip.

Downgrade renames the column back to `token` but cannot un-hash the values (sha256 is
one-way). Sessions therefore stop validating after a downgrade; users simply log in again.

Revision ID: 2b9f4c1e7a3d
Revises: 1da27d86e22d
Create Date: 2026-08-12 00:00:00.000000

"""
import hashlib
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = '2b9f4c1e7a3d'
down_revision: Union[str, None] = '1da27d86e22d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _columns(conn) -> set[str]:
    return {c["name"] for c in sa.inspect(conn).get_columns("session")}


def upgrade() -> None:
    conn = op.get_bind()
    cols = _columns(conn)

    if "token_hash" in cols and "token" not in cols:
        # Pre-Alembic DB built by create_all against the current model: the target column is
        # already present and its values are already hashes. Nothing to do.
        return

    # Hash the raw tokens in place *before* the rename. Doing it here (rather than after the
    # batch recreate) avoids depending on rowid survival across SQLite's table rebuild.
    rows = conn.execute(sa.text("SELECT token FROM session")).fetchall()
    for (raw,) in rows:
        digest = hashlib.sha256(raw.encode()).hexdigest()
        conn.execute(
            sa.text("UPDATE session SET token = :h WHERE token = :raw"),
            {"h": digest, "raw": raw},
        )

    with op.batch_alter_table("session", schema=None) as batch_op:
        batch_op.alter_column("token", new_column_name="token_hash")


def downgrade() -> None:
    conn = op.get_bind()
    cols = _columns(conn)
    if "token" in cols and "token_hash" not in cols:
        return
    # Best effort: restore the column name. Values remain hashed (sha256 is irreversible), so
    # existing sessions will not validate under the old code — users log in again.
    with op.batch_alter_table("session", schema=None) as batch_op:
        batch_op.alter_column("token_hash", new_column_name="token")
