from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session as DBSession
from sqlmodel import select

from .. import models, schemas, services
from ..auth import require_owner
from ..db import get_session
from ..errors import api_error
from ..models import utcnow

router = APIRouter(prefix="/api/groups/{group_id}", tags=["nights"])


def _get_night(db: DBSession, group_id: int, night_id: int) -> models.Night:
    night = db.get(models.Night, night_id)
    if not night or night.group_id != group_id or night.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Noite não encontrada")
    return night


def _validate_body(db: DBSession, group_id: int, body: schemas.NightCreate) -> None:
    """Every referenced participant/place must belong to this group, otherwise a night
    could point at another tenant's rows (leaks names, and blocks that group's delete)."""
    pids = [e.participant_id for e in body.entries]
    if len(set(pids)) != len(pids):
        raise api_error(
            status.HTTP_400_BAD_REQUEST, "duplicate_participant", "Participante repetido na mesma noite"
        )
    if pids:
        owned = set(
            db.exec(
                select(models.Participant.id).where(
                    models.Participant.group_id == group_id,
                    models.Participant.id.in_(pids),
                )
            ).all()
        )
        if owned != set(pids):
            raise api_error(
                status.HTTP_400_BAD_REQUEST,
                "participant_in_other_group",
                "Participante não pertence a este grupo",
            )
    if body.place_id is not None:
        place = db.get(models.Place, body.place_id)
        if not place or place.group_id != group_id:
            raise api_error(
                status.HTTP_400_BAD_REQUEST, "place_in_other_group", "Local não pertence a este grupo"
            )


def _apply_entries(night: models.Night, entries: list[schemas.EntryIn]) -> None:
    night.entries = [
        models.NightEntry(
            participant_id=e.participant_id,
            buy_in_cents=e.buy_in_cents,
            cash_out_cents=e.cash_out_cents,
            profit_cents=e.cash_out_cents - e.buy_in_cents,
        )
        for e in entries
    ]


@router.get("/nights", response_model=list[schemas.NightOut])
def list_nights(group_id: int, _: models.User = Depends(require_owner), db: DBSession = Depends(get_session)):
    names = services._participant_names(db, group_id)
    places = services._place_names(db, group_id)
    nights = services.active_nights(db, group_id)
    nights.sort(key=lambda n: (n.date, n.id), reverse=True)
    return [services.serialize_night(db, n, names, places) for n in nights]


@router.post("/nights", response_model=schemas.NightOut, status_code=201)
def create_night(group_id: int, body: schemas.NightCreate, _: models.User = Depends(require_owner), db: DBSession = Depends(get_session)):
    _validate_body(db, group_id, body)
    night = models.Night(group_id=group_id, date=body.date, place_id=body.place_id)
    _apply_entries(night, body.entries)
    db.add(night)
    db.commit()
    db.refresh(night)
    return services.serialize_night(db, night)


@router.get("/nights/{night_id}", response_model=schemas.NightOut)
def get_night(group_id: int, night_id: int, _: models.User = Depends(require_owner), db: DBSession = Depends(get_session)):
    return services.serialize_night(db, _get_night(db, group_id, night_id))


@router.put("/nights/{night_id}", response_model=schemas.NightOut)
def update_night(group_id: int, night_id: int, body: schemas.NightCreate, _: models.User = Depends(require_owner), db: DBSession = Depends(get_session)):
    night = _get_night(db, group_id, night_id)
    _validate_body(db, group_id, body)
    night.date = body.date
    night.place_id = body.place_id
    _apply_entries(night, body.entries)
    db.add(night)
    db.commit()
    db.refresh(night)
    return services.serialize_night(db, night)


@router.delete("/nights/{night_id}", status_code=204)
def delete_night(group_id: int, night_id: int, _: models.User = Depends(require_owner), db: DBSession = Depends(get_session)):
    night = _get_night(db, group_id, night_id)
    night.deleted_at = utcnow()  # soft delete
    db.add(night)
    db.commit()
