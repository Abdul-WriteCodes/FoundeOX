import streamlit as st
from streamlit_echarts import st_echarts

from utils import calculations as calc
from utils import charts
from utils import sheets
from utils.styling import inject_css, metrics_grid, fmt_money

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
        f"No exchange rate saved for: **{', '.join(missing)}**. Amounts in these currencies "
        f"are being treated as 1:1 with {base_currency} in combined totals below - "
        f"add their rates in **Settings → Exchange Rates** to fix this."
    )

enriched = calc.enrich_projects(projects, payments, rates, base_currency)
stream_monthly = calc.stream_revenue_monthly(payments, projects, saas_monthly, saas_transactions, rates, base_currency)
metrics = calc.dashboard_metrics(projects, payments, saas_monthly, saas_transactions, expenses, rates, base_currency)

st.title("💼 Founder Revenue OS")
st.caption(
    f"Combined revenue across Research & Consulting and every SaaS product you're shipping. "
    f"All totals below are converted to your reporting currency, **{base_currency}**."
)

tab_overview, tab_streams, tab_monthly, tab_profit = st.tabs(
    ["📊 Overview", "🥧 Revenue by Stream", "🗓️ Monthly Breakdown", "💹 Profit Trend"]
)

with tab_overview:
    metrics_grid([
        ("Lifetime Revenue", fmt_money(metrics["lifetime_revenue"], base_currency), ""),
        ("Revenue This Month", fmt_money(metrics["revenue_month"], base_currency), ""),
        ("Revenue This Year", fmt_money(metrics["revenue_year"], base_currency), ""),
        ("Revenue Today", fmt_money(metrics["revenue_today"], base_currency), ""),
        ("Outstanding (Consulting)", fmt_money(metrics["outstanding"], base_currency), ""),
        ("Net Profit", fmt_money(metrics["net_profit"], base_currency), ""),
        ("Total Expenses", fmt_money(metrics["total_expenses"], base_currency), ""),
        ("Consulting Projects", str(metrics["total_projects"]), ""),
        ("Consulting Clients", str(metrics["total_clients"]), ""),
    ], columns=2)

    if stream_monthly.empty:
        st.info(
            "No revenue logged yet. Head to **Consulting Projects** to add a client "
            "engagement, or **SaaS Revenue** to log product revenue."
        )

with tab_streams:
    if stream_monthly.empty:
        st.info("No revenue logged yet.")
    else:
        st.subheader(f"Revenue by Stream ({base_currency})")
        by_stream = calc.revenue_by_stream_total(stream_monthly)
        opts = charts.donut_chart(by_stream["stream"].tolist(), by_stream["revenue"].round(2).tolist(), unit_label=base_currency)
        st_echarts(options=opts, height="360px")

        st.subheader(f"Monthly Revenue Trend, Combined ({base_currency})")
        combined = calc.combined_monthly_revenue(stream_monthly)
        opts = charts.bar_chart(combined["month"].tolist(), combined["revenue"].round(2).tolist(), axis_name=base_currency)
        st_echarts(options=opts, height="340px")

with tab_monthly:
    if stream_monthly.empty:
        st.info("No revenue logged yet.")
    else:
        st.subheader(f"Revenue by Stream, by Month ({base_currency})")
        pivot = stream_monthly.pivot_table(index="month", columns="stream", values="revenue", aggfunc="sum").fillna(0).sort_index()
        series_data = {stream: pivot[stream].round(2).tolist() for stream in pivot.columns}
        opts = charts.stacked_bar_chart(pivot.index.tolist(), series_data, axis_name=base_currency, height="400px")
        st_echarts(options=opts, height="400px")

with tab_profit:
    if stream_monthly.empty:
        st.info("No revenue logged yet.")
    else:
        st.subheader(f"Profit Trend, Revenue vs. Expenses ({base_currency})")
        trend = calc.profit_trend(stream_monthly, expenses, rates, base_currency)
        if not trend.empty:
            series_data = {
                "Revenue": trend["revenue"].round(2).tolist(),
                "Expense": trend["expense"].round(2).tolist(),
                "Profit": trend["profit"].round(2).tolist(),
            }
            opts = charts.multi_line_area_chart(trend["month"].tolist(), series_data, axis_name=base_currency, height="360px")
            st_echarts(options=opts, height="360px")
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
