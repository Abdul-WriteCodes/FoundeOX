"""
Google Sheets data layer for VaultX.

Revenue model:
- "Research & Consulting" is tracked as client Projects + Payments
  (an engagement with a value that gets paid down over time).
- Each SaaS product is a "stream" tracked two ways that can coexist:
    - SaaSMonthly: one quick manual total per product per month
    - SaaSTransactions: individual sales/subscription payments
  For any product+month, if a manual monthly total exists it is treated
  as authoritative for that month (so you don't double count); otherwise
  the month's revenue is the sum of that month's logged transactions.
- Expenses can optionally be tagged to a stream (a product, "Research &
  Consulting", or "General/Overhead") so per-stream profit is possible,
  but an untagged/"General" expense just counts against the combined total.
"""

import uuid
from datetime import datetime

import gspread
import pandas as pd
import streamlit as st
from google.oauth2.service_account import Credentials

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

CONSULTING_STREAM = "Research & Consulting"
GENERAL_STREAM = "General/Overhead"

SHEET_SCHEMAS = {
    "Projects": [
        "project_id", "client_name", "project_title", "service_category",
        "project_value", "currency", "start_date", "due_date",
        "project_status", "payment_status", "acquisition_source",
        "notes", "created_at",
    ],
    "Payments": [
        "payment_id", "project_id", "payment_date", "amount",
        "payment_method", "transaction_reference", "notes", "created_at",
    ],
    "SaaSMonthly": [
        "entry_id", "product", "month", "amount", "currency", "notes", "created_at",
    ],
    "SaaSTransactions": [
        "transaction_id", "product", "date", "amount", "currency",
        "customer", "payment_method", "notes", "created_at",
    ],
    "Expenses": [
        "expense_id", "expense_date", "category", "stream", "amount",
        "currency", "description", "created_at",
    ],
    "Settings": [
        "setting_type", "value",
    ],
}

DEFAULT_SETTINGS = [
    ("service_category", "Consulting"),
    ("service_category", "Research"),
    ("service_category", "Advisory"),
    ("service_category", "Other"),
    ("currency", "USD"),
    ("currency", "NGN"),
    ("currency", "GBP"),
    ("currency", "EUR"),
    ("expense_category", "Internet"),
    ("expense_category", "Software"),
    ("expense_category", "Hosting"),
    ("expense_category", "Marketing"),
    ("expense_category", "Transportation"),
    ("expense_category", "Equipment"),
    ("expense_category", "Office Supplies"),
    ("expense_category", "Miscellaneous"),
    ("acquisition_source", "Referral"),
    ("acquisition_source", "LinkedIn"),
    ("acquisition_source", "Twitter/X"),
    ("acquisition_source", "Cold Outreach"),
    ("acquisition_source", "Inbound/Website"),
    ("acquisition_source", "Other"),
    ("product", "BizTrack-OS"),
    ("product", "StaX360 Suite"),
    ("product", "Kopt-OS"),
    ("product", "Crea8it Labs"),
    ("product", "Agent43"),
    ("product", "EmpiricX"),
    ("product", "Other"),
    # Reporting currency for combined/cross-stream totals. All aggregation
    # across streams/projects/products converts into this currency first -
    # raw amounts are NEVER summed across different currencies.
    ("base_currency", "USD"),
    # One rate per currency: how many units of base_currency one unit of
    # that currency is worth. These are placeholders - YOU must keep them
    # current in Settings; this app has no live FX feed.
    ("exchange_rate", "USD=1"),
    ("exchange_rate", "NGN=0.00062"),
    ("exchange_rate", "GBP=1.27"),
    ("exchange_rate", "EUR=1.08"),
]


@st.cache_resource(show_spinner=False)
def get_client():
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"], scopes=SCOPES
    )
    return gspread.authorize(creds)


@st.cache_resource(show_spinner=False)
def get_spreadsheet():
    client = get_client()
    sheet_url = st.secrets["app_config"]["sheet_url"]
    return client.open_by_url(sheet_url)


@st.cache_resource(show_spinner=False)
def _bootstrap_once():
    """Create any missing worksheets with correct headers, migrate missing
    columns into existing sheets, and seed Settings defaults on first run.

    Wrapped in cache_resource so this - which is several API calls - runs
    ONCE per running app process, not on every rerun/page load. Sheets
    already exist after the first successful run, so re-checking on every
    interaction just burns read quota for no benefit."""
    ss = get_spreadsheet()
    existing_titles = [ws.title for ws in ss.worksheets()]

    for sheet_name, headers in SHEET_SCHEMAS.items():
        if sheet_name not in existing_titles:
            ws = ss.add_worksheet(title=sheet_name, rows=1000, cols=len(headers) + 2)
            ws.append_row(headers)
        else:
            ws = ss.worksheet(sheet_name)
            current_headers = ws.row_values(1)
            if not current_headers:
                ws.append_row(headers)
            else:
                missing = [h for h in headers if h not in current_headers]
                if missing:
                    new_headers = current_headers + missing
                    ws.update("A1", [new_headers])

    settings_ws = ss.worksheet("Settings")
    rows = settings_ws.get_all_records()
    if not rows:
        settings_ws.append_rows([list(pair) for pair in DEFAULT_SETTINGS])
    else:
        existing_pairs = {(r["setting_type"], r["value"]) for r in rows}
        missing_defaults = [p for p in DEFAULT_SETTINGS if p not in existing_pairs and p[0] == "product"]
        if missing_defaults and not any(r["setting_type"] == "product" for r in rows):
            settings_ws.append_rows([list(p) for p in missing_defaults])

    return True


def bootstrap_sheets():
    _bootstrap_once()


def _worksheet(name):
    return get_spreadsheet().worksheet(name)


@st.cache_data(ttl=20, show_spinner=False)
def read_sheet(name: str) -> pd.DataFrame:
    """Read a worksheet into a DataFrame. Cached for 20 seconds - every
    Streamlit widget interaction reruns the whole page script, so without
    this cache a single page view can trigger 5-6+ fresh API reads. Any
    write elsewhere calls _invalidate_cache() to force an immediate
    fresh read instead of waiting out the TTL."""
    ws = _worksheet(name)
    records = ws.get_all_records()
    df = pd.DataFrame(records)
    schema = SHEET_SCHEMAS[name]
    if df.empty:
        return pd.DataFrame(columns=schema)
    for col in schema:
        if col not in df.columns:
            df[col] = None
    return df[schema]


def _invalidate_cache():
    """Call after any write so the next read reflects it immediately,
    rather than serving stale cached data for up to 20 seconds."""
    read_sheet.clear()


def refresh_data():
    """Public wrapper for a manual 'Refresh data' button in the UI."""
    read_sheet.clear()


def _new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8].upper()}"


def append_row(sheet_name: str, row: dict):
    ws = _worksheet(sheet_name)
    schema = SHEET_SCHEMAS[sheet_name]
    values = [str(row.get(col, "")) for col in schema]
    ws.append_row(values)
    _invalidate_cache()


def update_row(sheet_name: str, id_col: str, id_value: str, updates: dict):
    ws = _worksheet(sheet_name)
    schema = SHEET_SCHEMAS[sheet_name]
    cell = ws.find(id_value, in_column=schema.index(id_col) + 1)
    if cell is None:
        raise ValueError(f"{id_value} not found in {sheet_name}")
    row_values = ws.row_values(cell.row)
    row_dict = {schema[i]: (row_values[i] if i < len(row_values) else "") for i in range(len(schema))}
    row_dict.update({k: str(v) for k, v in updates.items()})
    new_values = [row_dict.get(col, "") for col in schema]
    ws.update(f"A{cell.row}", [new_values])
    _invalidate_cache()


def delete_row(sheet_name: str, id_col: str, id_value: str):
    ws = _worksheet(sheet_name)
    schema = SHEET_SCHEMAS[sheet_name]
    cell = ws.find(id_value, in_column=schema.index(id_col) + 1)
    if cell is None:
        return
    ws.delete_rows(cell.row)
    _invalidate_cache()


def delete_rows_where(sheet_name: str, match_col: str, match_value: str):
    ws = _worksheet(sheet_name)
    schema = SHEET_SCHEMAS[sheet_name]
    col_idx = schema.index(match_col) + 1
    col_values = ws.col_values(col_idx)
    rows_to_delete = [i + 1 for i, v in enumerate(col_values) if v == match_value and i > 0]
    for row_num in sorted(rows_to_delete, reverse=True):
        ws.delete_rows(row_num)
    _invalidate_cache()


# ---- convenience wrappers ----

def create_project(data: dict) -> str:
    pid = _new_id("PRJ")
    data["project_id"] = pid
    data["created_at"] = datetime.now().isoformat(timespec="seconds")
    append_row("Projects", data)
    return pid


def create_payment(data: dict) -> str:
    payid = _new_id("PAY")
    data["payment_id"] = payid
    data["created_at"] = datetime.now().isoformat(timespec="seconds")
    append_row("Payments", data)
    return payid


def upsert_saas_monthly(product: str, month: str, amount: float, currency: str, notes: str) -> str:
    """One row per product+month. If a row already exists for this
    product+month, overwrite its amount/notes instead of creating a
    duplicate."""
    existing = read_sheet("SaaSMonthly")
    match = existing[(existing["product"] == product) & (existing["month"] == month)]
    if not match.empty:
        entry_id = match.iloc[0]["entry_id"]
        update_row("SaaSMonthly", "entry_id", entry_id, {
            "amount": amount, "currency": currency, "notes": notes,
        })
        return entry_id
    entry_id = _new_id("SM")
    append_row("SaaSMonthly", {
        "entry_id": entry_id, "product": product, "month": month,
        "amount": amount, "currency": currency, "notes": notes,
        "created_at": datetime.now().isoformat(timespec="seconds"),
    })
    return entry_id


def create_saas_transaction(data: dict) -> str:
    tid = _new_id("TXN")
    data["transaction_id"] = tid
    data["created_at"] = datetime.now().isoformat(timespec="seconds")
    append_row("SaaSTransactions", data)
    return tid


def create_expense(data: dict) -> str:
    eid = _new_id("EXP")
    data["expense_id"] = eid
    data["created_at"] = datetime.now().isoformat(timespec="seconds")
    append_row("Expenses", data)
    return eid


def add_setting(setting_type: str, value: str):
    append_row("Settings", {"setting_type": setting_type, "value": value})


def delete_setting(setting_type: str, value: str):
    ws = _worksheet("Settings")
    records = ws.get_all_records()
    for i, r in enumerate(records):
        if r["setting_type"] == setting_type and r["value"] == value:
            ws.delete_rows(i + 2)
            break
    _invalidate_cache()


def set_base_currency(currency_code: str):
    """base_currency is a single-value setting - remove any existing
    entries before adding the new one so there's never more than one."""
    ws = _worksheet("Settings")
    records = ws.get_all_records()
    rows_to_delete = [i + 2 for i, r in enumerate(records) if r["setting_type"] == "base_currency"]
    for row_num in sorted(rows_to_delete, reverse=True):
        ws.delete_rows(row_num)
    ws.append_row(["base_currency", currency_code])
    _invalidate_cache()


def upsert_exchange_rate(currency_code: str, rate_to_base: float):
    """One rate per currency, stored as 'CODE=rate'. Overwrites any
    existing rate for that currency instead of duplicating it."""
    ws = _worksheet("Settings")
    records = ws.get_all_records()
    for i, r in enumerate(records):
        if r["setting_type"] == "exchange_rate" and r["value"].split("=")[0] == currency_code:
            ws.update(f"B{i + 2}", [[f"{currency_code}={rate_to_base}"]])
            _invalidate_cache()
            return
    ws.append_row(["exchange_rate", f"{currency_code}={rate_to_base}"])
    _invalidate_cache()
