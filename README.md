# AMC Financial Analytics

A starter platform for investment research, peer comparison, portfolio risk analysis, and interactive reporting. The repository is designed to grow from a local Streamlit prototype into a governed Microsoft Fabric solution.

> **Demo data only:** the current app creates deterministic synthetic mutual fund NAVs. These are illustrative and must not be used to make investment decisions. Connect only approved, licensed data before any real use.

## Run locally

1. Install Python 3.11 or later.
2. Create and activate a virtual environment.
3. Install the project: `python -m pip install -e .`
4. Start the app: `streamlit run app.py`

The app lets you select a peer category and date range, compare risk and return measures, inspect a time series, and download an interactive HTML snapshot.

## Repository map

- `app.py` — Streamlit user interface.
- `src/amc_analytics/` — reusable data and financial calculation modules.
- `docs/` — architecture, data definitions, and staged implementation roadmap.
- `configs/` — environment configuration examples; never put secrets here.
- `notebooks/` — exploratory analysis and Fabric notebook source.
- `reports/` — report templates and generated report instructions; do not commit confidential outputs.
- `.github/workflows/` — pull-request quality checks.

## Next implementation steps

1. Confirm investment use case, jurisdiction, data rights, user roles, and business definitions.
2. Replace the demo generator with a licensed, point-in-time data feed.
3. Implement Bronze/Silver/Gold tables in Fabric and add schema and reconciliation checks.
4. Add portfolio holdings, benchmark, transaction cost, and mandate constraints.
5. Add model cards, walk-forward validation, monitoring, approvals, and controlled deployment.

See [the implementation roadmap](docs/implementation-roadmap.md) and [architecture](docs/architecture.md).
For optional free/open-source tools and where they fit, see [tooling options](docs/tooling-options.md).
