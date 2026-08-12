from datetime import date

from pydantic import BaseModel, Field


# ---------- Auth ----------
class Credentials(BaseModel):
    username: str = Field(min_length=3, max_length=40)
    password: str = Field(min_length=6, max_length=200)


class UserOut(BaseModel):
    id: int
    username: str


class PasswordChange(BaseModel):
    # current_password is only ever fed to argon2 verify, so a wrong value must reach that
    # check and return `invalid_credentials` rather than tripping a 422 first — hence just
    # non-empty. new_password mirrors registration's rules (see Credentials.password).
    current_password: str = Field(min_length=1)
    new_password: str = Field(min_length=6, max_length=200)


# ---------- Groups ----------
class GroupCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    description: str = ""
    currency: str = "BRL"
    visibility: str = "private"


class GroupUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    currency: str | None = None
    visibility: str | None = None  # "private" | "public"


class GroupOut(BaseModel):
    id: int
    name: str
    slug: str
    description: str
    currency: str
    visibility: str
    share_token: str | None
    night_count: int = 0
    participant_count: int = 0


# ---------- Catalog (named lookups) ----------
class NamedCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)


class NamedOut(BaseModel):
    id: int
    name: str


class ParticipantOut(BaseModel):
    id: int
    name: str
    active: bool


class ParticipantUpdate(BaseModel):
    """Partial update: omitted fields keep their current value, so the UI can flip `active`
    (deactivate / reactivate) without having to echo the name back."""

    name: str | None = Field(default=None, min_length=1, max_length=80)
    active: bool | None = None


# ---------- Nights ----------
# Money is never negative and must stay far below the 64-bit range SQLite can store
# (a bare int would accept 2**63 and blow up with OverflowError on insert).
MONEY_MAX_CENTS = 10**12  # R$ 10 bilhões em centavos


class EntryIn(BaseModel):
    participant_id: int
    buy_in_cents: int = Field(default=0, ge=0, le=MONEY_MAX_CENTS)
    cash_out_cents: int = Field(default=0, ge=0, le=MONEY_MAX_CENTS)


class EntryOut(BaseModel):
    id: int
    participant_id: int
    participant_name: str
    buy_in_cents: int
    cash_out_cents: int
    profit_cents: int


class NightCreate(BaseModel):
    date: date
    place_id: int | None = None
    entries: list[EntryIn] = []


class NightOut(BaseModel):
    id: int
    date: date
    place_id: int | None
    place_name: str | None
    entries: list[EntryOut]
    total_pot_cents: int
    balance_cents: int  # sum of profits; should be ~0 if the pot closes


# ---------- Stats ----------
class RankingRow(BaseModel):
    participant_id: int
    name: str
    total_profit_cents: int
    nights_played: int
    avg_profit_cents: int
    total_buy_in_cents: int
    roi: float | None  # profit / buy_in


class Record(BaseModel):
    label: str
    participant_name: str | None
    value_cents: int | None  # None when the group has no data for this record yet
    night_date: date | None


class StatsOut(BaseModel):
    ranking: list[RankingRow]
    records: list[Record]
    total_nights: int


class EvolutionPoint(BaseModel):
    date: date
    # None before the participant's first night, so every series lines up with `dates`.
    cumulative_cents: int | None


class EvolutionSeries(BaseModel):
    participant_id: int
    name: str
    points: list[EvolutionPoint]


class EvolutionOut(BaseModel):
    dates: list[date]
    series: list[EvolutionSeries]


# ---------- Public ----------
class PublicGroupSummary(BaseModel):
    name: str
    slug: str
    description: str
    night_count: int
    participant_count: int


class PublicGroupOut(BaseModel):
    name: str
    slug: str
    description: str
    currency: str
    stats: StatsOut
    evolution: EvolutionOut
    nights: list[NightOut]
