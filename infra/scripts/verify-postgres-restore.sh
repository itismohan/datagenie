#!/usr/bin/env bash
set -euo pipefail

# Restores a custom-format backup into an isolated temporary database, verifies
# core tables, and always removes the temporary database on exit.
# Usage: infra/scripts/verify-postgres-restore.sh path/to/backup.dump

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 path/to/backup.dump" >&2
  exit 64
fi

BACKUP_FILE="$1"
if [[ ! -f "${BACKUP_FILE}" ]]; then
  echo "Backup file not found: ${BACKUP_FILE}" >&2
  exit 66
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
COMPOSE=(docker compose --env-file "${ROOT_DIR}/.env" -f "${ROOT_DIR}/infra/docker-compose.yml")
DB_USER="${DATAGENIE_POSTGRES_USER:-datagenie}"
TEMP_DB="datagenie_restore_check_$(date +%s)"

cleanup() {
  "${COMPOSE[@]}" exec -T postgres dropdb --if-exists -U "${DB_USER}" "${TEMP_DB}" >/dev/null 2>&1 || true
}
trap cleanup EXIT

"${COMPOSE[@]}" exec -T postgres createdb -U "${DB_USER}" "${TEMP_DB}"
cat "${BACKUP_FILE}" | "${COMPOSE[@]}" exec -T postgres pg_restore \
  -U "${DB_USER}" \
  -d "${TEMP_DB}" \
  --no-owner \
  --no-privileges

TABLE_COUNT="$("${COMPOSE[@]}" exec -T postgres psql -U "${DB_USER}" -d "${TEMP_DB}" -Atc \
  "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public' AND table_name IN ('assets', 'data_sources', 'audit_events', 'business_glossary_terms');")"

if [[ "${TABLE_COUNT}" -lt 4 ]]; then
  echo "Restore verification failed: expected core catalog tables are missing." >&2
  exit 1
fi

printf 'Restore verification succeeded for %s; temporary database %s will be removed.\n' "${BACKUP_FILE}" "${TEMP_DB}"
