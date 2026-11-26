"""Peer-group performance analytics using prepared monthly mutual-fund NAVs."""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

CATEGORY_ALIASES = {
    "ELSS": "ELSS - Tax Saver Fund",
    "Multi Sector Rotation Fund": "Multi Sector Fund",
    "Thematic": "Multi Sector Fund",
}
RETURN_HORIZONS = (1, 3, 5, 10)
NAV_KEY = ["scheme_id", "plan_type"]


def canonicalize_category(value: Any) -> str:
    """Apply user-confirmed category aliases while preserving other source labels."""
    label = "" if pd.isna(value) else str(value).strip()
    aliases = {source.casefold(): canonical for source, canonical in CATEGORY_ALIASES.items()}
    return aliases.get(label.casefold(), label)


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")


def attach_peer_metadata(nav: pd.DataFrame, master: pd.DataFrame) -> pd.DataFrame:
    """Attach canonical category and plan-separated peer identifiers to NAV rows."""
    required_nav = {"scheme_id", "plan_type", "nav_date", "nav", "is_valid"}
    required_master = {"scheme_id", "plan_type", "scheme_name", "category"}
    missing_nav = required_nav.difference(nav.columns)
    missing_master = required_master.difference(master.columns)
    if missing_nav:
        raise ValueError(f"NAV data is missing columns: {', '.join(sorted(missing_nav))}")
    if missing_master:
        raise ValueError(f"Peer master is missing columns: {', '.join(sorted(missing_master))}")

    nav_frame = nav.copy()
    master_frame = master.copy()
    for frame in (nav_frame, master_frame):
        frame["scheme_id"] = frame["scheme_id"].astype("string").str.strip()
        frame["plan_type"] = frame["plan_type"].astype("string").str.strip().str.title()
    if "source_category" not in master_frame:
        master_frame["source_category"] = master_frame["category"].astype("string").str.strip()
    master_frame["category"] = master_frame["category"].map(canonicalize_category)
    master_frame["peer_group_id"] = master_frame.apply(
        lambda row: f"{_slug(row['category'])}__{_slug(row['plan_type'])}", axis=1
    )
    master_frame["peer_group_name"] = master_frame.apply(
        lambda row: f"{row['category']} | {row['plan_type']} peer group", axis=1
    )
    if master_frame.duplicated(NAV_KEY).any():
        raise ValueError("Peer master has duplicate scheme_id and plan_type keys.")

    master_columns = [
        "scheme_id",
        "plan_type",
        "scheme_code",
        "scheme_isin",
        "scheme_name",
        "source_category",
        "category",
        "peer_group_id",
        "peer_group_name",
    ]
    master_columns = [column for column in master_columns if column in master_frame.columns]
    nav_frame["nav_date"] = pd.to_datetime(nav_frame["nav_date"], errors="coerce")
    nav_frame["nav"] = pd.to_numeric(nav_frame["nav"], errors="coerce")
    valid = nav_frame["is_valid"].astype(str).str.casefold().isin({"true", "1", "yes"})
    nav_frame = nav_frame.loc[valid & nav_frame["nav"].gt(0) & nav_frame["nav_date"].notna()].copy()
    if nav_frame.duplicated(NAV_KEY + ["nav_date"]).any():
        raise ValueError("NAV data has duplicate scheme, plan, and date keys.")

    merged = nav_frame.merge(
        master_frame[master_columns],
        on=NAV_KEY,
        how="left",
        validate="many_to_one",
        indicator=True,
        suffixes=("_nav", ""),
    )
    unmatched = merged["_merge"].ne("both")
    if unmatched.any():
        examples = merged.loc[unmatched, "scheme_id"].drop_duplicates().head(5).tolist()
        raise ValueError(
            f"{int(unmatched.sum())} NAV rows do not match MASTER; examples: {examples}"
        )
    return merged.drop(columns="_merge").sort_values(NAV_KEY + ["nav_date"]).reset_index(drop=True)


def load_peer_data(nav_path: Path, master_path: Path) -> pd.DataFrame:
    """Load prepared NAV history and the local scheme peer master."""
    nav = pd.read_csv(nav_path, dtype={"scheme_id": "string", "plan_type": "string"})
    master = pd.read_csv(master_path, dtype={"scheme_id": "string", "plan_type": "string"})
    return attach_peer_metadata(nav, master)


def _point_at_or_before(
    series: pd.Series, target: pd.Timestamp, tolerance_days: int
) -> tuple[pd.Timestamp, float] | None:
    available = series.loc[series.index <= target]
    if available.empty:
        return None
    observed_date = pd.Timestamp(available.index[-1])
    if (target - observed_date).days > tolerance_days:
        return None
    return observed_date, float(available.iloc[-1])


def _safe_median(values: pd.Series) -> float:
    available = values.dropna()
    return float(available.median()) if not available.empty else float("nan")


def peer_performance_table(
    data: pd.DataFrame,
    category: str,
    plan_type: str,
    *,
    as_of_date: str | pd.Timestamp | None = None,
    endpoint_tolerance_days: int = 10,
    start_tolerance_days: int = 10,
    minimum_risk_months: int = 24,
) -> pd.DataFrame:
    """Calculate horizon returns and three-year risk for one category-plan peer group."""
    group = data.loc[
        data["category"].eq(canonicalize_category(category))
        & data["plan_type"].eq(str(plan_type).title())
    ].copy()
    if group.empty:
        return pd.DataFrame()

    latest_available = group["nav_date"].max().normalize()
    as_of = (
        min(pd.Timestamp(as_of_date).normalize(), latest_available)
        if as_of_date is not None
        else latest_available
    )
    group = group.loc[group["nav_date"] <= as_of]
    records: list[dict[str, Any]] = []
    for scheme_id, rows in group.groupby("scheme_id", sort=False):
        rows = rows.sort_values("nav_date").drop_duplicates("nav_date", keep="last")
        series = rows.set_index("nav_date")["nav"].astype(float)
        endpoint = _point_at_or_before(series, as_of, endpoint_tolerance_days)
        if endpoint is None:
            continue
        end_date, end_nav = endpoint
        info = rows.iloc[-1]
        record: dict[str, Any] = {
            "scheme_id": scheme_id,
            "scheme_isin": info.get("scheme_isin", scheme_id),
            "scheme_code": info.get("scheme_code", ""),
            "scheme_name": info.get("scheme_name", ""),
            "source_category": info.get("source_category", info.get("category", "")),
            "category": canonicalize_category(info["category"]),
            "plan_type": str(info["plan_type"]).title(),
            "peer_group_id": info.get("peer_group_id", ""),
            "as_of_date": end_date.date().isoformat(),
            "latest_nav_date": end_date.date().isoformat(),
            "days_stale": (as_of - end_date).days,
            "nav_observations": len(series),
            "first_nav_date": series.index.min().date().isoformat(),
        }
        for years in RETURN_HORIZONS:
            target = as_of - pd.DateOffset(years=years)
            start = _point_at_or_before(series, target, start_tolerance_days)
            value = np.nan
            if start is not None:
                start_date, start_nav = start
                elapsed_days = (end_date - start_date).days
                if start_nav > 0 and end_nav > 0 and elapsed_days > 0:
                    value = (end_nav / start_nav) ** (1 / years) - 1
            record[f"cagr_{years}y"] = float(value)

        risk_start = _point_at_or_before(
            series, as_of - pd.DateOffset(years=3), start_tolerance_days
        )
        volatility = drawdown = np.nan
        if risk_start is not None:
            risk_start_date, _ = risk_start
            path = series.loc[(series.index >= risk_start_date) & (series.index <= end_date)]
            monthly_returns = path.pct_change().dropna()
            if len(monthly_returns) >= minimum_risk_months:
                volatility = float(monthly_returns.std(ddof=1) * np.sqrt(12))
                wealth = (1 + monthly_returns).cumprod()
                wealth = pd.concat([pd.Series([1.0], index=[risk_start_date]), wealth])
                drawdown = float((wealth / wealth.cummax() - 1).min())
        record["annualized_volatility_3y"] = volatility
        record["max_drawdown_3y"] = drawdown
        records.append(record)

    summary = pd.DataFrame(records)
    if summary.empty:
        return summary
    summary["peer_count"] = len(summary)
    for years in RETURN_HORIZONS:
        metric = f"cagr_{years}y"
        summary[f"peer_median_{metric}"] = _safe_median(summary[metric])
        summary[f"peer_count_{years}y"] = int(summary[metric].notna().sum())
        summary[f"peer_percentile_{years}y"] = (
            summary[metric].rank(method="average", pct=True) * 100
        )
    summary["peer_median_annualized_volatility_3y"] = _safe_median(
        summary["annualized_volatility_3y"]
    )
    summary["peer_median_max_drawdown_3y"] = _safe_median(summary["max_drawdown_3y"])
    return summary.sort_values(["cagr_3y", "scheme_name"], ascending=[False, True]).reset_index(
        drop=True
    )


def peer_growth_history(
    data: pd.DataFrame,
    category: str,
    plan_type: str,
    selected_scheme_id: str,
    *,
    as_of_date: str | pd.Timestamp | None = None,
    years: int = 5,
    start_tolerance_days: int = 10,
) -> pd.DataFrame:
    """Return a selected fund and same-plan peer median, each rebased to 100."""
    group = data.loc[
        data["category"].eq(canonicalize_category(category))
        & data["plan_type"].eq(str(plan_type).title())
    ].copy()
    if group.empty:
        return pd.DataFrame()
    latest = group["nav_date"].max().normalize()
    as_of = min(pd.Timestamp(as_of_date).normalize(), latest) if as_of_date else latest
    target = as_of - pd.DateOffset(years=years)
    histories: dict[str, pd.Series] = {}
    for scheme_id, rows in group.loc[group["nav_date"] <= as_of].groupby("scheme_id"):
        series = (
            rows.sort_values("nav_date").drop_duplicates("nav_date").set_index("nav_date")["nav"]
        )
        start = _point_at_or_before(series, target, start_tolerance_days)
        if start is None:
            continue
        start_date, start_nav = start
        path = series.loc[(series.index >= start_date) & (series.index <= as_of)].astype(float)
        if start_nav > 0 and not path.empty:
            histories[str(scheme_id)] = path / start_nav * 100
    if selected_scheme_id not in histories:
        return pd.DataFrame()
    panel = pd.concat(histories, axis=1).sort_index()
    selected = panel[selected_scheme_id].rename("Selected fund")
    peers = panel.drop(columns=[selected_scheme_id], errors="ignore")
    peer_median = peers.apply(_safe_median, axis=1).rename("Peer median")
    return pd.concat([selected, peer_median], axis=1).reset_index(names="nav_date")


def all_peer_performance(
    data: pd.DataFrame, *, as_of_date: str | pd.Timestamp | None = None
) -> pd.DataFrame:
    """Calculate performance for every available category and plan group."""
    pieces = []
    pairs = data[["category", "plan_type"]].drop_duplicates().sort_values(["category", "plan_type"])
    for row in pairs.itertuples(index=False):
        result = peer_performance_table(data, row.category, row.plan_type, as_of_date=as_of_date)
        if not result.empty:
            pieces.append(result)
    return pd.concat(pieces, ignore_index=True) if pieces else pd.DataFrame()


def _write_summary_notes(path: Path, results: pd.DataFrame, as_of: str) -> None:
    categories = results["category"].nunique() if not results.empty else 0
    groups = (
        results[["category", "plan_type"]].drop_duplicates().shape[0] if not results.empty else 0
    )
    notes = [
        "# Fund peer performance output",
        "",
        f"- As-of date: {as_of}",
        f"- Fund-plan rows: {len(results):,}",
        f"- Categories: {categories:,}",
        f"- Separate category-plan peer groups: {groups:,}",
        "- Source values: supplied monthly Adjusted NAV history.",
        "- Direct and Regular schemes are evaluated in separate peer groups.",
        "",
        "## Metrics",
        "",
        "- CAGR: endpoint NAV growth annualized over 1, 3, 5, or 10 years.",
        (
            "- Volatility: sample standard deviation of monthly NAV returns over 3 years, "
            "annualized by square-root of 12."
        ),
        ("- Maximum drawdown: largest peak-to-trough decline over the available 3-year NAV path."),
        (
            "- Peer percentile: percentile rank within the same category and plan; "
            "higher return percentile means stronger relative return."
        ),
        "",
        "## Limits",
        "",
        (
            "- The source labels values as Adjusted NAV; distribution and adjustment "
            "treatment has not been independently confirmed."
        ),
        "- The current source set may contain survivorship or historical coverage bias.",
        (
            "- This first stage excludes benchmark-relative measures, fees, taxes, "
            "and transaction costs."
        ),
        (
            "- Historical performance describes supplied data. It is not a forecast "
            "or investment recommendation."
        ),
        "",
    ]
    path.write_text("\n".join(notes), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--nav-file", type=Path, default=Path("OUTPUT/prepared/fund_nav_history.csv")
    )
    parser.add_argument("--master-file", type=Path, default=Path("MASTER/FUND_PEER_MASTER.csv"))
    parser.add_argument("--output-dir", type=Path, default=Path("OUTPUT/analytics"))
    parser.add_argument("--as-of", type=str, default=None)
    args = parser.parse_args()

    data = load_peer_data(args.nav_file, args.master_file)
    results = all_peer_performance(data, as_of_date=args.as_of)
    if results.empty:
        raise RuntimeError("No peer performance metrics could be calculated from supplied NAVs.")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    as_of = args.as_of or data["nav_date"].max().date().isoformat()
    csv_path = args.output_dir / "fund_peer_performance.csv"
    notes_path = args.output_dir / "peer_performance_notes.md"
    results.to_csv(csv_path, index=False, date_format="%Y-%m-%d", encoding="utf-8")
    _write_summary_notes(notes_path, results, as_of)
    print(f"Metrics: {csv_path}")
    print(f"Methodology and limits: {notes_path}")
    print(
        f"Funds: {results['scheme_id'].nunique():,}; peer groups: "
        f"{results[['category', 'plan_type']].drop_duplicates().shape[0]:,}; as of: {as_of}"
    )


if __name__ == "__main__":
    main()
