"""Prepare canonical local NAV and benchmark CSVs from approved Excel inputs.

The original workbooks are read-only inputs. This first-stage pipeline deliberately
leaves wide stock history and portfolio holdings for a later, source-specific pass.
"""

from __future__ import annotations

import argparse
import logging
from datetime import date, datetime
from logging.handlers import RotatingFileHandler
from numbers import Real
from pathlib import Path
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)

NAV_COLUMNS = {
    "Scheme Code": "scheme_code",
    "Scheme Name": "scheme_name",
    "SD_Scheme ISIN": "scheme_isin",
    "SD_Category": "category",
    "NAV_NAV Date": "nav_date",
    "NAV_Adjusted NAV": "nav",
}


def parse_excel_date(value: Any) -> Any:
    """Convert dates, Excel serials, and readable date strings to timestamps."""
    if value is None or pd.isna(value):
        return pd.NaT
    if isinstance(value, (pd.Timestamp, datetime, date)):
        return pd.Timestamp(value).normalize()
    if isinstance(value, Real) and not isinstance(value, bool):
        if 0 <= float(value) < 100000:
            return (pd.Timestamp("1899-12-30") + pd.to_timedelta(value, unit="D")).normalize()
        return pd.NaT
    return pd.to_datetime(value, errors="coerce", dayfirst=True)


def _identifier(value: Any) -> str | None:
    if value is None or pd.isna(value):
        return None
    if isinstance(value, Real) and not isinstance(value, bool):
        if float(value).is_integer():
            return str(int(value))
    cleaned = str(value).strip()
    return cleaned or None


def _strings(series: pd.Series) -> pd.Series:
    return series.map(_identifier).astype("string")


def _mark_issues(
    frame: pd.DataFrame,
    rules: list[tuple[pd.Series, str]],
) -> pd.DataFrame:
    issues: list[list[str]] = [[] for _ in range(len(frame))]
    for mask, code in rules:
        flags = mask.fillna(False).tolist()
        for position, flagged in enumerate(flags):
            if flagged:
                issues[position].append(code)
    result = frame.copy()
    result["quality_issue_codes"] = [";".join(row) for row in issues]
    result["is_valid"] = result["quality_issue_codes"].eq("")
    return result


def canonicalize_nav_frame(
    frame: pd.DataFrame,
    *,
    plan_type: str,
    source_file: str,
    source_sheet: str,
) -> pd.DataFrame:
    """Map one supplied direct or regular NAV worksheet to the canonical schema."""
    missing = [column for column in NAV_COLUMNS if column not in frame.columns]
    if missing:
        raise ValueError(f"Missing expected NAV columns: {', '.join(missing)}")

    data = frame.rename(columns=NAV_COLUMNS).copy()
    data["scheme_code"] = _strings(data["scheme_code"])
    data["scheme_isin"] = _strings(data["scheme_isin"])
    data["scheme_name"] = data["scheme_name"].astype("string").str.strip()
    data["category"] = data["category"].astype("string").str.strip()
    data["plan_type"] = plan_type
    data["scheme_id"] = data["scheme_isin"]
    fallback = data["scheme_code"].notna() & data["scheme_id"].isna()
    data.loc[fallback, "scheme_id"] = plan_type + ":" + data.loc[fallback, "scheme_code"]
    data["nav_date"] = data["nav_date"].map(parse_excel_date)
    data["nav"] = pd.to_numeric(data["nav"], errors="coerce")
    data["source_file"] = source_file
    data["source_sheet"] = source_sheet
    data["source_row"] = list(range(2, len(data) + 2))

    duplicate = data.duplicated(["scheme_id", "plan_type", "nav_date"], keep=False)
    rules = [
        (data["scheme_id"].isna(), "missing_scheme_identifier"),
        (data["nav_date"].isna(), "invalid_nav_date"),
        (data["nav"].isna(), "invalid_nav_value"),
        (data["nav"].notna() & data["nav"].le(0), "non_positive_nav"),
        (duplicate & data["scheme_id"].notna() & data["nav_date"].notna(), "duplicate_scheme_date"),
    ]
    data = _mark_issues(data, rules)
    columns = [
        "scheme_id",
        "scheme_code",
        "scheme_isin",
        "scheme_name",
        "category",
        "plan_type",
        "nav_date",
        "nav",
        "source_file",
        "source_sheet",
        "source_row",
        "quality_issue_codes",
        "is_valid",
    ]
    return data[columns]


def canonicalize_index_frame(
    frame: pd.DataFrame,
    *,
    benchmark_id: str,
    date_column: str,
    value_column: str,
    series_type: str,
    source_file: str,
    source_sheet: str,
) -> pd.DataFrame:
    """Map one index worksheet to a canonical benchmark time series."""
    missing = [column for column in (date_column, value_column) if column not in frame.columns]
    if missing:
        raise ValueError(f"Missing expected benchmark columns: {', '.join(missing)}")

    data = pd.DataFrame(index=frame.index)
    data["benchmark_id"] = benchmark_id
    data["series_type"] = series_type
    data["date"] = frame[date_column].map(parse_excel_date)
    data["close"] = pd.to_numeric(frame[value_column], errors="coerce")
    data["source_file"] = source_file
    data["source_sheet"] = source_sheet
    data["source_row"] = list(range(2, len(data) + 2))

    duplicate = data.duplicated(["benchmark_id", "date"], keep=False)
    rules = [
        (data["date"].isna(), "invalid_date"),
        (data["close"].isna(), "invalid_close"),
        (data["close"].notna() & data["close"].le(0), "non_positive_close"),
        (duplicate & data["date"].notna(), "duplicate_benchmark_date"),
    ]
    return _mark_issues(data, rules)


def _date_span(frame: pd.DataFrame, column: str) -> str:
    values = frame[column].dropna()
    if values.empty:
        return "unavailable"
    return f"{values.min():%Y-%m-%d} to {values.max():%Y-%m-%d}"


def _profile_line(label: str, frame: pd.DataFrame, date_column: str) -> str:
    valid_count = int(frame["is_valid"].sum())
    invalid_count = len(frame) - valid_count
    return (
        f"| {label} | {len(frame):,} | {valid_count:,} | {invalid_count:,} | "
        f"{_date_span(frame, date_column)} |"
    )


def build_local_outputs(input_dir: Path, output_dir: Path) -> dict[str, Path]:
    """Read supported NAV/index workbooks and write local CSV and Markdown outputs."""
    input_dir = Path(input_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    nav_tables: list[pd.DataFrame] = []
    benchmark_tables: list[pd.DataFrame] = []
    source_notes: list[str] = []
    nav_dirs = [
        input_dir / "FINAL DATA",
        input_dir / "CONSERVATIVE & ALL DEBT FUNDS NAV",
    ]
    nav_files = sorted(path for folder in nav_dirs for path in folder.glob("*.xlsx"))
    for path in nav_files:
        logger.info("Reading NAV workbook: %s", path)
        try:
            workbook = pd.ExcelFile(path, engine="openpyxl")
        except Exception as exc:
            logger.exception("Could not open NAV workbook %s", path)
            source_notes.append(f"- Skipped {path.name}: could not open workbook ({exc}).")
            continue

        for sheet_name in workbook.sheet_names:
            filename = path.stem.upper()
            sheet_label = sheet_name.strip().upper()
            if "DIRECT" in filename:
                plan_type = "Direct"
            elif "REGULAR" in filename:
                plan_type = "Regular"
            elif sheet_label == "DIRECT":
                plan_type = "Direct"
            elif sheet_label == "REGULAR":
                plan_type = "Regular"
            else:
                logger.warning("Skipping sheet without a plan label: %s / %s", path.name, sheet_name)
                source_notes.append(
                    f"- Skipped {path.name} / {sheet_name}: plan type not identified."
                )
                continue

            try:
                raw = pd.read_excel(workbook, sheet_name=sheet_name)
                canonical = canonicalize_nav_frame(
                    raw,
                    plan_type=plan_type,
                    source_file=path.name,
                    source_sheet=sheet_name,
                )
                nav_tables.append(canonical)
                logger.info("Read %s / %s: %s rows", path.name, sheet_name, len(canonical))
                source_notes.append(
                    f"- Read {path.name} / {sheet_name}: {len(canonical):,} source rows."
                )
            except Exception as exc:
                logger.exception("Could not read NAV sheet %s / %s", path.name, sheet_name)
                source_notes.append(
                    f"- Skipped {path.name} / {sheet_name}: {type(exc).__name__}: {exc}."
                )
        workbook.close()

    index_path = input_dir / "INDEX DATA.xlsx"
    if index_path.exists():
        try:
            workbook = pd.ExcelFile(index_path, engine="openpyxl")
            for sheet_name in workbook.sheet_names:
                raw = pd.read_excel(workbook, sheet_name=sheet_name)
                benchmark_tables.append(
                    canonicalize_index_frame(
                        raw,
                        benchmark_id=sheet_name,
                        date_column="time",
                        value_column="close",
                        series_type="PRI",
                        source_file=index_path.name,
                        source_sheet=sheet_name,
                    )
                )
            workbook.close()
            logger.info("Read %s: %s index sheets", index_path.name, len(workbook.sheet_names))
            source_notes.append(f"- Read {index_path.name}: {len(workbook.sheet_names)} index sheets.")
        except Exception as exc:
            logger.exception("Could not read index workbook %s", index_path)
            source_notes.append(
                f"- Index workbook could not be fully read: {type(exc).__name__}: {exc}."
            )

    tri_path = input_dir / "NIFTY LargeMidcap 250 - TRI.xlsx"
    if tri_path.exists():
        try:
            workbook = pd.ExcelFile(tri_path, engine="openpyxl")
            for sheet_name in workbook.sheet_names:
                raw = pd.read_excel(workbook, sheet_name=sheet_name)
                name_column = "Index Name" if "Index Name" in raw.columns else None
                benchmark_id = (
                    str(raw[name_column].dropna().iloc[0])
                    if name_column and raw[name_column].notna().any()
                    else "NIFTY LargeMidcap 250 TRI"
                )
                benchmark_tables.append(
                    canonicalize_index_frame(
                        raw,
                        benchmark_id=benchmark_id,
                        date_column="Date",
                        value_column="Close Price",
                        series_type="TRI",
                        source_file=tri_path.name,
                        source_sheet=sheet_name,
                    )
                )
            workbook.close()
            source_notes.append(f"- Read {tri_path.name}: TRI benchmark series.")
        except Exception as exc:
            logger.exception("Could not read TRI workbook %s", tri_path)
            source_notes.append(
                f"- TRI workbook could not be fully read: {type(exc).__name__}: {exc}."
            )

    if not nav_tables:
        raise RuntimeError(f"No supported NAV worksheets were found under {nav_dir}.")
    if not benchmark_tables:
        raise RuntimeError("No supported benchmark worksheets were found in Input.")

    nav = pd.concat(nav_tables, ignore_index=True)
    benchmark = pd.concat(benchmark_tables, ignore_index=True)
    global_duplicates = (
        nav.duplicated(["scheme_id", "plan_type", "nav_date"], keep=False)
        & nav["scheme_id"].notna()
        & nav["nav_date"].notna()
    )
    for index in nav.index[global_duplicates]:
        current = nav.at[index, "quality_issue_codes"]
        codes = current.split(";") if current else []
        if "duplicate_scheme_date" not in codes:
            codes.append("duplicate_scheme_date")
        nav.at[index, "quality_issue_codes"] = ";".join(codes)
        nav.at[index, "is_valid"] = False
    nav["nav_date"] = pd.to_datetime(nav["nav_date"])
    benchmark["date"] = pd.to_datetime(benchmark["date"])

    nav_output = output_dir / "fund_nav_history.csv"
    benchmark_output = output_dir / "benchmark_history.csv"
    report_output = output_dir / "data_quality_report.md"
    nav.to_csv(nav_output, index=False, date_format="%Y-%m-%d", encoding="utf-8")
    benchmark.to_csv(benchmark_output, index=False, date_format="%Y-%m-%d", encoding="utf-8")

    nav_valid = int(nav["is_valid"].sum())
    benchmark_valid = int(benchmark["is_valid"].sum())
    report = [
        "# Local input preparation report",
        "",
        "Generated from local INPUT workbooks. Original source files were read only.",
        "Only supported long NAV sheets and index-close sheets were standardized in this pass.",
        "",
        "## Summary",
        "",
        f"- NAV rows: {len(nav):,}; valid: {nav_valid:,}; flagged: {len(nav) - nav_valid:,}.",
        f"- Fund schemes: {nav['scheme_id'].nunique(dropna=True):,}.",
        f"- NAV date coverage: {_date_span(nav, 'nav_date')}.",
        f"- Benchmark rows: {len(benchmark):,}; valid: {benchmark_valid:,}; "
        f"flagged: {len(benchmark) - benchmark_valid:,}.",
        f"- Benchmark series: {benchmark['benchmark_id'].nunique(dropna=True):,}.",
        f"- Benchmark date coverage: {_date_span(benchmark, 'date')}.",
        "",
        "## Source profiles",
        "",
        "| Dataset/source | Rows | Valid | Flagged | Date range |",
        "|---|---:|---:|---:|---|",
    ]
    for name, group in nav.groupby("source_file", dropna=False):
        report.append(_profile_line(f"NAV: {name}", group, "nav_date"))
    for name, group in benchmark.groupby("benchmark_id", dropna=False):
        label = f"Benchmark: {name} ({group['series_type'].iloc[0]})"
        report.append(_profile_line(label, group, "date"))
    report.extend(["", "## Input handling notes", ""])
    report.extend(source_notes)
    report.extend(
        [
            "",
            "## Deferred sources",
            "",
            "- The wide stock history workbook contains millions of #N/A cells. It needs a "
            "streaming conversion and explicit missing-value policy.",
            "- The two monthly portfolio-holdings workbooks need a separate holdings key "
            "and unit review.",
            "- The merged direct-NAV matrix and 20 Nov multi-section workbook need "
            "overlap checks before combining with the NAV output.",
            "- The four INDEX DATA series are Price Return Indices (PRIs), as confirmed "
            "by the data owner. The source sheet is named MIDCAP 150 while the supplied "
            "description says Nifty Midcap 250; confirm that label before reporting it.",
            "",
            "Flagged rows remain in the CSV with quality_issue_codes and is_valid columns. "
            "Do not use flagged rows in model calculations until reviewed.",
        ]
    )
    report_output.write_text("\n".join(report) + "\n", encoding="utf-8")
    return {
        "fund_nav_history": nav_output,
        "benchmark_history": benchmark_output,
        "data_quality_report": report_output,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, default=Path("INPUT"))
    parser.add_argument("--output-dir", type=Path, default=Path("OUTPUT/prepared"))
    parser.add_argument("--log-dir", type=Path, default=Path("logs"))
    args = parser.parse_args()
    args.log_dir.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(),
            RotatingFileHandler(
                args.log_dir / "financial_analytics.log",
                maxBytes=5_000_000,
                backupCount=3,
                encoding="utf-8",
            ),
        ],
        force=True,
    )
    logger.info("Starting local input preparation")
    try:
        outputs = build_local_outputs(args.input_dir, args.output_dir)
        for label, path in outputs.items():
            logger.info("Created %s at %s", label, path)
            print(f"{label}: {path}")
    except Exception:
        logger.exception("Input preparation failed")
        raise


if __name__ == "__main__":
    main()

