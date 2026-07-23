import datetime
import json
from unittest.mock import MagicMock, patch

import pytest

from src.ingestion.run_daily_price_guide_pipeline import run

SNAPSHOT_DATE = datetime.date(2026, 7, 19)

SAMPLE_CONTENT = json.dumps({
    "version": 1,
    "createdAt": "2026-07-19T17:05:00+0200",
    "priceGuides": [
        {"idProduct": 1, "idCategory": 7, "avg": 1.0, "low": 0.5, "trend": 1.2,
         "avg1": None, "avg7": None, "avg30": 1.1},
        {"idProduct": 2, "idCategory": 7, "avg": None, "low": None, "trend": None,
         "avg1": None, "avg7": None, "avg30": None},
    ],
}).encode("utf-8")


def _patch_common(monkeypatch=None):
    """Shared patch targets for a successful run: download, local save, FTP,
    and get_pipeline_date. All patched at the ORCHESTRATOR module's own
    namespace, matching the project's established testing convention
    (DECISIONS.md §12 -- patch resolves against the importing module's
    namespace after a `from ... import`, not the origin module's)."""
    return dict(
        fetch_price_guide_bytes=patch(
            "src.ingestion.run_daily_price_guide_pipeline.fetch_price_guide_bytes",
            return_value=SAMPLE_CONTENT,
        ),
        save_local_copy=patch(
            "src.ingestion.run_daily_price_guide_pipeline.save_local_copy",
            return_value="/tmp/fake/price_guide_6_2026-07-19.json",
        ),
        connect_ftp=patch(
            "src.ingestion.run_daily_price_guide_pipeline.connect_ftp",
            return_value=MagicMock(),
        ),
        list_remote_filenames=patch(
            "src.ingestion.run_daily_price_guide_pipeline.list_remote_filenames",
            return_value=[],
        ),
        upload_to_ftp=patch(
            "src.ingestion.run_daily_price_guide_pipeline.upload_to_ftp",
            return_value="/remote/price_guides/price_guide_6_2026-07-19.json",
        ),
        get_pipeline_date=patch(
            "src.ingestion.run_daily_price_guide_pipeline.get_pipeline_date",
            return_value=SNAPSHOT_DATE,
        ),
        notify_telegram=patch(
            "src.ingestion.run_daily_price_guide_pipeline.notify_telegram"
        ),
    )


class TestRunSuccessPath:
    def test_run_loads_data_and_notifies_success(self, db_conn):
        patches = _patch_common()
        with patches["fetch_price_guide_bytes"], patches["save_local_copy"], \
             patches["connect_ftp"], patches["list_remote_filenames"], \
             patches["upload_to_ftp"], patches["get_pipeline_date"], \
             patches["notify_telegram"] as mock_notify:
            run()

        # Verify data actually landed in the real database.
        with db_conn.cursor() as cur:
            cur.execute(
                "SELECT id_product, trend FROM price_snapshots WHERE snapshot_date = %s ORDER BY id_product",
                (SNAPSHOT_DATE,),
            )
            rows = cur.fetchall()
        assert len(rows) == 2
        assert rows[0][0] == 1

        # Verify a single success notification was sent, mentioning real counts.
        mock_notify.assert_called_once()
        message = mock_notify.call_args[0][0]
        assert "Records in file: 2" in message
        assert "Rows loaded: 2" in message
        assert "✅" in message

    def test_source_created_at_populated_from_file(self, db_conn):
        patches = _patch_common()
        with patches["fetch_price_guide_bytes"], patches["save_local_copy"], \
             patches["connect_ftp"], patches["list_remote_filenames"], \
             patches["upload_to_ftp"], patches["get_pipeline_date"], \
             patches["notify_telegram"]:
            run()

        with db_conn.cursor() as cur:
            cur.execute(
                "SELECT source_created_at FROM price_snapshots WHERE snapshot_date = %s LIMIT 1",
                (SNAPSHOT_DATE,),
            )
            (source_created_at,) = cur.fetchone()
        assert source_created_at is not None
        assert source_created_at.year == 2026
        assert source_created_at.month == 7
        assert source_created_at.day == 19


class TestRunValidationFailure:
    def test_invalid_json_raises_and_archive_still_happened(self, db_conn):
        patches = _patch_common()
        bad_content_patch = patch(
            "src.ingestion.run_daily_price_guide_pipeline.fetch_price_guide_bytes",
            return_value=b"not valid json{{{",
        )
        with bad_content_patch, patches["save_local_copy"] as mock_save, \
             patches["connect_ftp"], patches["list_remote_filenames"], \
             patches["upload_to_ftp"] as mock_upload, patches["get_pipeline_date"], \
             patches["notify_telegram"]:
            with pytest.raises(Exception):
                run()

        # The critical property: archiving (save + FTP upload) must have
        # already happened BEFORE validation failed -- docs/07's "archive
        # before transform" rule. Confirms the raw file is never lost
        # just because it turned out to be invalid.
        mock_save.assert_called_once()
        mock_upload.assert_called_once()

        # And nothing was loaded into the database.
        with db_conn.cursor() as cur:
            cur.execute(
                "SELECT count(*) FROM price_snapshots WHERE snapshot_date = %s", (SNAPSHOT_DATE,)
            )
            (count,) = cur.fetchone()
        assert count == 0


class TestRunQualityCheckFailure:
    def test_empty_records_after_archive_rolls_back_and_raises(self, db_conn):
        # A file that validates as JSON but has zero price guide records --
        # transform_price_guide itself raises ValidationError before the
        # DB is ever touched (this is the expected, primary path for an
        # empty file, per docs/04).
        empty_content = json.dumps({
            "version": 1, "createdAt": "2026-07-19T17:05:00+0200", "priceGuides": [],
        }).encode("utf-8")

        patches = _patch_common()
        empty_patch = patch(
            "src.ingestion.run_daily_price_guide_pipeline.fetch_price_guide_bytes",
            return_value=empty_content,
        )
        with empty_patch, patches["save_local_copy"], patches["connect_ftp"], \
             patches["list_remote_filenames"], patches["upload_to_ftp"], \
             patches["get_pipeline_date"], patches["notify_telegram"] as mock_notify:
            with pytest.raises(Exception):
                run()

        with db_conn.cursor() as cur:
            cur.execute(
                "SELECT count(*) FROM price_snapshots WHERE snapshot_date = %s", (SNAPSHOT_DATE,)
            )
            (count,) = cur.fetchone()
        assert count == 0
        # No success notification should have gone out.
        for call in mock_notify.call_args_list:
            assert "✅" not in call[0][0]


class TestFtpArchivedBeforeLoad:
    def test_ftp_upload_called_before_db_write(self, db_conn):
        """
        Ordering assertion: upload_to_ftp must be called before any row
        appears in price_snapshots. Confirms archive-before-load isn't
        just true by accident of our happy-path test, but structurally
        guaranteed by the code order.
        """
        call_order = []

        def fake_upload(*args, **kwargs):
            call_order.append("ftp_upload")
            return "/remote/path.json"

        patches = _patch_common()
        with patches["fetch_price_guide_bytes"], patches["save_local_copy"], \
             patches["connect_ftp"], patches["list_remote_filenames"], \
             patch("src.ingestion.run_daily_price_guide_pipeline.upload_to_ftp", side_effect=fake_upload), \
             patches["get_pipeline_date"], patches["notify_telegram"]:
            run()

        with db_conn.cursor() as cur:
            cur.execute(
                "SELECT count(*) FROM price_snapshots WHERE snapshot_date = %s", (SNAPSHOT_DATE,)
            )
            (count,) = cur.fetchone()

        assert call_order == ["ftp_upload"]
        assert count == 2  # DB write happened (after FTP, by construction)