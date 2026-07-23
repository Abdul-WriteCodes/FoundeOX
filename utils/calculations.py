"""
All derived numbers live here. Nothing in this module talks to Google
Sheets - it only transforms DataFrames already loaded by utils.sheets.

CURRENCY HANDLING - read this before touching aggregation logic:

Every project, payment, expense, and SaaS entry is recorded in its own
currency. A single project's numbers (amount_received vs. project_value,
payment_percentage, etc.) never need conversion, because a project's
payments are always in that project's own currency.

But the moment we combine numbers ACROSS projects, clients, products, or
streams - dashboard totals, monthly trends, "largest client", expense
sums, anything that adds two rows together - we cannot just sum raw
amounts if they're in different currencies. NGN 10,000 and $10,000 are
not the same number of dollars, and adding them as if they were either
wildly inflates or deflates the total depending on which currency
"wins". Every aggregation function below converts each row to the
saved base currency FIRST (using the exchange rates from Settings),
then sums. Never add two `amount` columns together without doing this.
"""

from datetime import datetime

import pandas as pd

from utils.sheets import CONSULTING_STREAM


def _to_numeric(series):
    return pd.to_numeric(series, errors="coerce").fillna(0)


# ---------------- Base currency + exchange rates ----------------

def get_base_currency(settings: pd.DataFrame) -> str:
    vals = settings.loc[settings["setting_type"] == "base_currency", "value"].tolist()
    return vals[0] if vals else "USD"


def get_fx_rates(settings: pd.DataFrame) -> dict:
    """Returns {currency_code: rate_to_base}. A currency with no saved
    rate is NOT silently treated as 1:1 - callers should flag it."""
    rates = {}
    rate_rows = settings.loc[settings["setting_type"] == "exchange_rate", "value"].tolist()
    for val in rate_rows:
        if "=" in str(val):
            code, rate_str = val.split("=", 1)
            try:
                rates[code.strip()] = float(rate_str)
            except ValueError:
                continue
    return rates


def missing_fx_currencies(*dfs_with_currency_col, rates: dict) -> list:
    """Check a set of DataFrames (each must have a 'currency' column) for
    any currency in use that has no saved exchange rate. Surface these in
    the UI rather than silently mis-converting them."""
    used = set()
    for df in dfs_with_currency_col:
        if df is not None and not df.empty and "currency" in df.columns:
            used.update(df["currency"].dropna().unique().tolist())
    return sorted([c for c in used if c and c not in rates])


def _convert(amounts: pd.Series, currencies: pd.Series, rates: dict, base: str) -> pd.Series:
    """Convert each amount to base currency using its own currency's
    rate. Amounts in an unrecognized currency (no saved rate) are left
    UNCONVERTED rather than silently dropped or wrongly treated as
    base-currency - callers should surface missing_fx_currencies() to
    the user so this never happens quietly."""
    amounts = pd.to_numeric(amounts, errors="coerce").fillna(0)

    def rate_for(cur):
        if cur == base:
            return 1.0
        return rates.get(cur, 1.0)  # fallback 1.0 only as last resort

    factors = currencies.map(rate_for)
    return amounts * factors


def convert_to_base(amounts: pd.Series, currencies: pd.Series, rates: dict, base: str) -> pd.Series:
    """Public entry point for converting a Series of amounts (each with
    its own currency) into base currency. Use this instead of summing
    a raw 'amount' column whenever the rows might span currencies -
    e.g. a filtered table's displayed total."""
    return _convert(amounts, currencies, rates, base)

def enrich_projects(projects: pd.DataFrame, payments: pd.DataFrame, rates: dict, base: str) -> pd.DataFrame:
    """Attach amount_received, outstanding_balance, payment_percentage
    (all in the PROJECT's own currency - no conversion needed within a
    single project), plus *_base columns (converted to base currency)
    for cross-project aggregation like 'largest client' or dashboard
    totals."""
    df = projects.copy()
    if df.empty:
        for c in ["amount_received", "outstanding_balance", "payment_percentage",
                  "project_value_base", "amount_received_base", "outstanding_balance_base"]:
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

    # base-currency columns for cross-project aggregation
    df["project_value_base"] = _convert(df["project_value"], df["currency"], rates, base)
    df["amount_received_base"] = _convert(df["amount_received"], df["currency"], rates, base)
    df["outstanding_balance_base"] = _convert(df["outstanding_balance"], df["currency"], rates, base)

    return df


def consulting_monthly_revenue(payments: pd.DataFrame, projects: pd.DataFrame, rates: dict, base: str) -> pd.DataFrame:
    """Consulting revenue by month, converted to base currency. Payments
    don't carry their own currency column - they inherit it from their
    project, so we join to Projects first."""
    if payments.empty:
        return pd.DataFrame(columns=["month", "revenue"])
    pay = payments.merge(projects[["project_id", "currency"]], on="project_id", how="left")
    pay["amount"] = _to_numeric(pay["amount"])
    pay["currency"] = pay["currency"].fillna(base)
    pay["amount_base"] = _convert(pay["amount"], pay["currency"], rates, base)
    pay["payment_date"] = pd.to_datetime(pay["payment_date"], errors="coerce")
    pay = pay.dropna(subset=["payment_date"])
    pay["month"] = pay["payment_date"].dt.to_period("M").astype(str)
    return pay.groupby("month")["amount_base"].sum().reset_index(name="revenue").sort_values("month")


# ---------------- SaaS products (Monthly totals + Transactions) ----------------

def saas_transactions_monthly(saas_transactions: pd.DataFrame, rates: dict, base: str) -> pd.DataFrame:
    """Sum individual transactions per product+month, converted to base currency."""
    if saas_transactions.empty:
        return pd.DataFrame(columns=["product", "month", "revenue"])
    tx = saas_transactions.copy()
    tx["amount"] = _to_numeric(tx["amount"])
    tx["amount_base"] = _convert(tx["amount"], tx["currency"], rates, base)
    tx["date"] = pd.to_datetime(tx["date"], errors="coerce")
    tx = tx.dropna(subset=["date"])
    tx["month"] = tx["date"].dt.to_period("M").astype(str)
    return tx.groupby(["product", "month"])["amount_base"].sum().reset_index(name="revenue")


def saas_reconciled_monthly(saas_monthly: pd.DataFrame, saas_transactions: pd.DataFrame,
                             rates: dict, base: str) -> pd.DataFrame:
    """The authoritative product+month revenue table (in base currency):
    a manual monthly total (if present) overrides that month's
    transaction sum, otherwise the transaction sum is used."""
    tx_monthly = saas_transactions_monthly(saas_transactions, rates, base)

    if saas_monthly.empty:
        manual = pd.DataFrame(columns=["product", "month", "revenue"])
    else:
        m = saas_monthly.copy()
        m["amount"] = _to_numeric(m["amount"])
        m["revenue"] = _convert(m["amount"], m["currency"], rates, base)
        manual = m[["product", "month", "revenue"]]

    if manual.empty and tx_monthly.empty:
        return pd.DataFrame(columns=["product", "month", "revenue", "source"])

    manual = manual.copy()
    tx_monthly = tx_monthly.copy()
    manual["source"] = "manual"
    tx_monthly["source"] = "transactions"

    combined = pd.concat([manual, tx_monthly], ignore_index=True)
    combined = combined.sort_values("source")  # 'manual' < 'transactions' alphabetically
    combined = combined.drop_duplicates(subset=["product", "month"], keep="first")
    return combined.sort_values(["product", "month"])


def saas_total_by_product(saas_monthly: pd.DataFrame, saas_transactions: pd.DataFrame,
                           rates: dict, base: str) -> pd.DataFrame:
    reconciled = saas_reconciled_monthly(saas_monthly, saas_transactions, rates, base)
    if reconciled.empty:
        return pd.DataFrame(columns=["product", "revenue"])
    return reconciled.groupby("product")["revenue"].sum().reset_index().sort_values("revenue", ascending=False)


# ---------------- Combined streams ----------------

def stream_revenue_monthly(payments: pd.DataFrame, projects: pd.DataFrame, saas_monthly: pd.DataFrame,
                            saas_transactions: pd.DataFrame, rates: dict, base: str) -> pd.DataFrame:
    """One table: stream, month, revenue (all in base currency) - where
    stream is either 'Research & Consulting' or a product name."""
    consulting = consulting_monthly_revenue(payments, projects, rates, base)
    if not consulting.empty:
        consulting = consulting.copy()
        consulting["stream"] = CONSULTING_STREAM

    saas = saas_reconciled_monthly(saas_monthly, saas_transactions, rates, base)
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

def _expenses_base(expenses: pd.DataFrame, rates: dict, base: str) -> pd.DataFrame:
    exp = expenses.copy()
    exp["amount"] = _to_numeric(exp["amount"])
    exp["amount_base"] = _convert(exp["amount"], exp["currency"], rates, base)
    return exp


def monthly_expense_series(expenses: pd.DataFrame, rates: dict, base: str) -> pd.DataFrame:
    if expenses.empty:
        return pd.DataFrame(columns=["month", "expense"])
    exp = _expenses_base(expenses, rates, base)
    exp["expense_date"] = pd.to_datetime(exp["expense_date"], errors="coerce")
    exp = exp.dropna(subset=["expense_date"])
    exp["month"] = exp["expense_date"].dt.to_period("M").astype(str)
    return exp.groupby("month")["amount_base"].sum().reset_index(name="expense").sort_values("month")


def expense_distribution(expenses: pd.DataFrame, rates: dict, base: str) -> pd.DataFrame:
    if expenses.empty:
        return pd.DataFrame(columns=["category", "amount"])
    exp = _expenses_base(expenses, rates, base)
    return exp.groupby("category")["amount_base"].sum().reset_index().rename(
        columns={"amount_base": "amount"}
    ).sort_values("amount", ascending=False)


def expense_by_stream(expenses: pd.DataFrame, rates: dict, base: str) -> pd.DataFrame:
    if expenses.empty:
        return pd.DataFrame(columns=["stream", "amount"])
    exp = _expenses_base(expenses, rates, base)
    exp["stream"] = exp["stream"].replace("", "General/Overhead").fillna("General/Overhead")
    return exp.groupby("stream")["amount_base"].sum().reset_index().rename(
        columns={"amount_base": "amount"}
    ).sort_values("amount", ascending=False)


def profit_trend(stream_monthly: pd.DataFrame, expenses: pd.DataFrame, rates: dict, base: str) -> pd.DataFrame:
    rev = combined_monthly_revenue(stream_monthly)
    exp = monthly_expense_series(expenses, rates, base)
    merged = pd.merge(rev, exp, on="month", how="outer").sort_values("month")
    if merged.empty:
        return merged
    merged["revenue"] = pd.to_numeric(merged["revenue"], errors="coerce").fillna(0)
    merged["expense"] = pd.to_numeric(merged["expense"], errors="coerce").fillna(0)
    merged["profit"] = merged["revenue"] - merged["expense"]
    return merged


# ---------------- Dashboard metrics (all in base currency) ----------------

def dashboard_metrics(projects, payments, saas_monthly, saas_transactions, expenses, rates, base) -> dict:
    enriched = enrich_projects(projects, payments, rates, base)
    stream_monthly = stream_revenue_monthly(payments, projects, saas_monthly, saas_transactions, rates, base)
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

    today_total = 0.0
    if not payments.empty:
        pay = payments.merge(projects[["project_id", "currency"]], on="project_id", how="left")
        pay["amount"] = _to_numeric(pay["amount"])
        pay["currency"] = pay["currency"].fillna(base)
        pay["amount_base"] = _convert(pay["amount"], pay["currency"], rates, base)
        pay["payment_date"] = pd.to_datetime(pay["payment_date"], errors="coerce")
        today_total += pay.loc[pay["payment_date"].dt.date == today, "amount_base"].sum()
    if not saas_transactions.empty:
        tx = saas_transactions.copy()
        tx["amount"] = _to_numeric(tx["amount"])
        tx["amount_base"] = _convert(tx["amount"], tx["currency"], rates, base)
        tx["date"] = pd.to_datetime(tx["date"], errors="coerce")
        today_total += tx.loc[tx["date"].dt.date == today, "amount_base"].sum()

    outstanding = enriched["outstanding_balance_base"].sum() if not enriched.empty else 0.0
    total_projects = len(enriched)
    total_clients = enriched["client_name"].nunique() if not enriched.empty else 0

    total_expenses = _expenses_base(expenses, rates, base)["amount_base"].sum() if not expenses.empty else 0.0
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
    """Uses amount_received_base (converted) - never sum native-currency
    amounts across a client's projects if they're in different currencies."""
    if enriched_projects.empty:
        return None, 0.0
    rb = enriched_projects.groupby("client_name")["amount_received_base"].sum().reset_index()
    if rb.empty:
        return None, 0.0
    top = rb.sort_values("amount_received_base", ascending=False).iloc[0]
    return top["client_name"], top["amount_received_base"]


def average_project_value(projects: pd.DataFrame, rates: dict, base: str) -> float:
    """Average project value in base currency - averaging native amounts
    across different currencies would be meaningless."""
    if projects.empty:
        return 0.0
    values_base = _convert(_to_numeric(projects["project_value"]), projects["currency"], rates, base)
    return round(values_base.mean(), 2)
