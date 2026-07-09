# Tests

Unit-level tests only — no live database or network calls. Mirrors `src/`
folder-by-folder as modules get implemented:

- `test_timezone.py` — Europe/Vienna date computation
- `test_filenames.py` — dated filenames, rerun-suffix detection, canonical-file resolution
- `test_normalize.py` — hyphenated field normalization, productGroup/sourceFile enrichment
- `test_valuation.py` — estimatedMarketValue fallback logic
- `test_matching.py` — collection import matching order, matchConfidence values
- `test_signals.py` — analytics signal formulas and thresholds

Data-quality checks against a live database live in `sql/checks/` instead —
see docs/06-github-repository-structure.md for the distinction.
