import datetime
from decimal import Decimal

from src.load.price_snapshots import upsert_price_snapshots

SNAPSHOT_DATE = datetime.date(2026, 7, 19)


def make_row(**overrides):
    base = {
        "snapshot_date": SNAPSHOT_DATE,
        "source_created_at": None,
        "id_product": 1,
        "id_category": 7,
        "avg": Decimal("1.00"),
        "low": Decimal("0.50"),
        "trend": Decimal("1.20"),
        "avg1": None,
        "avg7": None,
        "avg30": Decimal("1.10"),
        "avg_holo": None,
        "low_holo": None,
        "trend_holo": Decimal("0"),
        "avg1_holo": None,
        "avg7_holo": None,
        "avg30_holo": None,
    }
    base.update(overrides)
    return base


def fetch_snapshot(conn, snapshot_date, id_product):
    with conn.cursor() as cur:
        cur.execute(
            "SELECT trend, avg30, trend_holo FROM price_snapshots "
            "WHERE snapshot_date = %s AND id_product = %s",
            (snapshot_date, id_product),
        )
        return cur.fetchone()


class TestUpsertPriceSnapshotsInsert:
    def test_inserts_row(self, db_conn):
        n = upsert_price_snapshots(db_conn, [make_row()])
        db_conn.commit()
        assert n == 1
        row = fetch_snapshot(db_conn, SNAPSHOT_DATE, 1)
        assert row[0] == Decimal("1.20")

    def test_zero_holo_value_preserved_not_null(self, db_conn):
        upsert_price_snapshots(db_conn, [make_row()])
        db_conn.commit()
        row = fetch_snapshot(db_conn, SNAPSHOT_DATE, 1)
        assert row[2] == Decimal("0")

    def test_empty_rows_is_a_noop(self, db_conn):
        assert upsert_price_snapshots(db_conn, []) == 0

    def test_multiple_products_same_date(self, db_conn):
        n = upsert_price_snapshots(
            db_conn, [make_row(id_product=1), make_row(id_product=2)]
        )
        db_conn.commit()
        assert n == 2
        with db_conn.cursor() as cur:
            cur.execute(
                "SELECT count(*) FROM price_snapshots WHERE snapshot_date = %s",
                (SNAPSHOT_DATE,),
            )
            (count,) = cur.fetchone()
        assert count == 2


class TestUpsertPriceSnapshotsRerun:
    def test_rerun_same_date_overwrites_not_duplicates(self, db_conn):
        upsert_price_snapshots(db_conn, [make_row(trend=Decimal("1.00"))])
        db_conn.commit()
        # Simulate a corrected rerun for the same date.
        upsert_price_snapshots(db_conn, [make_row(trend=Decimal("2.00"))])
        db_conn.commit()

        with db_conn.cursor() as cur:
            cur.execute(
                "SELECT count(*) FROM price_snapshots WHERE snapshot_date = %s AND id_product = 1",
                (SNAPSHOT_DATE,),
            )
            (count,) = cur.fetchone()
        assert count == 1

        row = fetch_snapshot(db_conn, SNAPSHOT_DATE, 1)
        assert row[0] == Decimal("2.00")

    def test_different_dates_do_not_collide(self, db_conn):
        upsert_price_snapshots(db_conn, [make_row(snapshot_date=SNAPSHOT_DATE)])
        upsert_price_snapshots(
            db_conn, [make_row(snapshot_date=SNAPSHOT_DATE - datetime.timedelta(days=1))]
        )
        db_conn.commit()
        with db_conn.cursor() as cur:
            cur.execute("SELECT count(*) FROM price_snapshots WHERE id_product = 1")
            (count,) = cur.fetchone()
        assert count == 2
