"""Build the local fund peer master from prepared NAV metadata."""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Any

import pandas as pd

from financial_analytics.peer_performance import CATEGORY_ALIASES, canonicalize_category

KEY = ["scheme_id", "plan_type"]
METADATA = ["scheme_code", "scheme_isin", "scheme_name", "category"]


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")


def build_peer_master(nav: pd.DataFrame) -> pd.DataFrame:
    """Create one local mapping row per scheme and plan from canonical NAV rows."""
    required = {
        "scheme_id",
        "scheme_code",
        "scheme_isin",
        "scheme_name",
        "category",
        "plan_type",
        "nav_date",
        "nav",
        "is_valid",
        "source_file",
    }
    missing = required.difference(nav.columns)
    if missing:
        raise ValueError(f"Prepared NAV is missing columns: {', '.join(sorted(missing))}")

    data = nav.copy()
    data["scheme_id"] = data["scheme_id"].astype("string").str.strip()
    data["plan_type"] = data["plan_type"].astype("string").str.strip().str.title()
    data["nav_date"] = pd.to_datetime(data["nav_date"], errors="coerce")
    data["nav"] = pd.to_numeric(data["nav"], errors="coerce")
    valid = data["is_valid"].astype(str).str.casefold().isin({"true", "1", "yes"})
    data = data.loc[
        valid
        & data["scheme_id"].notna()
        & data["plan_type"].isin({"Direct", "Regular"})
        & data["nav_date"].notna()
        & data["nav"].gt(0)
    ].copy()
    if data.empty:
        raise ValueError("No valid scheme NAV records are available to build the peer master.")

    records: list[dict[str, Any]] = []
    for (scheme_id, plan_type), rows in data.groupby(KEY, sort=True):
        metadata: dict[str, str] = {}
        for column in METADATA:
            values = rows[column].dropna().astype(str).str.strip().unique()
            if len(values) != 1:
                raise ValueError(
                    f"Expected one {column} value for scheme {scheme_id} ({plan_type}); "
                    f"found {len(values)}."
                )
            metadata[column] = values[0]
        source_category = metadata["category"]
        category = canonicalize_category(source_category)
        sources = sorted(rows["source_file"].dropna().astype(str).str.strip().unique())
        records.append(
            {
                "scheme_id": str(scheme_id),
                "scheme_code": metadata["scheme_code"],
                "scheme_isin": metadata["scheme_isin"],
                "scheme_name": metadata["scheme_name"],
                "source_category": source_category,
                "category": category,
                "plan_type": str(plan_type),
                "peer_group_id": f"{_slug(category)}__{_slug(str(plan_type))}",
                "peer_group_name": f"{category} | {plan_type} peer group",
                "first_nav_date_in_source": rows["nav_date"].min().date().isoformat(),
                "latest_nav_date_in_source": rows["nav_date"].max().date().isoformat(),
                "nav_observation_count": int(rows["nav_date"].nunique()),
                "source_files": "; ".join(sources),
                "mapping_basis": (
                    "Canonical category + plan type; Direct and Regular kept separate"
                ),
                "mapping_status": "SOURCE_CATEGORY_WITH_USER_CONFIRMED_ALIASES",
            }
        )
    master = pd.DataFrame(records)
    if master.duplicated(KEY).any():
        raise ValueError("Generated peer master has duplicate scheme and plan keys.")
    return master.sort_values(
        ["category", "plan_type", "scheme_name"], key=lambda col: col.str.casefold()
    ).reset_index(drop=True)


def category_crosswalk() -> pd.DataFrame:
    """Return the confirmed source-name aliases used for category grouping."""
    rows = [
        {
            "source_category": source,
            "canonical_category": canonical,
            "confirmation": "User-confirmed alias",
        }
        for source, canonical in CATEGORY_ALIASES.items()
    ]
    for canonical in sorted(set(CATEGORY_ALIASES.values())):
        rows.append(
            {
                "source_category": canonical,
                "canonical_category": canonical,
                "confirmation": "Canonical label",
            }
        )
    return pd.DataFrame(rows).sort_values("source_category").reset_index(drop=True)


def write_peer_master(nav_file: Path, master_dir: Path) -> tuple[Path, Path]:
    """Write peer master and alias crosswalk locally; neither contains NAV history."""
    nav = pd.read_csv(nav_file, dtype={"scheme_id": "string", "plan_type": "string"})
    master = build_peer_master(nav)
    master_dir = Path(master_dir)
    master_dir.mkdir(parents=True, exist_ok=True)
    master_path = master_dir / "FUND_PEER_MASTER.csv"
    crosswalk_path = master_dir / "CATEGORY_CROSSWALK.csv"
    master.to_csv(master_path, index=False, encoding="utf-8-sig")
    category_crosswalk().to_csv(crosswalk_path, index=False, encoding="utf-8-sig")
    return master_path, crosswalk_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--nav-file",
        type=Path,
        default=Path("OUTPUT/prepared/fund_nav_history.csv"),
    )
    parser.add_argument("--master-dir", type=Path, default=Path("MASTER"))
    args = parser.parse_args()
    master_path, crosswalk_path = write_peer_master(args.nav_file, args.master_dir)
    print(f"Fund peer master: {master_path}")
    print(f"Category crosswalk: {crosswalk_path}")


if __name__ == "__main__":
    main()
