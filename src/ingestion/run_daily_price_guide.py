"""
Entrypoint for the daily price guide pipeline (called from
.github/workflows/daily-price-guide.yml).

Phase 0a scope: download -> compute snapshotDate (Europe/Vienna) ->
archive (canonical or rerun-suffixed) -> upload to FTP. Validation,
normalization, and price_snapshots loading are added once Phase 1 (schema)
and Phase 3 (transform/load) exist.

TODO (Phase 0a): wire download + archive steps
TODO (Phase 3): add transform + load + data quality check steps
"""

if __name__ == "__main__":
    raise NotImplementedError("Phase 0a: implement daily price guide pipeline")
