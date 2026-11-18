# Platform architecture

## First version

```text
Licensed providers / approved internal systems
                    ↓
Fabric Data Factory ingestion → Bronze (immutable source extracts)
                    ↓
Fabric notebooks / Spark → Silver (validated, conformed tables)
                    ↓
Gold investment data products → shared Python analytics modules
                              ↙                         ↘
                    Streamlit research app       dated HTML reports
```

The repository currently contains only the Streamlit prototype and synthetic data generator. Fabric connections, hosting, identity, licensing, and production pipelines are future work and require the organization's tenant and security decisions.

For the first stage, keep the local stack light: Python, Streamlit, GitHub, and (optionally) DuckDB for local analytical queries. In the Fabric stage, prefer Fabric pipelines and notebooks for Fabric-native workloads. Add Airflow only if orchestration needs to span multiple platforms or independently managed services; avoid scheduling the same pipeline in both Airflow and Fabric.

## Data layers

- **Bronze:** retain source payload, source identifier, retrieval timestamp, effective timestamp, and ingestion run ID.
- **Silver:** normalize security/fund identifiers, currencies, calendars, units, corporate actions, and fiscal periods; preserve point-in-time history.
- **Gold:** publish investment-ready returns, fundamentals, factor exposures, holdings, benchmarks, and model outputs with documented definitions.

Use Delta tables in OneLake for analytical data. Use a Fabric warehouse or SQL analytics endpoint when SQL-oriented access and curated relational views suit the workload. Store secrets in approved secret management, never in Git.

## Serving the reports

Use generated HTML as the cost-conscious report artifact: calculations run once, then users can download or archive a self-contained snapshot without a continuously running web app. Fabric notebooks can render HTML with `displayHTML()` for analyst preview; for durable reports, write the HTML output to an approved OneLake location or another governed document store. Notebook rendering is a preview surface, not by itself a distribution site.

If users need a shared interactive URL, evaluate Fabric Apps static hosting (currently documented as preview). It can serve static HTML/CSS/JS with protected access, but it requires Fabric capacity, and static-asset reads, writes, and storage consume capacity. Use it only if the organization already has suitable Fabric capacity and the feature is approved for the target region and tenant. Otherwise, prefer generated files in approved existing storage over adding always-on hosting. Streamlit remains an optional richer interactive application, with hosting and compute costs considered separately.

Reports should show as-of time, source lineage, metric definitions, model version, and limitations. A downloaded HTML file does not enforce access controls; keep private reports in approved access-controlled storage.

## Environment separation

Start with separate Fabric development, test, and production workspaces when the organization is ready. Promote code and item metadata through reviewed releases. Do not assume lakehouse contents move with Git: seed, ingest, or otherwise manage data separately in each environment. Keep environment bindings and secrets outside committed source.
