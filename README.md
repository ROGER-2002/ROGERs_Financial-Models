# Financial Analytics

A practical project for mutual-fund and stock research, portfolio risk analysis, and interactive reporting. The current interface is a local Streamlit prototype. Microsoft Fabric is the planned governed data platform.

## Current status

- The Streamlit app compares a selected fund with its same-category, same-plan peers and shows fund metric cards, interactive charts, a peer heatmap, and CSV/standalone HTML exports.
- The local INPUT folder contains user-supplied mutual-fund NAVs, portfolio holdings, stock-price history, and index series.
- Prepared NAV history and local PRI/TRI benchmark series feed the fund peer analytics app. Original workbooks remain local, and Microsoft Fabric is not connected yet.
- Keep all source, master, generated data, and runtime logs local. INPUT/, MASTER/, OUTPUT/, and logs/ are excluded from GitHub.

## Software and libraries

| Tool | Purpose | Status |
|---|---|---|
| Python 3.11+ | Runs the application and models | Used |
| Visual Studio Code | Edit and run the project locally | Recommended |
| Git and GitHub | Version control, branches, pull requests, and reviews | Used |
| Streamlit | Interactive local research interface | Used |
| pandas | Tabular data preparation and analysis | Used |
| openpyxl | Read supplied Excel workbooks without changing originals | Used |
| PyArrow | Write and read compressed Parquet data for large time series | Used |
| NumPy | Numerical calculations | Used |
| Plotly | Interactive charts and standalone HTML charts | Used |
| Ruff | Python lint and import checks | Used in CI |
| pytest | Automated calculation and data-quality tests | Used in CI |
| GitHub Actions | Runs checks for pushes and pull requests | Used |
| Microsoft Fabric Lakehouse | Managed storage and scalable data engineering | Planned; not connected yet |
| Excel | Inspect and maintain supplied workbook files | Optional desktop application |

The fund dashboard calculates period and since-inception returns, peer ranks, Sharpe, Sortino, tracking error, information ratio, alpha, beta, drawdown, and benchmark-relative drawdown when an index is selected. The index must be selected manually because the supplied Master does not yet contain official fund-to-benchmark mappings. Expense ratio, portfolio turnover, and forward ratio are shown as unavailable until suitable source data and (for Forward Ratio) an agreed definition are supplied. Airflow and Power BI are not part of the current implementation. Fabric remains a planned integration.

## Step-by-step project workflow

1. **Set up the workstation.** Install Python 3.11 or newer, Git, and a code editor such as VS Code. Open the Financial Models project folder in VS Code.
2. **Create a Python environment.** From the project root, create and activate a virtual environment, then install requirements as shown below.
3. **Land source files locally.** Put original provider files in the matching INPUT subfolder; use MIXED_PLAN_SOURCE only when one original workbook contains both Direct and Regular plans or multiple source types. Do not rename or edit originals. Keep confidential or licensed files out of GitHub.
4. **Inspect each new file first.** Record its provider, sheet names, columns, units, frequency, date coverage, identifier, and known gaps before using it.
5. **Build the Master mappings.** Map each security to a stable ID, ticker and exchange, and ISIN where available. Map each fund scheme to its scheme code, ISIN, Direct or Regular plan, Growth or IDCW option, category, and benchmark. Keep effective dates when mappings change.
6. **Standardize and validate.** Convert source headers into agreed column names. Check dates, types, duplicate keys, positive prices and NAVs, and OHLC relationships. In the stock history matrix, #N/A means a price observation is unavailable for that date, often before the stock's first available history. Keep it missing; never replace it with zero or forward-fill it. Keep source rows unchanged and log rejected records in logs/.
7. **Store trusted data.** During local development, keep raw files in INPUT/ and curated mappings in MASTER/. The local preparation pipeline reads the PRI series from `INPUT/INDEXES/INDEX DATA.xlsx` and supported daily TRI workbooks from `INPUT/INDEXES/`. Store generated datasets and reports in OUTPUT/, and script activity logs in logs/. The planned Fabric flow is Bronze for raw landed data, Silver for cleaned and validated data, and Gold for model-ready tables. Fabric is not connected in the current prototype.
8. **Build analytics in stages.** The current fund module compares funds within the same category and plan type. Direct and Regular plans are never placed in the same peer group. Benchmark-relative metrics need a selected index; supplied index series include PRI, so dividend reinvestment treatment should be considered. Expense-ratio and turnover analysis need those scheme-level inputs. Holdings exposures, stock valuation, forecasts, and portfolio optimization can follow after their data and validation are ready.
9. **Create reports.** Use Streamlit for interactive filters and tables, Plotly for charts, and HTML export for shareable snapshots. Save generated results in OUTPUT/. Show the as-of date, benchmark, units, methodology, and data limitations in every report.
10. **Review changes safely.** Work on a feature branch, open a pull request, review the diff, and let GitHub Actions run Ruff, pytest, and compile checks before merging. Never add INPUT/, MASTER/, OUTPUT/, or logs/ files to a pull request.

## Run locally

From PowerShell in the project root:

    python -m venv .venv
    .\.venv\Scripts\Activate.ps1
    python -m pip install -r requirements.txt
    python -m financial_analytics.input_pipeline --input-dir INPUT --output-dir OUTPUT/prepared --log-dir logs
    python -m financial_analytics.peer_master --nav-file OUTPUT/prepared/fund_nav_history.csv --master-dir MASTER
    python -m financial_analytics.peer_performance
    streamlit run app.py
    python -m financial_analytics.stock_price_pipeline --input-file "INPUT/STOCKS/Historical Values 23-01.xlsx" --output-dir "OUTPUT/prepared/stock" --log-dir logs

For development checks:

    python -m pip install -e ".[dev]"
    ruff check .
    pytest
    python -m compileall -q app.py src

## Project layout

- app.py - Streamlit entry point.
- src/financial_analytics/ - reusable calculations and data-quality code.
- src/financial_analytics/fund_metrics.py - monthly fund return, peer-rank, and risk calculations.
- tests/ - automated tests.
- configs/ - safe example configuration; never store secrets here.
- docs/ - architecture, data definitions, intake guide, and roadmap.
- .github/workflows/ - automated pull-request checks.
- INPUT/FUNDS/DIRECT/ and INPUT/FUNDS/REGULAR/ - plan-specific source NAV workbooks.
- INPUT/FUNDS/MIXED_PLAN_SOURCE/ - intact source workbooks containing both plans or mixed source types.
- INPUT/INDEXES/ - PRI and TRI index workbooks.
- INPUT/STOCKS/ - historical stock-price sources.
- INPUT/PORTFOLIOS/ - historical portfolio holdings workbooks.
- MASTER/ - local-only reference, identifier, category crosswalk, and peer-group mappings.
- OUTPUT/ - local-only reports and model outputs.
- logs/ - local-only script activity, warning, and error logs.
- pyproject.toml - project metadata and the authoritative package/development dependency definitions.
- requirements.txt - beginner-friendly install entry point.

## Repository links

See the [implementation roadmap](docs/implementation-roadmap.md), [architecture](docs/architecture.md), [benchmark selection guide](docs/benchmarking.md), [data intake guide](docs/data-intake.md), and [tooling options](docs/tooling-options.md).
