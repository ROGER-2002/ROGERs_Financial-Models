"""Transparent return and risk measures for periodic return series."""

from __future__ import annotations

import numpy as np
import pandas as pd


def _clean(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").dropna().astype(float)


def summarize_returns(
    fund_returns: pd.Series,
    benchmark_returns: pd.Series | None = None,
    *,
    periods_per_year: int = 52,
    risk_free_rate: float = 0.0,
) -> dict[str, float]:
    """Compute annualized CAGR, volatility, Sharpe, Sortino, tracking error and IR."""
    returns = _clean(fund_returns)
    if returns.empty:
        return {key: float("nan") for key in (
            "cagr", "volatility", "sharpe", "sortino", "tracking_error", "information_ratio", "max_drawdown"
        )}

    wealth = (1 + returns).cumprod()
    years = len(returns) / periods_per_year
    cagr = float(wealth.iloc[-1] ** (1 / years) - 1) if years > 0 and wealth.iloc[-1] > 0 else float("nan")
    volatility = float(returns.std(ddof=1) * np.sqrt(periods_per_year)) if len(returns) > 1 else float("nan")
    downside = np.minimum(returns.to_numpy(), 0.0)
    downside_deviation = float(np.sqrt(np.mean(downside**2) * periods_per_year))
    sharpe = (cagr - risk_free_rate) / volatility if volatility > 0 else float("nan")
    sortino = (cagr - risk_free_rate) / downside_deviation if downside_deviation > 0 else float("nan")
    drawdown = wealth / wealth.cummax().clip(lower=1.0) - 1

    te = information_ratio = float("nan")
    if benchmark_returns is not None:
        aligned = pd.concat([returns.rename("fund"), _clean(benchmark_returns).rename("benchmark")], axis=1).dropna()
        active = aligned["fund"] - aligned["benchmark"]
        if len(active) > 1:
            te = float(active.std(ddof=1) * np.sqrt(periods_per_year))
            active_annualized = float(active.mean() * periods_per_year)
            information_ratio = active_annualized / te if te > 0 else float("nan")

    return {
        "cagr": cagr,
        "volatility": volatility,
        "sharpe": sharpe,
        "sortino": sortino,
        "tracking_error": te,
        "information_ratio": information_ratio,
        "max_drawdown": float(drawdown.min()),
    }
