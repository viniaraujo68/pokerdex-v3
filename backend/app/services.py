"""Serialization and stats computation. Stats are always derived from NightEntry
rows (no denormalized aggregates), so edits/deletes can never desync totals."""
from collections import defaultdict

from slugify import slugify
from sqlmodel import Session as DBSession
from sqlmodel import select

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


def serialize_night(
    db: DBSession, night: models.Night, names: dict[int, str] | None = None
) -> schemas.NightOut:
    if names is None:
        names = _participant_names(db, night.group_id)
    place_name = db.get(models.Place, night.place_id).name if night.place_id else None
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
    return list(
        db.exec(
            select(models.Night)
            .where(models.Night.group_id == group_id, models.Night.deleted_at == None)  # noqa: E711
            .order_by(models.Night.date, models.Night.id)
        ).all()
    )


def compute_stats(db: DBSession, group_id: int) -> schemas.StatsOut:
    nights = active_nights(db, group_id)
    names = _participant_names(db, group_id)

    profit = defaultdict(int)
    buy_in = defaultdict(int)
    played = defaultdict(int)
    best_win = (None, None, 0)  # (pid, date, cents)
    worst_loss = (None, None, 0)

    for night in nights:
        for e in night.entries:
            profit[e.participant_id] += e.profit_cents
            buy_in[e.participant_id] += e.buy_in_cents
            played[e.participant_id] += 1
            if e.profit_cents > best_win[2]:
                best_win = (e.participant_id, night.date, e.profit_cents)
            if e.profit_cents < worst_loss[2]:
                worst_loss = (e.participant_id, night.date, e.profit_cents)

    ranking = []
    for pid, total in profit.items():
        n = played[pid]
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
            participant_name=names.get(best_win[0]) if best_win[0] else None,
            value_cents=best_win[2],
            night_date=best_win[1],
        ),
        schemas.Record(
            label="Maior derrota numa noite",
            participant_name=names.get(worst_loss[0]) if worst_loss[0] else None,
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

    for night in nights:
        present = {e.participant_id: e.profit_cents for e in night.entries}
        seen.update(present.keys())
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
