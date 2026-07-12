"""
Product catalog ingestion — archive stage (see DECISIONS.md §11).

Scope, on purpose (mirrors download_price_guide.py — DECISIONS.md §2):
this script covers download -> local save -> FTP upload -> Telegram
notification only, for BOTH products_singles_6.json and
products_nonsingles_6.json. It does NOT validate JSON structure/fields,
enrich rows with productGroup/sourceFile, or load into the `products`
table — those are separate ETL stages (04-etl-pipeline-design.md) that come
later, once archiving itself is proven reliable.

CADENCE DEVIATION (DECISIONS.md §11): 01-mvp-scope.md, 04, 05, 06, and 07
all document a twice-monthly (1st/15th) schedule for this pipeline. This
script is scheduled WEEKLY (every Friday) instead, per an explicit,
later decision — those docs have not been updated to match yet. Flagged
here so nobody assumes 01/04/05/06/07 are still authoritative on this one
specific point.

PARTIAL-FAILURE BEHAVIOR (DECISIONS.md §11): if one of the two files fails
to download/archive, the other is still attempted and archived — a failure
on one file never blocks archiving the other, since discarding already-
successfully-downloaded data would contradict the raw archive's "never
discard data" principle (05-raw-archive-strategy.md). The run still exits
non-zero and notifies failure if *either* file failed, so it remains
visible and actionable. This is a different rule than the DATABASE LOAD
partial-failure rule in 04/07 ("if one catalog file succeeds and the other
fails, do not update products at all") — that rule is about the `products`
table, which this script does not touch.

Usage:
    python -m src.ingestion.download_product_catalogs

Requires (see .env.example / src/config/config.py):
    PIPELINE_TIMEZONE, CARDMARKET_PRODUCTS_SINGLES_URL,
    CARDMARKET_PRODUCTS_NONSINGLES_URL, FTP_HOST, FTP_USER, FTP_PASS,
    FTP_REMOTE_DIR

Optional:
    TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID — if either is unset, notification
    is skipped (logged), not treated as an error.
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

# Two Cardmarket source files, combined into one unified catalog later
# (04-etl-pipeline-design.md) — but archived here as two independent files,
# each following its own rerun-suffix history (archive_filenames.py already
# isolates prefixes from each other; confirmed by test_archive_filenames.py
# test_ignores_files_for_other_prefixes).
SOURCES = {
    "products_singles_6": lambda: config.CARDMARKET_PRODUCTS_SINGLES_URL,
    "products_nonsingles_6": lambda: config.CARDMARKET_PRODUCTS_NONSINGLES_URL,
}

# Local working copy — plain overwrite on rerun, no suffix logic, same
# scope decision as download_price_guide.py's LOCAL_ARCHIVE_DIR.
LOCAL_ARCHIVE_DIR = Path("data/raw/cardmarket/pokemon/product_catalogs")

# Confirmed flat FTP layout (DECISIONS.md §3) — product_catalogs/ directly
# under FTP_REMOTE_DIR, same as price_guides/ for the daily pipeline.
REMOTE_SUBDIR = "product_catalogs"

TELEGRAM_API_URL = "https://api.telegram.org/bot{token}/sendMessage"

# NOTE: connect_ftp / list_remote_filenames / upload_to_ftp below are
# intentionally duplicated from download_price_guide.py rather than
# factored into a shared src/utils/ftp_client.py. This is deliberate
# technical debt (DECISIONS.md §11), not an oversight — extracting a shared
# helper now would mean touching the already-tested, already-working daily
# price guide script while building this one. Worth doing as a follow-up
# refactor once this script is equally proven, not before.


def fetch_json_bytes(url: str, label: str) -> bytes:
    """Download a source file. Raises requests.HTTPError on a bad status,
    and ValueError if the response is empty."""
    response = requests.get(url, timeout=60)
    response.raise_for_status()
    content = response.content
    if not content:
        raise ValueError(f"Downloaded {label} from {url} was empty.")
    return content


def save_local_copy(content: bytes, catalog_date: date, prefix: str) -> Path:
    """Write the plain local working copy for one prefix. Overwrites any
    existing file for this date — no rerun-suffix logic locally."""
    LOCAL_ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    filename = build_filename(prefix, catalog_date)  # always the base name locally
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
        # Some FTP servers error on nlst for an empty directory rather than
        # returning an empty list. Treat that the same as "nothing there
        # yet" rather than failing the whole run over it.
        return []


def upload_to_ftp(ftps: FTP_TLS, local_path: Path, remote_dir: str, remote_filename: str) -> str:
    remote_full_path = posixpath.join(remote_dir, remote_filename)
    with open(local_path, "rb") as f:
        ftps.storbinary(f"STOR {remote_full_path}", f)
    return remote_full_path


def process_one(
    prefix: str,
    url: str,
    catalog_date: date,
    ftps: FTP_TLS,
    remote_dir: str,
    existing: list[str],
) -> dict:
    """
    Download, save, and upload one source file. Never raises — failures are
    captured in the returned dict so a failure on one file never prevents
    the other from being attempted (see module docstring).
    """
    try:
        print(f"[product-catalog] downloading {prefix} from {url} ...")
        content = fetch_json_bytes(url, prefix)
        print(f"[product-catalog] downloaded {prefix}: {len(content):,} bytes")

        local_path = save_local_copy(content, catalog_date, prefix)
        print(f"[product-catalog] saved local working copy: {local_path}")

        remote_filename = next_filename_for_upload(existing, prefix, catalog_date)
        if remote_filename != build_filename(prefix, catalog_date):
            print(
                f"[product-catalog] a file for {prefix} on {catalog_date.isoformat()} "
                f"already exists on FTP — uploading as a rerun-suffixed copy: "
                f"{remote_filename}"
            )
        remote_full_path = upload_to_ftp(ftps, local_path, remote_dir, remote_filename)
        print(f"[product-catalog] uploaded {prefix} to FTP: {remote_full_path}")

        existing.append(remote_filename)  # keep the listing current for this run
        return {"success": True, "filename": remote_filename, "size": len(content)}
    except Exception as exc:  # noqa: BLE001
        print(f"[product-catalog] FAILED for {prefix}: {exc}", file=sys.stderr)
        return {"success": False, "error": str(exc)}


def build_catalog_message(catalog_date: date, results: dict) -> str:
    all_ok = all(r["success"] for r in results.values())
    lines = [
        "✅ product catalog archived" if all_ok else "⚠️ product catalog PARTIAL FAILURE",
        f"Date: {catalog_date.isoformat()}",
    ]
    for prefix, r in results.items():
        if r["success"]:
            lines.append(f"{prefix}: {r['filename']} ({r['size']:,} bytes)")
        else:
            lines.append(f"{prefix}: FAILED — {r['error']}")
    return "\n".join(lines)


def build_failure_message(exc: Exception) -> str:
    return f"❌ product catalog FAILED\nError: {exc}"


def notify_telegram(message: str) -> None:
    """
    Send a Telegram notification. Never raises — a notification failure
    (or Telegram simply not being configured) must never fail the pipeline
    itself (DECISIONS.md §10).
    """
    if not config.TELEGRAM_BOT_TOKEN or not config.TELEGRAM_CHAT_ID:
        print("[product-catalog] Telegram not configured — skipping notification.")
        return
    try:
        requests.post(
            TELEGRAM_API_URL.format(token=config.TELEGRAM_BOT_TOKEN),
            data={"chat_id": config.TELEGRAM_CHAT_ID, "text": message},
            timeout=10,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"[product-catalog] Telegram notify failed: {exc}", file=sys.stderr)


def run() -> None:
    catalog_date = get_pipeline_date(config.PIPELINE_TIMEZONE)
    print(f"[product-catalog] catalogArchiveDate (Europe/Vienna) = {catalog_date.isoformat()}")

    remote_dir = posixpath.join(config.FTP_REMOTE_DIR, REMOTE_SUBDIR)
    print(f"[product-catalog] connecting to FTP ({config.FTP_HOST}) ...")
    ftps = connect_ftp()
    results: dict = {}
    try:
        existing = [
            posixpath.basename(name) for name in list_remote_filenames(ftps, remote_dir)
        ]
        for prefix, url_getter in SOURCES.items():
            results[prefix] = process_one(
                prefix, url_getter(), catalog_date, ftps, remote_dir, existing
            )
    finally:
        try:
            ftps.quit()
        except Exception:
            ftps.close()

    message = build_catalog_message(catalog_date, results)
    print(f"[product-catalog] {message}")
    notify_telegram(message)

    if not all(r["success"] for r in results.values()):
        print("[product-catalog] one or more files failed.", file=sys.stderr)
        sys.exit(1)

    print("[product-catalog] done.")


if __name__ == "__main__":
    try:
        run()
    except Exception as exc:  # noqa: BLE001
        # Reached only for failures outside the per-file try/except above,
        # e.g. connect_ftp() itself failing before any file is attempted.
        print(f"[product-catalog] FAILED: {exc}", file=sys.stderr)
        notify_telegram(build_failure_message(exc))
        sys.exit(1)
