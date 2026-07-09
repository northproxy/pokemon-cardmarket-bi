"""
Tests for src.utils.archive_filenames.

Run with either:
    pytest tests/test_archive_filenames.py
    python -m unittest tests.test_archive_filenames
"""
import sys
import unittest
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.utils.archive_filenames import (  # noqa: E402
    build_filename,
    get_latest_file_for_date,
    next_filename_for_upload,
    parse_filename,
)


class TestBuildFilename(unittest.TestCase):
    def test_base_filename(self):
        self.assertEqual(
            build_filename("price_guide_6", date(2026, 7, 3)),
            "price_guide_6_2026-07-03.json",
        )

    def test_rerun_filename_is_zero_padded_to_two_digits(self):
        self.assertEqual(
            build_filename("price_guide_6", date(2026, 7, 3), rerun=1),
            "price_guide_6_2026-07-03_rerun-01.json",
        )
        self.assertEqual(
            build_filename("price_guide_6", date(2026, 7, 3), rerun=2),
            "price_guide_6_2026-07-03_rerun-02.json",
        )

    def test_rerun_beyond_two_digits_still_works(self):
        # Not documented as expected in practice, but shouldn't silently
        # produce a malformed/ambiguous filename if it ever happens.
        self.assertEqual(
            build_filename("price_guide_6", date(2026, 7, 3), rerun=11),
            "price_guide_6_2026-07-03_rerun-11.json",
        )

    def test_rejects_non_positive_rerun(self):
        with self.assertRaises(ValueError):
            build_filename("price_guide_6", date(2026, 7, 3), rerun=0)
        with self.assertRaises(ValueError):
            build_filename("price_guide_6", date(2026, 7, 3), rerun=-1)


class TestParseFilename(unittest.TestCase):
    def test_parses_base_filename(self):
        parsed = parse_filename("price_guide_6_2026-07-03.json", "price_guide_6")
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed.snapshot_date, date(2026, 7, 3))
        self.assertIsNone(parsed.rerun)

    def test_parses_rerun_filename(self):
        parsed = parse_filename(
            "price_guide_6_2026-07-03_rerun-02.json", "price_guide_6"
        )
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed.snapshot_date, date(2026, 7, 3))
        self.assertEqual(parsed.rerun, 2)

    def test_returns_none_for_wrong_prefix(self):
        # products_singles_6 vs products_nonsingles_6 share "products_" —
        # confirms parsing doesn't get confused between the two.
        parsed = parse_filename(
            "products_nonsingles_6_2026-07-01.json", "products_singles_6"
        )
        self.assertIsNone(parsed)

    def test_returns_none_for_unrelated_filename(self):
        self.assertIsNone(parse_filename("readme.txt", "price_guide_6"))
        self.assertIsNone(
            parse_filename("price_guide_6_notadate.json", "price_guide_6")
        )


class TestNextFilenameForUpload(unittest.TestCase):
    def test_no_existing_files_returns_base_filename(self):
        result = next_filename_for_upload([], "price_guide_6", date(2026, 7, 3))
        self.assertEqual(result, "price_guide_6_2026-07-03.json")

    def test_base_file_exists_returns_rerun_01(self):
        existing = ["price_guide_6_2026-07-03.json"]
        result = next_filename_for_upload(existing, "price_guide_6", date(2026, 7, 3))
        self.assertEqual(result, "price_guide_6_2026-07-03_rerun-01.json")

    def test_base_and_rerun_01_exist_returns_rerun_02(self):
        existing = [
            "price_guide_6_2026-07-03.json",
            "price_guide_6_2026-07-03_rerun-01.json",
        ]
        result = next_filename_for_upload(existing, "price_guide_6", date(2026, 7, 3))
        self.assertEqual(result, "price_guide_6_2026-07-03_rerun-02.json")

    def test_ignores_files_for_other_dates(self):
        existing = [
            "price_guide_6_2026-07-02.json",
            "price_guide_6_2026-07-02_rerun-01.json",
        ]
        result = next_filename_for_upload(existing, "price_guide_6", date(2026, 7, 3))
        self.assertEqual(result, "price_guide_6_2026-07-03.json")

    def test_ignores_files_for_other_prefixes(self):
        # products_singles_6 and products_nonsingles_6 are uploaded on the
        # same date into the same FTP folder (05-raw-archive-strategy.md) —
        # confirms one prefix's history doesn't affect the other's naming.
        existing = [
            "products_nonsingles_6_2026-07-01.json",
            "products_nonsingles_6_2026-07-01_rerun-01.json",
        ]
        result = next_filename_for_upload(
            existing, "products_singles_6", date(2026, 7, 1)
        )
        self.assertEqual(result, "products_singles_6_2026-07-01.json")

    def test_handles_non_contiguous_or_unordered_existing_reruns(self):
        # Shouldn't matter what order the directory listing comes back in.
        existing = [
            "price_guide_6_2026-07-03_rerun-02.json",
            "price_guide_6_2026-07-03.json",
            "price_guide_6_2026-07-03_rerun-01.json",
        ]
        result = next_filename_for_upload(existing, "price_guide_6", date(2026, 7, 3))
        self.assertEqual(result, "price_guide_6_2026-07-03_rerun-03.json")


class TestGetLatestFileForDate(unittest.TestCase):
    def test_returns_none_when_nothing_exists(self):
        result = get_latest_file_for_date([], "price_guide_6", date(2026, 7, 3))
        self.assertIsNone(result)

    def test_returns_base_file_when_no_reruns(self):
        existing = ["price_guide_6_2026-07-03.json"]
        result = get_latest_file_for_date(existing, "price_guide_6", date(2026, 7, 3))
        self.assertEqual(result, "price_guide_6_2026-07-03.json")

    def test_returns_highest_rerun_when_reruns_exist(self):
        existing = [
            "price_guide_6_2026-07-03.json",
            "price_guide_6_2026-07-03_rerun-01.json",
            "price_guide_6_2026-07-03_rerun-02.json",
        ]
        result = get_latest_file_for_date(existing, "price_guide_6", date(2026, 7, 3))
        self.assertEqual(result, "price_guide_6_2026-07-03_rerun-02.json")


if __name__ == "__main__":
    unittest.main()
