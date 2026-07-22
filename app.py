import pandas as pd
import plotly.express as px
import streamlit as st

from utils import calculations as calc
from utils import sheets
from utils.styling import inject_css, metric_card, fmt_currency

st.set_page_config(
    page_title="Founder Revenue OS",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_css()


def check_password():
    """Simple shared-password gate. Good enough for a solo-founder tool;
    swap for real auth if you ever open this up to other users."""
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
expenses = sheets.read_sheet("Expenses")

enriched = calc.enrich_projects(projects, payments)
metrics = calc.dashboard_metrics(projects, payments, expenses)

st.title("💼 Founder Revenue OS")
st.caption("Your personal business operating system — every engagement, tracked from proposal to payment.")

col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    metric_card("Lifetime Revenue", fmt_currency(metrics["lifetime_revenue"]))
with col2:
    metric_card("Revenue This Month", fmt_currency(metrics["revenue_month"]))
with col3:
    metric_card("Revenue This Year", fmt_currency(metrics["revenue_year"]))
with col4:
    metric_card("Outstanding", fmt_currency(metrics["outstanding"]))
with col5:
    metric_card("Net Profit", fmt_currency(metrics["net_profit"]))

st.write("")
col6, col7, col8, col9, col10 = st.columns(5)
with col6:
    metric_card("Total Projects", str(metrics["total_projects"]))
with col7:
    metric_card("Total Clients", str(metrics["total_clients"]))
with col8:
    metric_card("Total Expenses", fmt_currency(metrics["total_expenses"]))
with col9:
    metric_card("Collection Rate", f"{metrics['collection_rate']}%")
with col10:
    metric_card("Revenue Today", fmt_currency(metrics["revenue_today"]))

st.write("")
st.divider()

if projects.empty:
    st.info("No projects yet — head to the **Projects** page in the sidebar to add your first one.")
else:
    left, right = st.columns(2)

    with left:
        st.subheader("Monthly Revenue Trend")
        monthly = calc.monthly_revenue_series(payments)
        if not monthly.empty:
            fig = px.bar(monthly, x="month", y="revenue", labels={"month": "Month", "revenue": "Revenue"})
            fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), height=320)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.caption("No payments recorded yet.")

    with right:
        st.subheader("Revenue by Service Category")
        by_cat = calc.revenue_by(enriched, "service_category")
        if not by_cat.empty:
            fig = px.pie(by_cat, names="service_category", values="revenue", hole=0.45)
            fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), height=320)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.caption("No revenue recorded yet.")

    left2, right2 = st.columns(2)

    with left2:
        st.subheader("Revenue by Client")
        by_client = calc.revenue_by(enriched, "client_name").head(10)
        if not by_client.empty:
            fig = px.bar(by_client, x="revenue", y="client_name", orientation="h",
                         labels={"revenue": "Revenue", "client_name": "Client"})
            fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), height=320,
                               yaxis=dict(autorange="reversed"))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.caption("No revenue recorded yet.")

    with right2:
        st.subheader("Revenue by Acquisition Source")
        by_source = calc.revenue_by(enriched, "acquisition_source")
        if not by_source.empty:
            fig = px.bar(by_source, x="acquisition_source", y="revenue",
                         labels={"acquisition_source": "Source", "revenue": "Revenue"})
            fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), height=320)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.caption("No revenue recorded yet.")

    st.subheader("Profit Trend (Revenue vs. Expenses)")
    trend = calc.profit_trend(payments, expenses)
    if not trend.empty:
        fig = px.line(trend, x="month", y=["revenue", "expense", "profit"], markers=True,
                      labels={"month": "Month", "value": "Amount", "variable": "Series"})
        fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), height=340)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.caption("Record some payments and expenses to see this chart.")

st.sidebar.success("Connected to Google Sheets")
st.sidebar.caption("Navigate using the pages above: Projects, Payments, Expenses, Analytics, Settings.")
