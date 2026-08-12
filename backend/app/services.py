"""Serialization and stats computation. Stats are always derived from NightEntry
rows (no denormalized aggregates), so edits/deletes can never desync totals."""
from collections import defaultdict
from collections.abc import Iterable

from slugify import slugify
from sqlalchemy.orm import selectinload
from sqlmodel import Session as DBSession
from sqlmodel import func, select

from . import models, schemas
from .security import new_token


def unique_slug(db: DBSession, name: str) -> str:
    base = slugify(name) or "grupo"
    slug = base
    i = 2
    while db.exec(select(models.Group).where(models.Group.slug == slug)).first():
        slug = f"{base}-{i}"
        i += 1
    return slug


def _participant_names(db: DBSession, group_id: int) -> dict[int, str]:
    rows = db.exec(
        select(models.Participant).where(models.Participant.group_id == group_id)
    ).all()
    return {p.id: p.name for p in rows}


def _place_names(db: DBSession, group_id: int) -> dict[int, str]:
    rows = db.exec(select(models.Place).where(models.Place.group_id == group_id)).all()
    return {p.id: p.name for p in rows}


def group_counts(
    db: DBSession, group_ids: Iterable[int]
) -> tuple[dict[int, int], dict[int, int]]:
    """Night and active-participant counts for many groups in 2 queries total (not 2 per
    group). Groups with no rows are simply absent from the dicts — callers default to 0."""
    ids = list(group_ids)
    if not ids:
        return {}, {}
    nights = dict(
        db.exec(
            select(models.Night.group_id, func.count(models.Night.id))
            .where(models.Night.group_id.in_(ids), models.Night.deleted_at == None)  # noqa: E711
            .group_by(models.Night.group_id)
        ).all()
    )
    participants = dict(
        db.exec(
            select(models.Participant.group_id, func.count(models.Participant.id))
            .where(models.Participant.group_id.in_(ids), models.Participant.active == True)  # noqa: E712
            .group_by(models.Participant.group_id)
        ).all()
    )
    return nights, participants


def serialize_night(
    db: DBSession,
    night: models.Night,
    names: dict[int, str] | None = None,
    places: dict[int, str] | None = None,
) -> schemas.NightOut:
    if names is None:
        names = _participant_names(db, night.group_id)
    # `places` is prebuilt once per request by list paths; the single-night paths fall back
    # to db.get, which is an identity-map hit when the place was already touched.
    if night.place_id is None:
        place_name = None
    elif places is not None:
        place_name = places.get(night.place_id)
    else:
        place = db.get(models.Place, night.place_id)
        place_name = place.name if place else None
    entries = [
        schemas.EntryOut(
            id=e.id,
            participant_id=e.participant_id,
            participant_name=names.get(e.participant_id, "?"),
            buy_in_cents=e.buy_in_cents,
            cash_out_cents=e.cash_out_cents,
            profit_cents=e.profit_cents,
        )
        for e in night.entries
    ]
    return schemas.NightOut(
        id=night.id,
        date=night.date,
        place_id=night.place_id,
        place_name=place_name,
        entries=entries,
        total_pot_cents=sum(e.buy_in_cents for e in night.entries),
        balance_cents=sum(e.profit_cents for e in night.entries),
    )


def active_nights(db: DBSession, group_id: int) -> list[models.Night]:
    """Nights oldest-first with entries eagerly loaded: every caller walks night.entries,
    so a lazy load would cost one extra query per night (N+1 across stats/evolution/list)."""
    return list(
        db.exec(
            select(models.Night)
            .where(models.Night.group_id == group_id, models.Night.deleted_at == None)  # noqa: E711
            .order_by(models.Night.date, models.Night.id)
            .options(selectinload(models.Night.entries))
        ).all()
    )


def compute_stats(db: DBSession, group_id: int) -> schemas.StatsOut:
    nights = active_nights(db, group_id)
    names = _participant_names(db, group_id)

    profit = defaultdict(int)
    buy_in = defaultdict(int)
    # Distinct night ids per participant: legacy rows may hold duplicate entries for the
    # same night, which would otherwise inflate nights_played and skew the averages.
    played: dict[int, set[int]] = defaultdict(set)
    # Seeded with None (not 0) so a group where nobody ever won doesn't report a
    # phantom "R$ 0,00 by nobody" record.
    best_win = (None, None, None)  # (pid, date, cents)
    worst_loss = (None, None, None)

    for night in nights:
        for e in night.entries:
            profit[e.participant_id] += e.profit_cents
            buy_in[e.participant_id] += e.buy_in_cents
            played[e.participant_id].add(night.id)
            if e.profit_cents > 0 and (best_win[2] is None or e.profit_cents > best_win[2]):
                best_win = (e.participant_id, night.date, e.profit_cents)
            if e.profit_cents < 0 and (worst_loss[2] is None or e.profit_cents < worst_loss[2]):
                worst_loss = (e.participant_id, night.date, e.profit_cents)

    ranking = []
    for pid, total in profit.items():
        n = len(played[pid])
        bi = buy_in[pid]
        ranking.append(
            schemas.RankingRow(
                participant_id=pid,
                name=names.get(pid, "?"),
                total_profit_cents=total,
                nights_played=n,
                avg_profit_cents=round(total / n) if n else 0,
                total_buy_in_cents=bi,
                roi=(total / bi) if bi else None,
            )
        )
    ranking.sort(key=lambda r: r.total_profit_cents, reverse=True)

    records = [
        schemas.Record(
            label="Maior vitória numa noite",
            participant_name=names.get(best_win[0]) if best_win[0] is not None else None,
            value_cents=best_win[2],
            night_date=best_win[1],
        ),
        schemas.Record(
            label="Maior derrota numa noite",
            participant_name=names.get(worst_loss[0]) if worst_loss[0] is not None else None,
            value_cents=worst_loss[2],
            night_date=worst_loss[1],
        ),
    ]
    return schemas.StatsOut(ranking=ranking, records=records, total_nights=len(nights))


def compute_evolution(db: DBSession, group_id: int) -> schemas.EvolutionOut:
    nights = active_nights(db, group_id)
    names = _participant_names(db, group_id)

    dates = [n.date for n in nights]
    # cumulative[pid] keeps a running total; we record it at every night date so all
    # series share the same x-axis (carry-forward when a player is absent).
    running = defaultdict(int)
    seen: set[int] = set()
    points_by_pid: dict[int, list[schemas.EvolutionPoint]] = defaultdict(list)

    for i, night in enumerate(nights):
        present = {e.participant_id: e.profit_cents for e in night.entries}
        for pid in present:
            if pid not in seen:
                seen.add(pid)
                # Left-pad with nulls up to the debut night so every series has exactly
                # len(dates) points and data[i] always lines up with labels[i].
                points_by_pid[pid] = [
                    schemas.EvolutionPoint(date=d, cumulative_cents=None) for d in dates[:i]
                ]
        for pid in seen:
            running[pid] += present.get(pid, 0)
            points_by_pid[pid].append(
                schemas.EvolutionPoint(date=night.date, cumulative_cents=running[pid])
            )

    series = [
        schemas.EvolutionSeries(participant_id=pid, name=names.get(pid, "?"), points=pts)
        for pid, pts in points_by_pid.items()
    ]
    series.sort(key=lambda s: s.points[-1].cumulative_cents if s.points else 0, reverse=True)
    return schemas.EvolutionOut(dates=dates, series=series)


def rotate_share_token(db: DBSession, group: models.Group) -> str:
    group.share_token = new_token(24)
    db.add(group)
    db.commit()
    db.refresh(group)
    return group.share_token
