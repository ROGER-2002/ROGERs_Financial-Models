from __future__ import annotations

import html
import re
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from financial_analytics.fund_metrics import calculate_fund_peer_metrics
from financial_analytics.peer_performance import load_peer_data, peer_growth_history

st.set_page_config(page_title="Financial Analytics | Fund Research", page_icon="📈", layout="wide")
st.markdown(
    """
    <style>
      .block-container {max-width: 1680px; padding-top: 1.5rem; padding-bottom: 3rem;}
      .hero {padding: 1.35rem 1.55rem; border: 1px solid #dce8e8; border-radius: 18px;
        background: linear-gradient(115deg, #f0f8f7 0%, #ffffff 62%, #eef4f7 100%);
        margin-bottom: 1.25rem;}
      .hero-kicker {font-size:.72rem; letter-spacing:.12em; text-transform:uppercase;
        font-weight:750; color:#087f70; margin-bottom:.35rem;}
      .hero h1 {font-size: clamp(1.65rem, 3vw, 2.35rem); margin:.1rem 0 .35rem;
        color:#18313b; letter-spacing:-.035em;}
      .hero p {color:#607582; margin:0; font-size:.98rem;}
      div[data-testid="stMetric"] {background:#fff; border:1px solid #dce6e9;
        border-radius:13px; padding:14px 15px; box-shadow:0 5px 18px #1839450a;}
      div[data-testid="stMetric"] label {color:#607582;}
      h2 {letter-spacing:-.02em;}
    </style>
    <section class="hero">
      <div class="hero-kicker">Financial Analytics · Mutual Fund Research</div>
      <h1>Performance, peers &amp; portfolio risk</h1>
      <p>Explore a fund alongside its category and plan peers, with transparent assumptions and interactive analysis.</p>
    </section>
    """,
    unsafe_allow_html=True,
)
st.caption("Research view · results depend on NAV coverage, selected period, and benchmark alignment.")

NAV_PATH = Path("OUTPUT/prepared/fund_nav_history.csv")
MASTER_PATH = Path("MASTER/FUND_PEER_MASTER.csv")
BENCHMARK_PATH = Path("OUTPUT/prepared/benchmark_history.csv")


@st.cache_data(show_spinner="Loading local fund and benchmark data…")
def load_inputs(nav_path: str, master_path: str, benchmark_path: str):
    funds = load_peer_data(Path(nav_path), Path(master_path))
    benchmarks = pd.read_csv(benchmark_path, parse_dates=["date"])
    return funds, benchmarks


missing = [str(p) for p in (NAV_PATH, MASTER_PATH, BENCHMARK_PATH) if not p.exists()]
if missing:
    st.error("Required prepared files are missing: " + ", ".join(missing))
    st.code(
        "python -m financial_analytics.input_pipeline "
        "--input-dir INPUT --output-dir OUTPUT/prepared --log-dir logs"
    )
    st.stop()

try:
    data, benchmark_history = load_inputs(str(NAV_PATH), str(MASTER_PATH), str(BENCHMARK_PATH))
except (OSError, ValueError, KeyError) as exc:
    st.error(f"Could not load local analytics data: {exc}")
    st.stop()

categories = sorted(data.category.dropna().unique().tolist())
with st.sidebar:
    st.header("Analysis settings")
    category = st.selectbox("Fund category", categories)
    plan_options = sorted(data.loc[data.category.eq(category), "plan_type"].dropna().unique())
    plan = st.selectbox("Plan type", plan_options)
    subset = data.loc[data.category.eq(category) & data.plan_type.eq(plan)]
    max_date = subset.nav_date.max().date()
    min_date = subset.nav_date.min().date()
    as_of = st.date_input("As-of date", value=max_date, min_value=min_date, max_value=max_date)
    period_years = st.selectbox(
        "Analysis period",
        [1, 3, 5, 10],
        index=1,
        format_func=lambda n: f"{n} year{'s' if n != 1 else ''}",
    )
    benchmark_ids = sorted(
        benchmark_history.loc[
            benchmark_history.is_valid.astype(str).str.casefold().isin({"true", "1"}),
            "benchmark_id",
        ]
        .dropna()
        .unique()
    )
    chosen_benchmark = st.selectbox("Benchmark (optional)", ["None"] + benchmark_ids)
    annual_rf_pct = st.number_input(
        "Annual risk-free rate (%)", min_value=0.0, max_value=30.0, value=0.0, step=0.25
    )
    st.caption("Direct and Regular plans are always analyzed separately.")

benchmark_id = None if chosen_benchmark == "None" else chosen_benchmark
metrics, drawdowns = calculate_fund_peer_metrics(
    data,
    benchmark_history,
    category,
    plan,
    as_of_date=pd.Timestamp(as_of),
    years=period_years,
    benchmark_id=benchmark_id,
    annual_risk_free_rate=annual_rf_pct / 100,
)
if metrics.empty:
    st.warning("There is not enough NAV history in this peer group for the selected period.")
    st.stop()

labels = {
    f"{r.scheme_name} · {r.scheme_isin}": r.scheme_id for r in metrics.itertuples(index=False)
}
selected_label = st.selectbox("Focus fund", list(labels))
selected_id = labels[selected_label]
focus = metrics.loc[metrics.scheme_id.eq(selected_id)].iloc[0]
latest_date = str(focus.period_end)

st.subheader(f"{focus.scheme_name}")
st.caption(
    f"{category} · {plan} · {period_years}-year window ending {latest_date} · "
    f"{len(metrics)} funds in peer group"
)
context = st.columns(3)
context[0].metric("Peer group", f"{len(metrics)} funds", help="Only funds in the selected category and plan are included.")
context[1].metric("Analysis window", f"{period_years} years", help=f"Selected end date: {latest_date}")
context[2].metric("Benchmark status", "Selected" if benchmark_id else "Not selected",
                  help=benchmark_id or "Benchmark-relative statistics need a manually selected benchmark.")
if benchmark_id:
    series_type = str(focus.benchmark_type)
    st.info(
        f"Benchmark selected: {benchmark_id} ({series_type}). Benchmark selection is manual "
        "because the supplied master does not map each fund to an official benchmark. "
        "PRI excludes dividend reinvestment; use TRI when available and appropriate."
    )
else:
    st.info(
        "Select a benchmark to calculate Information Ratio, Tracking Error, Alpha/Beta, "
        "and drawdown versus benchmark."
    )
if annual_rf_pct == 0:
    st.caption(
        "Risk-free rate is currently 0% because no risk-free series was supplied. "
        "Sharpe, Sortino, and Alpha use this assumption."
    )

metric_specs = [
    ("Return Since", "period_return", ".2%", "Selected analysis window"),
    ("Return Rank", "return_rank", "d", "Rank within category and plan"),
    ("Since Inception Return", "return_since_inception", ".2%", "Cumulative NAV change"),
    ("Since Inception Rank", "return_since_rank", "d", "Rank within category and plan"),
    ("Sharpe Ratio", "sharpe_ratio", ".2f", f"Risk-free rate {annual_rf_pct:.2f}%"),
    ("Sharpe Rank", "sharpe_rank", "d", "Rank within category and plan"),
    ("Sortino Ratio", "sortino_ratio", ".2f", "Downside volatility adjusted"),
    ("Information Ratio", "information_ratio", ".2f", "Requires selected benchmark"),
    ("IR Rank", "ir_rank", "d", "Rank within category and plan"),
    ("Tracking Error", "tracking_error", ".2%", "Annualized active-return volatility"),
    ("Maximum Drawdown", "max_drawdown", ".2%", "Peak-to-trough NAV decline"),
    ("Drawdown vs Benchmark", "drawdown_vs_benchmark", "+.2%", "Fund max drawdown minus benchmark"),
    ("Alpha", "alpha", "+.2%", "Annualized Jensen alpha estimate"),
    ("Beta", "beta", ".2f", "Sensitivity to selected benchmark"),
    ("Expense Ratio", "expense_ratio", ".2%", "Not present in supplied data"),
    ("Portfolio Turnover Rate", "portfolio_turnover_rate", ".2%", "Not present as reported metric"),
    ("Forward Ratio", "forward_ratio", ".2f", "Definition and forward inputs needed"),
]

st.subheader("Key metrics")
st.caption("Cards show the selected fund. Peer ranks are within the chosen category and plan; 1 is best.")
for offset in range(0, len(metric_specs), 4):
    cards = st.columns(4)
    for card, (label, key, fmt, description) in zip(
        cards, metric_specs[offset : offset + 4], strict=False
    ):
        raw = focus.get(key, np.nan)
        val = "N/A" if pd.isna(raw) else format(raw, fmt)
        card.metric(label, val, help=description, border=True)

with st.expander("Why some metrics show N/A", expanded=False):
    st.markdown(
        """
        - **Forward Ratio:** not a standardized mutual-fund performance measure. Please specify
          the exact formula or intended metric (for example forward P/E); forecast estimates
          are not supplied.
        - **Expense Ratio:** scheme-level expense-ratio history is absent from the supplied files.
        - **Portfolio Turnover Rate:** holdings snapshots alone are insufficient to calculate
          the official ratio; purchases/sales and period average net assets are needed.
        - **Benchmark metrics:** require a manually selected index because the master has no
          fund-to-benchmark mapping.
        - **Ranks:** calculated only within the selected category and plan peer group; lower is
          better.
        """
    )


def short_fund_name(name: str, max_length: int = 38) -> str:
    """Shorten repeated plan suffixes for chart labels; retain full name in hover/table."""
    label = re.sub(
        r"\s*\(?G\)?\s*-?\s*(Direct|Regular)\s*Plan\s*$", "", str(name), flags=re.I
    ).strip()
    return label if len(label) <= max_length else label[: max_length - 1].rstrip() + "…"


def peer_bar(metric: str, title: str, *, percent: bool = False) -> go.Figure:
    chart_data = metrics.copy()
    chart_data["chart_label"] = chart_data["scheme_name"].map(short_fund_name)
    duplicate_labels = chart_data["chart_label"].duplicated(keep=False)
    chart_data.loc[duplicate_labels, "chart_label"] = chart_data.loc[duplicate_labels].apply(
        lambda row: f"{row.chart_label} · {str(row.scheme_isin)[-4:]}", axis=1
    )
    chart_data["Fund"] = np.where(
        chart_data.scheme_id.eq(selected_id), "Selected fund", "Peer funds"
    )
    chart_data = chart_data.dropna(subset=[metric]).sort_values(metric, ascending=True)
    fig = px.bar(
        chart_data,
        x=metric,
        y="chart_label",
        color="Fund",
        orientation="h",
        hover_name="scheme_name",
        hover_data={
            "scheme_isin": True,
            metric: ":.2%" if percent else ":.2f",
            "chart_label": False,
        },
        color_discrete_map={"Selected fund": "#247956", "Peer funds": "#a1b9c5"},
        title=title,
        labels={metric: "Return" if metric == "period_return" else title, "chart_label": "Fund"},
    )
    fig.update_layout(
        height=max(390, 34 * max(len(chart_data), 1)),
        margin={"l": 245, "r": 28, "t": 65, "b": 55},
        yaxis={"categoryorder": "array", "categoryarray": chart_data.chart_label.tolist()},
        xaxis_tickformat=".0%" if percent else ".2f",
        legend_title_text="",
        font={"family": "Segoe UI, Arial, sans-serif", "size": 12},
    )
    fig.update_traces(marker_line_width=0)
    return fig


st.markdown("### Peer comparison")
fig = peer_bar("period_return", f"Return over {period_years} year(s)", percent=True)
st.plotly_chart(
    fig,
    width="stretch",
    alt="Selected fund return compared with funds in its category and plan group.",
)
risk_scatter = px.scatter(
    metrics,
    x="annualized_volatility",
    y="period_return",
    color=metrics.scheme_id.eq(selected_id).map({True: "Selected fund", False: "Peer"}),
    size="observations",
    hover_name="scheme_name",
    hover_data=["sharpe_ratio", "sortino_ratio", "max_drawdown"],
    color_discrete_map={"Selected fund": "#087f70", "Peer": "#aab7c4"},
    title="Return versus annualized volatility",
)
risk_scatter.update_layout(
    height=430, xaxis_tickformat=".0%", yaxis_tickformat=".0%", legend_title_text=""
)
st.plotly_chart(
    risk_scatter, width="stretch", alt="Risk and return scatter plot for peer funds."
)

st.subheader("Fund performance path")
st.caption("NAV is rebased to 100 from the first observation in the selected window. Drawdown is measured from the running NAV peak.")
if len(focus_nav) >= 2:
    normalized = focus_nav.assign(value=focus_nav.nav / focus_nav.nav.iloc[0] * 100)
    growth_fig = px.line(
        normalized,
        x="nav_date",
        y="value",
        title="Growth of 100 from first available NAV in window",
        labels={"nav_date": "Date", "value": "Value of 100"},
    )
    growth_fig.update_traces(line_color="#087f70")
    growth_fig.update_layout(height=430)
    st.plotly_chart(
        growth_fig,
        width="stretch",
        alt="Selected fund NAV rebased to 100 at the start of the period.",
    )
else:
    st.info("Not enough observations for the NAV chart.")

focus_dd = drawdowns.loc[drawdowns.scheme_id.eq(selected_id)]
if not focus_dd.empty:
    dd_fig = px.area(
        focus_dd,
        x="date",
        y="drawdown",
        title="Selected fund drawdown",
        labels={"date": "Date", "drawdown": "Drawdown"},
    )
    dd_fig.update_traces(line_color="#c44e52", fillcolor="rgba(196,78,82,0.22)")
    dd_fig.update_layout(height=430, yaxis_tickformat=".0%")
    st.plotly_chart(
        dd_fig, width="stretch", alt="Selected fund drawdown from its prior NAV peak."
    )
else:
    st.info("Drawdown path unavailable.")

if benchmark_id:
    st.subheader("Benchmark-relative view")
    bm_rows = benchmark_history.loc[
        benchmark_history.benchmark_id.eq(benchmark_id)
        & benchmark_history.is_valid.astype(str).str.casefold().isin({"true", "1"})
    ]
    bm = bm_rows.loc[
        pd.to_datetime(bm_rows.date).between(window_start, pd.Timestamp(as_of))
    ].sort_values("date")
    if len(bm) > 1 and len(focus_nav) > 1:
        # Convert benchmark daily closes to monthly endpoints, then normalize both paths.
        bm_month = bm.set_index(pd.to_datetime(bm.date)).close.resample("ME").last().dropna()
        fund_month = focus_nav.set_index("nav_date").nav.resample("ME").last().dropna()
        common = pd.concat(
            [fund_month.rename("Fund"), bm_month.rename("Benchmark")], axis=1
        ).dropna()
        if len(common) > 1:
            wealth = common / common.iloc[0] * 100
            g = px.line(
                wealth.reset_index(names="date"),
                x="date",
                y=["Fund", "Benchmark"],
                title="Growth of 100 · selected fund versus benchmark",
            )
            st.plotly_chart(
                g,
                width="stretch",
                alt="Normalized selected fund and benchmark performance over time.",
            )
            comp = pd.DataFrame(
                {
                    "Fund": wealth.Fund / wealth.Fund.cummax() - 1,
                    "Benchmark": wealth.Benchmark / wealth.Benchmark.cummax() - 1,
                }
            ).reset_index(names="date")
            dg = px.line(
                comp,
                x="date",
                y=["Fund", "Benchmark"],
                title="Drawdown versus benchmark",
                labels={"value": "Drawdown"},
            )
            dg.update_layout(yaxis_tickformat=".0%")
            st.plotly_chart(dg, width="stretch", alt="Fund and selected benchmark drawdown paths.")
        else:
            st.info("Fund and benchmark do not have enough overlapping monthly observations.")

st.subheader("Peer metric heatmap")
st.caption("Compare funds across return and risk measures. Blank cells mean the required inputs or history are unavailable.")
heat_cols = [
    ("period_return", "Period Return"),
    ("sharpe_ratio", "Sharpe"),
    ("sortino_ratio", "Sortino"),
    ("information_ratio", "Info Ratio"),
    ("max_drawdown", "Max Drawdown"),
]
heat = metrics.set_index("scheme_name")[[k for k, _ in heat_cols]].copy()
heat.columns = [label for _, label in heat_cols]
heat = heat.rename(index=lambda name: f"★ {name}" if name == focus.scheme_name else name)
if heat.notna().any().any():
    heat_fig = px.imshow(
        heat,
        aspect="auto",
        color_continuous_scale="RdYlGn",
        color_continuous_midpoint=0,
        title="Metric values by fund (blank where unavailable)",
    )
    heat_fig.update_layout(height=max(380, len(heat) * 24))
    st.plotly_chart(
        heat_fig,
        width="stretch",
        alt="Heatmap comparing return and risk metrics across peer funds.",
    )
else:
    st.info("Heatmap unavailable for this peer group and benchmark selection.")

st.subheader("Peer metrics table")
st.caption("Use the download button below to retain the underlying peer metrics as CSV.")
display_cols = [
    "scheme_name",
    "period_return",
    "return_rank",
    "return_since_inception",
    "return_since_rank",
    "sharpe_ratio",
    "sharpe_rank",
    "sortino_ratio",
    "information_ratio",
    "ir_rank",
    "tracking_error",
    "alpha",
    "beta",
    "max_drawdown",
    "drawdown_vs_benchmark",
    "expense_ratio",
    "portfolio_turnover_rate",
    "forward_ratio",
    "observations",
]
st.dataframe(
    metrics[display_cols]
    .rename(
        columns={
            "scheme_name": "Fund",
            "period_return": "Return Since",
            "return_rank": "Return Rank",
            "return_since_inception": "Since Inception Return",
            "return_since_rank": "Since Inception Rank",
            "sharpe_ratio": "Sharpe Ratio",
            "sharpe_rank": "Sharpe Rank",
            "sortino_ratio": "Sortino Ratio",
            "information_ratio": "Information Ratio",
            "ir_rank": "IR Rank",
            "tracking_error": "Tracking Error",
            "alpha": "Alpha",
            "beta": "Beta",
            "max_drawdown": "Maximum Drawdown",
            "drawdown_vs_benchmark": "Drawdown vs Benchmark",
            "expense_ratio": "Expense Ratio",
            "portfolio_turnover_rate": "Portfolio Turnover Rate",
            "forward_ratio": "Forward Ratio",
            "observations": "Monthly observations",
        }
    )
    .style.format(
        {
            "Return Since": "{:.2%}",
            "Since Inception Return": "{:.2%}",
            "Sharpe Ratio": "{:.2f}",
            "Sortino Ratio": "{:.2f}",
            "Information Ratio": "{:.2f}",
            "Tracking Error": "{:.2%}",
            "Alpha": "{:.2%}",
            "Beta": "{:.2f}",
            "Maximum Drawdown": "{:.2%}",
            "Drawdown vs Benchmark": "{:+.2%}",
            "Expense Ratio": "{:.2%}",
            "Portfolio Turnover Rate": "{:.2%}",
            "Forward Ratio": "{:.2f}",
        },
        na_rep="N/A",
    ),
    hide_index=True,
    width="stretch",
)

st.download_button(
    "Download peer metric CSV",
    metrics.to_csv(index=False).encode("utf-8"),
    file_name=(
        f"{re.sub(r'[^a-z0-9]+', '-', category.lower()).strip('-')}-{plan.lower()}-metrics.csv"
    ),
    mime="text/csv",
)

with st.expander("Definitions and interpretation"):
    st.markdown(
        """
        - **Sharpe:** annualized excess return divided by annualized volatility.
        - **Sortino:** annualized excess return divided by downside deviation.
        - **Tracking Error:** annualized standard deviation of monthly active returns.
        - **Information Ratio:** annualized average active return divided by Tracking Error.
        - **Alpha / Beta:** annualized regression intercept and benchmark sensitivity estimate.
        - **Drawdown vs Benchmark:** fund max drawdown minus benchmark max drawdown; negative
          means the fund's worst decline was deeper.
        - **Ranks:** ascending rank number, with 1 best.
        - **Return Since:** cumulative return for the selected period. Since-inception return
          uses each scheme's first and latest available NAV.
        - Metrics use the supplied Adjusted NAV observations. Past results do not predict future
          performance.
        """
    )

# Build a standalone report following the supplied reference's hierarchy:
# report heading, selected-scheme cards, peer legend, then one chart section per metric.
report_metric_labels = {
    "scheme_name": "Fund",
    "period_return": "Return in period",
    "return_rank": "Return rank",
    "return_since_inception": "Since-inception return",
    "return_since_rank": "Since-inception rank",
    "sharpe_ratio": "Sharpe ratio",
    "sharpe_rank": "Sharpe rank",
    "sortino_ratio": "Sortino ratio",
    "information_ratio": "Information ratio",
    "ir_rank": "IR rank",
    "tracking_error": "Tracking error",
    "alpha": "Alpha",
    "beta": "Beta",
    "max_drawdown": "Maximum drawdown",
    "drawdown_vs_benchmark": "Drawdown vs benchmark",
    "expense_ratio": "Expense ratio",
    "portfolio_turnover_rate": "Portfolio turnover rate",
    "forward_ratio": "Forward ratio",
    "observations": "Monthly observations",
}
report_table = metrics[display_cols].rename(columns=report_metric_labels).copy()
report_table["Fund"] = report_table["Fund"].map(html.escape)
for column in [
    "Return in period",
    "Since-inception return",
    "Tracking error",
    "Alpha",
    "Maximum drawdown",
    "Drawdown vs benchmark",
    "Expense ratio",
    "Portfolio turnover rate",
]:
    report_table[column] = report_table[column].map(
        lambda value: f"{value:.2%}" if pd.notna(value) else "N/A"
    )
for column in ["Sharpe ratio", "Sortino ratio", "Information ratio", "Beta", "Forward ratio"]:
    report_table[column] = report_table[column].map(
        lambda value: f"{value:.2f}" if pd.notna(value) else "N/A"
    )
for column in [
    "Return rank",
    "Since-inception rank",
    "Sharpe rank",
    "IR rank",
    "Monthly observations",
]:
    report_table[column] = report_table[column].map(
        lambda value: str(int(value)) if pd.notna(value) else "N/A"
    )
table_html = report_table.to_html(
    index=False,
    escape=False,
    border=0,
    na_rep="N/A",
    float_format=lambda value: f"{value:.2%}" if abs(value) < 1 else f"{value:.2f}",
    classes="peer-table",
)


def metric_display(key: str, format_spec: str) -> str:
    value = focus.get(key, np.nan)
    return "N/A" if pd.isna(value) else format(value, format_spec)


card_reasons = {
    "Information Ratio": "Needs a selected benchmark and enough aligned monthly returns.",
    "IR Rank": "Needs a valid Information Ratio for enough peer funds.",
    "Tracking Error": "Needs overlapping fund and benchmark return observations.",
    "Drawdown vs Benchmark": "Needs a selected benchmark with overlapping history.",
    "Alpha": "Needs a selected benchmark and sufficient overlapping returns.",
    "Beta": "Needs a selected benchmark with varying returns.",
    "Expense Ratio": "Scheme-level expense-ratio data was not supplied.",
    "Portfolio Turnover Rate": "Official turnover inputs were not supplied.",
    "Forward Ratio": "Please define the intended formula and supply forward estimates.",
    "Sharpe Ratio": "Needs sufficient period history and non-zero volatility.",
    "Sortino Ratio": "Needs sufficient period history and downside observations.",
    "Return Rank": "Insufficient NAV coverage for the selected period.",
    "Sharpe Rank": "Insufficient valid Sharpe values in this peer group.",
    "Return Since": "Insufficient NAV coverage for the selected period.",
    "Since Inception Return": "Needs at least two valid NAV observations.",
    "Since Inception Rank": "Needs at least two valid NAV observations.",
    "Maximum Drawdown": "Insufficient NAV coverage for the selected period.",
}
metric_card_html = []
html_metric_order = [
    "Information Ratio",
    "Sortino Ratio",
    "Tracking Error",
    "IR Rank",
    "Maximum Drawdown",
    "Drawdown vs Benchmark",
    "Sharpe Ratio",
    "Sharpe Rank",
    "Return Since",
    "Return Rank",
    "Since Inception Return",
    "Since Inception Rank",
    "Alpha",
    "Beta",
    "Expense Ratio",
    "Portfolio Turnover Rate",
    "Forward Ratio",
]
specs_by_label = {
    label: (key, format_spec, description) for label, key, format_spec, description in metric_specs
}
for label in html_metric_order:
    key, format_spec, description = specs_by_label[label]
    value = metric_display(key, format_spec)
    reason = card_reasons.get(label, description) if value == "N/A" else description
    metric_card_html.append(
        f"<article class='metric'><span>{html.escape(label)}</span>"
        f"<strong>{html.escape(value)}</strong><small>{html.escape(reason)}</small></article>"
    )

report_charts = []
chart_specs = [
    ("period_return", f"Return over {period_years} year(s)", True),
    ("information_ratio", "Information Ratio", False),
    ("sortino_ratio", "Sortino Ratio", False),
    ("tracking_error", "Tracking Error (annualized)", True),
    ("sharpe_ratio", "Sharpe Ratio", False),
    ("max_drawdown", "Maximum Drawdown", True),
    ("drawdown_vs_benchmark", "Drawdown vs Benchmark", True),
    ("alpha", "Alpha", True),
    ("beta", "Beta", False),
    ("return_rank", "Return Rank (1 is best)", False),
    ("sharpe_rank", "Sharpe Rank (1 is best)", False),
    ("ir_rank", "Information Ratio Rank (1 is best)", False),
    ("return_since_inception", "Since-Inception Return", True),
    ("expense_ratio", "Expense Ratio", True),
    ("portfolio_turnover_rate", "Portfolio Turnover Rate", True),
    ("forward_ratio", "Forward Ratio", False),
]
include_plotly = True
for metric_key, metric_title, is_percent in chart_specs:
    if metrics[metric_key].notna().any():
        chart = peer_bar(metric_key, metric_title, percent=is_percent)
        chart_html = chart.to_html(
            full_html=False,
            include_plotlyjs=include_plotly,
            config={"responsive": True, "displaylogo": False},
        )
        include_plotly = False
        report_charts.append(
            f"<section class='chart-section'><h2>{html.escape(metric_title)}</h2>"
            f"<p class='chart-meta'>Selected fund highlighted against {len(metrics) - 1} peers · "
            f"{period_years}-year period ending {html.escape(latest_date)}</p>"
            f"{chart_html}</section>"
        )

growth_for_report = peer_growth_history(
    data,
    category,
    plan,
    selected_id,
    as_of_date=pd.Timestamp(as_of),
    years=period_years,
)
if not growth_for_report.empty:
    growth_chart = px.line(
        growth_for_report,
        x="nav_date",
        y=["Selected fund", "Peer median"],
        title="Growth of 100 · selected fund and peer median",
        labels={"nav_date": "Date", "value": "Value of 100", "variable": "Series"},
        color_discrete_map={"Selected fund": "#247956", "Peer median": "#a1b9c5"},
    )
    growth_chart.update_layout(height=430, hovermode="x unified")
    growth_html = growth_chart.to_html(
        full_html=False,
        include_plotlyjs=include_plotly,
        config={"responsive": True, "displaylogo": False},
    )
    include_plotly = False
    report_charts.append(
        "<section class='chart-section'><h2>Scheme Performance</h2>"
        "<p class='chart-meta'>Growth of 100 · fund versus category-plan peer median</p>"
        f"{growth_html}</section>"
    )

if benchmark_id:
    report_benchmark = benchmark_history.loc[
        benchmark_history.benchmark_id.eq(benchmark_id)
        & benchmark_history.is_valid.astype(str).str.casefold().isin({"true", "1"})
    ].copy()
    report_benchmark["date"] = pd.to_datetime(report_benchmark["date"], errors="coerce")
    report_benchmark["close"] = pd.to_numeric(report_benchmark["close"], errors="coerce")
    report_benchmark = report_benchmark.dropna(subset=["date", "close"]).sort_values("date")
    report_benchmark = report_benchmark.loc[
        report_benchmark.date.between(window_start, pd.Timestamp(as_of))
    ]
    report_benchmark_monthly = (
        report_benchmark.set_index("date")["close"].resample("ME").last().dropna()
    )
    report_fund_monthly = focus_nav.set_index("nav_date")["nav"].resample("ME").last().dropna()
    report_paths = pd.concat(
        [report_fund_monthly.rename("Selected fund"), report_benchmark_monthly.rename("Benchmark")],
        axis=1,
    ).dropna()
    if len(report_paths) > 1:
        report_drawdowns = report_paths / report_paths.iloc[0]
        report_drawdowns = report_drawdowns.div(report_drawdowns.cummax()).sub(1)
        report_drawdown_figure = px.line(
            report_drawdowns.reset_index(names="Date"),
            x="Date",
            y=["Selected fund", "Benchmark"],
            title="Drawdown since the start of the selected period",
            labels={"value": "Drawdown", "variable": "Series"},
            color_discrete_map={"Selected fund": "#247956", "Benchmark": "#a1b9c5"},
        )
        report_drawdown_figure.update_layout(height=430, yaxis_tickformat=".0%")
        drawdown_html = report_drawdown_figure.to_html(
            full_html=False,
            include_plotlyjs=include_plotly,
            config={"responsive": True, "displaylogo": False},
        )
        include_plotly = False
        report_charts.append(
            "<section class='chart-section'><h2>Drawdown vs Benchmark</h2>"
            f"<p class='chart-meta'>{html.escape(str(focus.scheme_name))} vs "
            f"{html.escape(benchmark_id)} · aligned monthly observations</p>"
            f"{drawdown_html}</section>"
        )

if benchmark_id:
    benchmark_kind = str(focus.benchmark_type).upper()
    benchmark_note = (
        f"Selected benchmark: {html.escape(benchmark_id)} ({html.escape(benchmark_kind)}). "
        + (
            "PRI excludes dividends."
            if benchmark_kind == "PRI"
            else "TRI includes reinvested dividends, as defined by the source series."
            if benchmark_kind == "TRI"
            else "Check the benchmark return convention before interpreting results."
        )
    )
else:
    benchmark_note = (
        "Benchmark-relative measures are unavailable until you select a benchmark in the app."
    )
top_cards = "".join(metric_card_html)
charts_html = "".join(report_charts)
template_path = Path("templates/fund_peer_report.html")
report = template_path.read_text(encoding="utf-8")
report_values = {
    "__PAGE_TITLE__": f"{html.escape(str(focus.scheme_name))} · Fund Peer Comparison",
    "__CATEGORY__": html.escape(category),
    "__FOCUS_FUND__": html.escape(str(focus.scheme_name)),
    "__PLAN__": html.escape(plan),
    "__AS_OF__": html.escape(latest_date),
    "__PERIOD__": str(period_years),
    "__PEER_COUNT__": str(len(metrics)),
    "__BENCHMARK__": html.escape(benchmark_id or "No benchmark selected"),
    "__BENCHMARK_NOTE__": benchmark_note,
    "__METRIC_CARDS__": top_cards,
    "__CHART_SECTIONS__": charts_html,
    "__METRICS_TABLE__": table_html,
}
for placeholder, value in report_values.items():
    report = report.replace(placeholder, value)
st.download_button(
    "Download interactive HTML report",
    report.encode("utf-8"),
    file_name="fund-peer-analytics.html",
    mime="text/html",
)
