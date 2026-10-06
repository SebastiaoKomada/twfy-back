# Tw4y Marketplace — Backend

API FastAPI + SQLAlchemy + SQLite do laboratório de Web Hacking do INATEL.
Repositório: [SebastiaoKomada/twfy-back](https://github.com/SebastiaoKomada/twfy-back).
Frontend: [SebastiaoKomada/twfy-front](https://github.com/SebastiaoKomada/twfy-front).

## Desenvolvimento local

Na raiz deste repositório:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python -m app.seed
uvicorn app.main:app --reload --port 8000
```

A API responde em `http://localhost:8000`; documentação em `/docs`.
`/api/health` verifica a API e `/api/ready` verifica também o banco.

## Docker Hub e EC2

```bash
docker login
bash deploy/publish-image.sh SEU_USUARIO/tw4y-api 1.0.0
```

O deploy usa **us-east-1**, SQLite em volume persistente, Caddy para HTTPS
e `deploy/compose.ec2.yml`. O seed é executado explicitamente na EC2.

Veja [deploy/AWS.md](deploy/AWS.md) para criar a EC2, configurar o domínio,
publicar a imagem, fazer backup e conectar o frontend no Amplify.

Esta aplicação contém vulnerabilidades intencionais para os exercícios.
Restrinja a API aos IPs do laboratório e use dados de teste.
