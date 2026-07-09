"""
Date helpers for the PCIT pipeline.

Per 02-data-model.md, 04-etl-pipeline-design.md, and
07-github-actions-logic.md:

    snapshotDate        = the pipeline run date in the Europe/Vienna timezone
    catalogArchiveDate  = the same rule, applied to the catalog pipeline

This applies to EVERY run, including manual reruns and backfills — there is
no separate rule for exceptional cases. GitHub Actions runners default to
UTC, so this conversion must happen explicitly, in one shared place reused
by both scheduled workflows, rather than relying on the runner's local date
or being recomputed ad hoc inside each workflow (07-github-actions-logic.md,
"Timezone Requirement for Runners").

This module is that one shared place. Both the daily price guide pipeline
and the twice-monthly product catalog pipeline should call
get_pipeline_date() rather than each computing a date independently.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo


def get_pipeline_date(tz_name: str, now: datetime | None = None) -> date:
    """
    Compute the pipeline's "current date" in the given IANA timezone name
    (e.g. "Europe/Vienna").

    Args:
        tz_name: IANA timezone name. Callers should pass
            config.PIPELINE_TIMEZONE rather than hardcoding the string, so
            there is exactly one place the timezone value itself is
            configured (src/config), even though the conversion logic lives
            here.
        now: Optional timezone-aware datetime to use instead of the actual
            current time. This exists specifically to support manual
            backfills/reruns for a past date — the timezone rule applies "to
            every daily run, including manual reruns and backfills"
            (01-mvp-scope.md, 04-etl-pipeline-design.md) — and to make this
            function unit-testable without depending on wall-clock time. If
            omitted, the real current UTC time is used.

    Returns:
        The calendar date in the target timezone.

    Raises:
        ValueError: if `now` is provided but is naive (no tzinfo). A naive
            datetime is ambiguous about what instant it represents, and
            silently assuming a timezone for it would reintroduce exactly
            the kind of implicit timezone assumption this function exists to
            eliminate.
    """
    if now is None:
        now = datetime.now(timezone.utc)
    elif now.tzinfo is None:
        raise ValueError(
            "`now` must be timezone-aware. Pass a datetime with tzinfo set "
            "(e.g. datetime(..., tzinfo=timezone.utc)) rather than a naive "
            "datetime — a naive value is ambiguous about what instant it "
            "represents, before it's even converted to the target zone."
        )

    return now.astimezone(ZoneInfo(tz_name)).date()
