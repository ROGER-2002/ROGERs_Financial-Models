import csv
from datetime import date

import pyarrow.parquet as pq
from openpyxl import Workbook

from financial_analytics.stock_price_pipeline import build_stock_price_outputs


def test_streams_observed_prices_and_tracks_missing_coverage(tmp_path) -> None:
    source = tmp_path / "sample.xlsx"
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["Date", "AAA-NSE", "BBB-NSE"])
    sheet.append([date(2020, 1, 1), 10.0, "#N/A"])
    sheet.append([date(2020, 1, 2), 11.0, 12.0])
    sheet.append([date(2020, 1, 3), "#N/A", 13.0])
    sheet.append([date(2020, 1, 4), 0.0, None])
    workbook.save(source)

    outputs = build_stock_price_outputs(source, tmp_path / "prepared", chunk_rows=2)

    table = pq.read_table(outputs["prices"])
    assert table.num_rows == 5
    assert table.column("quality_issue_codes").to_pylist().count("non_positive_close") == 1

    with outputs["coverage"].open(newline="", encoding="utf-8") as coverage_file:
        coverage = {row["symbol"]: row for row in csv.DictReader(coverage_file)}

    assert coverage["AAA-NSE"]["first_observed_date"] == "2020-01-01"
    assert coverage["AAA-NSE"]["missing_within_history"] == "1"
    assert coverage["AAA-NSE"]["non_positive_price_count"] == "1"
    assert coverage["BBB-NSE"]["missing_before_first"] == "1"
    assert coverage["BBB-NSE"]["missing_after_last"] == "1"

    report = outputs["report"].read_text(encoding="utf-8")
    assert "Expected `#N/A` cells preserved as missing: 2." in report
    assert "Explicit blank cells: 1." in report

