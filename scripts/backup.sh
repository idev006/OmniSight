#!/usr/bin/env bash
# OmniSight production backup script
# Backs up: PostgreSQL, Qdrant vectors, storage files
# Retention: 7 days (configurable via KEEP_DAYS)
#
# Usage: bash scripts/backup.sh [--no-qdrant]
#
# Prerequisites:
#   - Docker Compose stack running (postgres, qdrant services)
#   - Run from project root: cd /path/to/OmniSight && bash scripts/backup.sh
#
# Backup layout:
#   backups/
#     YYYY-MM-DD_HHMMSS/
#       postgres.sql.gz      — pg_dump compressed
#       qdrant_snapshot.tar  — Qdrant collection snapshot
#       storage.tar.gz       — face images + attendance snapshots

set -euo pipefail

# ── Config ──────────────────────────────────────────────────────────────────
BACKUP_DIR="${BACKUP_DIR:-./backups}"
KEEP_DAYS="${KEEP_DAYS:-7}"
POSTGRES_DB="${POSTGRES_DB:-omnisight}"
POSTGRES_USER="${POSTGRES_USER:-omnisight}"
QDRANT_URL="${QDRANT_URL:-http://localhost:6333}"
COLLECTION="${QDRANT_COLLECTION:-face_registry}"
SKIP_QDRANT=false

for arg in "$@"; do
  [[ "$arg" == "--no-qdrant" ]] && SKIP_QDRANT=true
done

STAMP=$(date +%Y-%m-%d_%H%M%S)
DEST="$BACKUP_DIR/$STAMP"
mkdir -p "$DEST"

echo "=== OmniSight Backup — $STAMP ==="

# ── 1. PostgreSQL ─────────────────────────────────────────────────────────
echo "[1/3] PostgreSQL dump..."
docker compose exec -T postgres \
  pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" \
  | gzip > "$DEST/postgres.sql.gz"
echo "      → $DEST/postgres.sql.gz ($(du -sh "$DEST/postgres.sql.gz" | cut -f1))"

# ── 2. Qdrant snapshot ───────────────────────────────────────────────────
if [[ "$SKIP_QDRANT" == "false" ]]; then
  echo "[2/3] Qdrant snapshot..."

  # Create snapshot via REST API
  SNAP_RESP=$(curl -sf -X POST "$QDRANT_URL/collections/$COLLECTION/snapshots")
  SNAP_NAME=$(echo "$SNAP_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['result']['name'])" 2>/dev/null || true)

  if [[ -n "$SNAP_NAME" ]]; then
    # Download snapshot
    curl -sf "$QDRANT_URL/collections/$COLLECTION/snapshots/$SNAP_NAME" \
      -o "$DEST/qdrant_snapshot.snapshot"
    # Cleanup snapshot from server
    curl -sf -X DELETE "$QDRANT_URL/collections/$COLLECTION/snapshots/$SNAP_NAME" >/dev/null || true
    echo "      → $DEST/qdrant_snapshot.snapshot ($(du -sh "$DEST/qdrant_snapshot.snapshot" | cut -f1))"
  else
    echo "      WARNING: Qdrant snapshot failed (is the service running at $QDRANT_URL?). Skipping."
  fi
else
  echo "[2/3] Qdrant snapshot — skipped (--no-qdrant)"
fi

# ── 3. Storage files ─────────────────────────────────────────────────────
echo "[3/3] Storage files..."
if [[ -d "./data/storage" ]]; then
  tar -czf "$DEST/storage.tar.gz" -C "./data" storage
  echo "      → $DEST/storage.tar.gz ($(du -sh "$DEST/storage.tar.gz" | cut -f1))"
else
  echo "      WARNING: ./data/storage not found — skipping storage backup."
fi

# ── 4. Rotate old backups ────────────────────────────────────────────────
echo "[4] Rotating backups older than ${KEEP_DAYS} days..."
find "$BACKUP_DIR" -maxdepth 1 -type d -mtime +"$KEEP_DAYS" -exec rm -rf {} + 2>/dev/null || true

echo ""
echo "=== Backup complete: $DEST ==="
echo "    Total: $(du -sh "$DEST" | cut -f1)"
