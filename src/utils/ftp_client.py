"""
Shared FTP helper functions for the PCIT pipeline.

Extracted from src/ingestion/download_price_guide.py once
src/ingestion/download_product_catalogs.py needed the same connect/list/
upload logic (DECISIONS.md §11 Decision C -> resolved by §12).

Kept intentionally thin: connecting, listing a remote directory, and
uploading one local file. Deciding *what filename to use* is a separate
concern that lives in src/utils/archive_filenames.py — this module only
knows how to talk to FTP, not what to name things or when to suffix a
rerun.
"""
from __future__ import annotations

import posixpath
from ftplib import FTP_TLS
from pathlib import Path

from src.config import config


def connect_ftp() -> FTP_TLS:
    """
    Connect using explicit FTPS (AUTH TLS), per
    11-local-environment-setup.md: plain ftp:// is rejected by this
    provider with a 530 error even with correct credentials.
    """
    ftps = FTP_TLS()
    ftps.connect(config.FTP_HOST, 21, timeout=60)
    ftps.login(config.FTP_USER, config.FTP_PASS)
    ftps.prot_p()  # secure the data connection, not just the control connection
    return ftps


def list_remote_filenames(ftps: FTP_TLS, remote_dir: str) -> list[str]:
    """
    List filenames in `remote_dir`. Returns an empty list if the directory
    doesn't exist yet or the server errors on an empty-directory listing —
    both are treated as "nothing archived here yet" rather than failing the
    whole run over it.
    """
    try:
        return ftps.nlst(remote_dir)
    except Exception:
        return []


def upload_to_ftp(ftps: FTP_TLS, local_path: Path, remote_dir: str, remote_filename: str) -> str:
    """Upload `local_path` to `{remote_dir}/{remote_filename}`. Returns the
    full remote path uploaded to."""
    remote_full_path = posixpath.join(remote_dir, remote_filename)
    with open(local_path, "rb") as f:
        ftps.storbinary(f"STOR {remote_full_path}", f)
    return remote_full_path
