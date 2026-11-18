# End-to-end implementation roadmap

## Phase 0 — Product and control definition

Agree on the first fund manager workflow, supported asset classes, jurisdiction, users, report frequency, benchmark conventions, investment horizon, allowable decisions, data licensing, retention, and access policy. Define all key metrics in a glossary and appoint business and technical owners.

## Phase 1 — Local foundation

Use Python 3.11+, GitHub, a virtual environment, Streamlit, Pandas, NumPy, and Plotly. Keep reusable calculations in `src/`, UI code in `app.py`, documentation in `docs/`, and configuration examples in `configs/`. Start with this synthetic-data peer comparison; label it clearly and keep it out of investment workflows.

Optional free tools for this phase: VS Code for editing, DuckDB for local SQL exploration over Parquet/CSV, Ruff for linting, pytest for calculation tests, and GitHub Actions for pull-request checks (usage allowances depend on repository plan and runner type). Power BI Desktop is also free for personal report authoring and quick data QA; it is optional and does not replace the Streamlit/HTML product direction.

## Phase 2 — Master data and source onboarding

Select licensed sources for prices/NAV, corporate actions, fundamentals, holdings, benchmarks, rates/FX, and internal accounting or research data. Build masters for security, issuer, share class, fund, benchmark, exchange, currency, sector, and calendar. Record identifier history, data owner, effective date, received timestamp, rights, refresh cadence, and quality status. Preserve delisted securities and point-in-time fundamental availability for unbiased historical research.

## Phase 3 — Fabric ingestion and data quality

Create a development Fabric workspace and OneLake lakehouse. Use Data Factory pipelines or approved connectors for ingestion, immutable Bronze landing, Spark notebooks for Silver standardization, and Gold data products for research. Add checks for schema drift, duplicate keys, nulls, stale prices, currency mismatches, corporate actions, NAV reconciliation, and expected row counts. Quarantine failures with clear alerts rather than silently dropping them.

Use Fabric's native orchestration when the workload is Fabric-centered. If ingestion and processing must span on-premises systems, other clouds, and several independent platforms, evaluate open-source Apache Airflow or Dagster as an orchestration layer. These are free to install under their open-source licenses; running and operating the services still requires compute, storage, monitoring, and engineering time. Choose one scheduler as the owner for each pipeline.

## Phase 4 — Transparent analytics MVP

Prioritize descriptive analysis before prediction:

1. Returns, benchmark-relative performance, peer ranking, and attribution.
2. Risk: volatility, tracking error, drawdown, concentration, factor and sector exposure.
3. Portfolio construction with mandate constraints and transaction costs.
4. Scenarios and stress tests.
5. Forecasts and stock/fund ranking only after point-in-time datasets and walk-forward evaluation are established.

Candidate tools: `statsmodels` for statistical models; `scikit-learn` and Fabric FLAML for ML baselines; `arch` for volatility models; `cvxpy` or `PyPortfolioOpt` for constrained optimization; MLflow for experiment records. Use packages compatible with the chosen Fabric runtime.

## Phase 5 — Model validation and governance

Specify each target, horizon, eligible universe, decision timestamp, and benchmark. Use chronological walk-forward validation, not random splits. Compare against simple baselines. Include fees, turnover, slippage, liquidity, constraints, and capacity assumptions in portfolio simulations. Track rank quality, calibration/uncertainty, risk-adjusted performance, drawdown, and stability across regimes. Document each model's intended use, data, assumptions, limitations, approvals, and monitoring plan.

## Phase 6 — Reports and user experience

Build Streamlit pages for peer research, portfolio risk, scenarios, and model monitoring. Produce HTML snapshots from shared Python functions for durable review. Include report date, data freshness, filters, metric definitions, peer counts, source lineage, model/version details, missing-data explanations, and uncertainty. Support responsive layout, keyboard access, and print/export workflows. Apply identity-based access to all private data.

## Phase 7 — GitHub collaboration and deployment

- Protect `main`; use short-lived feature branches and pull requests.
- Require review, linked issue/context, and passing automated checks before merge.
- CI should lint/format code, run unit and data-contract checks, and scan dependencies/secrets.
- Use GitHub Actions with least-privilege credentials for approved deployment automation.
- Promote through dev → test → production; parameterize workspace and data locations outside code.
- Version code, schemas, configurations, report templates, and model metadata. Store datasets and trained artifacts in governed storage, not ordinary Git commits.
- Log release ID, data snapshot/version, model version, and report generation run for reproducibility.

## Proposed build order

1. Validate the local peer-comparison prototype with a fund manager.
2. Confirm metric definitions and source/licensing requirements.
3. Add a real, approved data feed and point-in-time master data.
4. Build Fabric Bronze/Silver/Gold and quality monitoring.
5. Connect Streamlit and HTML generation to Gold outputs.
6. Add portfolio constraints, attribution, scenarios, and optimization.
7. Add forecasting/ranking models with model governance and production controls.

No prediction model should be presented as reliably accurate without independent out-of-time evidence and ongoing monitoring. Investment decisions remain subject to the AMC's review and governance process.
