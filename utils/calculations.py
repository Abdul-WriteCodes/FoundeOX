"""
All derived numbers live here. Nothing in this module talks to Google
Sheets - it only transforms DataFrames already loaded by utils.sheets,
so it's easy to reason about and test.

Key idea - "stream revenue": Research & Consulting revenue comes from
Payments; each SaaS product's revenue comes from SaaSMonthly (manual
totals) reconciled against SaaSTransactions (itemized entries) so nothing
gets double-counted. Everything downstream (dashboard, analytics) is
built on top of a single combined stream_revenue table.
"""

from datetime import datetime

import pandas as pd

from utils.sheets import CONSULTING_STREAM


def _to_numeric(series):
    return pd.to_numeric(series, errors="coerce").fillna(0)


# ---------------- Consulting (Projects + Payments) ----------------

def enrich_projects(projects: pd.DataFrame, payments: pd.DataFrame) -> pd.DataFrame:
    """Attach amount_received, outstanding_balance, payment_percentage,
    and a computed payment_status to every project row."""
    df = projects.copy()
    if df.empty:
        for c in ["amount_received", "outstanding_balance", "payment_percentage"]:
            df[c] = []
        return df

    df["project_value"] = _to_numeric(df["project_value"])

    if payments.empty:
        received_by_project = pd.Series(dtype=float)
    else:
        pay = payments.copy()
        pay["amount"] = _to_numeric(pay["amount"])
        received_by_project = pay.groupby("project_id")["amount"].sum()

    df["amount_received"] = df["project_id"].map(received_by_project).fillna(0)
    df["outstanding_balance"] = (df["project_value"] - df["amount_received"]).clip(lower=0)
    df["payment_percentage"] = df.apply(
        lambda r: round((r["amount_received"] / r["project_value"] * 100), 1)
        if r["project_value"] > 0 else 0.0,
        axis=1,
    )

    def status(r):
        if r["amount_received"] <= 0:
            return "Unpaid"
        elif r["amount_received"] >= r["project_value"]:
            return "Paid"
        else:
            return "Partial"

    df["payment_status"] = df.apply(status, axis=1)
    return df


def consulting_monthly_revenue(payments: pd.DataFrame) -> pd.DataFrame:
    """Consulting revenue by month, from actual client payments."""
    if payments.empty:
        return pd.DataFrame(columns=["month", "revenue"])
    pay = payments.copy()
    pay["amount"] = _to_numeric(pay["amount"])
    pay["payment_date"] = pd.to_datetime(pay["payment_date"], errors="coerce")
    pay = pay.dropna(subset=["payment_date"])
    pay["month"] = pay["payment_date"].dt.to_period("M").astype(str)
    return pay.groupby("month")["amount"].sum().reset_index(name="revenue").sort_values("month")


# ---------------- SaaS products (Monthly totals + Transactions) ----------------

def saas_transactions_monthly(saas_transactions: pd.DataFrame) -> pd.DataFrame:
    """Sum individual transactions per product+month."""
    if saas_transactions.empty:
        return pd.DataFrame(columns=["product", "month", "revenue"])
    tx = saas_transactions.copy()
    tx["amount"] = _to_numeric(tx["amount"])
    tx["date"] = pd.to_datetime(tx["date"], errors="coerce")
    tx = tx.dropna(subset=["date"])
    tx["month"] = tx["date"].dt.to_period("M").astype(str)
    return tx.groupby(["product", "month"])["amount"].sum().reset_index(name="revenue")


def saas_reconciled_monthly(saas_monthly: pd.DataFrame, saas_transactions: pd.DataFrame) -> pd.DataFrame:
    """The authoritative product+month revenue table: a manual monthly
    total (if present) overrides that month's transaction sum, otherwise
    the transaction sum is used. This is how we avoid double-counting
    when both entry methods are used for the same product."""
    tx_monthly = saas_transactions_monthly(saas_transactions)

    if saas_monthly.empty:
        manual = pd.DataFrame(columns=["product", "month", "revenue"])
    else:
        m = saas_monthly.copy()
        m["amount"] = _to_numeric(m["amount"])
        manual = m[["product", "month", "amount"]].rename(columns={"amount": "revenue"})

    if manual.empty and tx_monthly.empty:
        return pd.DataFrame(columns=["product", "month", "revenue", "source"])

    manual["source"] = "manual"
    tx_monthly["source"] = "transactions"

    combined = pd.concat([manual, tx_monthly], ignore_index=True)
    # where both exist for a product+month, prefer manual (it's the
    # authoritative override); drop the transaction-derived duplicate
    combined = combined.sort_values("source")  # 'manual' < 'transactions' alphabetically
    combined = combined.drop_duplicates(subset=["product", "month"], keep="first")
    return combined.sort_values(["product", "month"])


def saas_total_by_product(saas_monthly: pd.DataFrame, saas_transactions: pd.DataFrame) -> pd.DataFrame:
    reconciled = saas_reconciled_monthly(saas_monthly, saas_transactions)
    if reconciled.empty:
        return pd.DataFrame(columns=["product", "revenue"])
    return reconciled.groupby("product")["revenue"].sum().reset_index().sort_values("revenue", ascending=False)


def saas_monthly_all_products(saas_monthly: pd.DataFrame, saas_transactions: pd.DataFrame) -> pd.DataFrame:
    """Total SaaS revenue (all products combined) per month."""
    reconciled = saas_reconciled_monthly(saas_monthly, saas_transactions)
    if reconciled.empty:
        return pd.DataFrame(columns=["month", "revenue"])
    return reconciled.groupby("month")["revenue"].sum().reset_index().sort_values("month")


# ---------------- Combined streams ----------------

def stream_revenue_monthly(payments: pd.DataFrame, saas_monthly: pd.DataFrame,
                            saas_transactions: pd.DataFrame) -> pd.DataFrame:
    """One table: stream, month, revenue - where stream is either
    'Research & Consulting' or a product name. This is the base table
    for the combined dashboard and the per-stream breakdowns."""
    consulting = consulting_monthly_revenue(payments)
    if not consulting.empty:
        consulting = consulting.copy()
        consulting["stream"] = CONSULTING_STREAM

    saas = saas_reconciled_monthly(saas_monthly, saas_transactions)
    if not saas.empty:
        saas = saas.rename(columns={"product": "stream"})[["stream", "month", "revenue"]]

    parts = [df for df in [consulting, saas] if not df.empty]
    if not parts:
        return pd.DataFrame(columns=["stream", "month", "revenue"])
    return pd.concat(parts, ignore_index=True)[["stream", "month", "revenue"]]


def revenue_by_stream_total(stream_monthly: pd.DataFrame) -> pd.DataFrame:
    if stream_monthly.empty:
        return pd.DataFrame(columns=["stream", "revenue"])
    return stream_monthly.groupby("stream")["revenue"].sum().reset_index().sort_values("revenue", ascending=False)


def combined_monthly_revenue(stream_monthly: pd.DataFrame) -> pd.DataFrame:
    if stream_monthly.empty:
        return pd.DataFrame(columns=["month", "revenue"])
    return stream_monthly.groupby("month")["revenue"].sum().reset_index().sort_values("month")


# ---------------- Expenses ----------------

def monthly_expense_series(expenses: pd.DataFrame) -> pd.DataFrame:
    if expenses.empty:
        return pd.DataFrame(columns=["month", "expense"])
    exp = expenses.copy()
    exp["amount"] = _to_numeric(exp["amount"])
    exp["expense_date"] = pd.to_datetime(exp["expense_date"], errors="coerce")
    exp = exp.dropna(subset=["expense_date"])
    exp["month"] = exp["expense_date"].dt.to_period("M").astype(str)
    return exp.groupby("month")["amount"].sum().reset_index(name="expense").sort_values("month")


def expense_distribution(expenses: pd.DataFrame) -> pd.DataFrame:
    if expenses.empty:
        return pd.DataFrame(columns=["category", "amount"])
    exp = expenses.copy()
    exp["amount"] = _to_numeric(exp["amount"])
    return exp.groupby("category")["amount"].sum().reset_index().sort_values("amount", ascending=False)


def expense_by_stream(expenses: pd.DataFrame) -> pd.DataFrame:
    if expenses.empty:
        return pd.DataFrame(columns=["stream", "amount"])
    exp = expenses.copy()
    exp["amount"] = _to_numeric(exp["amount"])
    exp["stream"] = exp["stream"].replace("", "General/Overhead").fillna("General/Overhead")
    return exp.groupby("stream")["amount"].sum().reset_index().sort_values("amount", ascending=False)


def profit_trend(stream_monthly: pd.DataFrame, expenses: pd.DataFrame) -> pd.DataFrame:
    rev = combined_monthly_revenue(stream_monthly)
    exp = monthly_expense_series(expenses)
    merged = pd.merge(rev, exp, on="month", how="outer").sort_values("month")
    if merged.empty:
        return merged
    # When either side starts out empty, its numeric column defaults to
    # object dtype - force both to float so Plotly doesn't choke on
    # mixed column types across revenue/expense/profit.
    merged["revenue"] = pd.to_numeric(merged["revenue"], errors="coerce").fillna(0)
    merged["expense"] = pd.to_numeric(merged["expense"], errors="coerce").fillna(0)
    merged["profit"] = merged["revenue"] - merged["expense"]
    return merged


# ---------------- Dashboard metrics ----------------

def dashboard_metrics(projects, payments, saas_monthly, saas_transactions, expenses) -> dict:
    enriched = enrich_projects(projects, payments)
    stream_monthly = stream_revenue_monthly(payments, saas_monthly, saas_transactions)
    today = datetime.now().date()
    this_month_str = today.strftime("%Y-%m")
    this_year = str(today.year)

    lifetime_revenue = stream_monthly["revenue"].sum() if not stream_monthly.empty else 0.0
    revenue_month = (
        stream_monthly.loc[stream_monthly["month"] == this_month_str, "revenue"].sum()
        if not stream_monthly.empty else 0.0
    )
    revenue_year = (
        stream_monthly.loc[stream_monthly["month"].str.startswith(this_year), "revenue"].sum()
        if not stream_monthly.empty else 0.0
    )

    # "today" only really applies to consulting payments / SaaS transactions
    # (a manual monthly total isn't a single-day event)
    today_total = 0.0
    if not payments.empty:
        pay = payments.copy()
        pay["amount"] = _to_numeric(pay["amount"])
        pay["payment_date"] = pd.to_datetime(pay["payment_date"], errors="coerce")
        today_total += pay.loc[pay["payment_date"].dt.date == today, "amount"].sum()
    if not saas_transactions.empty:
        tx = saas_transactions.copy()
        tx["amount"] = _to_numeric(tx["amount"])
        tx["date"] = pd.to_datetime(tx["date"], errors="coerce")
        today_total += tx.loc[tx["date"].dt.date == today, "amount"].sum()

    outstanding = enriched["outstanding_balance"].sum() if not enriched.empty else 0.0
    total_projects = len(enriched)
    total_clients = enriched["client_name"].nunique() if not enriched.empty else 0

    total_expenses = _to_numeric(expenses["amount"]).sum() if not expenses.empty else 0.0
    net_profit = lifetime_revenue - total_expenses

    return {
        "lifetime_revenue": lifetime_revenue,
        "revenue_today": today_total,
        "revenue_month": revenue_month,
        "revenue_year": revenue_year,
        "outstanding": outstanding,
        "total_projects": total_projects,
        "total_clients": total_clients,
        "total_expenses": total_expenses,
        "net_profit": net_profit,
    }


def largest_client(enriched_projects: pd.DataFrame):
    if enriched_projects.empty:
        return None, 0.0
    rb = enriched_projects.groupby("client_name")["amount_received"].sum().reset_index()
    if rb.empty:
        return None, 0.0
    top = rb.sort_values("amount_received", ascending=False).iloc[0]
    return top["client_name"], top["amount_received"]


def average_project_value(projects: pd.DataFrame) -> float:
    if projects.empty:
        return 0.0
    return round(_to_numeric(projects["project_value"]).mean(), 2)
