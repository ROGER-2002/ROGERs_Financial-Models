import pandas as pd

from financial_analytics.input_pipeline import (
    canonicalize_index_frame,
    canonicalize_nav_frame,
    parse_excel_date,
)


def test_parse_excel_serial_date() -> None:
    assert parse_excel_date(41305) == pd.Timestamp("2013-01-31")


def test_nav_frame_maps_direct_scheme_and_flags_bad_values() -> None:
    source = pd.DataFrame(
        {
            "Scheme Code": [18218, 18218],
            "Scheme Name": ["Fund Growth", "Fund Growth"],
            "SD_Scheme ISIN": ["INF209K01ZC0", "INF209K01ZC0"],
            "SD_Category": ["Aggressive Hybrid", "Aggressive Hybrid"],
            "NAV_NAV Date": [41305, 41305],
            "NAV_Adjusted NAV": [351.7, 0],
        }
    )

    result = canonicalize_nav_frame(
        source,
        plan_type="Direct",
        source_file="sample.xlsx",
        source_sheet="AGGRESSIVE HYBRID",
    )

    assert result.loc[0, "scheme_id"] == "INF209K01ZC0"
    assert result.loc[0, "nav_date"] == pd.Timestamp("2013-01-31")
    assert not result.loc[0, "is_valid"]
    assert "non_positive_nav" in result.loc[1, "quality_issue_codes"]
    assert "duplicate_scheme_date" in result.loc[0, "quality_issue_codes"]


def test_index_frame_keeps_price_return_series_type_explicit() -> None:
    source = pd.DataFrame({"time": [36528, 36529], "close": [1291.53, 1335.45]})

    result = canonicalize_index_frame(
        source,
        benchmark_id="NIFTY 500",
        date_column="time",
        value_column="close",
        series_type="PRI",
        source_file="INDEX DATA.xlsx",
        source_sheet="NIFTY 500",
    )

    assert result["series_type"].eq("PRI").all()
    assert result["is_valid"].all()

