"""
Archive filename helpers for the PCIT pipeline.

Scope (per the project's decision to apply rerun-suffix/canonical-file
logic to the FTP archive only, not the local data/raw/ working copy — see
11-local-environment-setup.md v0.2 and project.md's changelog):

    price_guide_6_YYYY-MM-DD.json             (first run of the day)
    price_guide_6_YYYY-MM-DD_rerun-01.json    (first rerun for that date)
    price_guide_6_YYYY-MM-DD_rerun-02.json    (second rerun, if it happens)

Same pattern for products_singles_6 / products_nonsingles_6
(04-etl-pipeline-design.md, 05-raw-archive-strategy.md,
07-github-actions-logic.md).

This module only decides *what filename to use*, given a list of filenames
that already exist for that date on the FTP archive. It does not talk to
FTP itself — listing the remote directory is a separate concern (an FTP
helper, not yet built). Keeping this pure and dependency-free means it can
be fully unit-tested without any network access, same as date_helpers.py.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from typing import Iterable, Optional

_RERUN_WIDTH = 2  # rerun-01, rerun-02, ... matches the width used in every
                  # example across 04/05/07 (never rerun-1).


def build_filename(prefix: str, snapshot_date: date, rerun: Optional[int] = None) -> str:
    """
    Build a single archive filename for the given prefix and date.

    Args:
        prefix: e.g. "price_guide_6", "products_singles_6",
            "products_nonsingles_6".
        snapshot_date: the date to embed in the filename (Europe/Vienna
            date, from get_pipeline_date() — this function doesn't compute
            or validate that itself, it just formats whatever date it's
            given).
        rerun: None for the base (first-run-of-the-day) file, or a positive
            integer for a rerun-suffixed copy.

    Returns:
        e.g. "price_guide_6_2026-07-03.json" or
        "price_guide_6_2026-07-03_rerun-01.json"

    Raises:
        ValueError: if rerun is provided but is not a positive integer.
    """
    date_str = snapshot_date.isoformat()
    if rerun is None:
        return f"{prefix}_{date_str}.json"

    if rerun < 1:
        raise ValueError(
            f"rerun must be a positive integer (1, 2, ...); got {rerun}. "
            f"There is no 'rerun-00' — the unsuffixed file already covers "
            f"the first run of the day."
        )
    return f"{prefix}_{date_str}_rerun-{rerun:0{_RERUN_WIDTH}d}.json"


@dataclass(frozen=True)
class ParsedArchiveFilename:
    prefix: str
    snapshot_date: date
    rerun: Optional[int]  # None means this is the base (non-suffixed) file


def parse_filename(filename: str, prefix: str) -> Optional[ParsedArchiveFilename]:
    """
    Parse `filename` as an archive file for the given `prefix`, if it
    matches. Returns None if `filename` doesn't belong to this prefix at
    all (e.g. it's for a different source file, or isn't an archive
    filename in the expected shape).

    The prefix must be passed explicitly rather than auto-detected, because
    prefixes themselves contain underscores (e.g. "products_nonsingles_6"
    vs "products_singles_6") — trying to split on "_" generically would be
    ambiguous. The caller always knows which prefix it's asking about.
    """
    pattern = (
        rf"^{re.escape(prefix)}_(\d{{4}}-\d{{2}}-\d{{2}})"
        rf"(?:_rerun-(\d{{{_RERUN_WIDTH}}}))?\.json$"
    )
    match = re.match(pattern, filename)
    if not match:
        return None

    date_str, rerun_str = match.group(1), match.group(2)
    try:
        parsed_date = date.fromisoformat(date_str)
    except ValueError:
        return None

    rerun = int(rerun_str) if rerun_str is not None else None
    return ParsedArchiveFilename(prefix=prefix, snapshot_date=parsed_date, rerun=rerun)


def _matching_files_for_date(
    existing_filenames: Iterable[str], prefix: str, snapshot_date: date
) -> list[ParsedArchiveFilename]:
    matches = []
    for filename in existing_filenames:
        parsed = parse_filename(filename, prefix)
        if parsed is not None and parsed.snapshot_date == snapshot_date:
            matches.append(parsed)
    return matches


def next_filename_for_upload(
    existing_filenames: Iterable[str], prefix: str, snapshot_date: date
) -> str:
    """
    Decide the filename the next FTP upload for this prefix/date should
    use, given the filenames that already exist on the FTP archive.

    This is the function the daily/catalog pipelines call right before
    uploading, so an upload for a date that's already been archived never
    silently overwrites the existing file — it always gets the next
    rerun-suffixed name instead (04-etl-pipeline-design.md,
    05-raw-archive-strategy.md, "Archive Immutability and Reruns").

    Args:
        existing_filenames: filenames currently present on the FTP archive
            (e.g. from an FTP directory listing) — not filtered to any
            particular date already; this function does that filtering
            itself.
        prefix: e.g. "price_guide_6".
        snapshot_date: the date this upload is for.

    Returns:
        The base filename if nothing exists yet for this date, otherwise a
        rerun-suffixed filename one higher than the highest existing rerun
        for that date.
    """
    matches = _matching_files_for_date(existing_filenames, prefix, snapshot_date)
    if not matches:
        return build_filename(prefix, snapshot_date)

    highest_rerun = max((m.rerun or 0) for m in matches)
    return build_filename(prefix, snapshot_date, rerun=highest_rerun + 1)


def get_latest_file_for_date(
    existing_filenames: Iterable[str], prefix: str, snapshot_date: date
) -> Optional[str]:
    """
    Return the canonical (most recent) archived filename for this
    prefix/date among `existing_filenames`, or None if nothing exists for
    that date yet.

    Per the project's current (a) decision, this is NOT used by the load
    step — the load step reads directly from the local data/raw/ working
    copy, which is always the single latest attempt for that date (plain
    overwrite, no rerun tracking locally). This function exists for FTP-side
    audit/inspection purposes only: e.g. "what's the actual canonical file
    on the durable archive for 2026-07-03, and was it a rerun?"
    """
    matches = _matching_files_for_date(existing_filenames, prefix, snapshot_date)
    if not matches:
        return None

    latest = max(matches, key=lambda m: (m.rerun or 0))
    return build_filename(prefix, snapshot_date, rerun=latest.rerun)
