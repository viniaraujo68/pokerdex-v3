from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete as sa_delete
from sqlmodel import Session as DBSession
from sqlmodel import func, select

from .. import models, schemas, services
from ..auth import get_current_user, require_owner
from ..db import get_session

router = APIRouter(prefix="/api/groups", tags=["groups"])


def _to_out(db: DBSession, g: models.Group) -> schemas.GroupOut:
    night_count = db.exec(
        select(func.count(models.Night.id)).where(
            models.Night.group_id == g.id, models.Night.deleted_at == None  # noqa: E711
        )
    ).one()
    participant_count = db.exec(
        select(func.count(models.Participant.id)).where(
            models.Participant.group_id == g.id, models.Participant.active == True  # noqa: E712
        )
    ).one()
    return schemas.GroupOut(
        id=g.id, name=g.name, slug=g.slug, description=g.description, currency=g.currency,
        visibility=g.visibility, share_token=g.share_token,
        night_count=night_count, participant_count=participant_count,
    )


@router.get("", response_model=list[schemas.GroupOut])
def list_my_groups(user: models.User = Depends(get_current_user), db: DBSession = Depends(get_session)):
    group_ids = db.exec(
        select(models.GroupOwner.group_id).where(models.GroupOwner.user_id == user.id)
    ).all()
    groups = db.exec(select(models.Group).where(models.Group.id.in_(group_ids))).all() if group_ids else []
    return [_to_out(db, g) for g in groups]


@router.post("", response_model=schemas.GroupOut, status_code=201)
def create_group(
    body: schemas.GroupCreate,
    user: models.User = Depends(get_current_user),
    db: DBSession = Depends(get_session),
):
    group = models.Group(
        name=body.name, slug=services.unique_slug(db, body.name),
        description=body.description, currency=body.currency,
        visibility=body.visibility if body.visibility in ("private", "public") else "private",
    )
    db.add(group)
    db.commit()
    db.refresh(group)
    db.add(models.GroupOwner(group_id=group.id, user_id=user.id))
    db.commit()
    return _to_out(db, group)


@router.get("/{group_id}", response_model=schemas.GroupOut)
def get_group(group_id: int, user: models.User = Depends(require_owner), db: DBSession = Depends(get_session)):
    group = db.get(models.Group, group_id)
    if not group:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Grupo não encontrado")
    return _to_out(db, group)


@router.patch("/{group_id}", response_model=schemas.GroupOut)
def update_group(
    group_id: int,
    body: schemas.GroupUpdate,
    user: models.User = Depends(require_owner),
    db: DBSession = Depends(get_session),
):
    group = db.get(models.Group, group_id)
    if not group:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Grupo não encontrado")
    data = body.model_dump(exclude_unset=True)
    if "visibility" in data and data["visibility"] not in ("private", "public"):
        data.pop("visibility")
    for k, v in data.items():
        setattr(group, k, v)
    db.add(group)
    db.commit()
    db.refresh(group)
    return _to_out(db, group)


@router.delete("/{group_id}", status_code=204)
def delete_group(group_id: int, user: models.User = Depends(require_owner), db: DBSession = Depends(get_session)):
    if not db.get(models.Group, group_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Grupo não encontrado")
    # Bulk-delete children in FK-safe order, then the group itself.
    night_ids = select(models.Night.id).where(models.Night.group_id == group_id)
    opts = {"synchronize_session": False}
    db.execute(sa_delete(models.NightEntry).where(models.NightEntry.night_id.in_(night_ids)), execution_options=opts)
    db.execute(sa_delete(models.Night).where(models.Night.group_id == group_id), execution_options=opts)
    db.execute(sa_delete(models.Participant).where(models.Participant.group_id == group_id), execution_options=opts)
    db.execute(sa_delete(models.Place).where(models.Place.group_id == group_id), execution_options=opts)
    db.execute(sa_delete(models.GroupOwner).where(models.GroupOwner.group_id == group_id), execution_options=opts)
    db.execute(sa_delete(models.Group).where(models.Group.id == group_id), execution_options=opts)
    db.commit()


@router.post("/{group_id}/rotate-share-token", response_model=schemas.GroupOut)
def rotate_token(group_id: int, user: models.User = Depends(require_owner), db: DBSession = Depends(get_session)):
    group = db.get(models.Group, group_id)
    if not group:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Grupo não encontrado")
    services.rotate_share_token(db, group)
    return _to_out(db, group)
