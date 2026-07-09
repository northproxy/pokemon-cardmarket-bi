"""
MVP analytics signals: growth, price_spike, new_product, collection_gain,
collection_loss, missing_price_data. Formulas/thresholds/minimum history
requirements: docs/09-analytics-signal-definitions.md.
collection_gain/collection_loss must key on collectionItemId.
price_spike.lookbackDays is always null (avg30 is a fixed Cardmarket field).

TODO (Phase 6): implement one generate_* function per signal type
"""
