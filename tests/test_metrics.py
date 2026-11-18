import numpy as np
import pandas as pd

from financial_analytics.metrics import summarize_returns


def test_constant_positive_returns_have_expected_cagr_and_no_drawdown() -> None:
    result = summarize_returns(pd.Series([0.01] * 52))

    assert np.isclose(result["cagr"], (1.01**52) - 1)
    assert result["max_drawdown"] == 0
    assert np.isclose(result["volatility"], 0)
    assert np.isnan(result["sharpe"])


def test_drawdown_includes_loss_from_initial_value() -> None:
    result = summarize_returns(pd.Series([-0.20, 0.05]))

    assert np.isclose(result["max_drawdown"], -0.20)


def test_benchmark_metrics_are_computed_from_active_returns() -> None:
    fund = pd.Series([0.02, 0.01, -0.01, 0.03])
    benchmark = pd.Series([0.01, 0.01, 0.00, 0.02])

    result = summarize_returns(fund, benchmark)

    assert result["tracking_error"] > 0
    assert np.isfinite(result["information_ratio"])


def test_empty_series_returns_unavailable_metrics() -> None:
    result = summarize_returns(pd.Series(dtype=float))

    assert all(np.isnan(value) for value in result.values())
