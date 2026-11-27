# INPUT folder guide

Keep original source files local and unchanged. All files under INPUT/ are excluded from GitHub.

## Folder map
- FUNDS/DIRECT/: source NAV workbooks containing Direct-plan data.
- FUNDS/REGULAR/: source NAV workbooks containing Regular-plan data.
- FUNDS/MIXED_PLAN_SOURCE/: original workbooks containing both plans or several source types. Keep these intact; do not duplicate a mixed workbook into both plan folders.
- INDEXES/: PRI and TRI history, including INDEX DATA.xlsx for PRI series.
- STOCKS/: historical stock-price sources.
- PORTFOLIOS/: historical fund portfolio and holdings snapshots.

## Adding new files
1. Copy the original file into the matching INPUT subfolder; preserve its name and contents.
2. For a workbook with both Direct and Regular data, put one copy in FUNDS/MIXED_PLAN_SOURCE/.
3. Put PRI/TRI history in INDEXES/, stock prices in STOCKS/, and holdings disclosures in PORTFOLIOS/.
4. If a new source type does not fit, create a clearly named folder and update the ingestion pipeline before relying on it.
5. After adding data, note the filename, folder, date coverage, and quality issues. Keep all raw data out of commits and PRs.

## Processing
NAV and index preparation:
    python -m financial_analytics.input_pipeline --input-dir INPUT --output-dir OUTPUT/prepared --log-dir logs

Stock-price preparation:
    python -m financial_analytics.stock_price_pipeline --input-file "INPUT/STOCKS/Historical Values 23-01.xlsx" --output-dir "OUTPUT/prepared/stock" --log-dir logs

The pipeline recognizes the former NAV and PRI locations for backward compatibility. The wide multi-section mixed-plan workbook remains an original source and is not automatically converted into canonical NAV data.
