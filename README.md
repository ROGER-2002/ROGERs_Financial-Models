# Financial Analytics

A starter platform for investment research, peer comparison, portfolio risk analysis, and interactive reporting. It is designed to grow from a local Streamlit prototype into a governed Microsoft Fabric solution.

> **Demo limitation:** the app currently uses deterministic synthetic NAV data for its demonstration. Files in the local `Input/` folder are staged source data and are not yet connected to the app. Do not use the demo output for investment decisions.

## Local data folders

These folders are for local files and are ignored by Git:

- `Input/` — original source datasets. Keep provider files unchanged.
- `Master/` — validated security, fund, benchmark, category, and sector mappings.
- `Output/` — generated reports, model results, and backtest outputs.

Do not put confidential, client, credential, or unlicensed data in GitHub. The repository contains code and documentation, not the contents of these local folders.

## Quick start

Requires Python 3.11 or later.

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
streamlit run app.py
```

The `requirements.txt` file installs the local project and runtime dependencies declared in `pyproject.toml`. To install developer tools for checks and tests:

```powershell
python -m pip install -e ".[dev]"
ruff check .
pytest
```

## Project map

- `app.py` — Streamlit user interface.
- `src/financial_analytics/` — reusable data-quality and financial calculation modules.
- `tests/` — automated unit tests.
- `docs/` — architecture, data definitions, intake guidance, and implementation roadmap.
- `configs/` — example environment configuration; never store secrets here.
- `.github/workflows/` — pull-request quality checks.
- `pyproject.toml` — package metadata, runtime dependencies, and developer tooling.
- `requirements.txt` — simple local installation entry point.
- `Input/`, `Master/`, `Output/` — local-only data folders; excluded from GitHub.

## Current capabilities

- Compare mutual-fund peers over a selected period.
- Calculate return and risk measures such as CAGR, volatility, Sharpe, Sortino, tracking error, information ratio, and maximum drawdown.
- Review interactive historical charts and download an HTML snapshot.
- Validate canonical market-price and mutual-fund NAV tables before model use.

## Next development steps

1. Map the supplied source workbook layouts to canonical data tables.
2. Build repeatable ingestion and reconciliation into Microsoft Fabric.
3. Connect validated data to the app and reports.
4. Add holdings-based exposures, mandate constraints, walk-forward model validation, monitoring, and approvals.

See the [implementation roadmap](docs/implementation-roadmap.md), [architecture](docs/architecture.md), [data intake guide](docs/data-intake.md), and [tooling options](docs/tooling-options.md).
