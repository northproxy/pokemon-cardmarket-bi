"""
Tests for src.ingestion.download_product_catalogs.

No real network or FTP server is available in this environment, so
`requests.get`/`requests.post` and FTP_TLS are mocked. These verify
orchestration logic — correct filenames, both files always attempted,
partial-failure behavior, and notification content — not connectivity.
"""
import sys
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import src.ingestion.download_product_catalogs as dpc  # noqa: E402


class TestFetchJsonBytes(unittest.TestCase):
    @patch("src.ingestion.download_product_catalogs.requests.get")
    def test_returns_content_on_success(self, mock_get):
        mock_get.return_value = MagicMock(content=b'[{"idProduct": 1}]')
        mock_get.return_value.raise_for_status = MagicMock()
        result = dpc.fetch_json_bytes("https://example.com/x.json", "products_singles_6")
        self.assertEqual(result, b'[{"idProduct": 1}]')

    @patch("src.ingestion.download_product_catalogs.requests.get")
    def test_raises_on_empty_response(self, mock_get):
        mock_get.return_value = MagicMock(content=b"")
        mock_get.return_value.raise_for_status = MagicMock()
        with self.assertRaises(ValueError):
            dpc.fetch_json_bytes("https://example.com/x.json", "products_singles_6")


class TestSaveLocalCopy(unittest.TestCase):
    def test_writes_correct_filename_per_prefix(self):
        with patch.object(dpc, "LOCAL_ARCHIVE_DIR", Path("/tmp/pcit_test_catalog_raw")):
            content = b'[{"idProduct": 1}]'
            path = dpc.save_local_copy(content, date(2026, 7, 3), "products_singles_6")
            self.assertEqual(path.name, "products_singles_6_2026-07-03.json")
            self.assertEqual(path.read_bytes(), content)

            # Different prefix, same date -> different file, no collision.
            path2 = dpc.save_local_copy(content, date(2026, 7, 3), "products_nonsingles_6")
            self.assertEqual(path2.name, "products_nonsingles_6_2026-07-03.json")
            self.assertNotEqual(path, path2)


class TestBuildCatalogMessage(unittest.TestCase):
    def test_all_success(self):
        results = {
            "products_singles_6": {"success": True, "filename": "products_singles_6_2026-07-03.json", "size": 1000},
            "products_nonsingles_6": {"success": True, "filename": "products_nonsingles_6_2026-07-03.json", "size": 2000},
        }
        msg = dpc.build_catalog_message(date(2026, 7, 3), results)
        self.assertIn("✅", msg)
        self.assertIn("2026-07-03", msg)
        self.assertIn("products_singles_6_2026-07-03.json", msg)
        self.assertIn("1,000", msg)
        self.assertIn("products_nonsingles_6_2026-07-03.json", msg)
        self.assertIn("2,000", msg)

    def test_partial_failure(self):
        results = {
            "products_singles_6": {"success": True, "filename": "products_singles_6_2026-07-03.json", "size": 1000},
            "products_nonsingles_6": {"success": False, "error": "connection reset"},
        }
        msg = dpc.build_catalog_message(date(2026, 7, 3), results)
        self.assertIn("PARTIAL FAILURE", msg)
        self.assertIn("products_singles_6_2026-07-03.json", msg)
        self.assertIn("FAILED", msg)
        self.assertIn("connection reset", msg)


class TestNotifyTelegram(unittest.TestCase):
    @patch("src.ingestion.download_product_catalogs.requests.post")
    def test_skips_silently_when_not_configured(self, mock_post):
        with patch.object(dpc.config, "TELEGRAM_BOT_TOKEN", None), \
             patch.object(dpc.config, "TELEGRAM_CHAT_ID", None):
            dpc.notify_telegram("hello")
        mock_post.assert_not_called()

    @patch("src.ingestion.download_product_catalogs.requests.post")
    def test_posts_when_configured(self, mock_post):
        with patch.object(dpc.config, "TELEGRAM_BOT_TOKEN", "fake-token"), \
             patch.object(dpc.config, "TELEGRAM_CHAT_ID", "fake-chat-id"):
            dpc.notify_telegram("hello")
        mock_post.assert_called_once()


class TestRunOrchestration(unittest.TestCase):
    @patch("src.ingestion.download_product_catalogs.notify_telegram")
    @patch("src.ingestion.download_product_catalogs.connect_ftp")
    @patch("src.ingestion.download_product_catalogs.fetch_json_bytes")
    @patch("src.ingestion.download_product_catalogs.get_pipeline_date")
    def test_both_files_uploaded_with_base_filenames(
        self, mock_get_date, mock_fetch, mock_connect_ftp, mock_notify
    ):
        mock_get_date.return_value = date(2026, 7, 3)
        mock_fetch.return_value = b'[{"idProduct": 1}]'

        mock_ftps = MagicMock()
        mock_ftps.nlst.return_value = []  # nothing on FTP yet
        mock_connect_ftp.return_value = mock_ftps

        with patch.object(dpc, "LOCAL_ARCHIVE_DIR", Path("/tmp/pcit_test_catalog_raw2")):
            dpc.run()

        # Both prefixes should have been uploaded, with base (non-rerun)
        # filenames, since nothing existed yet.
        stor_calls = [c.args[0] for c in mock_ftps.storbinary.call_args_list]
        self.assertEqual(len(stor_calls), 2)
        self.assertTrue(any("products_singles_6_2026-07-03.json" in c for c in stor_calls))
        self.assertTrue(any("products_nonsingles_6_2026-07-03.json" in c for c in stor_calls))
        self.assertTrue(all("rerun" not in c for c in stor_calls))

        mock_notify.assert_called_once()
        self.assertIn("✅", mock_notify.call_args.args[0])

    @patch("src.ingestion.download_product_catalogs.notify_telegram")
    @patch("src.ingestion.download_product_catalogs.connect_ftp")
    @patch("src.ingestion.download_product_catalogs.fetch_json_bytes")
    @patch("src.ingestion.download_product_catalogs.get_pipeline_date")
    def test_second_file_still_uploaded_if_first_fails(
        self, mock_get_date, mock_fetch, mock_connect_ftp, mock_notify
    ):
        # First call (singles) raises, second call (nonsingles) succeeds.
        # Dict iteration order in SOURCES is insertion order (singles first).
        mock_get_date.return_value = date(2026, 7, 3)
        mock_fetch.side_effect = [
            Exception("singles download failed"),
            b'[{"idProduct": 2}]',
        ]

        mock_ftps = MagicMock()
        mock_ftps.nlst.return_value = []
        mock_connect_ftp.return_value = mock_ftps

        with patch.object(dpc, "LOCAL_ARCHIVE_DIR", Path("/tmp/pcit_test_catalog_raw3")):
            with self.assertRaises(SystemExit) as ctx:
                dpc.run()

        # Exit code reflects the partial failure...
        self.assertEqual(ctx.exception.code, 1)

        # ...but nonsingles was still uploaded despite singles failing.
        stor_calls = [c.args[0] for c in mock_ftps.storbinary.call_args_list]
        self.assertEqual(len(stor_calls), 1)
        self.assertIn("products_nonsingles_6_2026-07-03.json", stor_calls[0])

        # Notification reports the partial failure.
        mock_notify.assert_called_once()
        self.assertIn("PARTIAL FAILURE", mock_notify.call_args.args[0])

    @patch("src.ingestion.download_product_catalogs.notify_telegram")
    @patch("src.ingestion.download_product_catalogs.connect_ftp")
    @patch("src.ingestion.download_product_catalogs.fetch_json_bytes")
    @patch("src.ingestion.download_product_catalogs.get_pipeline_date")
    def test_ftp_connection_is_always_closed(
        self, mock_get_date, mock_fetch, mock_connect_ftp, mock_notify
    ):
        mock_get_date.return_value = date(2026, 7, 3)
        mock_fetch.return_value = b'[{"idProduct": 1}]'

        mock_ftps = MagicMock()
        mock_ftps.nlst.return_value = []
        mock_connect_ftp.return_value = mock_ftps

        with patch.object(dpc, "LOCAL_ARCHIVE_DIR", Path("/tmp/pcit_test_catalog_raw4")):
            dpc.run()

        mock_ftps.quit.assert_called_once()

    @patch("src.ingestion.download_product_catalogs.notify_telegram")
    @patch("src.ingestion.download_product_catalogs.connect_ftp")
    @patch("src.ingestion.download_product_catalogs.fetch_json_bytes")
    @patch("src.ingestion.download_product_catalogs.get_pipeline_date")
    def test_rerun_suffix_applied_independently_per_prefix(
        self, mock_get_date, mock_fetch, mock_connect_ftp, mock_notify
    ):
        # Singles already has a base file on FTP; nonsingles doesn't.
        mock_get_date.return_value = date(2026, 7, 3)
        mock_fetch.return_value = b'[{"idProduct": 1}]'

        mock_ftps = MagicMock()
        mock_ftps.nlst.return_value = ["products_singles_6_2026-07-03.json"]
        mock_connect_ftp.return_value = mock_ftps

        with patch.object(dpc, "LOCAL_ARCHIVE_DIR", Path("/tmp/pcit_test_catalog_raw5")):
            dpc.run()

        stor_calls = [c.args[0] for c in mock_ftps.storbinary.call_args_list]
        self.assertTrue(
            any("products_singles_6_2026-07-03_rerun-01.json" in c for c in stor_calls)
        )
        self.assertTrue(
            any(
                "products_nonsingles_6_2026-07-03.json" in c and "rerun" not in c
                for c in stor_calls
            )
        )


if __name__ == "__main__":
    unittest.main()
