"""Deterministic synthetic mutual-fund data for UI development only."""

from __future__ import annotations

import numpy as np
import pandas as pd

FUND_CATALOG = pd.DataFrame(
    [
        ("SIM-AH-01", "Illustrative Hybrid A", "Aggressive Hybrid Fund", 0.145, 0.185),
        ("SIM-AH-02", "Illustrative Hybrid B", "Aggressive Hybrid Fund", 0.125, 0.155),
        ("SIM-AH-03", "Illustrative Hybrid C", "Aggressive Hybrid Fund", 0.105, 0.135),
        ("SIM-LC-01", "Illustrative Large Cap A", "Large Cap Fund", 0.115, 0.160),
        ("SIM-LC-02", "Illustrative Large Cap B", "Large Cap Fund", 0.095, 0.140),
        ("SIM-LC-03", "Illustrative Large Cap C", "Large Cap Fund", 0.085, 0.125),
        ("SIM-FL-01", "Illustrative Flexi Cap A", "Flexi Cap Fund", 0.135, 0.190),
        ("SIM-FL-02", "Illustrative Flexi Cap B", "Flexi Cap Fund", 0.115, 0.160),
        ("SIM-FL-03", "Illustrative Flexi Cap C", "Flexi Cap Fund", 0.090, 0.145),
    ],
    columns=["fund_id", "fund_name", "category", "annual_drift", "annual_volatility"],
)


def load_demo_data(seed: int = 23) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return synthetic weekly NAV and benchmark return series with stable results."""
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2025-08-29", "2026-11-13", freq="W-FRI")
    fund_rows: list[dict[str, object]] = []
    benchmark_rows: list[dict[str, object]] = []
    category_shocks = {
        category: rng.normal(0.0008, 0.022, len(dates))
        for category in FUND_CATALOG["category"].unique()
    }
    for category, shocks in category_shocks.items():
        benchmark_rows.extend(
            {"date": date, "category": category, "return": float(value)}
            for date, value in zip(dates, shocks, strict=True)
        )
    for row in FUND_CATALOG.itertuples(index=False):
        id_seed = sum(map(ord, row.fund_id))
        local_rng = np.random.default_rng(seed + id_seed)
        category_return = category_shocks[row.category]
        idiosyncratic = local_rng.normal(0, row.annual_volatility / np.sqrt(52), len(dates))
        weekly_drift = row.annual_drift / 52
        returns = weekly_drift + 0.55 * category_return + idiosyncratic
        nav = 100 * np.cumprod(1 + returns)
        fund_rows.extend(
            {
                "date": date,
                "fund_id": row.fund_id,
                "fund_name": row.fund_name,
                "category": row.category,
                "return": float(ret),
                "nav": float(value),
            }
            for date, ret, value in zip(dates, returns, nav, strict=True)
        )
    return pd.DataFrame(fund_rows), pd.DataFrame(benchmark_rows)
