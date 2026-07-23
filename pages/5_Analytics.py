import streamlit as st
from streamlit_echarts import st_echarts

from utils import calculations as calc
from utils import charts
from utils import sheets
from utils.styling import inject_css, metrics_grid, fmt_money

st.set_page_config(page_title="Analytics — Founder Revenue OS", page_icon="📊", layout="wide")
inject_css()

if not st.session_state.get("authenticated"):
    st.warning("Please log in from the main page first.")
    st.stop()

sheets.bootstrap_sheets()

st.title("📊 Analytics")

projects = sheets.read_sheet("Projects")
payments = sheets.read_sheet("Payments")
saas_monthly = sheets.read_sheet("SaaSMonthly")
saas_transactions = sheets.read_sheet("SaaSTransactions")
expenses = sheets.read_sheet("Expenses")
settings = sheets.read_sheet("Settings")

base_currency = calc.get_base_currency(settings)
rates = calc.get_fx_rates(settings)

payments_with_currency = None
if not payments.empty and not projects.empty:
    payments_with_currency = payments.merge(projects[["project_id", "currency"]], on="project_id", how="left")
missing = calc.missing_fx_currencies(
    projects, payments_with_currency, saas_monthly, saas_transactions, expenses, rates=rates
)
if missing:
    st.warning(
        f"No exchange rate saved for: **{', '.join(missing)}**. These are treated as "
        f"1:1 with {base_currency} below — fix in Settings → Exchange Rates."
    )

enriched = calc.enrich_projects(projects, payments, rates, base_currency)
stream_monthly = calc.stream_revenue_monthly(payments, projects, saas_monthly, saas_transactions, rates, base_currency)

if stream_monthly.empty:
    st.info("Log some revenue first (Consulting Payments or SaaS Revenue) to unlock analytics.")
    st.stop()

st.caption(f"All figures on this page are converted to your reporting currency, **{base_currency}**, before being combined across clients/streams/currencies.")

top_client, top_client_rev = calc.largest_client(enriched)
avg_value = calc.average_project_value(projects, rates, base_currency)
by_stream_total = calc.revenue_by_stream_total(stream_monthly)
top_stream = by_stream_total.iloc[0] if not by_stream_total.empty else None

outstanding_total = enriched["outstanding_balance_base"].sum() if not enriched.empty else 0.0
metrics_grid([
    ("Top Revenue Stream",
     top_stream["stream"] if top_stream is not None else "—",
     fmt_money(top_stream["revenue"], base_currency) if top_stream is not None else ""),
    ("Largest Client",
     top_client or "—",
     fmt_money(top_client_rev, base_currency) if top_client else ""),
    ("Avg. Consulting Project Value", fmt_money(avg_value, base_currency), ""),
    ("Outstanding Receivables", fmt_money(outstanding_total, base_currency), ""),
], columns=2)

st.divider()

st.subheader(f"Revenue Growth, Cumulative, Combined ({base_currency})")
combined = calc.combined_monthly_revenue(stream_monthly)
if not combined.empty:
    combined = combined.sort_values("month")
    combined["cumulative"] = combined["revenue"].cumsum()
    opts = charts.area_growth_chart(combined["month"].tolist(), combined["cumulative"].round(2).tolist(), axis_name=base_currency)
    st_echarts(options=opts, height="320px")

st.subheader(f"Per-Stream Profit ({base_currency})")
st.caption("Revenue by stream, minus expenses tagged to that same stream. Untagged/General expenses aren't split — see Combined Net Profit on the dashboard for the full picture.")
exp_by_stream = calc.expense_by_stream(expenses, rates, base_currency)
profit_table = by_stream_total.merge(exp_by_stream, left_on="stream", right_on="stream", how="left").fillna(0)
profit_table = profit_table.rename(columns={"amount": "tagged_expenses"})
if "tagged_expenses" not in profit_table.columns:
    profit_table["tagged_expenses"] = 0.0
profit_table["stream_profit"] = profit_table["revenue"] - profit_table["tagged_expenses"]
display_table = profit_table.copy()
for col in ["revenue", "tagged_expenses", "stream_profit"]:
    display_table[col] = display_table[col].map(lambda v: fmt_money(v, base_currency))
st.dataframe(display_table, use_container_width=True, hide_index=True)

col_a, col_b = st.columns(2)
with col_a:
    st.subheader(f"Outstanding Receivables by Client ({base_currency})")
    unpaid = enriched[enriched["outstanding_balance_base"] > 0] if not enriched.empty else enriched
    if not unpaid.empty:
        rb = unpaid.groupby("client_name")["outstanding_balance_base"].sum().reset_index().sort_values(
            "outstanding_balance_base", ascending=False
        )
        opts = charts.horizontal_bar_chart(rb["client_name"].tolist(), rb["outstanding_balance_base"].round(2).tolist(), axis_name=base_currency)
        st_echarts(options=opts, height="320px")
    else:
        st.caption("Nothing outstanding — fully collected! 🎉")

with col_b:
    st.subheader(f"Expense Trends ({base_currency})")
    exp_trend = calc.monthly_expense_series(expenses, rates, base_currency)
    if not exp_trend.empty:
        opts = charts.area_growth_chart(exp_trend["month"].tolist(), exp_trend["expense"].round(2).tolist(),
                                         axis_name=base_currency, color=charts.PALETTE[4])
        st_echarts(options=opts, height="320px")
    else:
        st.caption("No expenses recorded yet.")

st.subheader(f"Expense Distribution by Category ({base_currency})")
dist = calc.expense_distribution(expenses, rates, base_currency)
if not dist.empty:
    opts = charts.donut_chart(dist["category"].tolist(), dist["amount"].round(2).tolist(), unit_label=base_currency)
    st_echarts(options=opts, height="340px")
else:
    st.caption("No expenses recorded yet.")

st.divider()
st.subheader("Export")
e1, e2, e3, e4 = st.columns(4)
with e1:
    st.download_button("⬇️ Consulting Projects CSV", enriched.to_csv(index=False), "consulting_projects.csv", "text/csv")
with e2:
    st.download_button("⬇️ Consulting Payments CSV", payments.to_csv(index=False), "consulting_payments.csv", "text/csv")
with e3:
    st.download_button(f"⬇️ SaaS+Consulting Revenue by Stream CSV ({base_currency})", stream_monthly.to_csv(index=False), "revenue_by_stream.csv", "text/csv")
with e4:
    st.download_button("⬇️ Expenses CSV", expenses.to_csv(index=False), "expenses.csv", "text/csv")
