#!/usr/bin/env bash
# Execute na EC2, na pasta dos arquivos de deploy: bash backup-sqlite.sh
set -euo pipefail
cd "$(dirname "$0")"

mkdir -p backups
BACKUP_FILE="backups/tw4y-$(date -u +%Y%m%dT%H%M%SZ).db"
BACKUP_TEMP=$(mktemp)
trap 'rm -f "$BACKUP_TEMP"' EXIT

# A API de backup do SQLite gera uma cópia consistente com a API em uso.
docker compose --env-file .env.ec2 -f compose.ec2.yml exec -T backend python -c '
import os
import sqlite3
import sys
import tempfile

with tempfile.TemporaryDirectory() as directory:
    path = os.path.join(directory, "backup.db")
    with sqlite3.connect(os.environ["DATABASE_PATH"]) as source:
        with sqlite3.connect(path) as target:
            source.backup(target)
    with open(path, "rb") as backup:
        sys.stdout.buffer.write(backup.read())
' > "$BACKUP_TEMP"

mv "$BACKUP_TEMP" "$BACKUP_FILE"
chmod 600 "$BACKUP_FILE"
echo "Backup criado em $BACKUP_FILE. Copie para fora da EC2."
