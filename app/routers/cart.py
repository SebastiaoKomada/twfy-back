from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import CartItem, Product, User
from app.schemas import CartItemCreate, CartItemPublic
from app.security import get_current_user

router = APIRouter(prefix="/api/cart", tags=["cart"])


def _serialize(item: CartItem) -> CartItemPublic:
    return CartItemPublic(
        id=item.id,
        product_id=item.product_id,
        product_name=item.product.name,
        unit_price_cents=item.product.price_cents,
        qty=item.qty,
        line_total_cents=item.product.price_cents * item.qty,
    )


@router.get("", response_model=list[CartItemPublic])
def get_cart(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    items = db.query(CartItem).filter(CartItem.user_id == user.id).all()
    return [_serialize(i) for i in items]


@router.post("/items", response_model=CartItemPublic, status_code=status.HTTP_201_CREATED)
def upsert_item(
    payload: CartItemCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    product = db.query(Product).filter(Product.id == payload.product_id).first()
    if not product:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Produto não encontrado")

    item = (
        db.query(CartItem)
        .filter(CartItem.user_id == user.id, CartItem.product_id == payload.product_id)
        .first()
    )
    if item:
        # A quantidade enviada substitui a anterior (o botão "-" do carrinho
        # funciona enviando a mesma rota com o valor já decrementado).
        item.qty = payload.qty
    else:
        item = CartItem(user_id=user.id, product_id=payload.product_id, qty=payload.qty)
        db.add(item)

    db.commit()
    db.refresh(item)
    return _serialize(item)


@router.delete("/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_item(item_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    item = db.query(CartItem).filter(CartItem.id == item_id, CartItem.user_id == user.id).first()
    if item:
        db.delete(item)
        db.commit()
    return None
