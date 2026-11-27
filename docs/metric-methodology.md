# Weekly mutual-fund metric methodology

This document records the formula standard for the weekly fund dashboard and its downloadable HTML report. It explains the selected-window calculations; where a specific weekly report uses an August-end baseline, the same endpoint-return formula applies.

## Weekly observations

- Resample each fund NAV and benchmark series to Friday-ending weeks, using the last available observation in each week.
- Do not use an incomplete current week. For an as-of date before Friday, the latest included observation is the previous completed week.
- Each included interval has weight f = 1. The optional partial-week time adjustment is off.
- Use only dates where fund and benchmark observations overlap for benchmark-relative metrics.

## Metric formulas

Let N be fund NAV, V be the value or wealth index, r_t be weekly fund return, and b_t be weekly benchmark return.

| Metric | Formula |
|---|---|
| Return since baseline | N_end / N_start - 1 |
| Annualized scheme or benchmark return (CAGR) | (V_end / V_start)^(365.25 / elapsed calendar days) - 1 |
| Annualized volatility | Sample standard deviation of weekly scheme returns × sqrt(52) |
| Tracking error | Sample standard deviation of weekly active returns (r_t - b_t) × sqrt(52) |
| Downside deviation | sqrt(52 × mean(min(r_t, 0)^2)); target return is 0% |
| Information Ratio | (Aligned scheme CAGR - aligned benchmark CAGR) / annualized tracking error |
| Sortino Ratio | Scheme CAGR / annualized downside deviation; target return is 0% |
| Sharpe Ratio | (Scheme CAGR - annual risk-free rate) / annualized volatility |
| Drawdown | Weekly NAV / its running peak since the selected baseline - 1 |
| Growth index | 100 × NAV / baseline NAV |

The default annual risk-free rate in the dashboard is 7.20%; the user can change it in the analysis settings. The same rate is not subtracted from Sortino because its target return is explicitly 0%.

## Peer comparisons and ranks

- Compare schemes within the same canonical category and plan type. Direct and Regular plans remain separate.
- Rank eligible schemes within that peer group; rank 1 is best for return, Sharpe, and Information Ratio.
- If a category average is presented, calculate it as an equal-weighted average of eligible schemes.
- Historical weekly metrics, when shown, reuse these formulas at each expanding weekly endpoint.
- Display the actual start/end dates, number of weekly observations, benchmark variant, and risk-free assumption with each result.

## Interpretation and data limits

- A benchmark must represent the scheme mandate. Use a scheme's disclosed benchmark where the app supports official mappings; a manually selected common benchmark is only a research reference.
- PRI excludes dividend reinvestment; TRI includes the source-defined reinvested income. Do not compare them as if they were identical series.
- Alpha and beta use a weekly Jensen regression against the selected benchmark, with the risk-free rate converted to a weekly rate.
- Expense ratio and portfolio turnover require scheme disclosures; they cannot be inferred from NAV history. Forward Ratio remains unavailable until its definition and forward inputs are agreed.
- N/A means the required source data, aligned history, or minimum observations are unavailable. It is not imputed as zero.
