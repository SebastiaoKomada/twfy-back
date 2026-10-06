import platform
import sys

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.models import Product

router = APIRouter(prefix="/api", tags=["misc"])


@router.get("/categories", response_model=list[str])
def list_categories(db: Session = Depends(get_db)):
    rows = db.query(Product.category).distinct().all()
    return sorted({row[0] for row in rows})


@router.get("/system/status")
def system_status():
    """Usado pelo balanceador de carga para checar se a API está no ar."""
    return {
        "app": settings.app_name,
        "environment": settings.environment,
        "python_version": sys.version,
        "platform": platform.platform(),
        "database_path": str(settings.database_path),
    }
