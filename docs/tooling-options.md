# Tooling options: free to install vs. free to operate

“Free” can mean no software license fee. It does not necessarily include hosting, compute, storage, support, or staff time. Review each tool's license, deployment model, security posture, and vendor terms with the organization before using it with licensed or confidential data.

## Recommended starting stack

| Need | Suggested tool | Why / fit | Cost boundary |
|---|---|---|---|
| Code editor | Visual Studio Code | Python, notebooks, Git, and extensions in one editor | Free editor; extensions and enterprise management may have separate terms |
| Source control | Git + GitHub | Branches, PRs, review history, issues, and CI | Git is free; GitHub plan and Actions usage allowances vary |
| Python app | Streamlit | Build the interactive research interface in Python | Open-source library; private hosting and compute are separate |
| Interactive HTML | Plotly | Charts in Streamlit and downloadable HTML snapshots | Open-source Python library; report hosting is separate |
| Fabric notebook preview | `displayHTML()` | Preview HTML output within a Fabric notebook session | Notebook/Spark execution consumes Fabric capacity; this is not a standalone report portal |
| Local analytics | DuckDB + Parquet | Query sample or approved local extracts using SQL without running a database server | Free/open source; local disk and machine resources still apply |
| Quality checks | pytest + Pandera | Test calculation logic and validate input dataframe schemas | Open-source packages; team maintenance still required |
| Code quality | Ruff + pre-commit | Fast lint/format checks locally and in CI | Open-source tools |
| Analytics storage | Microsoft Fabric Lakehouse / OneLake | Shared governed lakehouse, Spark, pipelines, and data products | Fabric capacity/licensing is not a free open-source component |
| Fabric model tracking | MLflow in Fabric | Record model runs, parameters, metrics, and artifacts | MLflow is open source; Fabric compute/storage may incur cost |

## Optional tools as the platform grows

| Tool | Use it when | Trade-off |
|---|---|---|
| Apache Airflow | Jobs span Fabric, APIs, on-prem systems, and other clouds, and need centralized scheduled orchestration | Powerful and extensible, but requires deployment, upgrades, monitoring, and operational ownership. It is a batch workflow orchestrator. [Official docs](https://airflow.apache.org/docs/) |
| Dagster | You want a Python-first orchestrator with strong asset-oriented workflows | Another scheduler to operate; compare against Fabric pipelines and Airflow before choosing |
| dbt Core | Transformations are mostly SQL and you want modular models, dependencies, and SQL-focused checks | Adds a separate transformation workflow; confirm adapter support for the selected Fabric SQL endpoint |
| Power BI Desktop | Analysts want a quick local visual check or a secondary internal report | Free for authoring and personal use. Sharing via the Power BI service generally needs Pro/PPU or qualifying capacity; check current tenant licensing. [Desktop download](https://learn.microsoft.com/en-us/power-bi/fundamentals/desktop-get-the-desktop), [license capabilities](https://learn.microsoft.com/en-us/power-bi/fundamentals/service-features-license-type) |
| Great Expectations or Soda Core | You need richer data-quality checks, documentation, and failure reporting | Adds configuration and operational overhead; start with focused Pandera/SQL checks if that meets the need |
| Optuna | You need controlled hyperparameter search for selected predictive models | Use only after defining time-aware validation and baseline performance |
| CVXPY | You need transparent portfolio optimization with explicit constraints | Solver choice and licensing vary; document solver and constraint assumptions |
| Docker | You need a repeatable local/CI runtime or container-based deployment | Container tooling is free to use; registry, compute, and enterprise features may cost |
| Fabric Apps static hosting (preview) | You want protected static HTML/CSS/JS served at a Fabric app URL and already have Fabric capacity | Fabric Apps requires assigned capacity; static hosting reads, writes, and storage consume CUs. Check preview region/tenant availability and capacity usage before adopting. [Hosting](https://learn.microsoft.com/en-us/fabric/apps/hosting), [pricing and capacity usage](https://learn.microsoft.com/en-us/fabric/apps/pricing) |

## Power BI Free: the practical boundary

Power BI Desktop can be used at no cost to create local reports. The free Power BI service experience is mainly for personal use; collaboration and sharing typically need Pro/PPU unless the content is hosted on qualifying capacity. Therefore, use Desktop as an optional analyst tool, not as the foundation for shared production reporting. The platform's primary user experience remains Streamlit plus generated HTML, as requested.

## Airflow or Fabric pipelines?

Do not add Airflow automatically just because it is free software. For a Fabric-centered solution, start with Fabric Data Factory pipelines and notebooks. Add Airflow only when there is a clear cross-platform orchestration requirement or an existing Airflow operating capability. Assign each job one scheduler to prevent duplicate runs and unclear ownership.

## Data and security rule

Do not commit licensed market data, portfolio holdings, generated client reports, credentials, or secrets to GitHub. Store data in approved governed storage. Use synthetic or specifically approved fixtures in developer machines and CI. Free public hosting services are not suitable for confidential investment data unless the organization's security team has approved the exact configuration.

## Cost-conscious HTML delivery

1. Generate a dated, self-contained HTML file only when a report is requested or a scheduled report run completes.
2. Save or distribute it through an existing approved access-controlled location; a static file needs no continuously running app.
3. Use `displayHTML()` in Fabric notebooks for analyst preview when the job is already running there.
4. Consider Fabric Apps static hosting only when a persistent shared URL and interactive front end are required and existing capacity makes the incremental CU use acceptable. This preview option is not automatically zero-cost.
5. Avoid including unnecessary external JavaScript/CDN dependencies in archived reports; embedded assets make the report more portable and reduce dependency on network access.
