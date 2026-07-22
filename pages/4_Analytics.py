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
expenses = sheets.read_sheet("Expenses")
enriched = calc.enrich_projects(projects, payments)

if projects.empty:
    st.info("Add some projects and payments first to unlock analytics.")
    st.stop()

top_client, top_client_rev = calc.largest_client(enriched)
top_service, top_service_rev = calc.best_service(enriched)
avg_value = calc.average_project_value(projects)

c1, c2, c3, c4 = st.columns(4)
with c1:
    metric_card("Largest Client", top_client or "—", fmt_currency(top_client_rev) if top_client else "")
with c2:
    metric_card("Best Performing Service", top_service or "—", fmt_currency(top_service_rev) if top_service else "")
with c3:
    metric_card("Avg. Project Value", fmt_currency(avg_value))
with c4:
    outstanding_total = enriched["outstanding_balance"].sum()
    metric_card("Outstanding Receivables", fmt_currency(outstanding_total))

st.divider()

st.subheader("Revenue Growth (Cumulative)")
monthly = calc.monthly_revenue_series(payments)
if not monthly.empty:
    monthly = monthly.sort_values("month")
    monthly["cumulative"] = monthly["revenue"].cumsum()
    fig = px.area(monthly, x="month", y="cumulative", labels={"month": "Month", "cumulative": "Cumulative Revenue"})
    fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), height=320)
    st.plotly_chart(fig, use_container_width=True)
else:
    st.caption("No payments yet.")

col_a, col_b = st.columns(2)

with col_a:
    st.subheader("Outstanding Receivables by Client")
    unpaid = enriched[enriched["outstanding_balance"] > 0]
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

st.subheader("Expense Distribution")
dist = calc.expense_distribution(expenses)
if not dist.empty:
    fig = px.pie(dist, names="category", values="amount", hole=0.45)
    fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), height=340)
    st.plotly_chart(fig, use_container_width=True)
else:
    st.caption("No expenses recorded yet.")

st.divider()
st.subheader("Export")
e1, e2, e3 = st.columns(3)
with e1:
    st.download_button("⬇️ Download Projects CSV", enriched.to_csv(index=False), "projects.csv", "text/csv")
with e2:
    st.download_button("⬇️ Download Payments CSV", payments.to_csv(index=False), "payments.csv", "text/csv")
with e3:
    st.download_button("⬇️ Download Expenses CSV", expenses.to_csv(index=False), "expenses.csv", "text/csv")
