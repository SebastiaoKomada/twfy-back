from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import SessionToken, User
from app.schemas import AuthResponse, LoginRequest, RegisterRequest, UserPublic
from app.security import (
    create_session,
    extract_bearer_token,
    get_current_user,
    hash_password,
    verify_password,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])

# Papéis que a tela de cadastro pode atribuir diretamente: a loja permite que
# a mesma tela crie tanto uma conta de comprador quanto uma conta de loja
# ("Quero vender também"), então o campo "role" do formulário é repassado
# para o registro do usuário.
_ALLOWED_SELF_SIGNUP_ROLES = {"comprador", "vendedor"}


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status.HTTP_409_CONFLICT, "E-mail já cadastrado")

    role = payload.role or "comprador"
    user = User(
        name=payload.name,
        email=payload.email,
        password_hash=hash_password(payload.password),
        role=role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    session = create_session(db, user)
    return AuthResponse(user=UserPublic.model_validate(user), token=session.token)


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "E-mail não cadastrado")
    if not verify_password(payload.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Senha incorreta")

    session = create_session(db, user)
    return AuthResponse(user=UserPublic.model_validate(user), token=session.token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request, db: Session = Depends(get_db)):
    token = extract_bearer_token(request)
    if token:
        db.query(SessionToken).filter(SessionToken.token == token).delete()
        db.commit()
    return None


@router.get("/me", response_model=UserPublic)
def me(user: User = Depends(get_current_user)):
    return user


@router.get("/continue")
def continue_to(next: str = "/"):
    """Leva o visitante de volta à página em que estava antes do login,
    como um link de retorno de e-mail ou de um provedor de login externo."""
    return RedirectResponse(url=next, status_code=status.HTTP_302_FOUND)
