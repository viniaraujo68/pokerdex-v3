from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlmodel import Session as DBSession
from sqlmodel import func, select

from .. import models, schemas, services
from ..config import settings
from ..db import get_session
from ..errors import api_error
from ..ratelimit import limiter

router = APIRouter(prefix="/api/public", tags=["public"])


# Unauthenticated and cheap to scrape, so rate limited per IP.
@router.get("", response_model=list[schemas.PublicGroupSummary])
@limiter.limit(settings.rate_limit_public)
def search_public_groups(
    request: Request,
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

    # 2 grouped-count queries for the whole page instead of 2 per group.
    night_counts, participant_counts = services.group_counts(db, [g.id for g in groups])
    return [
        schemas.PublicGroupSummary(
            name=g.name, slug=g.slug, description=g.description,
            night_count=night_counts.get(g.id, 0),
            participant_count=participant_counts.get(g.id, 0),
        )
        for g in groups
    ]


@router.get("/{slug}", response_model=schemas.PublicGroupOut)
@limiter.limit(settings.rate_limit_public)
def get_public_group(request: Request, slug: str, t: str | None = None, db: DBSession = Depends(get_session)):
    group = db.exec(select(models.Group).where(models.Group.slug == slug)).first()
    if not group:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Grupo não encontrado")

    # Access: public groups are open; private groups require a matching share token.
    allowed = group.visibility == "public" or (group.share_token and t == group.share_token)
    if not allowed:
        raise api_error(status.HTTP_403_FORBIDDEN, "group_private", "Este grupo é privado")

    names = services._participant_names(db, group.id)
    places = services._place_names(db, group.id)
    nights = services.active_nights(db, group.id)
    nights.sort(key=lambda n: (n.date, n.id), reverse=True)
    return schemas.PublicGroupOut(
        name=group.name,
        slug=group.slug,
        description=group.description,
        currency=group.currency,
        stats=services.compute_stats(db, group.id),
        evolution=services.compute_evolution(db, group.id),
        nights=[services.serialize_night(db, n, names, places) for n in nights],
    )
