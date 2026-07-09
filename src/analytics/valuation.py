"""
estimatedMarketValue = (trend + avg30) / 2, with fallback to whichever of
trend/avg30 exists, or null if neither exists. `low` is never used
(noisy). See docs/01-mvp-scope.md, docs/02-data-model.md.

TODO (Phase 6): implement calculate_estimated_market_value()
"""
