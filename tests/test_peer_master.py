import pandas as pd

from financial_analytics.peer_master import build_peer_master, category_crosswalk


def test_master_canonicalizes_alias_and_keeps_plans_separate() -> None:
    nav = pd.DataFrame(
        [
            {
                "scheme_id": scheme,
                "scheme_code": scheme,
                "scheme_isin": scheme,
                "scheme_name": f"Fund {scheme}",
                "category": category,
                "plan_type": plan,
                "nav_date": date,
                "nav": 10.0 + index,
                "is_valid": True,
                "source_file": "source.xlsx",
            }
            for scheme, plan, category in [
                ("DIRECT1", "Direct", "Thematic"),
                ("REGULAR1", "Regular", "Multi Sector Fund"),
            ]
            for index, date in enumerate(["2025-09-30", "2025-10-31"])
        ]
    )

    master = build_peer_master(nav)

    assert len(master) == 2
    assert master["category"].eq("Multi Sector Fund").all()
    assert set(master["source_category"]) == {"Thematic", "Multi Sector Fund"}
    assert master["peer_group_id"].nunique() == 2
    assert master["nav_observation_count"].eq(2).all()


def test_category_crosswalk_records_confirmed_aliases() -> None:
    crosswalk = category_crosswalk().set_index("source_category")

    assert crosswalk.loc["ELSS", "canonical_category"] == "ELSS - Tax Saver Fund"
    assert crosswalk.loc["Multi Sector Rotation Fund", "canonical_category"] == "Multi Sector Fund"
    assert crosswalk.loc["Thematic", "canonical_category"] == "Multi Sector Fund"
