#!/usr/bin/env bash
# Pull the live SQLite DB off the Railway volume into data/backups/ for local
# inspection. Reads over `railway ssh` and base64-encodes in transit since ssh
# exec output isn't safe for arbitrary binary data.
set -euo pipefail

cd "$(dirname "$0")/.."

REMOTE_DB="/data/portfolio.db"
OUT_DIR="data/backups"
OUT_FILE="$OUT_DIR/portfolio-$(date +%Y-%m-%dT%H%M%S).db"

mkdir -p "$OUT_DIR"

echo "Pulling $REMOTE_DB via railway ssh..." >&2
railway ssh "base64 $REMOTE_DB" | base64 -d > "$OUT_FILE"

echo "Saved to $OUT_FILE ($(du -h "$OUT_FILE" | cut -f1))" >&2
