"""
Shared fixtures for src/load/ integration tests.

These tests run against a REAL local Postgres instance (schema applied
from sql/schema/001-006, identical to what's applied to the Supabase
dev/prod projects) rather than mocks -- upsert/ON CONFLICT behavior,
trigger behavior, and constraint behavior are exactly the kind of thing
that's easy to get subtly wrong under a mock and have it look fine.

Requires DATABASE_URL to point at a scratch/test Postgres database before
running. Every table is truncated after each test for isolation.
"""
from __future__ import annotations

import os

import psycopg
import pytest

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL", "postgresql://postgres:testpass@localhost/pcit_test"
)


@pytest.fixture
def db_conn():
    os.environ["DATABASE_URL"] = TEST_DATABASE_URL
    conn = psycopg.connect(TEST_DATABASE_URL, autocommit=False)
    yield conn
    conn.rollback()
    with conn.cursor() as cur:
        cur.execute(
            "TRUNCATE products, price_snapshots, collection_items, "
            "collection_import_staging, watchlist, analytics_signals "
            "RESTART IDENTITY CASCADE"
        )
    conn.commit()
    conn.close()
