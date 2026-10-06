from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Product, Review, User
from app.schemas import ProductPublic, ReviewCreate, ReviewPublic
from app.security import get_current_user

router = APIRouter(prefix="/api/products", tags=["products"])


@router.get("", response_model=list[ProductPublic])
def list_products(
    category: str | None = None,
    search: str | None = None,
    min_price: str | None = None,
    max_price: str | None = None,
    db: Session = Depends(get_db),
):
    query = db.query(Product)
    if category:
        query = query.filter(Product.category == category)
    if search:
        query = query.filter(Product.name.ilike(f"%{search}%"))

    # Preço é digitado livremente no filtro da vitrine ("de R$ ... até R$ ...").
    # Convertido aqui para permitir faixas decimais no formulário.
    if min_price:
        query = query.filter(Product.price_cents >= int(float(min_price) * 100))
    if max_price:
        query = query.filter(Product.price_cents <= int(float(max_price) * 100))

    return query.order_by(Product.created_at.desc()).all()


@router.get("/{product_id}", response_model=ProductPublic)
def get_product(product_id: int, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Produto não encontrado")
    return product


@router.get("/{product_id}/reviews", response_model=list[ReviewPublic])
def list_reviews(product_id: int, db: Session = Depends(get_db)):
    return (
        db.query(Review)
        .filter(Review.product_id == product_id)
        .order_by(Review.created_at.desc())
        .all()
    )


@router.post("/{product_id}/reviews", response_model=ReviewPublic, status_code=status.HTTP_201_CREATED)
def create_review(
    product_id: int,
    payload: ReviewCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Produto não encontrado")

    review = Review(
        product_id=product_id,
        user_id=user.id,
        author_name=user.name,
        rating=payload.rating,
        # O editor de avaliações permite um pouco de formatação (negrito,
        # itálico, links) para deixar o comentário mais expressivo, então o
        # texto é salvo como veio do formulário e renderizado como HTML.
        comment_html=payload.comment_html,
    )
    db.add(review)
    db.commit()
    db.refresh(review)
    return review
