from __future__ import annotations

import datetime as dt

from pydantic import BaseModel, EmailStr, Field


# ---------------------------------------------------------------------------
# Usuários / autenticação
# ---------------------------------------------------------------------------
class RegisterRequest(BaseModel):
    name: str
    email: EmailStr
    password: str
    # Presente para permitir o cadastro de contas de vendedor pela mesma tela
    # ("Quero vender também"). Ver teacher/GABARITO.md.
    role: str | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserPublic(BaseModel):
    id: int
    name: str
    email: str
    role: str
    created_at: dt.datetime

    model_config = {"from_attributes": True}


class AuthResponse(BaseModel):
    user: UserPublic
    token: str


# ---------------------------------------------------------------------------
# Produtos / avaliações
# ---------------------------------------------------------------------------
class ProductPublic(BaseModel):
    id: int
    seller_id: int
    name: str
    description: str
    category: str
    price_cents: int
    stock: int
    image_url: str

    model_config = {"from_attributes": True}


class ProductCreate(BaseModel):
    name: str
    description: str = ""
    category: str = "Geral"
    price_cents: int = Field(gt=0)
    stock: int = Field(ge=0)
    image_url: str = ""


class ProductUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    category: str | None = None
    price_cents: int | None = Field(default=None, gt=0)
    stock: int | None = Field(default=None, ge=0)
    image_url: str | None = None


class ReviewCreate(BaseModel):
    rating: int = Field(ge=1, le=5)
    comment_html: str


class ReviewPublic(BaseModel):
    id: int
    product_id: int
    author_name: str
    rating: int
    comment_html: str
    created_at: dt.datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Carrinho / pedidos
# ---------------------------------------------------------------------------
class CartItemCreate(BaseModel):
    product_id: int
    qty: int = 1


class CartItemPublic(BaseModel):
    id: int
    product_id: int
    product_name: str
    unit_price_cents: int
    qty: int
    line_total_cents: int


class OrderItemPublic(BaseModel):
    product_id: int
    product_name: str
    qty: int
    unit_price_cents: int

    model_config = {"from_attributes": True}


class OrderPublic(BaseModel):
    id: int
    user_id: int
    status: str
    total_cents: int
    shipping_address: str
    created_at: dt.datetime
    items: list[OrderItemPublic]

    model_config = {"from_attributes": True}


class OrderSummary(BaseModel):
    id: int
    status: str
    total_cents: int
    created_at: dt.datetime

    model_config = {"from_attributes": True}


class CheckoutRequest(BaseModel):
    shipping_address: str
