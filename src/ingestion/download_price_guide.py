"""
Daily price guide ingestion — Phase 0a.

Scope, on purpose: this script covers download -> local save -> FTP upload
-> Telegram notification only. It does NOT validate JSON structure/fields,
normalize holo field names, or load into the database — those are separate
ETL stages (04-etl-pipeline-design.md: validate -> transform -> load are
distinct steps) that come after archiving is proven reliable. See
DECISIONS.md for why this scope cut is deliberate, not an oversight.

Usage:
    python -m src.ingestion.download_price_guide

Requires (see .env.example / src/config/config.py):
    PIPELINE_TIMEZONE, CARDMARKET_PRICE_GUIDE_URL,
    FTP_HOST, FTP_USER, FTP_PASS, FTP_REMOTE_DIR

Optional (see .env.example / src/config/config.py):
    TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID — if either is unset, notification
    is skipped (logged), not treated as an error (DECISIONS.md §10).
"""
from __future__ import annotations

import posixpath
import sys
from datetime import date
from pathlib import Path

import requests

from src.config import config
from src.utils.archive_filenames import build_filename, next_filename_for_upload
from src.utils.date_helpers import get_pipeline_date
from src.utils.ftp_client import connect_ftp, list_remote_filenames, upload_to_ftp

PREFIX = "price_guide_6"

# Local working copy — plain overwrite on rerun, no suffix logic (see the
# project's decision: rerun-suffixing applies to the FTP archive only).
LOCAL_ARCHIVE_DIR = Path("data/raw/cardmarket/pokemon/price_guides")

# Actual confirmed FTP layout is price_guides/ and product_catalogs/ directly
# under FTP_REMOTE_DIR (account root) — flatter than the nested
# /raw/cardmarket/pokemon/price_guides/ tree originally described in
# 05-raw-archive-strategy.md. See DECISIONS.md §3: this script follows the
# real, confirmed server layout; 05's folder-structure diagram should be
# updated to match rather than the other way around.
REMOTE_SUBDIR = "price_guides"

TELEGRAM_API_URL = "https://api.telegram.org/bot{token}/sendMessage"


def fetch_price_guide_bytes(url: str) -> bytes:
    """Download the price guide file. Raises requests.HTTPError on a bad
    status, and ValueError if the response is empty — both are treated as
    hard failures per 04-etl-pipeline-design.md's failure conditions
    ("file could not be downloaded", "file is empty")."""
    response = requests.get(url, timeout=60)
    response.raise_for_status()
    content = response.content
    if not content:
        raise ValueError(f"Downloaded price guide from {url} was empty.")
    return content


def save_local_copy(content: bytes, snapshot_date: date) -> Path:
    """Write the plain local working copy. Overwrites any existing file for
    this date — no rerun-suffix logic locally (see module docstring)."""
    LOCAL_ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    filename = build_filename(PREFIX, snapshot_date)  # always the base name locally
    local_path = LOCAL_ARCHIVE_DIR / filename
    local_path.write_bytes(content)
    return local_path


def build_success_message(snapshot_date: date, filename: str, size_bytes: int) -> str:
    """
    Build the Telegram success message.

    "Last item / idProduct" is intentionally a placeholder for now
    (DECISIONS.md §10) — reporting it correctly requires knowing whether
    price_guide_6.json's root is a bare list or a nested object (e.g.
    {"priceGuides": [...]}), which hasn't been confirmed yet.
    """
    return (
        "✅ price_guide archived\n"
        f"Date: {snapshot_date.isoformat()}\n"
        f"File: {filename}\n"
        f"Size: {size_bytes:,} bytes\n"
        "Last item / idProduct: TBD — pending JSON structure confirmation"
    )


def build_failure_message(exc: Exception) -> str:
    return f"❌ price_guide FAILED\nError: {exc}"


def notify_telegram(message: str) -> None:
    """
    Send a Telegram notification. Never raises — a notification failure
    (or Telegram simply not being configured) must never fail the pipeline
    itself (DECISIONS.md §10). Archiving is the thing that matters; the
    notification is a convenience layered on top of it.
    """
    if not config.TELEGRAM_BOT_TOKEN or not config.TELEGRAM_CHAT_ID:
        print("[price-guide] Telegram not configured — skipping notification.")
        return
    try:
        requests.post(
            TELEGRAM_API_URL.format(token=config.TELEGRAM_BOT_TOKEN),
            data={"chat_id": config.TELEGRAM_CHAT_ID, "text": message},
            timeout=10,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"[price-guide] Telegram notify failed: {exc}", file=sys.stderr)


def run() -> None:
    snapshot_date = get_pipeline_date(config.PIPELINE_TIMEZONE)
    print(f"[price-guide] snapshotDate (Europe/Vienna) = {snapshot_date.isoformat()}")

    print(f"[price-guide] downloading from {config.CARDMARKET_PRICE_GUIDE_URL} ...")
    content = fetch_price_guide_bytes(config.CARDMARKET_PRICE_GUIDE_URL)
    print(f"[price-guide] downloaded {len(content):,} bytes")

    local_path = save_local_copy(content, snapshot_date)
    print(f"[price-guide] saved local working copy: {local_path}")

    remote_dir = posixpath.join(config.FTP_REMOTE_DIR, REMOTE_SUBDIR)
    print(f"[price-guide] connecting to FTP ({config.FTP_HOST}) ...")
    ftps = connect_ftp()
    try:
        existing = [
            posixpath.basename(name) for name in list_remote_filenames(ftps, remote_dir)
        ]
        remote_filename = next_filename_for_upload(existing, PREFIX, snapshot_date)
        if remote_filename != build_filename(PREFIX, snapshot_date):
            print(
                f"[price-guide] a file for {snapshot_date.isoformat()} already exists "
                f"on FTP — uploading as a rerun-suffixed copy: {remote_filename}"
            )
        remote_full_path = upload_to_ftp(ftps, local_path, remote_dir, remote_filename)
        print(f"[price-guide] uploaded to FTP: {remote_full_path}")
    finally:
        try:
            ftps.quit()
        except Exception:
            ftps.close()

    notify_telegram(build_success_message(snapshot_date, remote_filename, len(content)))
    print("[price-guide] done.")


if __name__ == "__main__":
    try:
        run()
    except Exception as exc:  # noqa: BLE001
        print(f"[price-guide] FAILED: {exc}", file=sys.stderr)
        notify_telegram(build_failure_message(exc))
        sys.exit(1)
