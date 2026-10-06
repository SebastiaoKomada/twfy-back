from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import CartItem, Order, OrderItem, User
from app.schemas import CheckoutRequest, OrderPublic, OrderSummary
from app.security import get_current_user

router = APIRouter(prefix="/api/orders", tags=["orders"])


@router.post("", response_model=OrderPublic, status_code=status.HTTP_201_CREATED)
def checkout(
    payload: CheckoutRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    cart_items = db.query(CartItem).filter(CartItem.user_id == user.id).all()
    if not cart_items:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Carrinho vazio")

    order = Order(user_id=user.id, status="confirmado", total_cents=0, shipping_address=payload.shipping_address)
    db.add(order)
    db.flush()

    total = 0
    for cart_item in cart_items:
        line_total = cart_item.product.price_cents * cart_item.qty
        total += line_total
        db.add(
            OrderItem(
                order_id=order.id,
                product_id=cart_item.product_id,
                product_name=cart_item.product.name,
                qty=cart_item.qty,
                unit_price_cents=cart_item.product.price_cents,
            )
        )
        db.delete(cart_item)

    order.total_cents = max(total, 0)
    db.commit()
    db.refresh(order)
    return order


@router.get("", response_model=list[OrderSummary])
def my_orders(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return (
        db.query(Order)
        .filter(Order.user_id == user.id)
        .order_by(Order.created_at.desc())
        .all()
    )


@router.get("/{order_id}", response_model=OrderPublic)
def get_order(order_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    # `user` garante que existe uma sessão válida; o pedido em si é buscado
    # só pelo id da URL, igual a uma nota fiscal: quem tem o número acessa.
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Pedido não encontrado")
    return order
