"""Reusable validation for canonical market price and fund NAV datasets."""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd


@dataclass(frozen=True)
class DataQualityIssue:
    """One validation finding and the source row labels affected by it."""

    code: str
    severity: str
    message: str
    affected_rows: tuple[object, ...] = ()


@dataclass
class ValidationResult:
    """Normalized copy of an input dataset plus validation findings."""

    data: pd.DataFrame
    errors: list[DataQualityIssue] = field(default_factory=list)
    warnings: list[DataQualityIssue] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        """Return true when no blocking data-quality errors were found."""
        return not self.errors


def _validate_series(
    frame: pd.DataFrame,
    *,
    identifier: str,
    date_column: str,
    value_column: str,
    dataset_name: str,
) -> ValidationResult:
    data = frame.copy()
    errors: list[DataQualityIssue] = []
    warnings: list[DataQualityIssue] = []
    required = [identifier, date_column, value_column]
    missing = [column for column in required if column not in data.columns]
    if missing:
        errors.extend(
            DataQualityIssue(
                code="missing_required_column",
                severity="error",
                message=f"{dataset_name} is missing required column '{column}'.",
            )
            for column in missing
        )
        return ValidationResult(data=data, errors=errors, warnings=warnings)

    data[date_column] = pd.to_datetime(data[date_column], errors="coerce")
    invalid_dates = data[date_column].isna()
    if invalid_dates.any():
        errors.append(
            DataQualityIssue(
                code="invalid_date",
                severity="error",
                message=f"{int(invalid_dates.sum())} rows have a missing or invalid date.",
                affected_rows=tuple(data.index[invalid_dates]),
            )
        )

    empty_ids = data[identifier].isna() | data[identifier].astype("string").str.strip().eq("")
    if empty_ids.any():
        errors.append(
            DataQualityIssue(
                code="missing_identifier",
                severity="error",
                message=f"{int(empty_ids.sum())} rows have a missing {identifier}.",
                affected_rows=tuple(data.index[empty_ids]),
            )
        )

    numeric_values = pd.to_numeric(data[value_column], errors="coerce")
    invalid_values = numeric_values.isna()
    if invalid_values.any():
        errors.append(
            DataQualityIssue(
                code="invalid_numeric_value",
                severity="error",
                message=f"{int(invalid_values.sum())} rows have an invalid {value_column}.",
                affected_rows=tuple(data.index[invalid_values]),
            )
        )
    data[value_column] = numeric_values
    non_positive = numeric_values.notna() & numeric_values.le(0)
    if non_positive.any():
        errors.append(
            DataQualityIssue(
                code="non_positive_value",
                severity="error",
                message=f"{int(non_positive.sum())} rows have a non-positive {value_column}.",
                affected_rows=tuple(data.index[non_positive]),
            )
        )

    duplicate_key = data.duplicated([identifier, date_column], keep=False)
    if duplicate_key.any():
        errors.append(
            DataQualityIssue(
                code="duplicate_identifier_date",
                severity="error",
                message=(
                    f"{int(duplicate_key.sum())} rows duplicate the "
                    f"({identifier}, {date_column}) key."
                ),
                affected_rows=tuple(data.index[duplicate_key]),
            )
        )

    ordered = data.sort_values([identifier, date_column], kind="stable")
    if not data.index.equals(ordered.index):
        warnings.append(
            DataQualityIssue(
                code="unsorted_observations",
                severity="warning",
                message=(
                    f"{dataset_name} is not ordered by {identifier} and {date_column}; "
                    "the validator did not reorder the source."
                ),
            )
        )
    return ValidationResult(data=data, errors=errors, warnings=warnings)


def validate_price_history(
    frame: pd.DataFrame,
    *,
    identifier: str = "instrument_id",
    date_column: str = "date",
) -> ValidationResult:
    """Validate canonical daily security or index prices.

    Required columns are the identifier, date, and close. Open, high, low, and volume
    are checked when supplied. Source data is copied and never silently repaired.
    """
    result = _validate_series(
        frame,
        identifier=identifier,
        date_column=date_column,
        value_column="close",
        dataset_name="Price history",
    )
    data = result.data
    errors = result.errors
    ohlc = {"open", "high", "low", "close"}
    if ohlc.issubset(data.columns):
        values = {
            column: pd.to_numeric(data[column], errors="coerce")
            for column in ohlc
        }
        invalid = pd.Series(False, index=data.index)
        for column, series in values.items():
            bad_numeric = series.isna()
            if bad_numeric.any():
                errors.append(
                    DataQualityIssue(
                        code="invalid_numeric_value",
                        severity="error",
                        message=f"{int(bad_numeric.sum())} rows have an invalid {column}.",
                        affected_rows=tuple(data.index[bad_numeric]),
                    )
                )
            data[column] = series
            invalid |= bad_numeric
        bad_ohlc = (
            ~invalid
            & (
                values["high"].lt(values["low"])
                | values["high"].lt(values["open"])
                | values["high"].lt(values["close"])
                | values["low"].gt(values["open"])
                | values["low"].gt(values["close"])
            )
        )
        if bad_ohlc.any():
            errors.append(
                DataQualityIssue(
                    code="inconsistent_ohlc",
                    severity="error",
                    message=f"{int(bad_ohlc.sum())} rows have inconsistent OHLC values.",
                    affected_rows=tuple(data.index[bad_ohlc]),
                )
            )
    if "volume" in data.columns:
        volume = pd.to_numeric(data["volume"], errors="coerce")
        invalid_volume = volume.isna()
        if invalid_volume.any():
            errors.append(
                DataQualityIssue(
                    code="invalid_numeric_value",
                    severity="error",
                    message=f"{int(invalid_volume.sum())} rows have an invalid volume.",
                    affected_rows=tuple(data.index[invalid_volume]),
                )
            )
        negative_volume = volume.notna() & volume.lt(0)
        if negative_volume.any():
            errors.append(
                DataQualityIssue(
                    code="negative_volume",
                    severity="error",
                    message=f"{int(negative_volume.sum())} rows have negative volume.",
                    affected_rows=tuple(data.index[negative_volume]),
                )
            )
        data["volume"] = volume
    return result


def validate_fund_nav(
    frame: pd.DataFrame,
    *,
    identifier: str = "scheme_id",
    date_column: str = "date",
    nav_column: str = "nav",
) -> ValidationResult:
    """Validate canonical mutual-fund NAV observations."""
    return _validate_series(
        frame,
        identifier=identifier,
        date_column=date_column,
        value_column=nav_column,
        dataset_name="Fund NAV",
    )
