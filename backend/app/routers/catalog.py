from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session as DBSession
from sqlmodel import select

from .. import models, schemas
from ..auth import require_owner
from ..db import get_session
from ..errors import api_error

router = APIRouter(prefix="/api/groups/{group_id}", tags=["catalog"])


# ---------- Participants (soft-delete to preserve history) ----------
@router.get("/participants", response_model=list[schemas.ParticipantOut])
def list_participants(group_id: int, _: models.User = Depends(require_owner), db: DBSession = Depends(get_session)):
    rows = db.exec(
        select(models.Participant).where(models.Participant.group_id == group_id).order_by(models.Participant.name)
    ).all()
    return [schemas.ParticipantOut(id=p.id, name=p.name, active=p.active) for p in rows]


@router.post("/participants", response_model=schemas.ParticipantOut, status_code=201)
def create_participant(group_id: int, body: schemas.NamedCreate, _: models.User = Depends(require_owner), db: DBSession = Depends(get_session)):
    if db.exec(select(models.Participant).where(models.Participant.group_id == group_id, models.Participant.name == body.name)).first():
        raise api_error(
            status.HTTP_409_CONFLICT, "participant_exists", "Participante já existe neste grupo"
        )
    p = models.Participant(group_id=group_id, name=body.name)
    db.add(p)
    db.commit()
    db.refresh(p)
    return schemas.ParticipantOut(id=p.id, name=p.name, active=p.active)


@router.patch("/participants/{participant_id}", response_model=schemas.ParticipantOut)
def update_participant(group_id: int, participant_id: int, body: schemas.ParticipantUpdate, _: models.User = Depends(require_owner), db: DBSession = Depends(get_session)):
    p = db.get(models.Participant, participant_id)
    if not p or p.group_id != group_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Participante não encontrado")
    # Partial: only what the client sent. Lets `{"active": true}` reactivate without a name.
    data = body.model_dump(exclude_unset=True, exclude_none=True)
    if "name" in data:
        p.name = data["name"]
    if "active" in data:
        p.active = data["active"]
    db.add(p)
    db.commit()
    db.refresh(p)
    return schemas.ParticipantOut(id=p.id, name=p.name, active=p.active)


@router.delete("/participants/{participant_id}", status_code=204)
def delete_participant(group_id: int, participant_id: int, _: models.User = Depends(require_owner), db: DBSession = Depends(get_session)):
    p = db.get(models.Participant, participant_id)
    if not p or p.group_id != group_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Participante não encontrado")
    has_history = db.exec(select(models.NightEntry).where(models.NightEntry.participant_id == participant_id)).first()
    if has_history:
        p.active = False  # keep stats intact
        db.add(p)
    else:
        db.delete(p)
    db.commit()


# ---------- Generic named lookups: places / variants / formats ----------
def _place_in_use(db: DBSession, place_id: int) -> bool:
    return db.exec(select(models.Night).where(models.Night.place_id == place_id)).first() is not None


def _named_routes(path: str, model: type, label: str, code: str, in_use=None):
    @router.get(f"/{path}", response_model=list[schemas.NamedOut], name=f"list_{path}")
    def _list(group_id: int, _: models.User = Depends(require_owner), db: DBSession = Depends(get_session)):
        rows = db.exec(select(model).where(model.group_id == group_id).order_by(model.name)).all()
        return [schemas.NamedOut(id=r.id, name=r.name) for r in rows]

    @router.post(f"/{path}", response_model=schemas.NamedOut, status_code=201, name=f"create_{path}")
    def _create(group_id: int, body: schemas.NamedCreate, _: models.User = Depends(require_owner), db: DBSession = Depends(get_session)):
        if db.exec(select(model).where(model.group_id == group_id, model.name == body.name)).first():
            raise api_error(status.HTTP_409_CONFLICT, f"{code}_exists", f"{label} já existe")
        r = model(group_id=group_id, name=body.name)
        db.add(r)
        db.commit()
        db.refresh(r)
        return schemas.NamedOut(id=r.id, name=r.name)

    @router.delete(f"/{path}/{{item_id}}", status_code=204, name=f"delete_{path}")
    def _delete(group_id: int, item_id: int, _: models.User = Depends(require_owner), db: DBSession = Depends(get_session)):
        r = db.get(model, item_id)
        if not r or r.group_id != group_id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"{label} não encontrado")
        # Check up front: relying on the FK error would surface as an opaque 500/409.
        if in_use and in_use(db, item_id):
            raise api_error(
                status.HTTP_409_CONFLICT,
                f"{code}_in_use",
                f"{label} está sendo usado por noites registradas e não pode ser excluído",
            )
        db.delete(r)
        db.commit()


_named_routes("places", models.Place, "Local", code="place", in_use=_place_in_use)
