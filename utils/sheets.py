"""
Google Sheets data layer for Founder Revenue OS.

This module owns:
- Authenticating to Google Sheets via a service account
- Creating the four required worksheets (with headers) if they don't exist
- Reading each worksheet into a pandas DataFrame
- Appending / updating / deleting rows by ID

Every other part of the app should go through this module rather than
calling gspread directly, so there is exactly one place that knows about
sheet layout.
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

# Column order is the contract for each worksheet. If you add a column,
# add it here AND it will be auto-migrated into existing sheets on next run.
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
    "Expenses": [
        "expense_id", "expense_date", "category", "amount", "currency",
        "description", "created_at",
    ],
    "Settings": [
        "setting_type", "value",
    ],
}

DEFAULT_SETTINGS = [
    ("service_category", "Consulting"),
    ("service_category", "Web Development"),
    ("service_category", "Data Analysis"),
    ("service_category", "Content Writing"),
    ("service_category", "Design"),
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
]


@st.cache_resource(show_spinner=False)
def get_client():
    """Authenticate once per session and cache the gspread client."""
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"], scopes=SCOPES
    )
    return gspread.authorize(creds)


@st.cache_resource(show_spinner=False)
def get_spreadsheet():
    client = get_client()
    sheet_url = st.secrets["app_config"]["sheet_url"]
    return client.open_by_url(sheet_url)


def bootstrap_sheets():
    """Create any missing worksheets with correct headers, and seed
    Settings with sensible defaults on first run. Safe to call every
    time the app starts - it's a no-op if everything already exists."""
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
                # migrate: add any missing columns at the end
                missing = [h for h in headers if h not in current_headers]
                if missing:
                    new_headers = current_headers + missing
                    ws.update("A1", [new_headers])

    # seed default settings if the Settings sheet is empty of rows
    settings_ws = ss.worksheet("Settings")
    rows = settings_ws.get_all_records()
    if not rows:
        settings_ws.append_rows([list(pair) for pair in DEFAULT_SETTINGS])


def _worksheet(name):
    return get_spreadsheet().worksheet(name)


def read_sheet(name: str) -> pd.DataFrame:
    """Read a worksheet into a DataFrame with the correct column order,
    even if the sheet is empty."""
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


def _new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8].upper()}"


def append_row(sheet_name: str, row: dict):
    ws = _worksheet(sheet_name)
    schema = SHEET_SCHEMAS[sheet_name]
    values = [str(row.get(col, "")) for col in schema]
    ws.append_row(values)


def update_row(sheet_name: str, id_col: str, id_value: str, updates: dict):
    """Find the row where id_col == id_value and overwrite the given
    fields in place."""
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


def delete_row(sheet_name: str, id_col: str, id_value: str):
    ws = _worksheet(sheet_name)
    schema = SHEET_SCHEMAS[sheet_name]
    cell = ws.find(id_value, in_column=schema.index(id_col) + 1)
    if cell is None:
        return
    ws.delete_rows(cell.row)


def delete_rows_where(sheet_name: str, match_col: str, match_value: str):
    """Delete every row where match_col == match_value (e.g. all payments
    for a deleted project). Deletes bottom-up so row indices stay valid."""
    ws = _worksheet(sheet_name)
    schema = SHEET_SCHEMAS[sheet_name]
    col_idx = schema.index(match_col) + 1
    col_values = ws.col_values(col_idx)
    rows_to_delete = [i + 1 for i, v in enumerate(col_values) if v == match_value and i > 0]
    for row_num in sorted(rows_to_delete, reverse=True):
        ws.delete_rows(row_num)


# ---- convenience wrappers used by the pages ----

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
            ws.delete_rows(i + 2)  # +2: header row + 1-indexing
            break
