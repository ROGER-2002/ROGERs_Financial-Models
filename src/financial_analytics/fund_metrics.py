"""Monthly mutual-fund performance, risk and peer-rank calculations."""

from __future__ import annotations

import numpy as np
import pandas as pd

UNAVAILABLE_INPUT_METRICS = ("forward_ratio", "expense_ratio", "portfolio_turnover_rate")


def _monthly_series(frame: pd.DataFrame, date_col: str, value_col: str) -> pd.Series:
    values = frame[[date_col, value_col]].copy()
    values[date_col] = pd.to_datetime(values[date_col], errors="coerce")
    values[value_col] = pd.to_numeric(values[value_col], errors="coerce")
    values = values.dropna().sort_values(date_col)
    values = values.drop_duplicates(date_col, keep="last").set_index(date_col)[value_col]
    return values.resample("ME").last().dropna()


def _drawdown(values: pd.Series) -> pd.Series:
    if values.empty:
        return values
    wealth = values / values.iloc[0]
    return wealth / wealth.cummax() - 1.0


def _risk_metrics(
    nav: pd.Series,
    benchmark: pd.Series | None,
    annual_risk_free_rate: float,
) -> dict[str, float]:
    result = {
        key: float("nan")
        for key in (
            "period_return",
            "annualized_return",
            "annualized_volatility",
            "sharpe_ratio",
            "sortino_ratio",
            "tracking_error",
            "information_ratio",
            "alpha",
            "beta",
            "max_drawdown",
            "benchmark_return",
            "drawdown_vs_benchmark",
        )
    }
    if len(nav) < 2 or nav.iloc[0] <= 0:
        return result
    rets = nav.pct_change().dropna()
    if rets.empty:
        return result
    n = len(rets)
    years = n / 12
    cumulative = float(nav.iloc[-1] / nav.iloc[0] - 1)
    annual = float((nav.iloc[-1] / nav.iloc[0]) ** (1 / years) - 1) if years else np.nan
    vol = float(rets.std(ddof=1) * np.sqrt(12)) if n > 1 else np.nan
    rf_month = (1 + annual_risk_free_rate) ** (1 / 12) - 1
    excess = rets - rf_month
    downside = np.minimum(excess.to_numpy(), 0.0)
    downside_dev = float(np.sqrt(np.mean(downside**2) * 12))
    dd = _drawdown(nav)
    result.update(
        {
            "period_return": cumulative,
            "annualized_return": annual,
            "annualized_volatility": vol,
            "sharpe_ratio": (annual - annual_risk_free_rate) / vol if vol and vol > 0 else np.nan,
            "sortino_ratio": (annual - annual_risk_free_rate) / downside_dev
            if downside_dev > 0
            else np.nan,
            "max_drawdown": float(dd.min()),
        }
    )
    if benchmark is not None:
        joined = pd.concat(
            [rets.rename("fund"), benchmark.pct_change().rename("benchmark")], axis=1
        ).dropna()
        if not joined.empty:
            bm = benchmark.reindex(nav.index).dropna()
            if len(bm) > 1:
                result["benchmark_return"] = float(bm.iloc[-1] / bm.iloc[0] - 1)
                result["drawdown_vs_benchmark"] = float(
                    result["max_drawdown"] - _drawdown(bm).min()
                )
            active = joined["fund"] - joined["benchmark"]
            te = float(active.std(ddof=1) * np.sqrt(12)) if len(active) > 1 else np.nan
            result["tracking_error"] = te
            result["information_ratio"] = (
                float(active.mean() * 12 / te) if te and te > 0 else np.nan
            )
            if len(joined) > 1 and joined["benchmark"].var(ddof=1) > 0:
                beta = float(
                    joined["fund"].cov(joined["benchmark"]) / joined["benchmark"].var(ddof=1)
                )
                result["beta"] = beta
                result["alpha"] = float(
                    (
                        joined["fund"].mean()
                        - rf_month
                        - beta * (joined["benchmark"].mean() - rf_month)
                    )
                    * 12
                )
    return result


def calculate_fund_peer_metrics(
    data: pd.DataFrame,
    benchmark_history: pd.DataFrame,
    category: str,
    plan_type: str,
    *,
    as_of_date: str | pd.Timestamp,
    years: int,
    benchmark_id: str | None = None,
    annual_risk_free_rate: float = 0.0,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return peer metric table and focus-fund drawdown series for a selected period."""
    as_of = pd.Timestamp(as_of_date).normalize()
    start = as_of - pd.DateOffset(years=years)
    group = data.loc[data.category.eq(category) & data.plan_type.eq(plan_type)].copy()
    group = group.loc[group.nav_date <= as_of]
    bench = None
    benchmark_label = None
    if benchmark_id:
        b = benchmark_history.loc[
            benchmark_history.benchmark_id.eq(benchmark_id)
            & benchmark_history.is_valid.astype(str).str.casefold().isin({"true", "1"})
        ].copy()
        if not b.empty:
            bench = _monthly_series(b, "date", "close")
            bench = bench.loc[
                (bench.index <= as_of) & (bench.index >= start - pd.Timedelta(days=40))
            ]
            benchmark_label = str(b.iloc[0].get("series_type", ""))
    records = []
    dd_paths = []
    for scheme_id, rows in group.groupby("scheme_id", sort=False):
        nav = _monthly_series(rows, "nav_date", "nav")
        nav = nav.loc[(nav.index <= as_of) & (nav.index >= start - pd.Timedelta(days=40))]
        if len(nav) < 2:
            continue
        fund_start = nav.index[0]
        has_period_coverage = fund_start <= start + pd.Timedelta(days=40) and len(nav) >= max(
            2, int(np.ceil(years * 12 * 0.8))
        )
        metrics = (
            _risk_metrics(nav, bench, annual_risk_free_rate)
            if has_period_coverage
            else _risk_metrics(nav.iloc[:1], bench, annual_risk_free_rate)
        )
        meta = rows.sort_values("nav_date").iloc[-1]
        inception = _monthly_series(
            data.loc[
                data.scheme_id.eq(scheme_id)
                & data.plan_type.eq(plan_type)
                & data.nav_date.le(as_of)
            ],
            "nav_date",
            "nav",
        )
        inception_return = (
            float(inception.iloc[-1] / inception.iloc[0] - 1) if len(inception) > 1 else np.nan
        )
        record = {
            "scheme_id": scheme_id,
            "scheme_name": meta.get("scheme_name", str(scheme_id)),
            "scheme_isin": meta.get("scheme_isin", ""),
            "category": category,
            "plan_type": plan_type,
            "period_start": fund_start.date().isoformat() if has_period_coverage else "",
            "period_end": nav.index[-1].date().isoformat(),
            "observations": len(nav),
            "return_since_inception": inception_return,
            "benchmark_id": benchmark_id or "",
            "benchmark_type": benchmark_label or "",
            **metrics,
        }
        records.append(record)
        dd_paths.append(
            pd.DataFrame(
                {"date": nav.index, "scheme_id": scheme_id, "drawdown": _drawdown(nav).values}
            )
        )
    table = pd.DataFrame(records)
    if table.empty:
        return table, pd.DataFrame(columns=["date", "scheme_id", "drawdown"])
    rank_ascending = {
        "return_rank": ("period_return", False),
        "sharpe_rank": ("sharpe_ratio", False),
        "ir_rank": ("information_ratio", False),
    }
    for rank, (metric, ascending) in rank_ascending.items():
        table[rank] = table[metric].rank(method="min", ascending=ascending).astype("Int64")
    table["return_since_rank"] = table.return_since_inception.rank(
        method="min", ascending=False
    ).astype("Int64")
    table["peer_count"] = len(table)
    table["forward_ratio"] = np.nan
    table["expense_ratio"] = np.nan
    table["portfolio_turnover_rate"] = np.nan
    return table.sort_values(["period_return", "scheme_name"], ascending=[False, True]).reset_index(
        drop=True
    ), pd.concat(dd_paths, ignore_index=True)
