# Analytics Signal Definitions

## Document Version

```text
Version: 0.2
Status: Draft / MVP design (architecture decisions applied)
Last updated: 2026-07-04
```

## Changelog

| Version | Date | Change |
|---|---|---|
| 0.1 | 2026-07-04 | Initial analytics signal definitions |
| 0.2 | 2026-07-04 | Reconciled `analytics_signals` schema with `02-data-model.md`/`03-data-dictionary.md`, keyed collection-level signals on `collectionItemId`, aligned `new_product` aging tiers with the canonical 14-day reliability flag, added the missing `missing_price_data` MVP signal, deferred `sealed_growth` to Later (matching 02/03), and cross-referenced the signal-specific BI views to the data dictionary's view catalog, based on architecture review |

## Purpose

This document defines the analytics signals used in the Pokémon Cardmarket BI project.

The goal is not to build a complex prediction system in the MVP.
The goal is to create simple, explainable, and portfolio-friendly analytical signals based on historical price snapshots.

The project stores daily Cardmarket price guide data and turns it into useful collection and market insights over time.

```text
Daily price snapshots
→ price history
→ calculated changes
→ analytics signals
→ BI views / dashboards
```

---

## Important MVP Principle

The MVP should avoid overclaiming.

At the beginning, the project does not have enough historical data for serious forecasting or machine learning.

Therefore, MVP analytics should focus on:

```text
descriptive analytics
trend detection
price movement flags
collection value changes
simple historical comparisons
```

Not:

```text
machine learning
investment advice
guaranteed predictions
automatic buy/sell decisions
```

The project can still be analytically strong without pretending to predict the market too early.

---

## Signal Storage

Analytics signals are stored in:

```text
analytics_signals
```

The canonical schema for this table lives in `02-data-model.md` and `03-data-dictionary.md`; it is repeated here for convenience only, and this document should not be treated as an independent source of truth for the table's structure.

```text
signalId
signalDate
idProduct
collectionItemId
signalType
signalValue
signalStrength
lookbackDays
referenceValue
currentValue
signalDescription
createdAt
```

---

## Field Explanation

| Field               | Description                                                                                      |
| ------------------- | -------------------------------------------------------------------------------------------------- |
| `signalId`          | Unique technical ID of the signal                                                                 |
| `signalDate`        | Date when the signal was calculated                                                               |
| `idProduct`         | Cardmarket product ID. Nullable for collection-only signals. Populated alongside `collectionItemId` on collection-level signals, for convenient joins. |
| `collectionItemId`  | Specific physical collection item, when the signal is collection-level. **Required** for `collection_gain`/`collection_loss` — see "Why Collection Signals Key on `collectionItemId`" below. |
| `signalType`        | Type of signal, for example `growth` or `price_spike`                                             |
| `signalValue`       | Main numeric value of the signal                                                                  |
| `signalStrength`    | Simple category such as `low`, `medium`, `high`                                                   |
| `lookbackDays`      | Historical window used for the calculation, when the signal has one (null otherwise — see `price_spike`) |
| `referenceValue`    | Previous / comparison value                                                                       |
| `currentValue`      | Current value used for comparison                                                                 |
| `signalDescription` | Human-readable explanation                                                                        |
| `createdAt`         | Timestamp when the signal was created                                                             |

---

## Why Collection Signals Key on `collectionItemId`

`collection_gain` and `collection_loss` describe a *specific physical item's* change in value relative to what was paid for it. Since `purchasePrice` lives on `collection_items`, not `products`, and two copies of the exact same card can have different purchase prices, a signal keyed only on `idProduct` cannot distinguish "copy A gained value" from "copy B, bought later at a different price, did not." Every `collection_gain`/`collection_loss` row must set `collectionItemId`. `idProduct` should still be populated on the same row so product-level rollups (e.g. "total gain across all Pikachu copies") don't require an extra join.

Product-level signals (`growth`, `price_spike`, `new_product`, `missing_price_data`) key on `idProduct` and leave `collectionItemId` null, since they describe the market, not a specific owned copy.

---

## Recommended MVP Signals

For the MVP, signals should stay simple and explainable.

Recommended MVP signals:

```text
growth
price_spike
new_product
collection_gain
collection_loss
missing_price_data
```

Signals that can wait until later:

```text
sealed_growth
potential_buy_opportunity
undervalued_product
momentum_score
volatility_score
forecasted_growth
```

`sealed_growth` moved to this list to match the scope already settled in `02-data-model.md`/`03-data-dictionary.md` — meaningfully separating sealed products from singles benefits from having enough historical data across both groups to compare, which the project won't have on day one. `missing_price_data` moved into the MVP list to match those same docs — see its definition below.

---

# 1. Growth Signal

## Purpose

The `growth` signal identifies products whose price increased over a selected historical period.

This is one of the most important early signals because it is simple, useful, and easy to explain.

---

## Example Question

```text
Which products increased the most over the last 30 days?
```

---

## Suggested MVP Calculation

Use the estimated market value or `trend` price.

For a simple MVP version:

```text
growthPercent = ((currentTrend - previousTrend) / previousTrend) * 100
```

Where:

```text
currentTrend = latest trend value
previousTrend = trend value from N days ago
```

Recommended MVP lookback windows:

```text
7 days
30 days
90 days
```

`lookbackDays` on the stored signal row records which window (7, 30, or 90) was used.

---

## Example

```text
previousTrend = 10.00
currentTrend = 13.00

growthPercent = ((13.00 - 10.00) / 10.00) * 100
growthPercent = 30%
```

Stored as: `referenceValue = 10.00`, `currentValue = 13.00`, `signalValue = 30.00`, `lookbackDays = 30`.

---

## Suggested Signal Strength

```text
low = 5% to 10% growth
medium = 10% to 25% growth
high = more than 25% growth
```

These thresholds are simple starting values, not statistically derived, and can be adjusted after observing real data — the same caveat applies to every strength scale in this document, even where not repeated verbatim.

---

## MVP Notes

The growth signal should ignore products where the previous value is missing or zero.

**New-product suppression:** this signal uses the same 14-day `isNewProduct` reliability flag defined in `02-data-model.md`/`03-data-dictionary.md` (`priceAgeDays = snapshotDate - products.firstSeenAt`, `isNewProduct = priceAgeDays < 14`). While `isNewProduct` is true for a product, a `growth` signal should either be suppressed entirely or explicitly marked as low-confidence in its `signalDescription` — early price swings for a brand-new product are not comparable to genuine market movement for an established one. This is the same rule referenced by the `new_product` signal below; there is only one 14-day aging concept in this project, not two.

---

# 2. Price Spike Signal

## Purpose

The `price_spike` signal identifies unusually strong short-term price movements.

This signal is useful for detecting sudden market attention, hype, supply changes, or temporary pricing anomalies.

---

## Example Question

```text
Which products suddenly became more expensive compared to their recent average?
```

---

## Suggested MVP Calculation

Compare the latest `trend` price with the 30-day average:

```text
priceSpikePercent = ((trend - avg30) / avg30) * 100
```

Where:

```text
trend = latest trend price
avg30 = latest 30-day average price from Cardmarket
```

`lookbackDays` should be stored as **null** for this signal — unlike `growth`, there is no freely chosen window here; `avg30` is a fixed Cardmarket-provided field, not a lookback this project selects. An earlier draft of this document populated `lookbackDays = 30` for this signal by analogy with `growth`, which conflated "the field is named avg30" with "we chose a 30-day window," and has been corrected here.

---

## Example

```text
trend = 20.00
avg30 = 15.00

priceSpikePercent = ((20.00 - 15.00) / 15.00) * 100
priceSpikePercent = 33.33%
```

Stored as: `referenceValue = 15.00`, `currentValue = 20.00`, `signalValue = 33.33`, `lookbackDays = null`.

---

## Suggested Signal Strength

```text
low = 10% to 20% above avg30
medium = 20% to 40% above avg30
high = more than 40% above avg30
```

---

## MVP Notes

This signal should be interpreted carefully.

A price spike can mean:

```text
real market growth
temporary hype
low supply
data noise
unstable pricing for a new product
```

The signal should not automatically mean "buy".

**New-product suppression:** applies here exactly as described for `growth` above — a product where `isNewProduct` is true should have its `price_spike` signal suppressed or explicitly flagged as low-confidence, since `avg30` itself is not yet meaningful for a product with under 14 days of history.

---

# 3. New Product Signal

## Purpose

The `new_product` signal identifies products that recently appeared in the local catalog or price guide.

This is useful because newly released Pokémon products often have unstable early prices, and because it gives a single, discrete event marking when a product first became trackable — rather than requiring every consumer to compute `firstSeenAt` age themselves.

---

## Example Question

```text
Which products appeared recently and should be monitored?
```

---

## Suggested MVP Calculation

A product is considered for this signal based on one criterion only:

```text
priceAgeDays = signalDate - products.firstSeenAt
```

This is the same `firstSeenAt`-based calculation used for the canonical `isNewProduct` reliability flag (see `02-data-model.md`). An earlier draft of this document also allowed a second, vaguer criterion ("appears in price_snapshots but has only a short local price history") — that has been dropped in favor of a single, well-defined measure.

---

## Suggested Signal Strength

Aligned with the canonical 14-day reliability boundary, rather than an independently chosen scale:

```text
high   = priceAgeDays <= 3   (very new, most unstable)
medium = priceAgeDays <= 14  (isNewProduct is true — matches the canonical
                               growth/price_spike suppression boundary)
low    = priceAgeDays <= 30  (recently added, no longer flagged unstable
                               elsewhere, but still worth surfacing)
```

A product past 30 days does not generate a new `new_product` signal.

---

## MVP Notes

New products should be analyzed separately from older products.

Reason:

```text
early prices can be unstable
release hype can distort price movement
supply may not be stable yet
catalog data may lag behind price guide data
```

This signal is especially useful for separating real long-term growth from release-window volatility, and its `medium`/`high` tiers correspond directly to when `isNewProduct` is true elsewhere in the system — so a BI view can cross-reference "is this product flagged as new" and "is this product's growth/spike signal suppressed" using the same 14-day boundary.

---

# 4. Collection Gain Signal

## Purpose

The `collection_gain` signal identifies a specific collection item whose estimated market value increased compared to its purchase price.

This signal connects market price data with the user's personal collection.

---

## Example Question

```text
Which items in my collection are currently worth more than I paid?
```

---

## Suggested MVP Calculation

Use the existing estimated market value formula:

```text
estimatedMarketValue = (trend + avg30) / 2
```

Then compare it to the item's `purchasePrice`:

```text
collectionGain = estimatedMarketValue - purchasePrice
```

Percentage gain:

```text
collectionGainPercent = ((estimatedMarketValue - purchasePrice) / purchasePrice) * 100
```

This signal is calculated **per `collectionItemId`**, not per `idProduct` — see "Why Collection Signals Key on `collectionItemId`" above. Two copies of the same card with different purchase prices produce two separate `collection_gain` (or one gain, one loss) signal rows.

---

## Example

```text
purchasePrice = 20.00
estimatedMarketValue = 30.00

collectionGain = 10.00
collectionGainPercent = 50%
```

Stored as: `collectionItemId = <the specific item>`, `idProduct = <its product, for convenience>`, `referenceValue = 20.00`, `currentValue = 30.00`, `signalValue = 10.00`.

---

## Suggested Signal Strength

```text
low = 5% to 15% gain
medium = 15% to 40% gain
high = more than 40% gain
```

---

## MVP Notes

This signal only works when `purchasePrice` is known.

For pulled cards, purchase price may be empty or difficult to calculate.
In that case, the item can still have an estimated market value, but not a real gain/loss calculation, and no `collection_gain`/`collection_loss` signal should be generated for it.

An item does not generate both a `collection_gain` and a `collection_loss` signal on the same `signalDate` — the sign of `estimatedMarketValue - purchasePrice` determines which one (if either) applies. An item exactly at breakeven generates neither.

---

# 5. Collection Loss Signal

## Purpose

The `collection_loss` signal identifies a specific collection item whose estimated market value is lower than its purchase price.

This is useful for realistic portfolio tracking and avoids showing only positive results.

---

## Example Question

```text
Which items in my collection are currently below purchase price?
```

---

## Suggested MVP Calculation

```text
collectionLoss = purchasePrice - estimatedMarketValue
```

Percentage loss:

```text
collectionLossPercent = ((purchasePrice - estimatedMarketValue) / purchasePrice) * 100
```

As with `collection_gain`, this signal is calculated **per `collectionItemId`**, not per `idProduct`.

---

## Example

```text
purchasePrice = 40.00
estimatedMarketValue = 30.00

collectionLoss = 10.00
collectionLossPercent = 25%
```

Stored as: `collectionItemId = <the specific item>`, `idProduct = <its product, for convenience>`, `referenceValue = 40.00`, `currentValue = 30.00`, `signalValue = 10.00`.

---

## Suggested Signal Strength

```text
low = 5% to 15% loss
medium = 15% to 40% loss
high = more than 40% loss
```

---

## MVP Notes

Loss signals should be handled neutrally.

A current loss does not automatically mean the product is bad.
It may simply mean:

```text
the item was bought during hype
the market corrected
the product is still too new
the purchase price included shipping or fees
```

---

# 6. Missing Price Data Signal

## Purpose

The `missing_price_data` signal flags a product that exists in the local catalog but has no usable price in the latest snapshot — i.e., `trend` and `avg30` are both null for its most recent `price_snapshots` row.

## Relationship to `vw_products_without_prices`

`03-data-dictionary.md` already defines a BI view, `vw_products_without_prices`, that shows this same condition live, at query time. The `missing_price_data` **signal** is a complementary, dated record of the same condition, not a duplicate of the view:

```text
vw_products_without_prices  = "which products currently lack price data,
                               right now" — always reflects the live state
missing_price_data signal   = "this product was missing price data as of
                               this specific signalDate" — a permanent,
                               dated record, useful for tracking how long a
                               gap has persisted or when it started/resolved
```

## Example Question

```text
Which catalog products still don't have usable price data, and since when?
```

## Suggested MVP Calculation

No percentage or comparison value applies here. `signalValue`, `referenceValue`, and `currentValue` are null for this signal type; `signalDescription` carries the explanation (e.g. "No trend or avg30 price available as of this date").

## Suggested Signal Strength

```text
low    = missing for fewer than 14 days
medium = missing for 14 to 30 days
high   = missing for more than 30 days
```

Strength here reflects how long the gap has persisted, which is meaningfully different from "how new is this product" — a product can be old and still lack price data (e.g. very low market activity), so this scale is independent of the 14-day `isNewProduct` flag even though it reuses 14 as a convenient first boundary.

## MVP Notes

This signal should not fire for genuinely new products still within their expected data-lag window — a product added yesterday not yet having a price is expected, not a data quality problem. A reasonable MVP rule is to only generate this signal once a product has been in the catalog for at least as long as one full daily pipeline cycle (i.e., it has had at least one chance to appear in `price_snapshots` and didn't).

---

# 7. Sealed Growth Signal (Deferred)

## MVP Status

This signal is **not part of the first MVP**, matching the scope already settled in `02-data-model.md`/`03-data-dictionary.md`. An earlier draft of this document listed it as MVP; that was a scope conflict with those docs, not a deliberate expansion, and has been corrected here.

## Purpose

The `sealed_growth` signal would track growth specifically for sealed products, since sealed Pokémon products often behave differently from individual cards.

## Why This Should Wait

Meaningfully separating sealed products from singles benefits from having enough historical data across both groups to compare against each other — something the project won't have on day one. Building this signal before that data exists risks drawing conclusions from too little history, the same concern that applies to `potential_buy_opportunity` below.

## Possible Later Logic

Once enough history exists, the same logic as the general `growth` signal, restricted to:

```text
productGroup = non_single
```

or, for collection items:

```text
isSealed = true
```

```text
sealedGrowthPercent = ((currentTrend - previousTrend) / previousTrend) * 100
```

using the same strength tiers as `growth` (5-10% low, 10-25% medium, >25% high) as a starting point.

## Later Notes

Sealed products should eventually be analyzable separately from singles because their price behavior may depend on:

```text
print runs
availability
reprints
collector demand
sealed display value
set popularity
```

This can become one of the more interesting parts of the project once it's promoted out of "later."

---

# 8. Potential Buy Opportunity Signal

## MVP Status

This signal should not be part of the first MVP.

It is an interesting future idea, but it is more subjective and easier to overclaim.

---

## Purpose

The `potential_buy_opportunity` signal would try to identify products that may be temporarily undervalued.

---

## Possible Later Logic

A product could be flagged if:

```text
current trend is below avg30
long-term growth is positive
short-term drop appears temporary
product has enough historical data
volatility is not too high
```

Example future formula:

```text
if trend < avg30
and 90-day growth > 0
and product has at least 90 days of price history:
    potential_buy_opportunity = true
```

---

## Why This Should Wait

This signal requires more context than simple growth.

It can be misleading without:

```text
enough historical data
volatility checks
product age
sealed vs single separation
release/reprint awareness
market context
```

For this reason, it belongs to a later analytics stage, not the MVP.

---

# Suggested Signal Types

The following values can be used in `analytics_signals.signalType`:

```text
growth
price_spike
new_product
collection_gain
collection_loss
missing_price_data
sealed_growth
potential_buy_opportunity
```

For MVP, use:

```text
growth
price_spike
new_product
collection_gain
collection_loss
missing_price_data
```

For later versions, add:

```text
sealed_growth
potential_buy_opportunity
```

This list matches the MVP / Later split in `02-data-model.md`/`03-data-dictionary.md` exactly.

---

# Suggested Signal Strength Values

To keep the model simple, signal strength should use a small controlled list:

```text
low
medium
high
```

Optional later value:

```text
critical
```

For MVP, `low`, `medium`, and `high` are enough.

---

# Data Quality Rules for Signals

Analytics signals should not be created blindly.

Before creating a signal, the project should check:

```text
required price fields are not null (for price-based signals)
comparison value is not zero
product has enough price history, or the signal type (missing_price_data,
  new_product) is specifically designed to handle sparse history
idProduct exists, or collectionItemId exists for collection-level signals
new products are handled separately (see New-Product Suppression under
  growth and price_spike)
collection-level signals use collectionItemId, not just idProduct
```

---

## Minimum History Requirements

Recommended minimum history:

| Signal                      | Minimum History                                          |
| ---------------------------- | --------------------------------------------------------- |
| `growth`                     | 7 days for short-term growth; suppressed while isNewProduct |
| `price_spike`                | current snapshot with `trend` and `avg30`; suppressed while isNewProduct |
| `new_product`                | product `firstSeenAt` (no price history needed)          |
| `collection_gain`            | latest price + `purchasePrice` on the specific collection item |
| `collection_loss`            | latest price + `purchasePrice` on the specific collection item |
| `missing_price_data`         | at least one completed daily pipeline cycle since the product was catalogued |
| `sealed_growth`              | later only — same as `growth`, once promoted from deferred |
| `potential_buy_opportunity`  | 90+ days, later only                                     |

---

# Recommended MVP BI Views for Signals

Signals can be exposed through BI views instead of building a full app.

**These views extend the catalog in `03-data-dictionary.md`, which remains the single source of truth for view definitions.** They are listed here because they are specific to the signals defined in this document, but their field-level definitions should be added to the data dictionary rather than treated as living only in this file.

Recommended views:

```text
vw_top_growth_products
vw_recent_price_spikes
vw_new_products
vw_collection_gains
vw_collection_losses
```

`vw_sealed_growth` has been removed from this list since `sealed_growth` is deferred, not MVP; it can be added back to both this list and the data dictionary's catalog when that signal is promoted.

These views can later feed dashboards, reports, or a small web app.

---

# Example Signal Records

## Growth Signal

```text
signalDate: 2026-07-04
idProduct: 12345
collectionItemId: null
signalType: growth
signalValue: 30.00
signalStrength: high
lookbackDays: 30
referenceValue: 10.00
currentValue: 13.00
signalDescription: Product increased by 30% over the last 30 days.
```

---

## Price Spike Signal

```text
signalDate: 2026-07-04
idProduct: 67890
collectionItemId: null
signalType: price_spike
signalValue: 33.33
signalStrength: medium
lookbackDays: null
referenceValue: 15.00
currentValue: 20.00
signalDescription: Current trend price is 33.33% above avg30.
```

---

## Collection Gain Signal

```text
signalDate: 2026-07-04
idProduct: 55555
collectionItemId: 8a1e2f90-...
signalType: collection_gain
signalValue: 10.00
signalStrength: high
lookbackDays: null
referenceValue: 20.00
currentValue: 30.00
signalDescription: This collection item is currently estimated 10.00 EUR above its purchase price.
```

Note `collectionItemId` is now populated on this example, unlike the earlier draft — this is the field that actually identifies which physical copy the signal describes.

---

# MVP vs Later Improvements

## MVP

The MVP should include:

```text
growth signal
price spike signal
new product signal
collection gain signal
collection loss signal
missing price data signal
basic BI views
clear documentation
```

The MVP should not include:

```text
sealed growth signal
machine learning
price prediction
automatic buy recommendations
complex scoring models
real-time alerts
```

---

## Later Improvements

Later versions may add:

```text
sealed growth signal
volatility score
momentum score
watchlist alerts
email notifications
product category benchmarks
single vs sealed comparison dashboards
reprint-aware logic
manual signal review
forecasting models after enough history exists
```

---

# Portfolio Value

This analytics signal layer shows that the project is more than data storage.

It demonstrates:

```text
historical price tracking
BI-friendly metric design
explainable analytics
data quality awareness
collection valuation logic at the level of individual physical items
separation of MVP and future features
responsible handling of market signals
```

The project does not claim to predict the Pokémon market from day one.
Instead, it builds the foundation needed for serious analysis later.
