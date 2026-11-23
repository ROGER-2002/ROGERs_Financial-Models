import pandas as pd

from financial_analytics.data_quality import validate_fund_nav, validate_price_history


def test_valid_price_history_is_normalized_without_changing_source() -> None:
    source = pd.DataFrame(
        {
            "instrument_id": ["NSE:ABC"],
            "date": ["2026-01-02"],
            "open": ["100"],
            "high": ["105"],
            "low": ["98"],
            "close": ["103"],
            "volume": ["1200"],
        }
    )

    result = validate_price_history(source)

    assert result.is_valid
    assert pd.api.types.is_datetime64_any_dtype(result.data["date"])
    assert result.data.loc[0, "close"] == 103.0
    assert source.loc[0, "close"] == "103"


def test_price_history_flags_duplicate_keys_and_bad_ohlc() -> None:
    source = pd.DataFrame(
        {
            "instrument_id": ["NSE:ABC", "NSE:ABC"],
            "date": ["2026-01-02", "2026-01-02"],
            "open": [100, 110],
            "high": [105, 108],
            "low": [98, 109],
            "close": [103, 107],
        }
    )

    result = validate_price_history(source)

    assert {issue.code for issue in result.errors} >= {
        "duplicate_identifier_date",
        "inconsistent_ohlc",
    }


def test_fund_nav_flags_invalid_dates_and_non_positive_nav() -> None:
    source = pd.DataFrame(
        {
            "scheme_id": ["FUND-DIRECT-GROWTH", "FUND-REGULAR-GROWTH"],
            "date": ["2026-01-02", "not-a-date"],
            "nav": [0, 15.25],
        }
    )

    result = validate_fund_nav(source)

    assert {issue.code for issue in result.errors} == {
        "invalid_date",
        "non_positive_value",
    }


def test_missing_columns_are_reported() -> None:
    result = validate_fund_nav(pd.DataFrame({"date": ["2026-01-02"]}))

    assert not result.is_valid
    assert {issue.code for issue in result.errors} == {"missing_required_column"}
