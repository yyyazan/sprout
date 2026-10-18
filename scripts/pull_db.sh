#!/usr/bin/env bash
# Pull the live SQLite DB off the Railway volume into data/backups/ for local
# inspection. Reads over `railway ssh` and base64-encodes in transit since ssh
# exec output isn't safe for arbitrary binary data.
#
# The live DB runs in WAL mode, so recent writes sit in portfolio.db-wal until a
# checkpoint. A raw copy of portfolio.db silently drops them — snapshot with
# VACUUM INTO on the server first (same as api/backup.py) and pull that.
set -euo pipefail

cd "$(dirname "$0")/.."

REMOTE_DB="/data/portfolio.db"
REMOTE_SNAP="/tmp/pull-snapshot.db"
OUT_DIR="data/backups"
OUT_FILE="$OUT_DIR/portfolio-$(date +%Y-%m-%dT%H%M%S).db"

mkdir -p "$OUT_DIR"

echo "Snapshotting $REMOTE_DB via railway ssh..." >&2
railway ssh "rm -f $REMOTE_SNAP && python -c \"import sqlite3; sqlite3.connect('$REMOTE_DB').execute('VACUUM INTO ?', ('$REMOTE_SNAP',))\" && base64 $REMOTE_SNAP && rm -f $REMOTE_SNAP" | base64 -d > "$OUT_FILE"

echo "Saved to $OUT_FILE ($(du -h "$OUT_FILE" | cut -f1))" >&2
