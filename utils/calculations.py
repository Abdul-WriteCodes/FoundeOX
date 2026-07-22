"""
All derived numbers live here: payment status per project, dashboard
metrics, and the aggregations that feed the analytics charts.

Nothing in this module talks to Google Sheets - it only transforms
DataFrames that have already been loaded, so it's easy to test.
"""

from datetime import datetime

import pandas as pd


def _to_numeric(series):
    return pd.to_numeric(series, errors="coerce").fillna(0)


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


def dashboard_metrics(projects: pd.DataFrame, payments: pd.DataFrame, expenses: pd.DataFrame) -> dict:
    enriched = enrich_projects(projects, payments)
    today = datetime.now().date()

    if not payments.empty:
        pay = payments.copy()
        pay["amount"] = _to_numeric(pay["amount"])
        pay["payment_date"] = pd.to_datetime(pay["payment_date"], errors="coerce")
        lifetime_revenue = pay["amount"].sum()
        revenue_today = pay.loc[pay["payment_date"].dt.date == today, "amount"].sum()
        revenue_month = pay.loc[
            (pay["payment_date"].dt.month == today.month)
            & (pay["payment_date"].dt.year == today.year),
            "amount",
        ].sum()
        revenue_year = pay.loc[pay["payment_date"].dt.year == today.year, "amount"].sum()
    else:
        lifetime_revenue = revenue_today = revenue_month = revenue_year = 0.0

    outstanding = enriched["outstanding_balance"].sum() if not enriched.empty else 0.0
    total_projects = len(enriched)
    total_clients = enriched["client_name"].nunique() if not enriched.empty else 0

    if not expenses.empty:
        exp = expenses.copy()
        exp["amount"] = _to_numeric(exp["amount"])
        total_expenses = exp["amount"].sum()
    else:
        total_expenses = 0.0

    net_profit = lifetime_revenue - total_expenses

    total_value = enriched["project_value"].sum() if not enriched.empty else 0.0
    collection_rate = round((lifetime_revenue / total_value * 100), 1) if total_value > 0 else 0.0

    return {
        "lifetime_revenue": lifetime_revenue,
        "revenue_today": revenue_today,
        "revenue_month": revenue_month,
        "revenue_year": revenue_year,
        "outstanding": outstanding,
        "total_projects": total_projects,
        "total_clients": total_clients,
        "total_expenses": total_expenses,
        "net_profit": net_profit,
        "collection_rate": collection_rate,
    }


def monthly_revenue_series(payments: pd.DataFrame) -> pd.DataFrame:
    if payments.empty:
        return pd.DataFrame(columns=["month", "revenue"])
    pay = payments.copy()
    pay["amount"] = _to_numeric(pay["amount"])
    pay["payment_date"] = pd.to_datetime(pay["payment_date"], errors="coerce")
    pay = pay.dropna(subset=["payment_date"])
    pay["month"] = pay["payment_date"].dt.to_period("M").astype(str)
    out = pay.groupby("month")["amount"].sum().reset_index(name="revenue")
    return out.sort_values("month")


def monthly_expense_series(expenses: pd.DataFrame) -> pd.DataFrame:
    if expenses.empty:
        return pd.DataFrame(columns=["month", "expense"])
    exp = expenses.copy()
    exp["amount"] = _to_numeric(exp["amount"])
    exp["expense_date"] = pd.to_datetime(exp["expense_date"], errors="coerce")
    exp = exp.dropna(subset=["expense_date"])
    exp["month"] = exp["expense_date"].dt.to_period("M").astype(str)
    out = exp.groupby("month")["amount"].sum().reset_index(name="expense")
    return out.sort_values("month")


def revenue_by(enriched_projects: pd.DataFrame, by_col: str) -> pd.DataFrame:
    if enriched_projects.empty:
        return pd.DataFrame(columns=[by_col, "revenue"])
    out = enriched_projects.groupby(by_col)["amount_received"].sum().reset_index(name="revenue")
    return out.sort_values("revenue", ascending=False)


def expense_distribution(expenses: pd.DataFrame) -> pd.DataFrame:
    if expenses.empty:
        return pd.DataFrame(columns=["category", "amount"])
    exp = expenses.copy()
    exp["amount"] = _to_numeric(exp["amount"])
    return exp.groupby("category")["amount"].sum().reset_index().sort_values("amount", ascending=False)


def profit_trend(payments: pd.DataFrame, expenses: pd.DataFrame) -> pd.DataFrame:
    rev = monthly_revenue_series(payments)
    exp = monthly_expense_series(expenses)
    merged = pd.merge(rev, exp, on="month", how="outer").fillna(0).sort_values("month")
    merged["profit"] = merged["revenue"] - merged["expense"]
    return merged


def largest_client(enriched_projects: pd.DataFrame):
    if enriched_projects.empty:
        return None, 0.0
    rb = revenue_by(enriched_projects, "client_name")
    if rb.empty:
        return None, 0.0
    top = rb.iloc[0]
    return top["client_name"], top["revenue"]


def best_service(enriched_projects: pd.DataFrame):
    if enriched_projects.empty:
        return None, 0.0
    rb = revenue_by(enriched_projects, "service_category")
    if rb.empty:
        return None, 0.0
    top = rb.iloc[0]
    return top["service_category"], top["revenue"]


def average_project_value(projects: pd.DataFrame) -> float:
    if projects.empty:
        return 0.0
    return round(_to_numeric(projects["project_value"]).mean(), 2)
