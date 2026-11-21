from __future__ import annotations

import io

import pandas as pd
import plotly.express as px
import streamlit as st

from financial_analytics.demo_data import load_demo_data
from financial_analytics.metrics import summarize_returns


st.set_page_config(page_title="Financial Analytics | Peer Research", page_icon="📈", layout="wide")
st.title("Fund peer comparison")
st.caption("Research prototype · all displayed values are synthetic and for interface demonstration only")

funds, benchmarks = load_demo_data()
categories = sorted(funds["category"].unique())

with st.sidebar:
    st.header("Analysis settings")
    category = st.selectbox("Fund category", categories)
    category_funds = funds.loc[funds["category"] == category]
    min_date = category_funds["date"].min().date()
    max_date = category_funds["date"].max().date()
    selected_dates = st.date_input("Observation period", value=(min_date, max_date), min_value=min_date, max_value=max_date)
    risk_free_rate = st.number_input("Annual risk-free rate (%)", min_value=-10.0, max_value=30.0, value=0.0, step=0.25) / 100
    st.caption("Replace this demo source with approved, licensed, point-in-time data before investment use.")

if isinstance(selected_dates, tuple) and len(selected_dates) == 2:
    start_date, end_date = selected_dates
else:
    start_date, end_date = min_date, max_date

filtered = category_funds.loc[
    category_funds["date"].dt.date.between(start_date, end_date)
].copy()
benchmark = benchmarks.loc[
    (benchmarks["category"] == category)
    & benchmarks["date"].dt.date.between(start_date, end_date), "return"
]

rows = []
for fund_id, group in filtered.groupby("fund_id", sort=False):
    info = group.iloc[0]
    metrics = summarize_returns(group["return"].reset_index(drop=True), benchmark.reset_index(drop=True), risk_free_rate=risk_free_rate)
    rows.append({"Fund": info["fund_name"], "Fund ID": fund_id, **metrics})
summary = pd.DataFrame(rows)

if summary.empty:
    st.warning("No observations are available for this date range.")
    st.stop()

best_return = summary.loc[summary["cagr"].idxmax()]
best_sharpe = summary.loc[summary["sharpe"].idxmax()]
worst_drawdown = summary.loc[summary["max_drawdown"].idxmin()]

metric_cards = st.columns(4)
metric_cards[0].metric("Peer schemes", f"{len(summary)}")
metric_cards[1].metric("Period leader · CAGR", best_return["Fund"], f"{best_return['cagr']:.1%}")
metric_cards[2].metric("Highest Sharpe", best_sharpe["Fund"], f"{best_sharpe['sharpe']:.2f}")
metric_cards[3].metric("Largest drawdown", worst_drawdown["Fund"], f"{worst_drawdown['max_drawdown']:.1%}")

tabs = st.tabs(["Peer metrics", "Historical view", "Definitions & limits"])
with tabs[0]:
    view = st.selectbox("Rank schemes by", ["cagr", "sharpe", "sortino", "information_ratio", "volatility", "tracking_error", "max_drawdown"], format_func=lambda x: x.replace("_", " ").title())
    ascending = view in {"volatility", "tracking_error", "max_drawdown"}
    ranked = summary.sort_values(view, ascending=ascending, na_position="last")
    chart = px.bar(ranked, x=view, y="Fund", orientation="h", color="Fund", title=f"Peer ranking · {view.replace('_', ' ').title()}")
    chart.update_layout(showlegend=False, height=390, xaxis_tickformat=".1%" if view in {"cagr", "volatility", "tracking_error", "max_drawdown"} else None)
    st.plotly_chart(chart, use_container_width=True)
    display = summary[["Fund", "cagr", "volatility", "sharpe", "sortino", "tracking_error", "information_ratio", "max_drawdown"]].copy()
    display.columns = ["Fund", "CAGR", "Volatility", "Sharpe", "Sortino", "Tracking error", "Information ratio", "Max drawdown"]
    st.dataframe(display.style.format({col: "{:.2%}" for col in ["CAGR", "Volatility", "Tracking error", "Max drawdown"]}).format({col: "{:.2f}" for col in ["Sharpe", "Sortino", "Information ratio"]}), hide_index=True, use_container_width=True)
    csv = summary.to_csv(index=False).encode("utf-8")
    st.download_button("Download metrics CSV", csv, file_name="synthetic_peer_metrics.csv", mime="text/csv")

with tabs[1]:
    history = filtered.pivot(index="date", columns="fund_name", values="nav")
    normalized = history.divide(history.iloc[0]).subtract(1)
    fig = px.line(normalized, x=normalized.index, y=normalized.columns, labels={"value": "Cumulative return", "date": "Date", "variable": "Fund"}, title="Growth of 1 unit · rebased to selected period")
    fig.update_yaxes(tickformat=".0%")
    st.plotly_chart(fig, use_container_width=True)
    st.caption("Synthetic weekly NAVs. Historical paths do not imply future performance.")

with tabs[2]:
    st.markdown("""
    **Definitions used in this prototype**

    - CAGR: compound growth over the selected weekly observations, annualized using 52 periods.
    - Volatility: sample standard deviation of weekly returns × √52.
    - Sharpe: (CAGR − selected annual risk-free rate) ÷ annualized volatility.
    - Sortino: (CAGR − selected annual risk-free rate) ÷ annualized downside deviation; weeks above zero count as zero downside.
    - Tracking error: sample standard deviation of weekly fund-minus-category-benchmark returns × √52.
    - Information ratio: mean weekly active return × 52 ÷ tracking error.
    - Maximum drawdown: lowest decline from a prior cumulative wealth peak within the selected period.

    **Limitations:** synthetic observations only; no fees, taxes, transaction costs, survivorship adjustments, corporate actions, or validated benchmark methodology. The calculations are educational and are not investment recommendations.
    """)

st.divider()
st.caption(f"As of {end_date:%d %b %Y} · {start_date:%d %b %Y} to {end_date:%d %b %Y} · source: deterministic synthetic generator")

if st.button("Prepare interactive HTML snapshot"):
    html_chart = px.line(normalized, x=normalized.index, y=normalized.columns, title="Growth of 1 unit · synthetic data").to_html(full_html=False, include_plotlyjs=True)
    table_html = summary.to_html(index=False, float_format=lambda x: f"{x:.4f}", border=0)
    html = f"""<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Synthetic peer comparison</title>
    <style>body{{font:15px Arial,sans-serif;color:#23343a;margin:32px auto;max-width:1250px;padding:0 20px}}h1{{color:#174b3b}}.note{{background:#fff4dc;padding:14px;border-left:4px solid #d29a32}}table{{border-collapse:collapse;width:100%}}th,td{{padding:9px;border-bottom:1px solid #dde5e7;text-align:left}}th{{background:#f2f6f5}}</style>
    <h1>{category} · Peer comparison</h1><p>Period: {start_date} to {end_date} · generated snapshot</p><p class="note"><b>SYNTHETIC DEMO DATA.</b> Not actual fund data; not for investment use.</p>{table_html}{html_chart}</html>"""
    st.download_button("Download HTML snapshot", io.BytesIO(html.encode("utf-8")), file_name="synthetic_peer_comparison.html", mime="text/html")
