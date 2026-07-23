"""
Loading logic for the `price_snapshots` table.

Source of truth: docs/02-data-model.md, docs/03-data-dictionary.md,
docs/04-etl-pipeline-design.md ("Price Snapshot Load Logic", "Database
Load Failure").

Responsibility here, per docs/06 (src/load/): upsert price_snapshots by
snapshot_date + id_product, reading from the already-transformed rows
produced by src/transform/price_guide.py::transform_price_guide.

On "duplicate (snapshot_date, id_product) remaining after upsert" (listed
in docs/04 as a FAILURE condition): the composite PRIMARY KEY on
(snapshot_date, id_product) in sql/schema/002 makes this structurally
impossible via this upsert path -- ON CONFLICT can only resolve into
exactly one row per key. This check is therefore satisfied by the schema
itself, not by application logic re-checking it after the fact.
"""
from __future__ import annotations

from typing import Iterable

import psycopg

_UPSERT_SQL = """
INSERT INTO price_snapshots (
    snapshot_date, source_created_at, id_product, id_category,
    avg, low, trend, avg1, avg7, avg30,
    avg_holo, low_holo, trend_holo, avg1_holo, avg7_holo, avg30_holo
)
VALUES (
    %(snapshot_date)s, %(source_created_at)s, %(id_product)s, %(id_category)s,
    %(avg)s, %(low)s, %(trend)s, %(avg1)s, %(avg7)s, %(avg30)s,
    %(avg_holo)s, %(low_holo)s, %(trend_holo)s, %(avg1_holo)s, %(avg7_holo)s, %(avg30_holo)s
)
ON CONFLICT (snapshot_date, id_product) DO UPDATE SET
    source_created_at = EXCLUDED.source_created_at,
    id_category        = EXCLUDED.id_category,
    avg                  = EXCLUDED.avg,
    low                   = EXCLUDED.low,
    trend                  = EXCLUDED.trend,
    avg1                     = EXCLUDED.avg1,
    avg7                      = EXCLUDED.avg7,
    avg30                      = EXCLUDED.avg30,
    avg_holo                    = EXCLUDED.avg_holo,
    low_holo                     = EXCLUDED.low_holo,
    trend_holo                    = EXCLUDED.trend_holo,
    avg1_holo                      = EXCLUDED.avg1_holo,
    avg7_holo                       = EXCLUDED.avg7_holo,
    avg30_holo                       = EXCLUDED.avg30_holo
"""


def upsert_price_snapshots(conn: "psycopg.Connection", rows: Iterable[dict]) -> int:
    """
    Upsert a full day's worth of already-transformed price snapshot rows
    (see src/transform/price_guide.py::transform_price_guide).

    Reprocessing the same snapshot_date (manual rerun, or a corrected
    canonical file) overwrites that date's existing rows rather than
    creating duplicates or failing -- see docs/02/03/04 "Load / Rerun
    Behavior".

    Does not commit -- caller controls the transaction. Per docs/04
    "Database Load Failure", callers should run this inside
    src/load/db.py::get_connection()'s `with` block so the WHOLE day's
    batch either commits or rolls back together; do not commit
    mid-batch.
    """
    rows = list(rows)
    if not rows:
        return 0

    with conn.cursor() as cur:
        cur.executemany(_UPSERT_SQL, rows)

    return len(rows)
