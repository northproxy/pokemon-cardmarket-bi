import datetime
import uuid

import pytest

from src.load.products import upsert_products
from src.load.price_snapshots import upsert_price_snapshots
from src.load.quality_checks import (
    check_category_mismatch,
    check_empty_price_snapshot,
    check_missing_products,
    check_products_without_prices,
    check_record_count_drift,
    run_collection_integrity_check,
    run_daily_price_guide_checks,
)

DATE = datetime.date(2026, 7, 19)
PREV_DATE = datetime.date(2026, 7, 18)


def make_product(**overrides):
    base = {
        "id_product": 1, "name": "Pikachu", "id_category": 7,
        "category_name": "Singles", "id_expansion": None, "id_metacard": None,
        "date_added": None, "product_group": "single",
        "source_file": "products_singles_6.json",
    }
    base.update(overrides)
    return base


def make_snapshot(**overrides):
    base = {
        "snapshot_date": DATE, "source_created_at": None, "id_product": 1,
        "id_category": 7, "avg": None, "low": None, "trend": None,
        "avg1": None, "avg7": None, "avg30": None, "avg_holo": None,
        "low_holo": None, "trend_holo": None, "avg1_holo": None,
        "avg7_holo": None, "avg30_holo": None,
    }
    base.update(overrides)
    return base


class TestCheckMissingProducts:
    def test_flags_price_row_with_no_product(self, db_conn):
        upsert_price_snapshots(db_conn, [make_snapshot(id_product=999, trend=1)])
        db_conn.commit()
        result = check_missing_products(db_conn, DATE)
        assert not result.passed
        assert result.violation_count == 1
        assert result.severity == "warning"

    def test_passes_when_product_exists(self, db_conn):
        upsert_products(db_conn, [make_product(id_product=1)])
        upsert_price_snapshots(db_conn, [make_snapshot(id_product=1, trend=1)])
        db_conn.commit()
        result = check_missing_products(db_conn, DATE)
        assert result.passed


class TestCheckEmptyPriceSnapshot:
    def test_flags_zero_rows(self, db_conn):
        result = check_empty_price_snapshot(db_conn, DATE)
        assert not result.passed
        assert result.severity == "failure"

    def test_passes_with_at_least_one_row(self, db_conn):
        upsert_price_snapshots(db_conn, [make_snapshot(id_product=1, trend=1)])
        db_conn.commit()
        result = check_empty_price_snapshot(db_conn, DATE)
        assert result.passed


class TestCheckProductsWithoutPrices:
    def test_flags_row_with_null_trend_and_avg30(self, db_conn):
        upsert_products(db_conn, [make_product(id_product=1)])
        upsert_price_snapshots(db_conn, [make_snapshot(id_product=1)])  # all null
        db_conn.commit()
        result = check_products_without_prices(db_conn, DATE)
        assert not result.passed
        assert result.violations[0][0] == 1

    def test_flags_missing_row_entirely(self, db_conn):
        upsert_products(db_conn, [make_product(id_product=1)])
        db_conn.commit()  # no price_snapshots row inserted for id_product=1
        result = check_products_without_prices(db_conn, DATE)
        assert not result.passed

    def test_passes_when_trend_present(self, db_conn):
        upsert_products(db_conn, [make_product(id_product=1)])
        upsert_price_snapshots(db_conn, [make_snapshot(id_product=1, trend=1.5)])
        db_conn.commit()
        result = check_products_without_prices(db_conn, DATE)
        assert result.passed

    def test_ignores_inactive_products(self, db_conn):
        upsert_products(db_conn, [make_product(id_product=1)])
        db_conn.commit()
        with db_conn.cursor() as cur:
            cur.execute("UPDATE products SET is_active_in_catalog = FALSE WHERE id_product = 1")
        db_conn.commit()
        result = check_products_without_prices(db_conn, DATE)
        assert result.passed  # inactive products aren't flagged


class TestCheckCategoryMismatch:
    def test_flags_drift(self, db_conn):
        upsert_products(db_conn, [make_product(id_product=1, id_category=7)])
        upsert_price_snapshots(db_conn, [make_snapshot(id_product=1, id_category=99, trend=1)])
        db_conn.commit()
        result = check_category_mismatch(db_conn, DATE)
        assert not result.passed

    def test_passes_when_matching(self, db_conn):
        upsert_products(db_conn, [make_product(id_product=1, id_category=7)])
        upsert_price_snapshots(db_conn, [make_snapshot(id_product=1, id_category=7, trend=1)])
        db_conn.commit()
        result = check_category_mismatch(db_conn, DATE)
        assert result.passed

    def test_ignores_null_category_either_side(self, db_conn):
        upsert_products(db_conn, [make_product(id_product=1, id_category=None)])
        upsert_price_snapshots(db_conn, [make_snapshot(id_product=1, id_category=7, trend=1)])
        db_conn.commit()
        result = check_category_mismatch(db_conn, DATE)
        assert result.passed


class TestCheckRecordCountDrift:
    def test_passes_when_no_prior_date(self, db_conn):
        upsert_price_snapshots(db_conn, [make_snapshot(id_product=1, trend=1)])
        db_conn.commit()
        result = check_record_count_drift(db_conn, DATE)
        assert result.passed

    def test_flags_large_drop(self, db_conn):
        prev_rows = [make_snapshot(snapshot_date=PREV_DATE, id_product=i, trend=1) for i in range(1, 11)]
        upsert_price_snapshots(db_conn, prev_rows)
        # Today only 1 row loaded -- a 90% drop.
        upsert_price_snapshots(db_conn, [make_snapshot(id_product=1, trend=1)])
        db_conn.commit()
        result = check_record_count_drift(db_conn, DATE, threshold_percent=20.0)
        assert not result.passed

    def test_passes_within_threshold(self, db_conn):
        prev_rows = [make_snapshot(snapshot_date=PREV_DATE, id_product=i, trend=1) for i in range(1, 11)]
        upsert_price_snapshots(db_conn, prev_rows)
        # 10 -> 9 rows is a 10% drop, under the 20% threshold.
        today_rows = [make_snapshot(id_product=i, trend=1) for i in range(1, 10)]
        upsert_price_snapshots(db_conn, today_rows)
        db_conn.commit()
        result = check_record_count_drift(db_conn, DATE, threshold_percent=20.0)
        assert result.passed


class TestRunDailyPriceGuideChecks:
    def test_status_failed_when_no_rows(self, db_conn):
        summary = run_daily_price_guide_checks(db_conn, DATE)
        assert summary["status"] == "failed"
        assert summary["checks"]["empty_price_snapshot"]["violation_count"] == 1

    def test_status_success_with_warnings(self, db_conn):
        # Row exists (avoids the failure check) but references an unknown product (warning).
        upsert_price_snapshots(db_conn, [make_snapshot(id_product=999, trend=1)])
        db_conn.commit()
        summary = run_daily_price_guide_checks(db_conn, DATE)
        assert summary["status"] == "success with warnings"

    def test_status_success_when_clean(self, db_conn):
        upsert_products(db_conn, [make_product(id_product=1, id_category=7)])
        upsert_price_snapshots(db_conn, [make_snapshot(id_product=1, id_category=7, trend=1.5, avg30=1.4)])
        db_conn.commit()
        summary = run_daily_price_guide_checks(db_conn, DATE)
        assert summary["status"] == "success"


class TestRunCollectionIntegrityCheck:
    def test_flags_multiple_issues_on_same_item(self, db_conn):
        upsert_products(db_conn, [make_product(id_product=1)])
        db_conn.commit()
        with db_conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO collection_items (
                    id_product, is_graded, grading_company, grade,
                    is_sold, sold_price, sold_date, purchase_price
                ) VALUES (1, TRUE, NULL, NULL, FALSE, 5.00, '2026-07-01', -3.00)
                """
            )
        db_conn.commit()
        result = run_collection_integrity_check(db_conn)
        assert result.severity == "info"
        assert result.violation_count == 3  # graded-missing, sold-mismatch, negative-price

    def test_passes_for_clean_item(self, db_conn):
        upsert_products(db_conn, [make_product(id_product=1)])
        db_conn.commit()
        with db_conn.cursor() as cur:
            cur.execute(
                "INSERT INTO collection_items (id_product, purchase_price) VALUES (1, 10.00)"
            )
        db_conn.commit()
        result = run_collection_integrity_check(db_conn)
        assert result.passed
