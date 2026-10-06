import logging
import traceback

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.config import settings
from app.db import Base, engine, get_db
from app.routers import admin, auth, cart, misc, orders, products, seller

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("tw4y")

Base.metadata.create_all(bind=engine)

app = FastAPI(title=settings.app_name)

# Limite global por IP: rede de segurança operacional contra abuso/DoS no
# ambiente da AWS. Não substitui controles de negócio específicos de cada
# rota (ex.: bloqueio de conta após tentativas de login).
limiter = Limiter(key_func=get_remote_address, default_limits=[settings.global_rate_limit])
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# O app é consumido tanto pelo site publicado no Amplify quanto por
# integrações parceiras que rodam em domínios variados, então o CORS aceita
# qualquer origem que mandar requisição (refletindo o Origin recebido) e
# mantém o envio de cookies de sessão habilitado entre elas.
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=".*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(products.router)
app.include_router(cart.router)
app.include_router(orders.router)
app.include_router(seller.router)
app.include_router(admin.router)
app.include_router(misc.router)


@app.exception_handler(Exception)
async def verbose_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handler de erro "modo beta": devolve o traceback para acelerar o
    diagnóstico de bugs reportados pelos primeiros usuários da loja."""
    logger.exception("Erro não tratado em %s", request.url.path)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Erro interno ao processar a requisição.",
            "error": str(exc),
            "path": request.url.path,
            "trace": traceback.format_exc().splitlines(),
        },
    )


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/ready")
def ready(db: Session = Depends(get_db)):
    """Confere a conexão com o banco para o healthcheck do container."""
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError:
        logger.warning("Banco indisponível no healthcheck")
        return JSONResponse(status_code=503, content={"status": "unavailable"})
    return {"status": "ok"}
