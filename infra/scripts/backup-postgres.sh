#!/usr/bin/env bash
set -euo pipefail

# Creates a custom-format PostgreSQL backup through the running Compose service.
# Usage: infra/scripts/backup-postgres.sh [output-directory]

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
OUTPUT_DIR="${1:-${ROOT_DIR}/backups}"
COMPOSE=(docker compose --env-file "${ROOT_DIR}/.env" -f "${ROOT_DIR}/infra/docker-compose.yml")
DB_NAME="${DATAGENIE_POSTGRES_DB:-datagenie}"
DB_USER="${DATAGENIE_POSTGRES_USER:-datagenie}"

mkdir -p "${OUTPUT_DIR}"
TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
BACKUP_FILE="${OUTPUT_DIR}/datagenie-${TIMESTAMP}.dump"

"${COMPOSE[@]}" exec -T postgres pg_dump \
  -U "${DB_USER}" \
  -d "${DB_NAME}" \
  --format=custom \
  --no-owner \
  --no-privileges > "${BACKUP_FILE}"

sha256sum "${BACKUP_FILE}" > "${BACKUP_FILE}.sha256"
printf 'Backup written to %s\nChecksum written to %s.sha256\n' "${BACKUP_FILE}" "${BACKUP_FILE}"
