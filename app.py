import plotly.express as px
import streamlit as st

from utils import calculations as calc
from utils import sheets
from utils.sheets import CONSULTING_STREAM
from utils.styling import inject_css, metric_card, fmt_currency

st.set_page_config(
    page_title="Founder Revenue OS",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_css()


def check_password():
    if st.session_state.get("authenticated"):
        return True

    st.title("💼 Founder Revenue OS")
    pwd = st.text_input("Enter app password", type="password")
    if st.button("Enter"):
        if pwd == st.secrets["app_config"].get("app_password", ""):
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("Incorrect password.")
    return False


if not check_password():
    st.stop()

with st.spinner("Connecting to Google Sheets..."):
    try:
        sheets.bootstrap_sheets()
    except Exception as e:
        st.error(
            "Couldn't connect to Google Sheets. Check that:\n\n"
            "1. Your `secrets.toml` service account details are correct\n"
            "2. The sheet has been shared (Editor access) with the "
            "service account's client_email\n"
            "3. `app_config.sheet_url` points to the right spreadsheet\n\n"
            f"Raw error: {e}"
        )
        st.stop()

projects = sheets.read_sheet("Projects")
payments = sheets.read_sheet("Payments")
saas_monthly = sheets.read_sheet("SaaSMonthly")
saas_transactions = sheets.read_sheet("SaaSTransactions")
expenses = sheets.read_sheet("Expenses")

enriched = calc.enrich_projects(projects, payments)
stream_monthly = calc.stream_revenue_monthly(payments, saas_monthly, saas_transactions)
metrics = calc.dashboard_metrics(projects, payments, saas_monthly, saas_transactions, expenses)

st.title("💼 Founder Revenue OS")
st.caption("Combined revenue across Research & Consulting and every SaaS product you're shipping.")

col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    metric_card("Lifetime Revenue", fmt_currency(metrics["lifetime_revenue"]))
with col2:
    metric_card("Revenue This Month", fmt_currency(metrics["revenue_month"]))
with col3:
    metric_card("Revenue This Year", fmt_currency(metrics["revenue_year"]))
with col4:
    metric_card("Outstanding (Consulting)", fmt_currency(metrics["outstanding"]))
with col5:
    metric_card("Net Profit", fmt_currency(metrics["net_profit"]))

st.write("")
col6, col7, col8, col9 = st.columns(4)
with col6:
    metric_card("Consulting Projects", str(metrics["total_projects"]))
with col7:
    metric_card("Consulting Clients", str(metrics["total_clients"]))
with col8:
    metric_card("Total Expenses", fmt_currency(metrics["total_expenses"]))
with col9:
    metric_card("Revenue Today", fmt_currency(metrics["revenue_today"]))

st.write("")
st.divider()

if stream_monthly.empty:
    st.info(
        "No revenue logged yet. Head to **Consulting Projects** to add a client "
        "engagement, or **SaaS Revenue** to log product revenue."
    )
else:
    left, right = st.columns(2)

    with left:
        st.subheader("Revenue by Stream")
        by_stream = calc.revenue_by_stream_total(stream_monthly)
        fig = px.pie(by_stream, names="stream", values="revenue", hole=0.45)
        fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), height=340)
        st.plotly_chart(fig, use_container_width=True)

    with right:
        st.subheader("Monthly Revenue Trend (Combined)")
        combined = calc.combined_monthly_revenue(stream_monthly)
        fig = px.bar(combined, x="month", y="revenue", labels={"month": "Month", "revenue": "Revenue"})
        fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), height=340)
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Revenue by Stream, by Month")
    fig = px.bar(
        stream_monthly, x="month", y="revenue", color="stream",
        labels={"month": "Month", "revenue": "Revenue", "stream": "Stream"},
        barmode="stack",
    )
    fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), height=380)
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Profit Trend (Revenue vs. Expenses)")
    trend = calc.profit_trend(stream_monthly, expenses)
    if not trend.empty:
        fig = px.line(trend, x="month", y=["revenue", "expense", "profit"], markers=True,
                      labels={"month": "Month", "value": "Amount", "variable": "Series"})
        fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), height=340)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.caption("Record some expenses to see this chart.")

st.sidebar.success("Connected to Google Sheets")
st.sidebar.caption(
    "Navigate using the pages above: Consulting Projects, Consulting Payments, "
    "SaaS Revenue, Expenses, Analytics, Settings."
)
if st.sidebar.button("🔄 Refresh data"):
    sheets.refresh_data()
    st.rerun()
st.sidebar.caption("Data is cached for ~20s to stay well under Google's API rate limits — use Refresh if you just edited the Sheet directly.")
