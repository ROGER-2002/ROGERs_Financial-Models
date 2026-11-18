# Initial data dictionary

| Dataset | Grain / key | Required fields | Use |
|---|---|---|---|
| Security master | security ID + effective dates | permanent ID, issuer ID, ticker history, exchange, currency, sector, status | Join prices, fundamentals, holdings |
| Fund master | fund/share-class ID + effective dates | permanent ID, plan/share class, category, inception, base currency, benchmark ID | Fund comparisons and eligibility |
| Price/NAV | instrument ID + observation date | close/NAV, currency, adjustment/corporate-action status, source, received time | Returns and valuation |
| Corporate actions | instrument ID + event ID | event type, ex-date, pay date, split/dividend terms, source | Total return and adjusted prices |
| Fundamentals | issuer/security ID + fiscal period + available timestamp | statement line items, units, period end, publication/availability date | Valuation, quality, growth, leverage |
| Holdings | fund ID + as-of date + security ID | market value, units/weight, cash, currency, source | Exposure, attribution, look-through risk |
| Benchmark | benchmark ID + observation date | return/level, currency, methodology/version | Relative performance and tracking risk |
| Rates/FX/macro | series ID + observation date | value, unit, currency, publication timestamp | Risk-free return, conversion, scenarios |
| Trades/transactions | account/fund + trade ID | order/trade date, security ID, quantity, price, fees, status | Turnover, cost, implementation analysis |

For each source, also define licensed-use restrictions, refresh cadence, late-arriving correction policy, quality thresholds, and lineage fields. Keep effective time (when the fact applies) separate from system/received time (when it became known). Never infer point-in-time availability from fiscal period end alone.
