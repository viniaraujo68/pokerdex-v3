from fastapi import APIRouter, Depends
from sqlmodel import Session as DBSession

from .. import models, schemas, services
from ..auth import require_owner
from ..db import get_session

router = APIRouter(prefix="/api/groups/{group_id}", tags=["stats"])


@router.get("/stats", response_model=schemas.StatsOut)
def get_stats(group_id: int, _: models.User = Depends(require_owner), db: DBSession = Depends(get_session)):
    return services.compute_stats(db, group_id)


@router.get("/evolution", response_model=schemas.EvolutionOut)
def get_evolution(group_id: int, _: models.User = Depends(require_owner), db: DBSession = Depends(get_session)):
    return services.compute_evolution(db, group_id)
