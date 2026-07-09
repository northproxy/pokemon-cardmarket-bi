"""
Daily price guide ingestion — Phase 0a.

Scope, on purpose: this script covers download -> local save -> FTP upload
only. It does NOT validate JSON structure/fields, normalize holo field
names, or load into the database — those are separate ETL stages
(04-etl-pipeline-design.md: validate -> transform -> load are distinct
steps) that come after archiving is proven reliable. See DECISIONS.md for
why this scope cut is deliberate, not an oversight.

Usage:
    python -m src.ingestion.download_price_guide

Requires (see .env.example / src/config/config.py):
    PIPELINE_TIMEZONE, CARDMARKET_PRICE_GUIDE_URL,
    FTP_HOST, FTP_USER, FTP_PASS, FTP_REMOTE_DIR
"""
from __future__ import annotations

import posixpath
import sys
from datetime import date
from ftplib import FTP_TLS
from pathlib import Path

import requests

from src.config import config
from src.utils.archive_filenames import build_filename, next_filename_for_upload
from src.utils.date_helpers import get_pipeline_date

PREFIX = "price_guide_6"

# Local working copy — plain overwrite on rerun, no suffix logic (see the
# project's (a) decision: rerun-suffixing applies to the FTP archive only).
LOCAL_ARCHIVE_DIR = Path("data/raw/cardmarket/pokemon/price_guides")

# Actual confirmed FTP layout is price_guides/ and product_catalogs/ directly
# under FTP_REMOTE_PATH (account root) — flatter than the nested
# /raw/cardmarket/pokemon/price_guides/ tree originally described in
# 05-raw-archive-strategy.md. See DECISIONS.md: this script follows the
# real, confirmed server layout; 05's folder-structure diagram should be
# updated to match rather than the other way around.
REMOTE_SUBDIR = "price_guides"


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
    this date — no rerun-suffix logic locally (see (a) decision)."""
    LOCAL_ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    filename = build_filename(PREFIX, snapshot_date)  # always the base name locally
    local_path = LOCAL_ARCHIVE_DIR / filename
    local_path.write_bytes(content)
    return local_path


def connect_ftp() -> FTP_TLS:
    """Connect using explicit FTPS (AUTH TLS), per
    11-local-environment-setup.md: plain ftp:// is rejected by this
    provider with a 530 error even with correct credentials."""
    ftps = FTP_TLS()
    ftps.connect(config.FTP_HOST, 21, timeout=60)
    ftps.login(config.FTP_USER, config.FTP_PASS)
    ftps.prot_p()  # secure the data connection, not just the control connection
    return ftps


def list_remote_filenames(ftps: FTP_TLS, remote_dir: str) -> list[str]:
    try:
        return ftps.nlst(remote_dir)
    except Exception:
        # Some FTP servers return an error for nlst on an empty directory
        # rather than an empty list. Treat that the same as "nothing there
        # yet" rather than failing the whole run over it.
        return []


def upload_to_ftp(ftps: FTP_TLS, local_path: Path, remote_dir: str, remote_filename: str) -> str:
    remote_full_path = posixpath.join(remote_dir, remote_filename)
    with open(local_path, "rb") as f:
        ftps.storbinary(f"STOR {remote_full_path}", f)
    return remote_full_path


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

    print("[price-guide] done.")


if __name__ == "__main__":
    try:
        run()
    except Exception as exc:  # noqa: BLE001
        print(f"[price-guide] FAILED: {exc}", file=sys.stderr)
        sys.exit(1)
