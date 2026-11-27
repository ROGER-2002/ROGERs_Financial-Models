import numpy as np
import pandas as pd

from financial_analytics.peer_performance import (
    attach_peer_metadata,
    canonicalize_category,
    peer_performance_table,
)


def _test_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    dates = pd.date_range("2022-10-31", periods=37, freq="ME")
    schemes = [
        ("D1", "Direct", "Thematic", 0.01),
        ("D2", "Direct", "Multi Sector Fund", 0.005),
        ("D3", "Direct", "Multi Sector Fund", 0.0),
        ("R1", "Regular", "Multi Sector Fund", 0.02),
        ("R2", "Regular", "Multi Sector Fund", -0.005),
    ]
    nav_rows = []
    master_rows = []
    for scheme_id, plan, category, monthly_return in schemes:
        master_rows.append(
            {
                "scheme_id": scheme_id,
                "scheme_isin": scheme_id,
                "scheme_code": scheme_id,
                "scheme_name": f"Fund {scheme_id}",
                "category": category,
                "plan_type": plan,
            }
        )
        for index, nav_date in enumerate(dates):
            nav_rows.append(
                {
                    "scheme_id": scheme_id,
                    "plan_type": plan,
                    "nav_date": nav_date,
                    "nav": 10 * (1 + monthly_return) ** index,
                    "is_valid": True,
                }
            )
    return pd.DataFrame(nav_rows), pd.DataFrame(master_rows)


def test_confirmed_category_aliases_canonicalize_to_peer_categories() -> None:
    assert canonicalize_category("ELSS") == "ELSS - Tax Saver Fund"
    assert canonicalize_category("Multi Sector Rotation Fund") == "Multi Sector Fund"
    assert canonicalize_category("Thematic") == "Multi Sector Fund"


def test_direct_and_regular_peer_groups_remain_separate() -> None:
    nav, master = _test_data()
    data = attach_peer_metadata(nav, master)

    direct = peer_performance_table(data, "Multi Sector Fund", "Direct")
    regular = peer_performance_table(data, "Thematic", "Regular")

    assert set(direct["plan_type"]) == {"Direct"}
    assert set(regular["plan_type"]) == {"Regular"}
    assert len(direct) == 3
    assert len(regular) == 2
    assert direct["category"].eq("Multi Sector Fund").all()


def test_cagr_and_peer_percentile_use_same_plan_peers() -> None:
    nav, master = _test_data()
    data = attach_peer_metadata(nav, master)
    result = peer_performance_table(data, "Multi Sector Fund", "Direct")

    fastest = result.sort_values("cagr_1y").iloc[-1]
    assert np.isclose(fastest["cagr_1y"], (1.01**12) - 1)
    assert fastest["peer_percentile_1y"] == 100.0
    assert result["peer_count"].eq(3).all()
