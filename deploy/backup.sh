#!/bin/sh
# Uso: deploy/backup.sh  (cron diário). Guarda cópias fora do servidor e CRIPTOGRAFE o destino.
set -e
D=${1:-./backups}; mkdir -p "$D"; T=$(date +%F_%H%M)
docker compose exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB"' | gzip > "$D/db_$T.sql.gz"
docker compose cp web:/app/private_media - | gzip > "$D/media_$T.tar.gz"
find "$D" -type f -mtime +30 -delete
echo "Backup em $D (guarde também FIELD_ENCRYPTION_KEY, sem ela os dados protegidos não abrem)."
