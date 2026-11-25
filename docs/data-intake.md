# Financial data intake guide

Use this guide to prepare your supplied files before connecting them to the analytics modules. The project does not download, scrape, or invent real market data. Keep original files unchanged and retain their source, license, and as-of details.

## 1. Local folder layout and GitHub boundary

Keep all real input, master, and generated output files on your local machine:

- `INPUT/` — original source datasets; keep the provided folder structure and files unchanged.
- `MASTER/` — stable security, scheme, benchmark, category, and sector mappings used to join sources.
- `OUTPUT/` — generated reports, model outputs, and backtest results.
- `logs/` — local script activity, warning, and error records.

These folders are ignored by Git and are not stored in the GitHub repository. Never commit account details, client holdings, licensed files, credentials, or confidential research. Preserve an untouched copy of each source file; perform cleanup and transformations on separate working copies. Record the provider, file name, extraction time, coverage dates, license, and transformations.

## 2. Preferred first batch

Start with a small representative sample (a few instruments/funds and 1–2 years if available). Include:

1. Security daily prices and broad-market benchmark prices.
2. Mutual fund NAV observations with Direct/Regular and Growth/IDCW identity.
3. A master mapping for symbols, exchange, security identifiers, benchmark membership, and scheme identifiers.
4. Optional corporate actions and fund benchmark/category mappings.

A sample is enough to map headers and formats before loading a full history. Excel, CSV, and Parquet can all be adapted. Do not rename or edit the original files just to match the examples below.

## 3. Canonical price history

The first validation module accepts a table with:

| Column | Required | Meaning |
|---|---:|---|
| `instrument_id` | Yes | Stable security or index key, preferably mapped to an exchange-qualified identifier |
| `date` | Yes | Observation date |
| `close` | Yes | Closing value/price |
| `open`, `high`, `low` | Optional | Daily OHLC values; if all four OHLC columns exist, their relationships are checked |
| `volume` | Optional | Non-negative traded quantity |

The supplied stock-price workbook is a wide daily matrix: one date column and one close-price column per stock. `#N/A` means a price is unavailable on that date, including dates before the stock's available price history. Preserve it as missing; never convert it to zero or forward-fill it. When calculating returns, do not bridge an internal missing observation without an explicit, documented rule.

The validator also accepts custom identifier and date column names. Map source headers to canonical names in an ingestion adapter after we inspect your files. Prices must be positive. Corporate-action treatment (raw versus adjusted) must be explicit and consistent; the validator does not adjust prices.

## 4. Canonical mutual-fund NAV

The validator accepts:

| Column | Required | Meaning |
|---|---:|---|
| `scheme_id` | Yes | Stable identifier that distinguishes scheme, plan, and option |
| `date` | Yes | NAV date |
| `nav` | Yes | Per-unit NAV |

Direct and Regular plans or Growth and IDCW options must have distinct scheme identifiers (or be mapped to one). Do not combine them just because display names are similar.

## 5. Checks and interpretation

Call `validate_price_history(frame)` or `validate_fund_nav(frame)` after mapping source columns. The result contains a normalized copy, blocking `errors`, non-blocking `warnings`, and an `is_valid` flag.

- Errors include missing required fields, invalid dates or numbers, non-positive prices/NAVs, duplicate instrument/date keys, inconsistent OHLC relationships, and negative volume.
- Warnings identify observations that are not sorted by identifier and date.
- Validation reports findings; it does not drop rows, impute values, reorder the source, or resolve corporate actions.

Resolve errors in the source mapping or a documented cleaning step. Keep a reject log and reconcile row counts before promoting records from a raw landing area into a curated dataset.

## 6. Official benchmark reference and index variants

Use the [Nifty Indices Historical Data page](https://www.niftyindices.com/reports/historical-data) to distinguish historical price-index data, valuation metrics (P/E, P/B, and dividend yield), and total-return index values. Keep the selected index variant and report type in the data catalog.

- **Nifty Midcap 150** represents 150 companies ranked 101–250 within Nifty 500 ([official index page](https://www.niftyindices.com/indices/equity/broad-based-indices/nifty-midcap-150)).
- **Nifty LargeMidcap 250** combines 100 Nifty 100 companies and 150 Nifty Midcap 150 companies, with a 50% aggregate weight for each group ([official index page](https://www.niftyindices.com/indices/equity/broad-based-indices/nifty-largemidcap-250)).
- In the supplied files, `INDEX DATA.xlsx` contains four PRIs, including the Nifty Midcap 150; `NIFTY LargeMidcap 250 - TRI.xlsx` is the separate LargeMidcap 250 total-return series.

## 7. Next implementation step

Continue documenting each source's real header names, keys, frequency, coverage, null conventions, units, license, and update schedule. The current local adapter standardizes supported NAV and benchmark sheets; a streaming adapter for the wide stock matrix and source-specific holdings reconciliation are the next ingestion steps. Build master-data joins and Fabric Bronze/Silver/Gold loads around the verified formats. This avoids baking assumptions from a synthetic sample into the production data model.
