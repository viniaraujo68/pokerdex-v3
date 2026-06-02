from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlmodel import Session as DBSession
from sqlmodel import select

from .. import schemas
from ..auth import create_session, destroy_session, get_current_user
from ..db import get_session
from ..models import User
from ..security import hash_password, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=schemas.UserOut, status_code=201)
def register(creds: schemas.Credentials, response: Response, db: DBSession = Depends(get_session)):
    exists = db.exec(select(User).where(User.username == creds.username)).first()
    if exists:
        raise HTTPException(status.HTTP_409_CONFLICT, "Nome de usuário já existe")
    user = User(username=creds.username, password_hash=hash_password(creds.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    create_session(db, user.id, response)
    return schemas.UserOut(id=user.id, username=user.username)


@router.post("/login", response_model=schemas.UserOut)
def login(creds: schemas.Credentials, response: Response, db: DBSession = Depends(get_session)):
    user = db.exec(select(User).where(User.username == creds.username)).first()
    if not user or not verify_password(creds.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Usuário ou senha inválidos")
    create_session(db, user.id, response)
    return schemas.UserOut(id=user.id, username=user.username)


@router.post("/logout", status_code=204)
def logout(request: Request, response: Response, db: DBSession = Depends(get_session)):
    destroy_session(db, request, response)


@router.get("/me", response_model=schemas.UserOut)
def me(user: User = Depends(get_current_user)):
    return schemas.UserOut(id=user.id, username=user.username)
