"""
Canonical-file resolution for database loading.

Source of truth: docs/05-raw-archive-strategy.md ("Same-Date Reruns"),
docs/04-etl-pipeline-design.md ("Archive Immutability and Reruns"),
docs/07-github-actions-logic.md ("Archive Immutability and Reruns").

Rule (all three docs agree verbatim): the canonical file for a given date
is the most recent successful run for that date -- the highest-numbered
rerun file if one exists, otherwise the base (non-suffixed) file. The
database always loads from the canonical file; superseded files stay on
disk for audit but are never loaded.

This module is deliberately READ-ONLY / decision-only: it takes a list of
filenames already retrieved from the FTP archive (via
src/utils/ftp_client.py::list_remote_filenames, built in Phase 0a) and
decides which one is canonical. It does not talk to FTP itself, and it
does not decide the NEXT filename to write on upload -- that's the
write-side concern already handled in src/ingestion/ (see DECISIONS.md
SS1's next_filename_for_upload), which this module is a read-side
counterpart to, not a replacement for.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

# Matches: {prefix}_{YYYY-MM-DD}.json
#      or: {prefix}_{YYYY-MM-DD}_rerun-{NN}.json
_FILENAME_RE_TEMPLATE = r"^{prefix}_{date}(?:_rerun-(\d+))?\.json$"


@dataclass(frozen=True)
class CanonicalFileResult:
    filename: str | None
    is_rerun: bool
    rerun_number: int | None
    superseded_filenames: tuple[str, ...]


def resolve_canonical_filename(
    prefix: str, date_str: str, existing_filenames: list[str]
) -> CanonicalFileResult:
    """
    Given a filename prefix (e.g. "price_guide_6", "products_singles_6",
    "products_nonsingles_6"), a date string in YYYY-MM-DD form, and the
    list of filenames actually present in the relevant FTP folder, return
    the canonical filename for that date -- or CanonicalFileResult(None, ...)
    if no file exists for that date at all (an archive gap, see docs/05
    "Archive Gaps in the Historical Timeline" -- this is an expected,
    documented possibility, not something this function should raise on).

    Does not validate that `date_str` is a real calendar date -- callers
    are expected to pass a value already produced by the Europe/Vienna
    date logic in src/config (docs/04 "Price Snapshot Date Logic").
    """
    pattern = re.compile(
        _FILENAME_RE_TEMPLATE.format(prefix=re.escape(prefix), date=re.escape(date_str))
    )

    base_filename = f"{prefix}_{date_str}.json"
    matches: list[tuple[int | None, str]] = []  # (rerun_number or None, filename)

    for name in existing_filenames:
        m = pattern.match(name)
        if not m:
            continue
        rerun_group = m.group(1)
        rerun_number = int(rerun_group) if rerun_group is not None else None
        matches.append((rerun_number, name))

    if not matches:
        return CanonicalFileResult(
            filename=None, is_rerun=False, rerun_number=None, superseded_filenames=()
        )

    # Highest-numbered rerun wins; base file (rerun_number=None) sorts
    # lowest so it's only picked when no reruns exist.
    matches.sort(key=lambda pair: (pair[0] is not None, pair[0] or 0))
    canonical_rerun_number, canonical_filename = matches[-1]
    superseded = tuple(name for (_, name) in matches[:-1])

    return CanonicalFileResult(
        filename=canonical_filename,
        is_rerun=canonical_rerun_number is not None,
        rerun_number=canonical_rerun_number,
        superseded_filenames=superseded,
    )
