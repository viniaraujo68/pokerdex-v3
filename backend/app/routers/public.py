from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session as DBSession
from sqlmodel import func, select

from .. import models, schemas, services
from ..db import get_session

router = APIRouter(prefix="/api/public", tags=["public"])


@router.get("", response_model=list[schemas.PublicGroupSummary])
def search_public_groups(
    q: str = Query("", max_length=80),
    limit: int = Query(30, ge=1, le=100),
    db: DBSession = Depends(get_session),
):
    """Directory/search of public groups (anyone can discover these)."""
    stmt = select(models.Group).where(models.Group.visibility == "public")
    term = q.strip()
    if term:
        like = f"%{term.lower()}%"
        stmt = stmt.where(
            func.lower(models.Group.name).like(like) | func.lower(models.Group.slug).like(like)
        )
    groups = db.exec(stmt.order_by(models.Group.name).limit(limit)).all()

    out = []
    for g in groups:
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
        out.append(
            schemas.PublicGroupSummary(
                name=g.name, slug=g.slug, description=g.description,
                night_count=night_count, participant_count=participant_count,
            )
        )
    return out


@router.get("/{slug}", response_model=schemas.PublicGroupOut)
def get_public_group(slug: str, t: str | None = None, db: DBSession = Depends(get_session)):
    group = db.exec(select(models.Group).where(models.Group.slug == slug)).first()
    if not group:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Grupo não encontrado")

    # Access: public groups are open; private groups require a matching share token.
    allowed = group.visibility == "public" or (group.share_token and t == group.share_token)
    if not allowed:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Este grupo é privado")

    names = services._participant_names(db, group.id)
    nights = services.active_nights(db, group.id)
    nights.sort(key=lambda n: (n.date, n.id), reverse=True)
    return schemas.PublicGroupOut(
        name=group.name,
        slug=group.slug,
        description=group.description,
        currency=group.currency,
        stats=services.compute_stats(db, group.id),
        evolution=services.compute_evolution(db, group.id),
        nights=[services.serialize_night(db, n, names) for n in nights],
    )
