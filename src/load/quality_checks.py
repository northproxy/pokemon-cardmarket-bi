"""
Programmatic data quality checks, run against a real database connection.

Source of truth: docs/04-etl-pipeline-design.md ("Data Quality Checks",
"Failure vs. Warning: MVP Thresholds"), docs/07-github-actions-logic.md
("Data Quality Checks in GitHub Actions", "Pipeline Run Metadata").

Relationship to sql/checks/*.sql: those files contain the SAME logic,
written for manual/ad-hoc review via `psql -v snapshot_date=... -f
check_x.sql`. This module is the automated-pipeline execution path --
the SQL here is functionally equivalent (kept in sync deliberately; if
one changes, the other should too), just parameterized for psycopg
instead of psql's `:name` substitution.

check_duplicate_price_snapshots is NOT included here -- it is a pure
defensive/regression check with no realistic way to fail given the
composite PRIMARY KEY on (snapshot_date, id_product), so it isn't part
of the routine per-run summary. It remains available as a standalone
SQL file for manual/CI regression testing.

check_invalid_collection_items is also NOT included in the daily/weekly
summaries below -- per docs/04, it's informational only, not tied to
either scheduled pipeline. See run_collection_integrity_check().
"""
from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from typing import Any

import psycopg


@dataclass
class CheckResult:
    name: str
    severity: str  # "failure" | "warning" | "info"
    violation_count: int
    violations: list[tuple] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return self.violation_count == 0


def _run_query(conn: "psycopg.Connection", sql: str, params: dict) -> list[tuple]:
    with conn.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def check_missing_products(conn, snapshot_date: datetime.date) -> CheckResult:
    """WARNING: price rows with no matching product (docs/04)."""
    rows = _run_query(
        conn,
        """
        SELECT ps.id_product, ps.snapshot_date
          FROM price_snapshots ps
          LEFT JOIN products p ON p.id_product = ps.id_product
         WHERE ps.snapshot_date = %(snapshot_date)s
           AND p.id_product IS NULL
         ORDER BY ps.id_product
        """,
        {"snapshot_date": snapshot_date},
    )
    return CheckResult("missing_products", "warning", len(rows), rows)


def check_empty_price_snapshot(conn, snapshot_date: datetime.date) -> CheckResult:
    """FAILURE: zero rows loaded for a date that should have data (docs/04)."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT count(*) FROM price_snapshots WHERE snapshot_date = %(snapshot_date)s",
            {"snapshot_date": snapshot_date},
        )
        (count,) = cur.fetchone()
    violated = count == 0
    return CheckResult(
        "empty_price_snapshot", "failure", 1 if violated else 0,
        [(snapshot_date, count)] if violated else [],
    )


def check_products_without_prices(conn, snapshot_date: datetime.date) -> CheckResult:
    """
    WARNING: catalogued+active products with no usable price for this
    date -- either no row at all, or a row with trend AND avg30 both
    null (confirmed necessary against a real sample, see the matching
    .sql file's header comment).
    """
    rows = _run_query(
        conn,
        """
        SELECT p.id_product, p.name, p.product_group, p.category_name, p.last_seen_at
          FROM products p
          LEFT JOIN price_snapshots ps
            ON ps.id_product = p.id_product
           AND ps.snapshot_date = %(snapshot_date)s
         WHERE p.is_active_in_catalog = TRUE
           AND (ps.id_product IS NULL OR (ps.trend IS NULL AND ps.avg30 IS NULL))
         ORDER BY p.id_product
        """,
        {"snapshot_date": snapshot_date},
    )
    return CheckResult("products_without_prices", "warning", len(rows), rows)


def check_category_mismatch(conn, snapshot_date: datetime.date) -> CheckResult:
    """WARNING: id_category drift between price_snapshots and products (docs/02/03)."""
    rows = _run_query(
        conn,
        """
        SELECT ps.id_product, ps.snapshot_date, ps.id_category, p.id_category
          FROM price_snapshots ps
          JOIN products p ON p.id_product = ps.id_product
         WHERE ps.snapshot_date = %(snapshot_date)s
           AND ps.id_category IS NOT NULL
           AND p.id_category IS NOT NULL
           AND ps.id_category != p.id_category
         ORDER BY ps.id_product
        """,
        {"snapshot_date": snapshot_date},
    )
    return CheckResult("category_mismatch", "warning", len(rows), rows)


def check_record_count_drift(
    conn, snapshot_date: datetime.date, threshold_percent: float = 20.0
) -> CheckResult:
    """
    WARNING: loaded record count differs from the previous successful
    run by more than `threshold_percent` (docs/04/07). Per docs/07's
    explicit resolution, "previous run" is read directly from
    price_snapshots for the most recent prior snapshot_date -- no
    dedicated pipeline_runs/archive_manifest table in MVP.

    If there is no prior date to compare against (first-ever run), the
    check trivially passes -- there's nothing to have drifted from.
    """
    with conn.cursor() as cur:
        cur.execute(
            "SELECT count(*) FROM price_snapshots WHERE snapshot_date = %(d)s",
            {"d": snapshot_date},
        )
        (current_count,) = cur.fetchone()

        cur.execute(
            """
            SELECT count(*) FROM price_snapshots
             WHERE snapshot_date = (
                 SELECT max(snapshot_date) FROM price_snapshots
                  WHERE snapshot_date < %(d)s
             )
            """,
            {"d": snapshot_date},
        )
        row = cur.fetchone()
        previous_count = row[0] if row else 0

    if previous_count == 0:
        return CheckResult("record_count_drift", "warning", 0, [])

    pct_diff = abs(current_count - previous_count) / previous_count * 100
    violated = pct_diff > threshold_percent
    detail = [(previous_count, current_count, round(pct_diff, 2))] if violated else []
    return CheckResult("record_count_drift", "warning", 1 if violated else 0, detail)


def run_daily_price_guide_checks(
    conn, snapshot_date: datetime.date
) -> dict[str, Any]:
    """
    Run every check relevant to the daily price guide pipeline and
    classify the overall run status, per docs/04's threshold table:
    any FAILURE-severity violation -> status "failed"; otherwise any
    WARNING-severity violation -> "success with warnings"; otherwise
    "success". Mirrors the example summary format in docs/04.
    """
    checks = [
        check_empty_price_snapshot(conn, snapshot_date),   # failure-level
        check_missing_products(conn, snapshot_date),         # warning-level
        check_products_without_prices(conn, snapshot_date),   # warning-level
        check_category_mismatch(conn, snapshot_date),          # warning-level
        check_record_count_drift(conn, snapshot_date),          # warning-level
    ]
    return _summarize(checks, snapshot_date)


def _summarize(checks: list[CheckResult], run_date: datetime.date) -> dict[str, Any]:
    has_failure = any(c.severity == "failure" and not c.passed for c in checks)
    has_warning = any(c.severity == "warning" and not c.passed for c in checks)

    if has_failure:
        status = "failed"
    elif has_warning:
        status = "success with warnings"
    else:
        status = "success"

    return {
        "date": run_date,
        "status": status,
        "checks": {c.name: {"severity": c.severity, "violation_count": c.violation_count} for c in checks},
    }


def run_collection_integrity_check(conn) -> CheckResult:
    """
    INFORMATIONAL only (docs/04) -- NOT part of either scheduled
    pipeline's failure/warning thresholds, never blocks anything. Call
    this after a collection import, or periodically -- not from
    run_daily_price_guide_checks / a catalog-pipeline equivalent.
    """
    rows = _run_query(
        conn,
        """
        SELECT collection_item_id, 'graded item missing grading_company or grade' AS issue
          FROM collection_items
         WHERE is_graded = TRUE AND (grading_company IS NULL OR grade IS NULL)
        UNION ALL
        SELECT collection_item_id, 'sold item missing sold_price or sold_date'
          FROM collection_items
         WHERE is_sold = TRUE AND (sold_price IS NULL OR sold_date IS NULL)
        UNION ALL
        SELECT collection_item_id, 'sold_price/sold_date populated while is_sold = false'
          FROM collection_items
         WHERE is_sold = FALSE AND (sold_price IS NOT NULL OR sold_date IS NOT NULL)
        UNION ALL
        SELECT collection_item_id, 'negative purchase_price'
          FROM collection_items
         WHERE purchase_price IS NOT NULL AND purchase_price < 0
        UNION ALL
        SELECT collection_item_id, 'negative sold_price'
          FROM collection_items
         WHERE sold_price IS NOT NULL AND sold_price < 0
        UNION ALL
        SELECT collection_item_id, 'purchase_date in the future'
          FROM collection_items
         WHERE purchase_date IS NOT NULL AND purchase_date > CURRENT_DATE
        UNION ALL
        SELECT collection_item_id, 'sold_date in the future'
          FROM collection_items
         WHERE sold_date IS NOT NULL AND sold_date > CURRENT_DATE
        ORDER BY 1
        """,
        {},
    )
    return CheckResult("invalid_collection_items", "info", len(rows), rows)
