from datetime import date, datetime, timezone

from sqlmodel import Field, Relationship, SQLModel, UniqueConstraint


def utcnow() -> datetime:
    # Naive UTC keeps comparisons simple and consistent with SQLite storage.
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    username: str = Field(unique=True, index=True)
    password_hash: str
    created_at: datetime = Field(default_factory=utcnow)


class Session(SQLModel, table=True):
    # The opaque token stored in the httpOnly cookie is the primary key.
    token: str = Field(primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    expires_at: datetime
    created_at: datetime = Field(default_factory=utcnow)


class GroupOwner(SQLModel, table=True):
    group_id: int = Field(foreign_key="group.id", primary_key=True)
    user_id: int = Field(foreign_key="user.id", primary_key=True)
    created_at: datetime = Field(default_factory=utcnow)


class Group(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
    slug: str = Field(unique=True, index=True)
    description: str = ""
    currency: str = "BRL"
    visibility: str = "private"  # "private" | "public"
    share_token: str | None = Field(default=None, index=True)
    created_at: datetime = Field(default_factory=utcnow)

    participants: list["Participant"] = Relationship(back_populates="group")
    places: list["Place"] = Relationship(back_populates="group")
    nights: list["Night"] = Relationship(back_populates="group")


class Participant(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("group_id", "name", name="uq_participant_group_name"),)
    id: int | None = Field(default=None, primary_key=True)
    group_id: int = Field(foreign_key="group.id", index=True)
    name: str
    active: bool = True
    created_at: datetime = Field(default_factory=utcnow)

    group: Group | None = Relationship(back_populates="participants")


class Place(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("group_id", "name", name="uq_place_group_name"),)
    id: int | None = Field(default=None, primary_key=True)
    group_id: int = Field(foreign_key="group.id", index=True)
    name: str

    group: Group | None = Relationship(back_populates="places")


class Night(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    group_id: int = Field(foreign_key="group.id", index=True)
    date: date
    place_id: int | None = Field(default=None, foreign_key="place.id")
    created_at: datetime = Field(default_factory=utcnow)
    deleted_at: datetime | None = None  # soft delete to preserve history

    group: Group | None = Relationship(back_populates="nights")
    entries: list["NightEntry"] = Relationship(
        back_populates="night",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )


class NightEntry(SQLModel, table=True):
    # All money values are stored as integer cents (centavos), never floats.
    id: int | None = Field(default=None, primary_key=True)
    night_id: int = Field(foreign_key="night.id", index=True)
    participant_id: int = Field(foreign_key="participant.id", index=True)
    buy_in_cents: int = 0
    cash_out_cents: int = 0
    profit_cents: int = 0  # = cash_out_cents - buy_in_cents (stored for fast queries)

    night: Night | None = Relationship(back_populates="entries")
