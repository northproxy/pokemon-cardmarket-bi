"""
Tests for src.ingestion.download_price_guide.

No real network or FTP server is available in this environment, so
`requests.get` and FTP_TLS are mocked. These tests verify the orchestration
logic (call order, correct filenames, correct paths) rather than actual
connectivity.
"""
import sys
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import src.ingestion.download_price_guide as dpg  # noqa: E402


class TestFetchPriceGuideBytes(unittest.TestCase):
    @patch("src.ingestion.download_price_guide.requests.get")
    def test_returns_content_on_success(self, mock_get):
        mock_get.return_value = MagicMock(content=b'{"some": "json"}')
        mock_get.return_value.raise_for_status = MagicMock()
        result = dpg.fetch_price_guide_bytes("https://example.com/price_guide_6.json")
        self.assertEqual(result, b'{"some": "json"}')

    @patch("src.ingestion.download_price_guide.requests.get")
    def test_raises_on_empty_response(self, mock_get):
        mock_get.return_value = MagicMock(content=b"")
        mock_get.return_value.raise_for_status = MagicMock()
        with self.assertRaises(ValueError):
            dpg.fetch_price_guide_bytes("https://example.com/price_guide_6.json")


class TestSaveLocalCopy(unittest.TestCase):
    def test_writes_plain_overwrite_file(self):
        with patch.object(dpg, "LOCAL_ARCHIVE_DIR", Path("/tmp/pcit_test_raw")):
            content = b'{"a": 1}'
            path1 = dpg.save_local_copy(content, date(2026, 7, 3))
            self.assertTrue(path1.exists())
            self.assertEqual(path1.name, "price_guide_6_2026-07-03.json")
            self.assertEqual(path1.read_bytes(), content)

            # Rerun for the same date overwrites — no suffixing locally.
            content2 = b'{"a": 2}'
            path2 = dpg.save_local_copy(content2, date(2026, 7, 3))
            self.assertEqual(path1, path2)
            self.assertEqual(path2.read_bytes(), content2)


class TestRunOrchestration(unittest.TestCase):
    @patch("src.ingestion.download_price_guide.connect_ftp")
    @patch("src.ingestion.download_price_guide.fetch_price_guide_bytes")
    @patch("src.ingestion.download_price_guide.get_pipeline_date")
    def test_uploads_base_filename_when_nothing_exists_on_ftp(
        self, mock_get_date, mock_fetch, mock_connect_ftp
    ):
        mock_get_date.return_value = date(2026, 7, 3)
        mock_fetch.return_value = b'{"price": "data"}'

        mock_ftps = MagicMock()
        mock_ftps.nlst.return_value = []  # nothing on FTP yet for this date
        mock_connect_ftp.return_value = mock_ftps

        with patch.object(dpg, "LOCAL_ARCHIVE_DIR", Path("/tmp/pcit_test_raw2")):
            dpg.run()

        # storbinary should have been called with the BASE filename, since
        # nothing existed yet for 2026-07-03.
        stor_call = mock_ftps.storbinary.call_args
        command = stor_call.args[0]
        self.assertIn("price_guide_6_2026-07-03.json", command)
        self.assertNotIn("rerun", command)

    @patch("src.ingestion.download_price_guide.connect_ftp")
    @patch("src.ingestion.download_price_guide.fetch_price_guide_bytes")
    @patch("src.ingestion.download_price_guide.get_pipeline_date")
    def test_uploads_rerun_suffixed_filename_when_base_already_exists(
        self, mock_get_date, mock_fetch, mock_connect_ftp
    ):
        mock_get_date.return_value = date(2026, 7, 3)
        mock_fetch.return_value = b'{"price": "data"}'

        mock_ftps = MagicMock()
        # Simulate an existing base file already on FTP for this date.
        mock_ftps.nlst.return_value = ["price_guide_6_2026-07-03.json"]
        mock_connect_ftp.return_value = mock_ftps

        with patch.object(dpg, "LOCAL_ARCHIVE_DIR", Path("/tmp/pcit_test_raw3")):
            dpg.run()

        stor_call = mock_ftps.storbinary.call_args
        command = stor_call.args[0]
        self.assertIn("price_guide_6_2026-07-03_rerun-01.json", command)

    @patch("src.ingestion.download_price_guide.connect_ftp")
    @patch("src.ingestion.download_price_guide.fetch_price_guide_bytes")
    @patch("src.ingestion.download_price_guide.get_pipeline_date")
    def test_ftp_connection_is_always_closed(
        self, mock_get_date, mock_fetch, mock_connect_ftp
    ):
        mock_get_date.return_value = date(2026, 7, 3)
        mock_fetch.return_value = b'{"price": "data"}'

        mock_ftps = MagicMock()
        mock_ftps.nlst.return_value = []
        mock_connect_ftp.return_value = mock_ftps

        with patch.object(dpg, "LOCAL_ARCHIVE_DIR", Path("/tmp/pcit_test_raw4")):
            dpg.run()

        mock_ftps.quit.assert_called_once()


if __name__ == "__main__":
    unittest.main()
