"""Popula o banco com dados de demonstração para a aula.

Uso:
    python -m app.seed          # cria as tabelas (se não existirem) e semeia
    python -m app.seed --reset  # apaga tudo e recomeça do zero
"""
from __future__ import annotations

import argparse
import datetime as dt
from urllib.parse import quote

from app.db import Base, SessionLocal, engine
from app.models import CartItem, Order, OrderItem, Product, Review, SessionToken, User
from app.security import hash_password


def _img(commons_filename: str) -> str:
    """Foto real do produto, servida pelo Wikimedia Commons (acervo livre,
    sem necessidade de chave de API). ``Special:FilePath`` sempre resolve
    para o arquivo atual, com ``width`` pedindo uma miniatura do tamanho
    certo para os cards da vitrine."""
    return f"https://commons.wikimedia.org/wiki/Special:FilePath/{quote(commons_filename)}?width=480"


def reset_schema() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def seed() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.query(User).count() > 0:
            print("Banco já populado — nada a fazer (use --reset para recomeçar).")
            return

        admin = User(
            name="Administração Tw4y",
            email="admin@tw4y.com.br",
            password_hash=hash_password("admin123"),
            role="admin",
        )
        seller_a = User(
            name="Loja Aventura",
            email="loja.aventura@tw4y.com.br",
            password_hash=hash_password("vendedor123"),
            role="vendedor",
        )
        seller_b = User(
            name="Tech Store BR",
            email="techstore@tw4y.com.br",
            password_hash=hash_password("vendedor456"),
            role="vendedor",
        )
        buyer_a = User(
            name="Ana Silva",
            email="ana.silva@tw4y.com.br",
            password_hash=hash_password("comprador123"),
            role="comprador",
        )
        buyer_b = User(
            name="Bruno Costa",
            email="bruno.costa@tw4y.com.br",
            password_hash=hash_password("comprador456"),
            role="comprador",
        )
        db.add_all([admin, seller_a, seller_b, buyer_a, buyer_b])
        db.flush()

        # Última posição de cada tupla: nome do arquivo no Wikimedia Commons
        # (conferido visualmente — ver teacher/ para o critério de escolha).
        aventura_products = [
            ("Barraca de Camping 4 Pessoas", "Barraca impermeável, armação em fibra, ideal para trilhas.", "Esportes", 59900, 15, "CampingTent1.jpg"),
            ("Mochila Cargueira 60L", "Mochila de trilha com suporte lombar ajustável.", "Esportes", 42900, 20, "Haglöfs Alaska backpack.jpg"),
            ("Kit Trekking Poles", "Par de bastões retráteis em alumínio.", "Esportes", 18900, 30, "Retracted trekking poles.jpg"),
            ("Lanterna de Cabeça LED", "300 lúmens, recarregável via USB.", "Esportes", 8900, 50, "Ledlenser H7R 2 liegend.jpg"),
            ("Saco de Dormir Térmico", "Conforto térmico até -5°C.", "Esportes", 25900, 18, "Mummy bag.jpg"),
            ("Garrafa Térmica 1L", "Mantém temperatura por até 12 horas.", "Esportes", 7900, 60, "Esbit thermosflasche.jpg"),
            ("Bota de Trilha Impermeável", "Solado emborrachado antiderrapante.", "Esportes", 34900, 22, "Hiking shoes Lowa.jpg"),
        ]
        tech_products = [
            ("Fone Bluetooth Over-ear", "Cancelamento de ruído ativo, 30h de bateria.", "Eletrônicos", 29900, 40, "HIFIMAN Edition XS.jpg"),
            ("Carregador Portátil 20000mAh", "Duas saídas USB-C, carga rápida.", "Eletrônicos", 14900, 55, "Portable power bank.jpg"),
            ("Smartwatch Fit 2", "Monitor cardíaco, GPS integrado, resistente à água.", "Eletrônicos", 49900, 25, "Huawei Smartwatch Fit 2.jpg"),
            ("Teclado Mecânico Compacto", "Switches blue, layout ABNT2, RGB.", "Eletrônicos", 32900, 30, "Keychron K4 mechanical keyboard.jpg"),
            ("Mouse sem Fio Ergonômico", "Sensor óptico 1600dpi, pilha de até 6 meses.", "Eletrônicos", 9900, 70, "Logitech-mouse.JPG"),
            ("Webcam Full HD", "1080p 30fps com microfone embutido.", "Eletrônicos", 15900, 35, "Creative.webcam.jpg"),
            ("Hub USB-C 7 em 1", "HDMI, leitor de cartão e 3 portas USB 3.0.", "Eletrônicos", 19900, 45, "USB-C Hubb 5 portar.jpg"),
        ]

        products: list[Product] = []
        for name, desc, cat, price, stock, commons_file in aventura_products:
            products.append(
                Product(
                    seller_id=seller_a.id,
                    name=name,
                    description=desc,
                    category=cat,
                    price_cents=price,
                    stock=stock,
                    image_url=_img(commons_file),
                )
            )
        for name, desc, cat, price, stock, commons_file in tech_products:
            products.append(
                Product(
                    seller_id=seller_b.id,
                    name=name,
                    description=desc,
                    category=cat,
                    price_cents=price,
                    stock=stock,
                    image_url=_img(commons_file),
                )
            )
        db.add_all(products)
        db.flush()

        sample_reviews = [
            (products[0], buyer_a, "Ana Silva", 5, "Excelente barraca, usei em 3 trilhas e não entrou uma gota de água."),
            (products[0], buyer_b, "Bruno Costa", 4, "Boa qualidade, só achei a montagem um pouco trabalhosa."),
            (products[7], buyer_b, "Bruno Costa", 5, "Som muito bom e cancelamento de ruído impressiona."),
            (products[9], buyer_a, "Ana Silva", 4, "Teclado gostoso de digitar, só o RGB consome mais bateria no notebook."),
        ]
        for product, user, author, rating, comment in sample_reviews:
            db.add(
                Review(
                    product_id=product.id,
                    user_id=user.id,
                    author_name=author,
                    rating=rating,
                    comment_html=comment,
                )
            )

        def make_order(buyer: User, items: list[tuple[Product, int]], address: str, days_ago: int) -> None:
            total = sum(p.price_cents * qty for p, qty in items)
            order = Order(
                user_id=buyer.id,
                status="confirmado",
                total_cents=total,
                shipping_address=address,
                created_at=dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=days_ago),
            )
            db.add(order)
            db.flush()
            for product, qty in items:
                db.add(
                    OrderItem(
                        order_id=order.id,
                        product_id=product.id,
                        product_name=product.name,
                        qty=qty,
                        unit_price_cents=product.price_cents,
                    )
                )

        make_order(buyer_a, [(products[0], 1), (products[3], 2)], "Rua das Palmeiras, 120 - São Paulo/SP", days_ago=10)
        make_order(buyer_a, [(products[9], 1)], "Rua das Palmeiras, 120 - São Paulo/SP", days_ago=3)
        make_order(buyer_b, [(products[7], 1), (products[8], 1)], "Av. Beira Mar, 850 - Florianópolis/SC", days_ago=6)

        db.commit()
        print("Banco semeado com sucesso.")
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true", help="Apaga todas as tabelas antes de semear")
    args = parser.parse_args()

    if args.reset:
        reset_schema()
    seed()
