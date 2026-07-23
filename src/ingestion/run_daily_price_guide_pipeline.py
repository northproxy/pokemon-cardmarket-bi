"""
Full daily price guide pipeline orchestrator (Phase 0b).

Implements all steps from docs/04-etl-pipeline-design.md's "Daily
Pipeline Steps":
    1. Start scheduled run
    2. Download price_guide_6.json
    3. Assign snapshot_date (Europe/Vienna)
    4. Archive raw file (canonical name, or rerun-suffixed copy if one
       already exists for that date)
    5. Validate JSON structure
    6. Validate required fields
    7. Normalize field names
    8. Insert/upsert into price_snapshots
    9. Run data quality checks
   10. (Nothing to actively "expose" here — BI views are plain SQL views
       over the live tables, per docs/03/04, so they reflect step 8's
       results automatically once committed.)

Steps 1-4 are NOT reimplemented here. They are the exact, already-tested
functions from src/ingestion/download_price_guide.py (Phase 0a),
imported and called directly. This module adds nothing to and changes
nothing about that file — its own docstring is explicit that DB loading
is intentionally out of its scope (see DECISIONS.md §2), and that
boundary is preserved, not eroded, by building this as a separate
orchestrator on top of it.

Load-source note (per docs/11-local-environment-setup.md §3): this
pipeline validates/loads the SAME in-memory `content` it just downloaded
and archived -- it does not re-download, and does not re-list the FTP
folder to resolve a "canonical" file. src/load/canonical_file.py is
reserved for the separate, not-yet-built reprocessing-from-archive flow
sketched in docs/04, and is intentionally unused here.

Archive-before-validate ordering is preserved by construction: steps 1-4
run and complete (raw bytes are on FTP and local disk) BEFORE step 5's
json.loads() is ever attempted -- so a later validation/load failure can
never cause the raw file to go unarchived (docs/07's stated rationale for
this step order).

Transaction behavior (docs/04 "Database Load Failure" -- "either the full
daily snapshot is inserted/upserted, or the load is rolled back"): the
upsert AND the quality-check evaluation both happen inside ONE
src.load.db.get_connection() block. If quality checks come back
"failed", this module raises INSIDE that block, so
src.load.db.get_connection rolls back instead of committing -- the
failure path genuinely leaves the database untouched, not just
"committed, then reported as failed after the fact."

Usage:
    python -m src.ingestion.run_daily_price_guide_pipeline

This is the entry point intended for .github/workflows/daily-price-guide.yml.
src.ingestion.download_price_guide remains available standalone for manual
archive-only runs/debugging (docs/07 "Manual Trigger Support") -- it is a
separate, still-valid entry point, not superseded by this one.

Requires everything download_price_guide.py requires, PLUS:
    DATABASE_URL (see src/load/db.py — pooled Supabase connection string,
    no default/fallback).
"""
from __future__ import annotations

import json
import posixpath
import sys

from src.config import config
from src.ingestion.download_price_guide import (
    PREFIX,
    REMOTE_SUBDIR,
    fetch_price_guide_bytes,
    notify_telegram,
    save_local_copy,
)
from src.load.db import get_connection
from src.load.price_snapshots import upsert_price_snapshots
from src.load.quality_checks import run_daily_price_guide_checks
from src.transform.errors import ValidationError
from src.transform.price_guide import transform_price_guide
from src.utils.archive_filenames import build_filename, next_filename_for_upload
from src.utils.date_helpers import get_pipeline_date
from src.utils.ftp_client import connect_ftp, list_remote_filenames, upload_to_ftp


def build_pipeline_success_message(
    snapshot_date, filename: str, size_bytes: int, item_count: int,
    load_count: int, check_summary: dict,
) -> str:
    """
    Unlike download_price_guide.py's build_success_message (which
    legitimately can't report a real item count, since that script never
    parses the file), this message reports the ACTUAL record count --
    this pipeline has already parsed and loaded the file by the time this
    message is built. Closes the "TBD" gap from DECISIONS.md §10 Decision
    B for this entry point specifically; download_price_guide.py's own
    message is untouched and correctly still says TBD.
    """
    lines = [
        "✅ daily price guide pipeline",
        f"Date: {snapshot_date.isoformat()}",
        f"File: {filename}",
        f"Size: {size_bytes:,} bytes",
        f"Records in file: {item_count:,}",
        f"Rows loaded: {load_count:,}",
        f"Status: {check_summary['status']}",
    ]
    warnings = {
        name: result["violation_count"]
        for name, result in check_summary["checks"].items()
        if result["severity"] == "warning" and result["violation_count"] > 0
    }
    if warnings:
        lines.append("Warnings: " + ", ".join(f"{k}={v}" for k, v in warnings.items()))
    return "\n".join(lines)


def build_pipeline_failure_message(exc: Exception) -> str:
    return f"❌ daily price guide pipeline FAILED\nError: {exc}"


def run() -> None:
    snapshot_date = get_pipeline_date(config.PIPELINE_TIMEZONE)
    print(f"[daily-pipeline] snapshotDate (Europe/Vienna) = {snapshot_date.isoformat()}")

    # --- Steps 1-4: download + archive, reusing Phase 0a's tested path ---
    print(f"[daily-pipeline] downloading from {config.CARDMARKET_PRICE_GUIDE_URL} ...")
    content = fetch_price_guide_bytes(config.CARDMARKET_PRICE_GUIDE_URL)
    print(f"[daily-pipeline] downloaded {len(content):,} bytes")

    local_path = save_local_copy(content, snapshot_date)
    print(f"[daily-pipeline] saved local working copy: {local_path}")

    remote_dir = posixpath.join(config.FTP_REMOTE_DIR, REMOTE_SUBDIR)
    print(f"[daily-pipeline] connecting to FTP ({config.FTP_HOST}) ...")
    ftps = connect_ftp()
    try:
        existing = [
            posixpath.basename(name) for name in list_remote_filenames(ftps, remote_dir)
        ]
        remote_filename = next_filename_for_upload(existing, PREFIX, snapshot_date)
        if remote_filename != build_filename(PREFIX, snapshot_date):
            print(
                f"[daily-pipeline] a file for {snapshot_date.isoformat()} already exists "
                f"on FTP — uploading as a rerun-suffixed copy: {remote_filename}"
            )
        remote_full_path = upload_to_ftp(ftps, local_path, remote_dir, remote_filename)
        print(f"[daily-pipeline] uploaded to FTP: {remote_full_path}")
    finally:
        try:
            ftps.quit()
        except Exception:
            ftps.close()

    # --- Step 5: validate JSON structure ---
    # Deliberately happens AFTER archiving above -- by this point the raw
    # bytes are already safe on FTP and local disk regardless of what
    # happens next (docs/07's stated rationale for this ordering).
    try:
        raw_json = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ValidationError(f"price_guide_6.json is not valid JSON: {exc}") from exc

    # --- Steps 6-7: validate required fields + normalize field names ---
    rows = transform_price_guide(raw_json, snapshot_date)
    print(f"[daily-pipeline] validated + normalized {len(rows):,} records")

    # --- Step 8 (upsert) + Step 9 (quality checks), one transaction ---
    with get_connection() as conn:
        load_count = upsert_price_snapshots(conn, rows)
        print(f"[daily-pipeline] upserted {load_count:,} rows into price_snapshots")

        check_summary = run_daily_price_guide_checks(conn, snapshot_date)
        print(f"[daily-pipeline] quality checks: {check_summary['status']}")

        if check_summary["status"] == "failed":
            # Raising HERE, still inside the `with` block, means
            # get_connection()'s exception handling rolls back instead
            # of committing -- a failed run leaves the database
            # untouched, not "committed, then reported as failed."
            raise RuntimeError(
                f"Daily price guide quality checks failed: {check_summary['checks']}"
            )

    notify_telegram(
        build_pipeline_success_message(
            snapshot_date, remote_filename, len(content), len(rows), load_count, check_summary
        )
    )
    print("[daily-pipeline] done.")


if __name__ == "__main__":
    try:
        run()
    except Exception as exc:  # noqa: BLE001
        print(f"[daily-pipeline] FAILED: {exc}", file=sys.stderr)
        notify_telegram(build_pipeline_failure_message(exc))
        sys.exit(1)