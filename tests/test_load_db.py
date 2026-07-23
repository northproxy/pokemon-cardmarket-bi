import os

import pytest

from src.load.db import MissingDatabaseUrlError, get_connection


class TestGetConnectionRequiresDatabaseUrl:
    def test_raises_when_unset(self, monkeypatch):
        monkeypatch.delenv("DATABASE_URL", raising=False)
        with pytest.raises(MissingDatabaseUrlError):
            with get_connection():
                pass

    def test_no_silent_fallback(self, monkeypatch):
        # Unlike CARDMARKET_PRICE_GUIDE_URL (which has a safe default per
        # DECISIONS.md SS9), DATABASE_URL must never default silently --
        # a wrong DB target is a genuine corruption risk.
        monkeypatch.delenv("DATABASE_URL", raising=False)
        with pytest.raises(MissingDatabaseUrlError, match="no default/fallback"):
            with get_connection():
                pass
