# Financial Analytics

A practical project for mutual-fund and stock research, portfolio risk analysis, and interactive reporting. The current interface is a local Streamlit prototype. Microsoft Fabric is the planned governed data platform.

## Current status

- The Streamlit app still runs on clearly labelled synthetic demonstration data.
- The local Input folder contains user-supplied mutual-fund NAVs, portfolio holdings, stock-price history, and index series.
- Those workbooks are not yet connected to the app or Fabric. Outputs from the demo are not investment research or recommendations.
- Keep all source, master, and generated data local. Input/, Master/, and Output/ are excluded from GitHub.

## Software and libraries

| Tool | Purpose | Status |
|---|---|---|
| Python 3.11+ | Runs the application and models | Used |
| Visual Studio Code | Edit and run the project locally | Recommended |
| Git and GitHub | Version control, branches, pull requests, and reviews | Used |
| Streamlit | Interactive local research interface | Used |
| pandas | Tabular data preparation and analysis | Used |
| NumPy | Numerical calculations | Used |
| Plotly | Interactive charts and standalone HTML charts | Used |
| Ruff | Python lint and import checks | Used in CI |
| pytest | Automated calculation and data-quality tests | Used in CI |
| GitHub Actions | Runs checks for pushes and pull requests | Used |
| Microsoft Fabric Lakehouse | Managed storage and scalable data engineering | Planned; not connected yet |
| Excel | Inspect and maintain supplied workbook files | Optional desktop application |

Airflow and Power BI are not part of the current implementation. They can be evaluated later if orchestration or dashboard requirements call for them. The current reporting direction is Streamlit plus downloadable HTML.

## Step-by-step project workflow

1. **Set up the workstation.** Install Python 3.11 or newer, Git, and a code editor such as VS Code. Open the Financial Models project folder in VS Code.
2. **Create a Python environment.** From the project root, create and activate a virtual environment, then install requirements as shown below.
3. **Land source files locally.** Put original provider files in Input/. Do not rename or edit originals. Keep confidential or licensed files out of GitHub.
4. **Inspect each new file first.** Record its provider, sheet names, columns, units, frequency, date coverage, identifier, and known gaps before using it.
5. **Build the Master mappings.** Map each security to a stable ID, ticker and exchange, and ISIN where available. Map each fund scheme to its scheme code, ISIN, Direct or Regular plan, Growth or IDCW option, category, and benchmark. Keep effective dates when mappings change.
6. **Standardize and validate.** Convert source headers into agreed column names. Check dates, types, duplicate keys, positive prices and NAVs, and OHLC relationships. Treat spreadsheet errors such as #N/A as missing observations; do not fill them blindly. Keep source rows unchanged and log rejected records.
7. **Store trusted data.** During local development, keep raw files in Input/ and curated mappings in Master/. The planned Fabric flow is Bronze for raw landed data, Silver for cleaned and validated data, and Gold for model-ready tables. Fabric is not connected in the current prototype.
8. **Build analytics in stages.** The current app demonstrates peer returns and risk metrics. Next, connect the supplied NAV and benchmark histories, then add holdings exposures and concentration. Add stock valuation, technical indicators, forecasts, and constrained portfolio optimization only after the related data and validation are ready.
9. **Create reports.** Use Streamlit for interactive filters and tables, Plotly for charts, and HTML export for shareable snapshots. Save generated results in Output/. Show the as-of date, benchmark, units, methodology, and data limitations in every report.
10. **Review changes safely.** Work on a feature branch, open a pull request, review the diff, and let GitHub Actions run Ruff, pytest, and compile checks before merging. Never add Input/, Master/, or Output/ files to a pull request.

## Run locally

From PowerShell in the project root:

    python -m venv .venv
    .\.venv\Scripts\Activate.ps1
    python -m pip install -r requirements.txt
    streamlit run app.py

For development checks:

    python -m pip install -e ".[dev]"
    ruff check .
    pytest
    python -m compileall -q app.py src

## Project layout

- app.py - Streamlit entry point.
- src/financial_analytics/ - reusable calculations and data-quality code.
- tests/ - automated tests.
- configs/ - safe example configuration; never store secrets here.
- docs/ - architecture, data definitions, intake guide, and roadmap.
- .github/workflows/ - automated pull-request checks.
- Input/ - local-only original source workbooks.
- Master/ - local-only reference and identifier mappings.
- Output/ - local-only reports and model outputs.
- pyproject.toml - project metadata and the authoritative package/development dependency definitions.
- requirements.txt - beginner-friendly install entry point.

## Repository links

See the [implementation roadmap](docs/implementation-roadmap.md), [architecture](docs/architecture.md), [data intake guide](docs/data-intake.md), and [tooling options](docs/tooling-options.md).
