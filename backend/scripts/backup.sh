#!/usr/bin/env bash
# PostgreSQL backup for the Personal Finance Tracking Platform.
#
# Financial records are retained forever (04-database_schema.md section 9), so
# a backup that silently produced nothing is worse than no backup at all: the
# failure would not be noticed until a restore was needed. This script fails
# loudly, verifies the dump is non-empty, and prunes only after a good backup.
#
# Usage:
#   DATABASE_URL=postgresql://... ./scripts/backup.sh [output-directory]
#
# Cron example, daily at 02:00:
#   0 2 * * * cd /srv/ledger-ai && DATABASE_URL=... ./backend/scripts/backup.sh /var/backups/ledger-ai
set -euo pipefail

BACKUP_DIR="${1:-./backups}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-30}"
MIN_BACKUP_BYTES="${MIN_BACKUP_BYTES:-1024}"

if [ -z "${DATABASE_URL:-}" ]; then
  echo "ERROR: DATABASE_URL is not set." >&2
  exit 1
fi

# pg_dump does not understand the SQLAlchemy driver suffix.
DUMP_URL="${DATABASE_URL/postgresql+psycopg:\/\//postgresql://}"

mkdir -p "$BACKUP_DIR"
TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
ARCHIVE="${BACKUP_DIR}/ledger-ai-${TIMESTAMP}.dump"

echo "Backing up to ${ARCHIVE}..."
# Custom format so pg_restore can do a selective or parallel restore.
pg_dump --format=custom --no-owner --no-privileges --file="$ARCHIVE" "$DUMP_URL"

if [ ! -s "$ARCHIVE" ]; then
  echo "ERROR: backup file is empty; refusing to continue." >&2
  rm -f "$ARCHIVE"
  exit 1
fi

SIZE="$(wc -c < "$ARCHIVE")"
if [ "$SIZE" -lt "$MIN_BACKUP_BYTES" ]; then
  echo "ERROR: backup is only ${SIZE} bytes, below the ${MIN_BACKUP_BYTES} floor." >&2
  echo "Keeping the file for inspection at ${ARCHIVE}." >&2
  exit 1
fi

# Verify the archive is readable before trusting it. A dump that cannot be
# listed cannot be restored.
if ! pg_restore --list "$ARCHIVE" > /dev/null 2>&1; then
  echo "ERROR: backup archive failed verification; keeping it for inspection." >&2
  exit 1
fi

echo "Backup complete: ${ARCHIVE} (${SIZE} bytes, verified)."

# Prune only after a verified backup, so a run of failures never erodes history.
if [ "$RETENTION_DAYS" -gt 0 ]; then
  echo "Removing backups older than ${RETENTION_DAYS} days..."
  find "$BACKUP_DIR" -name 'ledger-ai-*.dump' -type f -mtime "+${RETENTION_DAYS}" -print -delete
fi

echo "Done."