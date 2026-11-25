"""Stream a wide Excel stock-price matrix into local long-form Parquet."""

from __future__ import annotations

import argparse
import csv
import logging
import math
from datetime import date, datetime, timedelta
from logging.handlers import RotatingFileHandler
from numbers import Real
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq
from openpyxl import load_workbook

logger = logging.getLogger(__name__)
EXCEL_EPOCH = datetime(1899, 12, 30)
EXPECTED_NA = {"#N/A", "#N/A N/A"}
PRICE_SCHEMA = pa.schema(
    [
        ("date", pa.date32()),
        ("symbol", pa.string()),
        ("close", pa.float64()),
        ("is_valid", pa.bool_()),
        ("quality_issue_codes", pa.string()),
    ]
)


def _as_date(value: Any) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, Real) and not isinstance(value, bool):
        if math.isfinite(float(value)) and 0 <= float(value) < 100000:
            return (EXCEL_EPOCH + timedelta(days=float(value))).date()
    if isinstance(value, str):
        try:
            return date.fromisoformat(value.strip()[:10])
        except ValueError:
            return None
    return None


def _flush_prices(
    writer: pq.ParquetWriter,
    dates: list[date],
    symbols: list[str],
    closes: list[float],
    valid: list[bool],
    issue_codes: list[str],
) -> None:
    if not dates:
        return
    table = pa.Table.from_arrays(
        [
            pa.array(dates, type=pa.date32()),
            pa.array(symbols, type=pa.string()),
            pa.array(closes, type=pa.float64()),
            pa.array(valid, type=pa.bool_()),
            pa.array(issue_codes, type=pa.string()),
        ],
        schema=PRICE_SCHEMA,
    )
    writer.write_table(table)
    dates.clear()
    symbols.clear()
    closes.clear()
    valid.clear()
    issue_codes.clear()


def build_stock_price_outputs(
    input_file: Path,
    output_dir: Path,
    *,
    sheet_name: str | None = None,
    chunk_rows: int = 200_000,
) -> dict[str, Path]:
    """Write observed prices, per-symbol coverage, rejects, and a quality report."""
    input_file = Path(input_file)
    output_dir = Path(output_dir)
    if chunk_rows < 1:
        raise ValueError("chunk_rows must be a positive integer.")
    output_dir.mkdir(parents=True, exist_ok=True)

    prices_path = output_dir / "stock_price_history.parquet"
    coverage_path = output_dir / "stock_price_coverage.csv"
    rejects_path = output_dir / "stock_price_rejects.csv"
    report_path = output_dir / "stock_price_quality_report.md"
    partial_path = output_dir / "stock_price_history.partial.parquet"

    workbook = load_workbook(input_file, read_only=True, data_only=True)
    writer: pq.ParquetWriter | None = None
    try:
        worksheet = workbook[sheet_name] if sheet_name else workbook[workbook.sheetnames[0]]
        rows = worksheet.iter_rows(values_only=True)
        header = next(rows, None)
        if not header or len(header) < 2:
            raise ValueError("Expected a date column followed by one or more stock columns.")
        if str(header[0]).strip().casefold() != "date":
            raise ValueError(f"Expected first header 'Date', found {header[0]!r}.")
        symbols = [str(value).strip() if value is not None else "" for value in header[1:]]
        if any(not symbol for symbol in symbols):
            raise ValueError("Every stock price column must have a non-empty symbol header.")
        if len(symbols) != len(set(symbols)):
            raise ValueError(
                "Duplicate stock symbol headers found; resolve them before conversion."
            )

        symbol_count = len(symbols)
        first_index: list[int | None] = [None] * symbol_count
        last_index: list[int | None] = [None] * symbol_count
        first_price_date: list[date | None] = [None] * symbol_count
        last_price_date: list[date | None] = [None] * symbol_count
        observed: list[int] = [0] * symbol_count
        na_counts: list[int] = [0] * symbol_count
        blank_counts: list[int] = [0] * symbol_count
        invalid_counts: list[int] = [0] * symbol_count
        non_positive_counts: list[int] = [0] * symbol_count
        date_buffer: list[date] = []
        symbol_buffer: list[str] = []
        close_buffer: list[float] = []
        valid_buffer: list[bool] = []
        issue_buffer: list[str] = []
        last_date: date | None = None
        date_rows = 0
        na_total = 0
        blank_total = 0
        invalid_total = 0
        non_positive_total = 0
        source_first_date: date | None = None

        with rejects_path.open("w", newline="", encoding="utf-8") as rejects_file:
            rejects = csv.DictWriter(
                rejects_file,
                fieldnames=["source_row", "date", "symbol", "source_value", "issue_code"],
            )
            rejects.writeheader()
            writer = pq.ParquetWriter(partial_path, PRICE_SCHEMA, compression="zstd")
            for source_row, row in enumerate(rows, start=2):
                if not row or all(value is None for value in row):
                    continue
                if len(row) < symbol_count + 1:
                    raise ValueError(f"Row {source_row} has fewer cells than the header.")
                observation_date = _as_date(row[0])
                if observation_date is None:
                    raise ValueError(
                        f"Invalid or missing date in source row {source_row}: {row[0]!r}."
                    )
                if last_date is not None and observation_date <= last_date:
                    raise ValueError(
                        f"Dates must be unique and increasing; row {source_row} "
                        f"has {observation_date}."
                    )
                last_date = observation_date
                if source_first_date is None:
                    source_first_date = observation_date
                date_rows += 1

                for index, value in enumerate(row[1 : symbol_count + 1]):
                    if value is None:
                        blank_counts[index] += 1
                        blank_total += 1
                        continue
                    if isinstance(value, str):
                        cleaned = value.strip()
                        if cleaned.upper() in EXPECTED_NA:
                            na_counts[index] += 1
                            na_total += 1
                            continue
                        rejects.writerow(
                            {
                                "source_row": source_row,
                                "date": observation_date.isoformat(),
                                "symbol": symbols[index],
                                "source_value": cleaned,
                                "issue_code": "non_numeric_close",
                            }
                        )
                        invalid_counts[index] += 1
                        invalid_total += 1
                        continue
                    if (
                        isinstance(value, bool)
                        or not isinstance(value, Real)
                        or not math.isfinite(float(value))
                    ):
                        rejects.writerow(
                            {
                                "source_row": source_row,
                                "date": observation_date.isoformat(),
                                "symbol": symbols[index],
                                "source_value": str(value),
                                "issue_code": "non_numeric_close",
                            }
                        )
                        invalid_counts[index] += 1
                        invalid_total += 1
                        continue

                    close = float(value)
                    issue = "non_positive_close" if close <= 0 else ""
                    is_valid = not issue
                    if issue:
                        non_positive_counts[index] += 1
                        non_positive_total += 1
                    if first_index[index] is None:
                        first_index[index] = date_rows - 1
                        first_price_date[index] = observation_date
                    last_index[index] = date_rows - 1
                    last_price_date[index] = observation_date
                    observed[index] += 1
                    date_buffer.append(observation_date)
                    symbol_buffer.append(symbols[index])
                    close_buffer.append(close)
                    valid_buffer.append(is_valid)
                    issue_buffer.append(issue)

                if len(date_buffer) >= chunk_rows:
                    _flush_prices(
                        writer,
                        date_buffer,
                        symbol_buffer,
                        close_buffer,
                        valid_buffer,
                        issue_buffer,
                    )
                if date_rows % 500 == 0:
                    logger.info("Processed %s dates from %s", date_rows, input_file.name)

            _flush_prices(
                writer,
                date_buffer,
                symbol_buffer,
                close_buffer,
                valid_buffer,
                issue_buffer,
            )
        writer.close()
        writer = None
        partial_path.replace(prices_path)

        with coverage_path.open("w", newline="", encoding="utf-8") as coverage_file:
            coverage = csv.DictWriter(
                coverage_file,
                fieldnames=[
                    "symbol",
                    "first_observed_date",
                    "last_observed_date",
                    "observed_price_count",
                    "missing_before_first",
                    "missing_within_history",
                    "missing_after_last",
                    "na_cell_count",
                    "blank_cell_count",
                    "invalid_cell_count",
                    "non_positive_price_count",
                    "total_date_rows",
                    "observed_coverage_pct",
                ],
            )
            coverage.writeheader()
            for index, symbol in enumerate(symbols):
                first = first_index[index]
                last = last_index[index]
                missing_before = first if first is not None else date_rows
                missing_inside = (
                    last - first + 1 - observed[index]
                    if first is not None and last is not None
                    else 0
                )
                missing_after = date_rows - 1 - last if last is not None else 0
                coverage.writerow(
                    {
                        "symbol": symbol,
                        "first_observed_date": (
                            ""
                            if first_price_date[index] is None
                            else first_price_date[index].isoformat()
                        ),
                        "last_observed_date": (
                            ""
                            if last_price_date[index] is None
                            else last_price_date[index].isoformat()
                        ),
                        "observed_price_count": observed[index],
                        "missing_before_first": missing_before,
                        "missing_within_history": missing_inside,
                        "missing_after_last": missing_after,
                        "na_cell_count": na_counts[index],
                        "blank_cell_count": blank_counts[index],
                        "invalid_cell_count": invalid_counts[index],
                        "non_positive_price_count": non_positive_counts[index],
                        "total_date_rows": date_rows,
                        "observed_coverage_pct": (
                            f"{observed[index] / date_rows * 100:.6f}" if date_rows else "0"
                        ),
                    }
                )

        report = [
            "# Stock price ingestion report",
            "",
            f"- Source workbook: `{input_file.name}` (sheet `{worksheet.title}`).",
            f"- Source dimensions: {date_rows:,} dates × {symbol_count:,} stock columns.",
            f"- Date coverage: {source_first_date or 'unavailable'} to "
            f"{last_date or 'unavailable'}.",
            f"- Observed numeric closes written: {sum(observed):,}.",
            f"- Expected `#N/A` cells preserved as missing: {na_total:,}.",
            f"- Explicit blank cells: {blank_total:,}.",
            f"- Invalid non-numeric cells written to rejects: {invalid_total:,}.",
            f"- Non-positive closes retained but flagged in Parquet: {non_positive_total:,}.",
            "",
            "The price table is sparse long form: each row is an observed numeric close. "
            "Missing cells are not emitted as zeroes.",
            "Coverage separates leading missing history, gaps within each symbol's observed "
            "range, and trailing missing dates.",
            "",
            f"- Price data: `{prices_path.name}`.",
            f"- Per-symbol coverage: `{coverage_path.name}`.",
            f"- Rejected non-numeric values: `{rejects_path.name}`.",
        ]
        report_path.write_text("\n".join(report) + "\n", encoding="utf-8")
        logger.info(
            "Stock conversion complete: %s dates, %s symbols, %s numeric closes",
            date_rows,
            symbol_count,
            sum(observed),
        )
    finally:
        if writer is not None:
            writer.close()
        workbook.close()

    return {
        "prices": prices_path,
        "coverage": coverage_path,
        "rejects": rejects_path,
        "report": report_path,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input-file",
        type=Path,
        default=Path("INPUT/Historical Values 23-01.xlsx"),
    )
    parser.add_argument("--output-dir", type=Path, default=Path("OUTPUT/prepared/stock"))
    parser.add_argument("--log-dir", type=Path, default=Path("logs"))
    parser.add_argument("--sheet", default=None)
    args = parser.parse_args()
    args.log_dir.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(),
            RotatingFileHandler(
                args.log_dir / "stock_price_pipeline.log",
                maxBytes=5_000_000,
                backupCount=3,
                encoding="utf-8",
            ),
        ],
        force=True,
    )
    try:
        outputs = build_stock_price_outputs(
            args.input_file,
            args.output_dir,
            sheet_name=args.sheet,
        )
        for label, path in outputs.items():
            logger.info("Created %s at %s", label, path)
            print(f"{label}: {path}")
    except Exception:
        logger.exception("Stock price conversion failed")
        raise


if __name__ == "__main__":
    main()

