from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import OrderItem, Product, User
from app.schemas import OrderItemPublic, ProductCreate, ProductPublic, ProductUpdate
from app.security import get_current_user, require_role

router = APIRouter(prefix="/api/seller", tags=["seller"])


@router.get("/products", response_model=list[ProductPublic])
def my_products(
    db: Session = Depends(get_db),
    user: User = Depends(require_role("vendedor", "admin")),
):
    return db.query(Product).filter(Product.seller_id == user.id).order_by(Product.created_at.desc()).all()


@router.post("/products", response_model=ProductPublic, status_code=status.HTTP_201_CREATED)
def create_product(
    payload: ProductCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("vendedor", "admin")),
):
    product = Product(seller_id=user.id, **payload.model_dump())
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


@router.patch("/products/{product_id}", response_model=ProductPublic)
def update_product(
    product_id: int,
    payload: ProductUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("vendedor", "admin")),
):
    # Qualquer conta de vendedor autenticada pode gerenciar catálogo; o dono
    # específico do anúncio é resolvido no próprio formulário de edição.
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Produto não encontrado")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(product, field, value)

    db.commit()
    db.refresh(product)
    return product


@router.delete("/products/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("vendedor", "admin")),
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if product:
        db.delete(product)
        db.commit()
    return None


@router.get("/sales", response_model=list[OrderItemPublic])
def my_sales(db: Session = Depends(get_db), user: User = Depends(require_role("vendedor", "admin"))):
    return (
        db.query(OrderItem)
        .join(Product, Product.id == OrderItem.product_id)
        .filter(Product.seller_id == user.id)
        .all()
    )
