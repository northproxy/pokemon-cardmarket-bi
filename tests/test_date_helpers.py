"""
Tests for src.utils.date_helpers.get_pipeline_date.

Run with either:
    pytest tests/test_date_helpers.py
    python -m unittest tests.test_date_helpers
"""
import sys
import unittest
from datetime import date, datetime, timezone
from pathlib import Path

# Works even without pytest/conftest.py picking this up (e.g. plain
# `python -m unittest`).
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.utils.date_helpers import get_pipeline_date  # noqa: E402


class TestGetPipelineDate(unittest.TestCase):
    def test_same_calendar_day_in_utc_and_vienna_at_midday(self):
        # Midday UTC is nowhere near a day boundary in either zone, so this
        # should trivially agree — a sanity check before the edge cases.
        now = datetime(2026, 7, 3, 12, 0, tzinfo=timezone.utc)
        self.assertEqual(
            get_pipeline_date("Europe/Vienna", now=now),
            date(2026, 7, 3),
        )

    def test_late_utc_evening_is_already_next_day_in_vienna_summer(self):
        # This is the exact scenario 07-github-actions-logic.md calls out:
        # "a run starting at 23:30 UTC is already the next day in
        # Europe/Vienna during summer time." Vienna is UTC+2 (CEST) in July,
        # so 23:30 UTC on the 3rd is 01:30 on the 4th in Vienna.
        now = datetime(2026, 7, 3, 23, 30, tzinfo=timezone.utc)
        self.assertEqual(
            get_pipeline_date("Europe/Vienna", now=now),
            date(2026, 7, 4),
        )

    def test_late_utc_evening_in_winter_cet_offset(self):
        # In January, Vienna is UTC+1 (CET, no DST), so the boundary shifts
        # by an hour versus the summer case above. This confirms the
        # function is actually DST-aware (via ZoneInfo) rather than using a
        # hardcoded +2 offset that would silently be wrong half the year.
        now_before_midnight_vienna = datetime(2026, 1, 3, 22, 30, tzinfo=timezone.utc)
        self.assertEqual(
            get_pipeline_date("Europe/Vienna", now=now_before_midnight_vienna),
            date(2026, 1, 3),
        )
        now_after_midnight_vienna = datetime(2026, 1, 3, 23, 30, tzinfo=timezone.utc)
        self.assertEqual(
            get_pipeline_date("Europe/Vienna", now=now_after_midnight_vienna),
            date(2026, 1, 4),
        )

    def test_backfill_with_explicit_past_datetime(self):
        # 01-mvp-scope.md / 04-etl-pipeline-design.md: the Europe/Vienna
        # rule applies "to every daily run, including manual reruns and
        # backfills." Passing an explicit `now` is how a backfill script
        # would compute the correct snapshotDate for a past date.
        backfill_instant = datetime(2026, 3, 15, 10, 0, tzinfo=timezone.utc)
        self.assertEqual(
            get_pipeline_date("Europe/Vienna", now=backfill_instant),
            date(2026, 3, 15),
        )

    def test_naive_datetime_is_rejected(self):
        naive = datetime(2026, 7, 3, 23, 30)  # no tzinfo
        with self.assertRaises(ValueError):
            get_pipeline_date("Europe/Vienna", now=naive)

    def test_defaults_to_real_current_time_when_now_omitted(self):
        result = get_pipeline_date("Europe/Vienna")
        self.assertIsInstance(result, date)

    def test_works_for_other_iana_zones_not_just_vienna(self):
        # The function itself is generic; only the *caller* (config,
        # pipeline code) hardcodes Europe/Vienna specifically. Confirming
        # this isn't accidentally Vienna-specific inside the helper itself.
        now = datetime(2026, 7, 3, 23, 30, tzinfo=timezone.utc)
        self.assertEqual(
            get_pipeline_date("America/New_York", now=now),
            date(2026, 7, 3),
        )


if __name__ == "__main__":
    unittest.main()
