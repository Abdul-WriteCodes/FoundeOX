"""
Founder Metrics Dashboard
--------------------------
A single-file Streamlit app that turns a Google Sheet into a personal
business-intelligence system across multiple ventures.

Data source: Google Sheets (see setup_sheets.py + README.md to provision it)
Charts: Plotly
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials

# =========================================================================
# CONFIG
# =========================================================================
st.set_page_config(
    page_title="Founder Metrics Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
]

# Business -> (icon, sheet tab name, [metric1, metric2])
BUSINESSES = {
    "BizTrack-OS": {"icon": "📟", "sheet": "BizTrack-OS", "metrics": ("Users", "Revenue")},
    "StaX360": {"icon": "📈", "sheet": "StaX360", "metrics": ("Users", "Revenue")},
    "Research & Consulting": {"icon": "📊", "sheet": "Research & Consulting", "metrics": ("Projects", "Revenue")},
    "Crea8it Studio": {"icon": "🎨", "sheet": "Crea8it Studio", "metrics": ("Members", "Onboarded")},
}

DEFAULT_CURRENCY = "₦"

# =========================================================================
# DATA LAYER
# =========================================================================
@st.cache_resource(show_spinner=False)
def get_gspread_client():
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    return gspread.authorize(creds)


@st.cache_data(ttl=300, show_spinner=False)
def load_worksheet(sheet_name: str) -> pd.DataFrame:
    """Load a single tab from the configured Google Sheet as a DataFrame."""
    try:
        client = get_gspread_client()
        sheet_url = st.secrets["general"]["sheet_url"]
        sh = client.open_by_url(sheet_url)
        ws = sh.worksheet(sheet_name)
        records = ws.get_all_records()
        df = pd.DataFrame(records)
        return df
    except Exception as e:
        st.session_state.setdefault("load_errors", []).append(f"{sheet_name}: {e}")
        return pd.DataFrame()


def load_business_df(business: str) -> pd.DataFrame:
    """Load and clean a business's monthly data. Ensures numeric columns + a sortable date."""
    cfg = BUSINESSES[business]
    df = load_worksheet(cfg["sheet"])
    if df.empty:
        return df
    m1, m2 = cfg["metrics"]
    for col in (m1, m2):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    if "Month" in df.columns:
        df["_MonthDate"] = pd.to_datetime(df["Month"], errors="coerce", format="mixed")
        df = df.sort_values("_MonthDate")
    return df


@st.cache_data(ttl=300, show_spinner=False)
def load_goals() -> pd.DataFrame:
    df = load_worksheet("Goals")
    if not df.empty:
        for col in ("Current", "Target"):
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    return df


@st.cache_data(ttl=300, show_spinner=False)
def load_milestones() -> pd.DataFrame:
    df = load_worksheet("Milestones")
    if not df.empty and "Date" in df.columns:
        df["_Date"] = pd.to_datetime(df["Date"], errors="coerce", format="mixed")
        df = df.sort_values("_Date", ascending=False)
    return df


def clear_all_caches():
    st.cache_data.clear()
    st.cache_resource.clear()


def get_currency() -> str:
    return st.session_state.get("currency", DEFAULT_CURRENCY)


def fmt_money(value) -> str:
    try:
        return f"{get_currency()}{value:,.0f}"
    except Exception:
        return f"{get_currency()}0"


def pct_change(current, previous):
    if previous in (0, None) or pd.isna(previous):
        return None
    return ((current - previous) / previous) * 100


def growth_badge(delta):
    if delta is None:
        return ""
    arrow = "▲" if delta >= 0 else "▼"
    return f"{arrow} {abs(delta):.1f}%"


# =========================================================================
# SHARED UI HELPERS
# =========================================================================
def kpi_row(items):
    """items: list of (label, value_str, delta_str_or_None)"""
    cols = st.columns(len(items))
    for col, (label, value, delta) in zip(cols, items):
        with col:
            if delta:
                st.metric(label, value, delta)
            else:
                st.metric(label, value)


def load_all_business_data():
    return {biz: load_business_df(biz) for biz in BUSINESSES}


def ecosystem_totals(data: dict):
    total_revenue, total_users, total_projects, total_community = 0, 0, 0, 0
    for biz, df in data.items():
        if df.empty:
            continue
        m1, m2 = BUSINESSES[biz]["metrics"]
        if biz == "Crea8it Studio":
            total_community += df[m1].sum() if m1 in df else 0
        elif biz == "Research & Consulting":
            total_projects += df[m1].sum() if m1 in df else 0
            total_revenue += df[m2].sum() if m2 in df else 0
        else:
            total_users += df[m1].sum() if m1 in df else 0
            total_revenue += df[m2].sum() if m2 in df else 0
    return total_revenue, total_users, total_projects, total_community


def latest_and_prior_month(df, col):
    """Return (latest_value, prior_value) for a metric column, using the last two rows."""
    if df.empty or col not in df.columns or len(df) == 0:
        return 0, None
    latest = df[col].iloc[-1]
    prior = df[col].iloc[-2] if len(df) > 1 else None
    return latest, prior


# =========================================================================
# PAGE: MAIN DASHBOARD
# =========================================================================
def page_main_dashboard():
    st.title("📊 Founder Metrics Dashboard")
    st.caption("How is everything I'm building performing?")

    data = load_all_business_data()
    total_revenue, total_users, total_projects, total_community = ecosystem_totals(data)
    active_units = sum(1 for df in data.values() if not df.empty)

    # Monthly growth: sum revenue this month vs last month across all businesses
    this_month_rev, last_month_rev = 0, 0
    for biz, df in data.items():
        m1, m2 = BUSINESSES[biz]["metrics"]
        if df.empty or m2 not in df.columns:
            continue
        cur, prior = latest_and_prior_month(df, m2)
        this_month_rev += cur or 0
        last_month_rev += prior or 0
    monthly_growth = pct_change(this_month_rev, last_month_rev)

    kpi_row([
        ("Lifetime Revenue", fmt_money(total_revenue), None),
        ("Total Users", f"{total_users:,.0f}", None),
        ("Total Projects", f"{total_projects:,.0f}", None),
        ("Community Members", f"{total_community:,.0f}", None),
        ("Monthly Growth", growth_badge(monthly_growth) or "—", None),
        ("Active Units", f"{active_units}/{len(BUSINESSES)}", None),
    ])

    st.divider()

    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("Revenue Trend")
        frames = []
        for biz, df in data.items():
            m1, m2 = BUSINESSES[biz]["metrics"]
            if df.empty or "Month" not in df.columns or m2 not in df.columns:
                continue
            tmp = df[["Month", m2]].copy()
            tmp.columns = ["Month", "Revenue"]
            tmp["Business"] = biz
            frames.append(tmp)
        if frames:
            all_rev = pd.concat(frames, ignore_index=True)
            fig = px.line(all_rev, x="Month", y="Revenue", color="Business", markers=True)
            fig.update_layout(height=380, legend_title="")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No revenue data yet — add rows to your business sheets.")

    with col2:
        st.subheader("Business Comparison")
        comp_rows = []
        for biz, df in data.items():
            m1, m2 = BUSINESSES[biz]["metrics"]
            rev = df[m2].sum() if (not df.empty and m2 in df.columns) else 0
            comp_rows.append({"Business": biz, "Revenue": rev})
        comp_df = pd.DataFrame(comp_rows)
        if comp_df["Revenue"].sum() > 0:
            fig = px.pie(comp_df, names="Business", values="Revenue", hole=0.5)
            fig.update_layout(height=380, showlegend=True)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No revenue yet to compare.")

    st.divider()
    col3, col4 = st.columns(2)

    with col3:
        st.subheader("Recent Milestones")
        ms = load_milestones()
        if ms.empty:
            st.info("No milestones logged yet.")
        else:
            for _, row in ms.head(5).iterrows():
                date_str = row["Date"]
                st.markdown(f"**{date_str}** — {row.get('Business', '')}  \n{row.get('Milestone', '')}")

    with col4:
        st.subheader("Goal Progress")
        goals = load_goals()
        if goals.empty:
            st.info("No goals set yet — add rows to the Goals sheet.")
        else:
            for _, row in goals.head(4).iterrows():
                current, target = row.get("Current", 0), row.get("Target", 0)
                progress = min(current / target, 1.0) if target else 0
                st.caption(f"{row.get('Business','')} — {row.get('Metric','')}")
                st.progress(progress, text=f"{current:,.0f} / {target:,.0f}")


# =========================================================================
# PAGE: BUSINESS DETAIL
# =========================================================================
def page_business(business: str):
    cfg = BUSINESSES[business]
    m1, m2 = cfg["metrics"]
    st.title(f"{cfg['icon']} {business}")

    df = load_business_df(business)
    if df.empty:
        st.info(f"No data yet in the '{cfg['sheet']}' sheet tab. Add monthly rows to see this dashboard populate.")
        return

    latest_m1, prior_m1 = latest_and_prior_month(df, m1)
    latest_m2, prior_m2 = latest_and_prior_month(df, m2)
    is_revenue_metric = m2 == "Revenue"

    kpi_row([
        (f"Total {m1}", f"{df[m1].sum():,.0f}", None),
        (f"Latest {m1}", f"{latest_m1:,.0f}", growth_badge(pct_change(latest_m1, prior_m1))),
        (f"Total {m2}", fmt_money(df[m2].sum()) if is_revenue_metric else f"{df[m2].sum():,.0f}", None),
        (f"Latest {m2}", fmt_money(latest_m2) if is_revenue_metric else f"{latest_m2:,.0f}",
         growth_badge(pct_change(latest_m2, prior_m2))),
    ])

    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        st.subheader(f"{m1} — Monthly Trend")
        fig = px.bar(df, x="Month", y=m1)
        fig.update_layout(height=350)
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        st.subheader(f"{m2} — Monthly Trend")
        fig = px.line(df, x="Month", y=m2, markers=True)
        fig.update_layout(height=350)
        st.plotly_chart(fig, use_container_width=True)

    st.divider()
    st.subheader("Historical Data")
    display_cols = [c for c in df.columns if not c.startswith("_")]
    st.dataframe(df[display_cols], use_container_width=True, hide_index=True)


# =========================================================================
# PAGE: REVENUE DASHBOARD
# =========================================================================
def page_revenue():
    st.title("💰 Revenue Dashboard")

    data = load_all_business_data()
    frames = []
    for biz, df in data.items():
        m1, m2 = BUSINESSES[biz]["metrics"]
        if df.empty or m2 not in df.columns or "Month" not in df.columns:
            continue
        tmp = df[["Month", m2]].copy()
        tmp.columns = ["Month", "Revenue"]
        tmp["Business"] = biz
        frames.append(tmp)

    if not frames:
        st.info("No revenue data yet across any business.")
        return

    all_rev = pd.concat(frames, ignore_index=True)
    monthly_total = all_rev.groupby("Month", sort=False)["Revenue"].sum().reset_index()

    lifetime_revenue = all_rev["Revenue"].sum()
    avg_monthly = monthly_total["Revenue"].mean()
    best_row = monthly_total.loc[monthly_total["Revenue"].idxmax()] if not monthly_total.empty else None
    latest_rev, prior_rev = (monthly_total["Revenue"].iloc[-1], monthly_total["Revenue"].iloc[-2]) \
        if len(monthly_total) > 1 else (monthly_total["Revenue"].iloc[-1] if len(monthly_total) else 0, None)

    kpi_row([
        ("Lifetime Revenue", fmt_money(lifetime_revenue), None),
        ("Monthly Revenue (latest)", fmt_money(latest_rev), growth_badge(pct_change(latest_rev, prior_rev))),
        ("Average Monthly Revenue", fmt_money(avg_monthly), None),
        ("Highest Revenue Month", f"{best_row['Month']}" if best_row is not None else "—",
         fmt_money(best_row['Revenue']) if best_row is not None else None),
    ])

    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Revenue Over Time (Line)")
        fig = px.line(all_rev, x="Month", y="Revenue", color="Business", markers=True)
        fig.update_layout(height=380)
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        st.subheader("Revenue by Business (Bar)")
        by_biz = all_rev.groupby("Business", sort=False)["Revenue"].sum().reset_index()
        fig = px.bar(by_biz, x="Business", y="Revenue", color="Business")
        fig.update_layout(height=380, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Revenue Share (Pie)")
    by_biz = all_rev.groupby("Business", sort=False)["Revenue"].sum().reset_index()
    fig = px.pie(by_biz, names="Business", values="Revenue", hole=0.5)
    fig.update_layout(height=400)
    st.plotly_chart(fig, use_container_width=True)


# =========================================================================
# PAGE: ANALYTICS DASHBOARD
# =========================================================================
def page_analytics():
    st.title("🔎 Analytics Dashboard")

    data = load_all_business_data()
    rows = []
    for biz, df in data.items():
        m1, m2 = BUSINESSES[biz]["metrics"]
        if df.empty:
            continue
        revenue_total = df[m2].sum() if m2 in df.columns else 0
        primary_total = df[m1].sum() if m1 in df.columns else 0
        latest, prior = latest_and_prior_month(df, m2) if m2 in df.columns else (0, None)
        growth = pct_change(latest, prior)
        rows.append({
            "Business": biz,
            "Primary Metric Total": primary_total,
            "Revenue Total": revenue_total,
            "Latest Growth %": growth if growth is not None else 0,
        })

    if not rows:
        st.info("Add data to your sheets to unlock cross-business analytics.")
        return

    summary = pd.DataFrame(rows)

    highest_rev = summary.loc[summary["Revenue Total"].idxmax()]
    fastest_growing = summary.loc[summary["Latest Growth %"].idxmax()]

    kpi_row([
        ("Highest Revenue Business", highest_rev["Business"], fmt_money(highest_rev["Revenue Total"])),
        ("Fastest Growing Business", fastest_growing["Business"], growth_badge(fastest_growing["Latest Growth %"])),
        ("Total Revenue (Ecosystem)", fmt_money(summary["Revenue Total"].sum()), None),
    ])

    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Revenue Contribution")
        fig = px.pie(summary, names="Business", values="Revenue Total", hole=0.4)
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        st.subheader("Business Comparison")
        fig = px.bar(summary, x="Business", y=["Primary Metric Total", "Revenue Total"], barmode="group")
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("User / Member Growth")
    growth_frames = []
    for biz, df in data.items():
        m1, _ = BUSINESSES[biz]["metrics"]
        if df.empty or "Month" not in df.columns or m1 not in df.columns:
            continue
        tmp = df[["Month", m1]].copy()
        tmp.columns = ["Month", "Count"]
        tmp["Business"] = biz
        growth_frames.append(tmp)
    if growth_frames:
        growth_df = pd.concat(growth_frames, ignore_index=True)
        fig = px.line(growth_df, x="Month", y="Count", color="Business", markers=True)
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Monthly Performance Table")
    st.dataframe(summary, use_container_width=True, hide_index=True)


# =========================================================================
# PAGE: GOALS DASHBOARD
# =========================================================================
def page_goals():
    st.title("🎯 Goals Dashboard")

    goals = load_goals()
    if goals.empty:
        st.info("No goals yet. Add rows to the 'Goals' sheet tab: Business | Metric | Current | Target.")
        return

    for _, row in goals.iterrows():
        business, metric = row.get("Business", ""), row.get("Metric", "")
        current, target = row.get("Current", 0), row.get("Target", 0)
        remaining = max(target - current, 0)
        progress = min(current / target, 1.0) if target else 0

        with st.container(border=True):
            c1, c2, c3 = st.columns([2, 1, 1])
            c1.markdown(f"**{business}** — {metric}")
            c2.metric("Current", f"{current:,.0f}")
            c3.metric("Target", f"{target:,.0f}")
            st.progress(progress, text=f"{progress*100:.0f}% complete — {remaining:,.0f} remaining")


# =========================================================================
# PAGE: MILESTONES
# =========================================================================
def page_milestones():
    st.title("🏁 Milestones")

    ms = load_milestones()
    if ms.empty:
        st.info("No milestones yet. Add rows to the 'Milestones' sheet tab: Date | Business | Milestone.")
        return

    businesses = ["All"] + sorted(ms["Business"].dropna().unique().tolist())
    chosen = st.selectbox("Filter by business", businesses)
    filtered = ms if chosen == "All" else ms[ms["Business"] == chosen]

    for _, row in filtered.iterrows():
        with st.container(border=True):
            st.markdown(f"**{row['Date']}** · {row.get('Business', '')}")
            st.write(row.get("Milestone", ""))


# =========================================================================
# PAGE: MONTHLY REPORT
# =========================================================================
def page_monthly_report():
    st.title("📝 Monthly Report")

    data = load_all_business_data()

    all_months = set()
    for df in data.values():
        if "Month" in df.columns:
            all_months.update(df["Month"].dropna().unique().tolist())
    if not all_months:
        st.info("No data yet to build a report from.")
        return

    months_sorted = sorted(all_months)
    selected_month = st.selectbox("Select month", options=list(reversed(months_sorted)))

    st.divider()
    st.subheader(f"Summary — {selected_month}")

    total_revenue, new_users, new_projects, new_community = 0, 0, 0, 0
    lines = []
    for biz, df in data.items():
        if df.empty or "Month" not in df.columns:
            continue
        m1, m2 = BUSINESSES[biz]["metrics"]
        row = df[df["Month"] == selected_month]
        if row.empty:
            continue
        v1 = row[m1].iloc[0] if m1 in row.columns else 0
        v2 = row[m2].iloc[0] if m2 in row.columns else 0
        if biz == "Crea8it Studio":
            new_community += v1
        elif biz == "Research & Consulting":
            new_projects += v1
            total_revenue += v2
        else:
            new_users += v1
            total_revenue += v2
        lines.append(f"- **{biz}**: {m1} = {v1:,.0f}, {m2} = {v2:,.0f}" if m2 != "Revenue"
                      else f"- **{biz}**: {m1} = {v1:,.0f}, {m2} = {fmt_money(v2)}")

    kpi_row([
        ("Revenue", fmt_money(total_revenue), None),
        ("New Users", f"{new_users:,.0f}", None),
        ("New Projects", f"{new_projects:,.0f}", None),
        ("Community Growth", f"{new_community:,.0f}", None),
    ])

    st.markdown("#### Breakdown by business")
    st.markdown("\n".join(lines) if lines else "No rows found for this month.")

    st.markdown("#### Key Achievements")
    ms = load_milestones()
    if not ms.empty and "Date" in ms.columns:
        month_ms = ms[ms["_Date"].dt.strftime("%Y-%m") == pd.to_datetime(selected_month, errors="coerce").strftime("%Y-%m")] \
            if pd.notna(pd.to_datetime(selected_month, errors="coerce")) else pd.DataFrame()
        if not month_ms.empty:
            for _, r in month_ms.iterrows():
                st.markdown(f"- **{r.get('Business','')}**: {r.get('Milestone','')}")
        else:
            st.caption("No milestones logged for this month.")
    else:
        st.caption("No milestones logged yet.")

    report_text = f"# Monthly Report — {selected_month}\n\n" \
                   f"**Revenue:** {fmt_money(total_revenue)}\n\n" \
                   f"**New Users:** {new_users:,.0f}\n\n" \
                   f"**New Projects:** {new_projects:,.0f}\n\n" \
                   f"**Community Growth:** {new_community:,.0f}\n\n" \
                   f"## Breakdown\n" + "\n".join(lines)
    st.download_button("Download report (Markdown)", report_text, file_name=f"report_{selected_month}.md")


# =========================================================================
# PAGE: SETTINGS
# =========================================================================
def page_settings():
    st.title("⚙️ Settings")

    st.subheader("Currency")
    currency = st.selectbox(
        "Display currency symbol",
        options=["₦", "$", "£", "€"],
        index=["₦", "$", "£", "€"].index(get_currency()) if get_currency() in ["₦", "$", "£", "€"] else 0,
    )
    st.session_state["currency"] = currency

    st.divider()
    st.subheader("Business Logo")
    logo = st.file_uploader("Upload a logo (displayed in the sidebar)", type=["png", "jpg", "jpeg"])
    if logo is not None:
        st.session_state["logo_bytes"] = logo.getvalue()
        st.success("Logo updated for this session.")
    if st.session_state.get("logo_bytes"):
        st.image(st.session_state["logo_bytes"], width=120)

    st.divider()
    st.subheader("Google Sheet")
    try:
        sheet_url = st.secrets["general"]["sheet_url"]
        st.text_input("Connected Sheet URL", value=sheet_url, disabled=True)
    except Exception:
        st.warning("No sheet_url configured in secrets.toml yet — see README.md.")

    st.divider()
    st.subheader("Theme")
    st.caption("Theme colors are set in `.streamlit/config.toml` and applied on app restart.")

    st.divider()
    st.subheader("Refresh Data")
    if st.button("🔄 Refresh now (clear cache)"):
        clear_all_caches()
        st.success("Cache cleared — data will reload from Google Sheets.")

    errors = st.session_state.get("load_errors", [])
    if errors:
        st.divider()
        st.subheader("Connection issues")
        for e in errors:
            st.error(e)


# =========================================================================
# NAVIGATION / ROUTER
# =========================================================================
def sidebar_nav():
    if st.session_state.get("logo_bytes"):
        st.sidebar.image(st.session_state["logo_bytes"], width=120)
    st.sidebar.title("📊 Founder Metrics")
    st.sidebar.caption("Measure what you build.")

    business_pages = {f"{cfg['icon']} {biz}": biz for biz, cfg in BUSINESSES.items()}

    section = st.sidebar.radio(
        "Navigate",
        options=[
            "🏠 Main Dashboard",
            *business_pages.keys(),
            "💰 Revenue Dashboard",
            "🔎 Analytics Dashboard",
            "🎯 Goals Dashboard",
            "🏁 Milestones",
            "📝 Monthly Report",
            "⚙️ Settings",
        ],
        label_visibility="collapsed",
    )

    st.sidebar.divider()
    if st.sidebar.button("🔄 Refresh Data", use_container_width=True):
        clear_all_caches()
        st.sidebar.success("Refreshed.")

    return section, business_pages


def main():
    section, business_pages = sidebar_nav()

    if section == "🏠 Main Dashboard":
        page_main_dashboard()
    elif section in business_pages:
        page_business(business_pages[section])
    elif section == "💰 Revenue Dashboard":
        page_revenue()
    elif section == "🔎 Analytics Dashboard":
        page_analytics()
    elif section == "🎯 Goals Dashboard":
        page_goals()
    elif section == "🏁 Milestones":
        page_milestones()
    elif section == "📝 Monthly Report":
        page_monthly_report()
    elif section == "⚙️ Settings":
        page_settings()


if __name__ == "__main__":
    main()
