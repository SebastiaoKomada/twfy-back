"""Hashing de senha, criação de sessão e dependências de autenticação.

A sessão trafega como um token Bearer (header ``Authorization``), não como
cookie: o front (Amplify) e a API (EC2) vivem em domínios distintos, e um
cookie de sessão entre sites diferentes esbarra no bloqueio de cookies de
terceiros dos navegadores atuais. Guardamos o token no SessionToken como um
valor opaco — o cliente só sabe que precisa reenviá-lo.
"""
from __future__ import annotations

import datetime as dt
import secrets

import bcrypt
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.models import SessionToken, User


def hash_password(raw: str) -> str:
    return bcrypt.hashpw(raw.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(raw: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(raw.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        return False


def create_session(db: Session, user: User) -> SessionToken:
    token = secrets.token_urlsafe(32)
    expires_at = dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=settings.session_ttl_days)
    session = SessionToken(token=token, user_id=user.id, expires_at=expires_at)
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def extract_bearer_token(request: Request) -> str | None:
    header = request.headers.get("authorization")
    if not header or not header.lower().startswith("bearer "):
        return None
    return header.split(" ", 1)[1].strip()


def get_current_session(request: Request, db: Session = Depends(get_db)) -> SessionToken:
    token = extract_bearer_token(request)
    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Não autenticado")

    session = db.query(SessionToken).filter(SessionToken.token == token).first()
    if not session:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sessão inválida")

    now = dt.datetime.now(dt.timezone.utc)
    expires_at = session.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=dt.timezone.utc)
    if expires_at < now:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sessão expirada")

    return session


def get_current_user(session: SessionToken = Depends(get_current_session), db: Session = Depends(get_db)) -> User:
    user = db.query(User).filter(User.id == session.user_id).first()
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sessão inválida")
    return user


def require_role(*roles: str):
    def _dependency(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Sem permissão para esta ação")
        return user

    return _dependency
