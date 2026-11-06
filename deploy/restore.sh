#!/bin/sh
# Uso: deploy/restore.sh db_AAAA-MM-DD_HHMM.sql.gz
set -e
gunzip -c "$1" | docker compose exec -T db sh -c 'psql -U "$POSTGRES_USER" "$POSTGRES_DB"'
