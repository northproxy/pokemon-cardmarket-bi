"""
Tests for src.utils.ftp_client.

FTP_TLS is mocked throughout — no real network/FTP server is used.
"""
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.utils import ftp_client  # noqa: E402


class TestConnectFtp(unittest.TestCase):
    @patch("src.utils.ftp_client.FTP_TLS")
    def test_connects_logs_in_and_secures_data_connection(self, mock_ftp_tls_cls):
        mock_instance = MagicMock()
        mock_ftp_tls_cls.return_value = mock_instance

        with patch.object(ftp_client.config, "FTP_HOST", "ftp.example.com"), \
             patch.object(ftp_client.config, "FTP_USER", "user"), \
             patch.object(ftp_client.config, "FTP_PASS", "pass"):
            result = ftp_client.connect_ftp()

        mock_instance.connect.assert_called_once_with("ftp.example.com", 21, timeout=60)
        mock_instance.login.assert_called_once_with("user", "pass")
        mock_instance.prot_p.assert_called_once()
        self.assertIs(result, mock_instance)


class TestListRemoteFilenames(unittest.TestCase):
    def test_returns_nlst_result(self):
        mock_ftps = MagicMock()
        mock_ftps.nlst.return_value = ["a.json", "b.json"]
        result = ftp_client.list_remote_filenames(mock_ftps, "/some/dir")
        self.assertEqual(result, ["a.json", "b.json"])
        mock_ftps.nlst.assert_called_once_with("/some/dir")

    def test_returns_empty_list_on_error(self):
        # Some FTP servers error on nlst for an empty directory rather than
        # returning an empty list — this should not propagate.
        mock_ftps = MagicMock()
        mock_ftps.nlst.side_effect = Exception("550 No such directory")
        result = ftp_client.list_remote_filenames(mock_ftps, "/empty/dir")
        self.assertEqual(result, [])


class TestUploadToFtp(unittest.TestCase):
    def test_uploads_with_correct_remote_path(self):
        mock_ftps = MagicMock()
        with patch("builtins.open", mock_open(read_data=b"fake bytes")):
            result = ftp_client.upload_to_ftp(
                mock_ftps, Path("/tmp/fake_local.json"), "/remote/dir", "fake_remote.json"
            )

        self.assertEqual(result, "/remote/dir/fake_remote.json")
        stor_call = mock_ftps.storbinary.call_args
        self.assertEqual(stor_call.args[0], "STOR /remote/dir/fake_remote.json")


if __name__ == "__main__":
    unittest.main()
