#!/usr/bin/env bash
# OmniSight production restore script
# Restores from a backup created by scripts/backup.sh
#
# Usage: bash scripts/restore.sh <backup-dir>
# Example: bash scripts/restore.sh backups/2026-05-18_143000
#
# WARNING: This OVERWRITES the current database and storage files.
#          The Compose stack must be running (postgres, qdrant, backend).

set -euo pipefail

POSTGRES_DB="${POSTGRES_DB:-omnisight}"
POSTGRES_USER="${POSTGRES_USER:-omnisight}"
QDRANT_URL="${QDRANT_URL:-http://localhost:6333}"
COLLECTION="${QDRANT_COLLECTION:-face_registry}"

if [[ $# -lt 1 ]]; then
  echo "Usage: bash scripts/restore.sh <backup-dir>"
  echo "Example: bash scripts/restore.sh backups/2026-05-18_143000"
  exit 1
fi

SRC="$1"

if [[ ! -d "$SRC" ]]; then
  echo "ERROR: Backup directory not found: $SRC"
  exit 1
fi

echo "=== OmniSight Restore from: $SRC ==="
echo "WARNING: This will overwrite the current database and storage."
read -r -p "Type 'yes' to confirm: " CONFIRM
if [[ "$CONFIRM" != "yes" ]]; then
  echo "Aborted."
  exit 0
fi

# ── 1. PostgreSQL restore ────────────────────────────────────────────────
if [[ -f "$SRC/postgres.sql.gz" ]]; then
  echo "[1/3] Restoring PostgreSQL..."
  # Drop and recreate schema
  docker compose exec -T postgres \
    psql -U "$POSTGRES_USER" -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;" "$POSTGRES_DB"
  # Restore
  gunzip -c "$SRC/postgres.sql.gz" \
    | docker compose exec -T postgres psql -U "$POSTGRES_USER" "$POSTGRES_DB"
  echo "      ✓ PostgreSQL restored"
else
  echo "[1/3] postgres.sql.gz not found — skipping PostgreSQL restore"
fi

# ── 2. Qdrant restore ────────────────────────────────────────────────────
if [[ -f "$SRC/qdrant_snapshot.snapshot" ]]; then
  echo "[2/3] Restoring Qdrant collection..."

  # Upload snapshot to Qdrant
  UPLOAD_RESP=$(curl -sf -X POST \
    "$QDRANT_URL/collections/$COLLECTION/snapshots/upload?priority=snapshot" \
    -H "Content-Type: multipart/form-data" \
    -F "snapshot=@$SRC/qdrant_snapshot.snapshot")
  echo "      Upload response: $UPLOAD_RESP"
  echo "      ✓ Qdrant snapshot uploaded (collection will rebuild from snapshot)"
else
  echo "[2/3] qdrant_snapshot.snapshot not found — skipping Qdrant restore"
fi

# ── 3. Storage restore ───────────────────────────────────────────────────
if [[ -f "$SRC/storage.tar.gz" ]]; then
  echo "[3/3] Restoring storage files..."
  mkdir -p "./data"
  rm -rf "./data/storage"
  tar -xzf "$SRC/storage.tar.gz" -C "./data"
  echo "      ✓ Storage files restored to ./data/storage"
else
  echo "[3/3] storage.tar.gz not found — skipping storage restore"
fi

echo ""
echo "=== Restore complete ==="
echo "    Restart the backend to pick up restored state:"
echo "    docker compose -f docker-compose.prod.yml restart backend"
