import plotly.express as px
import streamlit as st

from utils import calculations as calc
from utils import sheets
from utils.styling import inject_css, metric_card, fmt_currency

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

enriched = calc.enrich_projects(projects, payments)
stream_monthly = calc.stream_revenue_monthly(payments, saas_monthly, saas_transactions)

if stream_monthly.empty:
    st.info("Log some revenue first (Consulting Payments or SaaS Revenue) to unlock analytics.")
    st.stop()

top_client, top_client_rev = calc.largest_client(enriched)
avg_value = calc.average_project_value(projects)
by_stream_total = calc.revenue_by_stream_total(stream_monthly)
top_stream = by_stream_total.iloc[0] if not by_stream_total.empty else None

c1, c2, c3, c4 = st.columns(4)
with c1:
    metric_card("Top Revenue Stream", top_stream["stream"] if top_stream is not None else "—",
                fmt_currency(top_stream["revenue"]) if top_stream is not None else "")
with c2:
    metric_card("Largest Client", top_client or "—", fmt_currency(top_client_rev) if top_client else "")
with c3:
    metric_card("Avg. Consulting Project Value", fmt_currency(avg_value))
with c4:
    outstanding_total = enriched["outstanding_balance"].sum() if not enriched.empty else 0.0
    metric_card("Outstanding Receivables", fmt_currency(outstanding_total))

st.divider()

st.subheader("Revenue Growth (Cumulative, Combined)")
combined = calc.combined_monthly_revenue(stream_monthly)
if not combined.empty:
    combined = combined.sort_values("month")
    combined["cumulative"] = combined["revenue"].cumsum()
    fig = px.area(combined, x="month", y="cumulative", labels={"month": "Month", "cumulative": "Cumulative Revenue"})
    fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), height=320)
    st.plotly_chart(fig, use_container_width=True)

st.subheader("Per-Stream Profit")
st.caption("Revenue by stream, minus expenses tagged to that same stream. Untagged/General expenses aren't split — see Combined Net Profit below for the full picture.")
exp_by_stream = calc.expense_by_stream(expenses)
profit_table = by_stream_total.merge(exp_by_stream, left_on="stream", right_on="stream", how="left").fillna(0)
profit_table = profit_table.rename(columns={"revenue": "revenue", "amount": "tagged_expenses"})
if "tagged_expenses" not in profit_table.columns:
    profit_table["tagged_expenses"] = 0.0
profit_table["stream_profit"] = profit_table["revenue"] - profit_table["tagged_expenses"]
display_table = profit_table.copy()
for col in ["revenue", "tagged_expenses", "stream_profit"]:
    display_table[col] = display_table[col].map(fmt_currency)
st.dataframe(display_table, use_container_width=True, hide_index=True)

col_a, col_b = st.columns(2)
with col_a:
    st.subheader("Outstanding Receivables by Client")
    unpaid = enriched[enriched["outstanding_balance"] > 0] if not enriched.empty else enriched
    if not unpaid.empty:
        rb = unpaid.groupby("client_name")["outstanding_balance"].sum().reset_index().sort_values(
            "outstanding_balance", ascending=False
        )
        fig = px.bar(rb, x="outstanding_balance", y="client_name", orientation="h",
                     labels={"outstanding_balance": "Outstanding", "client_name": "Client"})
        fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), height=320, yaxis=dict(autorange="reversed"))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.caption("Nothing outstanding — fully collected! 🎉")

with col_b:
    st.subheader("Expense Trends")
    exp_trend = calc.monthly_expense_series(expenses)
    if not exp_trend.empty:
        fig = px.line(exp_trend, x="month", y="expense", markers=True,
                      labels={"month": "Month", "expense": "Expense"})
        fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), height=320)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.caption("No expenses recorded yet.")

st.subheader("Expense Distribution by Category")
dist = calc.expense_distribution(expenses)
if not dist.empty:
    fig = px.pie(dist, names="category", values="amount", hole=0.45)
    fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), height=340)
    st.plotly_chart(fig, use_container_width=True)
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
    st.download_button("⬇️ SaaS Revenue CSV", stream_monthly.to_csv(index=False), "saas_revenue_by_stream.csv", "text/csv")
with e4:
    st.download_button("⬇️ Expenses CSV", expenses.to_csv(index=False), "expenses.csv", "text/csv")
