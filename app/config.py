"""Configuração central da aplicação.

Valores sensíveis vêm de variáveis de ambiente, com defaults pensados para
desenvolvimento local. Em produção, defina as variáveis via docker-compose
ou pelo painel da EC2.
"""
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Tw4y Marketplace"
    environment: str = "development"

    database_path: Path = BASE_DIR / "tw4y.db"

    # Validade do token de sessão (enviado pelo cliente via header
    # "Authorization: Bearer <token>").
    session_ttl_days: int = 7

    # Limite global de requisições por IP, aplicado a toda a API como rede de
    # segurança operacional (custo/abuso na AWS), independente de qualquer
    # regra de negócio específica de cada rota.
    global_rate_limit: str = "120/minute"


settings = Settings()
