"""Daily off-site backup of the SQLite system-of-record to Cloudflare R2.

The cloud DB on the Railway volume is the only canonical copy of real trade
data, so we stream a consistent daily snapshot to R2 (S3-compatible, free tier,
no egress fees). Everything here is best-effort: a backup failure logs and is
swallowed — it must never take the app down.

Enabled only when the R2_* env vars are present, so local dev runs untouched.

Restore: download the desired `portfolio-YYYY-MM-DD.db` object and seed it back
to the volume the same way it was first seeded (base64 | railway ssh ...).
"""
from __future__ import annotations

import asyncio
import logging
import os
import sqlite3
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

from portfolio.data import db as db_mod

log = logging.getLogger("sprout.backup")

# One snapshot per calendar day; re-running the same day overwrites that key,
# so frequent redeploys don't pile up objects. We retain the most recent N days.
_RETAIN_DAYS = 30
_INTERVAL_SECONDS = 24 * 60 * 60
_FIRST_RUN_DELAY = 60  # let the app settle after boot before the first backup

_ENV = ("R2_ENDPOINT", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY", "R2_BUCKET")


def is_configured() -> bool:
    """True only when every R2 credential is set (otherwise backups are skipped)."""
    return all(os.environ.get(k) for k in _ENV)


def _client():
    import boto3  # imported lazily so the dep isn't required for local dev

    return boto3.client(
        "s3",
        endpoint_url=os.environ["R2_ENDPOINT"],
        aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
        region_name="auto",  # R2 ignores region but boto3 wants one
    )


def snapshot_and_upload() -> str | None:
    """Make a consistent DB snapshot and upload it to R2. Returns the key, or None."""
    db_path = Path(db_mod.DEFAULT_DB_PATH)
    if not db_path.is_file():
        log.warning("backup skipped: no DB at %s", db_path)
        return None

    bucket = os.environ["R2_BUCKET"]
    key = f"portfolio-{datetime.now(timezone.utc):%Y-%m-%d}.db"

    with tempfile.TemporaryDirectory() as tmp:
        snap = Path(tmp) / "snapshot.db"
        # VACUUM INTO writes a self-contained, internally-consistent copy even
        # while the app is mid-write (safe with WAL) — never raw-copy a live DB.
        conn = sqlite3.connect(str(db_path))
        try:
            conn.execute("VACUUM INTO ?", (str(snap),))
        finally:
            conn.close()

        client = _client()
        client.upload_file(str(snap), bucket, key)
        log.info("backup uploaded: s3://%s/%s (%d bytes)", bucket, key, snap.stat().st_size)

        _prune(client, bucket)
    return key


def _prune(client, bucket: str) -> None:
    """Rolling window: delete any snapshot whose date is older than _RETAIN_DAYS.

    Age is read from the date embedded in the key (`portfolio-YYYY-MM-DD.db`),
    so deletion is purely by age — gaps (days the app was down) don't keep stale
    objects alive the way a "keep newest N" rule would.
    """
    cutoff = (datetime.now(timezone.utc) - timedelta(days=_RETAIN_DAYS)).date()
    resp = client.list_objects_v2(Bucket=bucket, Prefix="portfolio-")
    stale = []
    for obj in resp.get("Contents", []):
        key = obj["Key"]
        try:
            day = datetime.strptime(key[len("portfolio-"):-len(".db")], "%Y-%m-%d").date()
        except ValueError:
            continue  # unrecognized key — leave it untouched
        if day < cutoff:
            stale.append(key)
    for k in stale:
        client.delete_object(Bucket=bucket, Key=k)
    if stale:
        log.info("backup pruned %d snapshot(s) older than %d days", len(stale), _RETAIN_DAYS)


async def run_backup_loop() -> None:
    """Background loop: first backup shortly after boot, then once a day.

    boto3 is blocking, so the actual work runs in a thread to keep the event
    loop free. Any error is logged and the loop continues — backups are
    best-effort and must not crash the server.
    """
    await asyncio.sleep(_FIRST_RUN_DELAY)
    while True:
        try:
            await asyncio.to_thread(snapshot_and_upload)
        except Exception:  # noqa: BLE001 — best-effort, never propagate
            log.exception("daily backup failed (will retry next cycle)")
        await asyncio.sleep(_INTERVAL_SECONDS)
