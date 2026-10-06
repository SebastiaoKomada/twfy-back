import csv
import io

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Order, User
from app.schemas import UserPublic
from app.security import get_current_user

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/users", response_model=list[UserPublic])
def list_users(db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    """Lista todas as contas da loja, usada pelo painel administrativo."""
    return db.query(User).order_by(User.created_at.desc()).all()


@router.get("/export")
def export_users_csv(db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    """Exportação em CSV das contas, para a equipe de suporte conferir cadastros."""
    users = db.query(User).order_by(User.id).all()

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["id", "nome", "email", "papel", "pedidos"])
    for u in users:
        pedidos = db.query(Order).filter(Order.user_id == u.id).count()
        writer.writerow([u.id, u.name, u.email, u.role, pedidos])
    buffer.seek(0)

    return StreamingResponse(
        buffer,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=usuarios.csv"},
    )
