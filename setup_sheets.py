"""
setup_sheets.py
----------------
One-time script that builds the entire Google Sheet structure the dashboard
expects: Overview, one tab per business, Goals, and Milestones — all with
the correct headers.

Run this ONCE, locally, after you've:
  1. Created a Google Sheet (any name, e.g. "Founder Metrics").
  2. Created a GCP service account and downloaded its JSON key
     (see README.md, Step 1-3).
  3. Shared the Google Sheet with the service account's email
     (found inside the JSON key as "client_email"), giving it Editor access.

Usage:
    pip install gspread google-auth
    python setup_sheets.py --key path/to/service_account.json --sheet-url "https://docs.google.com/spreadsheets/d/XXXX/edit"
"""

import argparse
import gspread
from google.oauth2.service_account import Credentials

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# tab_name -> header row
SHEET_SCHEMA = {
    "Overview": ["Business", "Metric 1", "Metric 2"],
    "BizTrack-OS": ["Month", "Users", "Revenue"],
    "StaX360": ["Month", "Users", "Revenue"],
    "Research & Consulting": ["Month", "Projects", "Revenue"],
    "Crea8it Studio": ["Month", "Members", "Onboarded"],
    "Goals": ["Business", "Metric", "Current", "Target"],
    "Milestones": ["Date", "Business", "Milestone"],
}

OVERVIEW_ROWS = [
    ["BizTrack-OS", "Users", "Revenue"],
    ["StaX360", "Users", "Revenue"],
    ["Research & Consulting", "Projects", "Revenue"],
    ["Crea8it Studio", "Members", "Onboarded"],
]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--key", required=True, help="Path to service account JSON key")
    parser.add_argument("--sheet-url", required=True, help="Full URL of the target Google Sheet")
    args = parser.parse_args()

    creds = Credentials.from_service_account_file(args.key, scopes=SCOPES)
    client = gspread.authorize(creds)
    sh = client.open_by_url(args.sheet_url)

    existing = {ws.title: ws for ws in sh.worksheets()}

    for tab_name, headers in SHEET_SCHEMA.items():
        if tab_name in existing:
            ws = existing[tab_name]
            print(f"[skip] '{tab_name}' already exists — leaving data intact, checking headers.")
            first_row = ws.row_values(1)
            if first_row != headers:
                ws.update("A1", [headers])
                print(f"   -> headers updated on '{tab_name}'")
        else:
            ws = sh.add_worksheet(title=tab_name, rows=200, cols=max(6, len(headers)))
            ws.update("A1", [headers])
            print(f"[created] '{tab_name}' with headers {headers}")

    # Pre-fill Overview with the four known businesses if it's empty
    overview_ws = sh.worksheet("Overview")
    if len(overview_ws.get_all_values()) <= 1:
        overview_ws.update("A2", OVERVIEW_ROWS)
        print("[filled] Overview rows for the 4 default business units")

    # Streamlit Cloud's default "Sheet1" is unused by the dashboard — leave it,
    # gspread/Sheets won't let us delete the very last remaining default sheet
    # if it happens to be the only one, so we just ignore it.

    print("\nDone. Your Google Sheet now has the structure the dashboard expects.")
    print("Next: fill in monthly rows for each business tab, then run the Streamlit app.")


if __name__ == "__main__":
    main()
