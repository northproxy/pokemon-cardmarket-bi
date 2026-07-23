"""
Database connection handling for src/load/.

Source of truth for connection behavior: docs/04-etl-pipeline-design.md
("Database Platform"), docs/06-github-repository-structure.md
(.env.example), docs/11-local-environment-setup.md.

Key rules this module exists to respect:
    - DATABASE_URL should be Supabase's POOLED connection string
      (Supavisor, transaction mode) -- GitHub Actions runs are short-lived
      and a hung/overlapping run could otherwise exhaust the free tier's
      connection limit. This module does not choose that string; it just
      reads whatever DATABASE_URL is set to. Picking the pooled string is
      an environment-configuration responsibility (.env / GitHub Actions
      secret), not something this code enforces.
    - Same variable name, different value depending on where it's set:
      local .env -> dev project, GitHub Actions secret -> prod project.
      This module has no awareness of dev vs. prod -- it just connects to
      whatever DATABASE_URL resolves to, by design (see docs/11 SS4).
    - Daily price snapshot loading must be transaction-safe: either the
      full batch loads, or it rolls back (docs/04 "Database Load
      Failure"). get_connection() is a context manager that commits on
      clean exit and rolls back on any exception, so callers get this for
      free by using `with get_connection() as conn:`.
"""
from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Iterator

import psycopg


class MissingDatabaseUrlError(RuntimeError):
    """Raised when DATABASE_URL is not set. No fallback -- a wrong/missing
    DB target is exactly the kind of silent-corruption risk this project
    treats seriously (same category as PIPELINE_TIMEZONE, see
    DECISIONS.md SS9), not something to default away."""


def _get_database_url() -> str:
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise MissingDatabaseUrlError(
            "DATABASE_URL is not set. This must point at Supabase's pooled "
            "connection string (Supavisor, transaction mode) -- see "
            "docs/06-github-repository-structure.md and docs/11 SS4. "
            "There is intentionally no default/fallback for this value."
        )
    return url


@contextmanager
def get_connection() -> Iterator["psycopg.Connection"]:
    """
    Yield a psycopg3 connection with autocommit disabled, so the caller's
    work is one transaction: commits on clean exit, rolls back on any
    exception. This is what makes "either the full daily snapshot loads,
    or it's rolled back" (docs/04) the default behavior rather than
    something every caller has to remember to implement.

    Usage:
        with get_connection() as conn:
            upsert_products(conn, rows)
        # committed here, or rolled back if an exception propagated
    """
    conn = psycopg.connect(_get_database_url(), autocommit=False)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
