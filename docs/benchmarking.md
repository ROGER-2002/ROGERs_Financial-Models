# Fund benchmark selection guide

## How to choose a benchmark

Use the scheme's currently disclosed **Tier 1 benchmark** from its Scheme Information Document (SID), Key Information Memorandum (KIM), or current factsheet as the official comparison. Do not infer the official benchmark from a category label alone. A scheme may have a different benchmark because its objective, allocation, or strategy differs from other funds in that category.

SEBI's March 2026 Master Circular says that benchmark selection should reflect the scheme's investment objective, asset allocation, and strategy. It describes first-tier benchmarks as category-representative, with an optional second-tier index for investment style. It also says TRI is more appropriate because it includes dividends and interest, and requires TRI for scheme performance comparison when available. [SEBI Master Circular, sections 7.22–7.23](https://www.sebi.gov.in/sebi_data/attachdocs/mar-2026/1774024028162.pdf)

AMFI publishes the intended first-tier benchmark list by scheme category. Check the latest [AMFI benchmark list](https://www.amfiindia.com/otherdata/listofbenchmarkindices) when maintaining the mapping.

## Working category guide for the current inputs

These are starting points for the **category-level research view**. They are not a substitute for each scheme's official benchmark disclosure.

| Fund category | Benchmark to look for in the scheme disclosure | Availability in current prepared data | Guidance |
|---|---|---|---|
| Large Cap | NIFTY 100 TRI or another disclosed broad large-cap Tier 1 TRI | NIFTY 100 is present as PRI; NIFTY 50 TRI is present | Obtain NIFTY 100 TRI. NIFTY 50 TRI is a narrower, more concentrated secondary comparison, not an automatic replacement. |
| Large & Mid Cap | NIFTY LargeMidcap 250 TRI | Available | Good category-level match. This index is a 250-stock blend of 100 large-cap and 150 mid-cap companies, weighted 50% to each segment. |
| Mid Cap | NIFTY Midcap 150 TRI | Only NIFTY Midcap 150 PRI is present | Obtain the TRI series before using it as a total-return benchmark. |
| Small Cap | NIFTY Smallcap 250 TRI | Only NIFTY Smallcap 100 PRI is present | Obtain the correct Smallcap 250 TRI. Smallcap 100 is not equivalent. |
| Flexi Cap | NIFTY 500 TRI is a common Tier 1 benchmark | Available | Verify the selected scheme SID. Example scheme documents use NIFTY 500 TRI. |
| ELSS / Tax Saver | NIFTY 500 TRI is a common Tier 1 benchmark | Available | Verify the scheme's latest SID. Direct and Regular plans of the same scheme normally share the scheme benchmark. |
| Multi Cap | NIFTY 500 Multicap 50:25:25 TRI | Not available; NIFTY 500 TRI is available | Obtain the multicap 50:25:25 TRI. Broad NIFTY 500 TRI does not keep the 50/25/25 segment weights. |
| Aggressive Hybrid | A disclosed hybrid equity/debt composite, such as an Aggressive 65:35 TRI | Not available | Do not use an all-equity index as the sole official benchmark for a mixed equity/debt fund. |
| Balanced, Conservative Hybrid, Balanced Advantage, Equity Savings, Multi Asset | Scheme-specific composite/bespoke benchmark matching its asset allocation | Not available in the current benchmark set | Obtain the exact index components and weights from the scheme disclosure and source series. |
| Debt, Liquid, Overnight, Arbitrage | Debt or arbitrage benchmark matching duration, credit quality, and portfolio mix | Not available in the current benchmark set | Obtain the relevant AMFI Tier 1 debt/arbitrage benchmark. An equity index is not suitable. |
| Sector or Thematic | The sector/theme index matching the scheme mandate | Not available in the current benchmark set | Use the specific theme index. The user's canonical “Multi Sector Fund” label alone is not enough to infer a benchmark. |

The new NIFTY 50 TRI and NIFTY 500 TRI files are now included in `OUTPUT/prepared/benchmark_history.csv`. The 50 TRI is useful as a broad large-company comparison, and the 500 TRI as a broad equity-market comparison. They do not replace category-specific or scheme-disclosed benchmarks when those are different.

**Index-name check:** the supplied `NIFTY LargeMidcap 250 - TRI.xlsx` is the LargeMidcap 250 composite, not a pure Midcap 250 index. NSE describes it as 100 large-cap plus 150 mid-cap companies with a 50/50 segment weighting. The current inputs contain NIFTY Midcap 150 PRI, but not NIFTY Midcap 150 TRI or a pure 250-stock mid-cap TRI series. [NSE Index profile](https://niftyindices.com/indices/equity/broad-based-indices/nifty-largemidcap-250)

## How the app should use the benchmark

- The current benchmark selector applies one **common reference index** to the selected category/plan peer group. This makes peer risk-adjusted measures comparable to the same market reference.
- Treat that as a research comparison until the Master contains each scheme's official benchmark.
- For official scheme reporting, add a benchmark mapping keyed by stable scheme ID, with benchmark ID, series type, effective-from and effective-to dates, source document, and verification date.
- Keep Direct and Regular plans separate for peer rankings. They usually share the underlying scheme benchmark, but use the same benchmark history only after confirming that they are the same scheme and mandate.
- Never join a PRI and TRI series under one ID. Keep each benchmark variant uniquely named and labeled.
- For long histories that predate the benchmark TRI launch, use the applicable PRI-to-TRI composite-return method described by SEBI; do not silently fill the missing period with an unrelated index.

## Verified examples

- SEBI's current circular gives NSE 100/BSE 100 as broad first-tier examples for Large Cap and says a benchmark should reflect the scheme category. [SEBI Master Circular](https://www.sebi.gov.in/sebi_data/attachdocs/mar-2026/1774024028162.pdf)
- Recent official scheme documents use NIFTY 500 TRI for Flexi Cap and ELSS, NIFTY LargeMidcap 250 TRI for Large & Mid Cap, NIFTY Midcap 150 TRI for Mid Cap, and NIFTY 500 Multicap 50:25:25 TRI for Multi Cap. [Flexi Cap SID](https://www.sebi.gov.in/sebi_data/attachdocs/mar-2025/1742466793745.pdf), [ELSS SID](https://portal.amfiindia.com/spages/13608.pdf), [Large & Mid Cap factsheet](https://www.invescomutualfund.com/docs/default-source/factsheet/invesco-factsheet---may-2025.pdf), [Mid Cap SID](https://portal.amfiindia.com/spages/14260.pdf), [Multi Cap SID](https://portal.amfiindia.com/spages/14123.pdf)
- Aggressive Hybrid scheme documents commonly disclose a hybrid 35+65 benchmark or NIFTY 50 Hybrid Composite Debt 65:35 TRI. The exact benchmark is scheme-specific. [Aggressive Hybrid SID example](https://portal.amfiindia.com/spages/1512.pdf)
