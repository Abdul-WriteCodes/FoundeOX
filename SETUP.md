# VaultX — Setup Guide

VaultX is a Streamlit + Google Sheets app for tracking revenue and expenses
across Research & Consulting work and SaaS products. This guide walks
through cloning the repo and getting it running, either locally or on
Streamlit Community Cloud.

---

## 1. Prerequisites

- Python 3.9+
- A Google account
- (Optional, for deployment) A [Streamlit Community Cloud](https://streamlit.io/cloud) account

---

## 2. Clone the repo

```bash
git clone <your-fork-or-repo-url>
cd Vaultx-main
```

---

## 3. Install dependencies

It's recommended to use a virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

pip install -r requirements.txt
```

This installs Streamlit, pandas, streamlit-echarts, gspread, google-auth,
and python-dateutil.

---

## 4. Set up Google Sheets access

VaultX stores all data in a Google Sheet, accessed via a Google Cloud
service account. You do **not** need to create the worksheets yourself —
the app creates and seeds them automatically on first run (see step 6).

### 4.1 Create a Google Cloud service account

1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Create a new project (or select an existing one).
3. Enable these two APIs for the project:
   - **Google Sheets API**
   - **Google Drive API**
4. Go to **IAM & Admin → Service Accounts → Create Service Account**.
5. Give it any name (e.g. `vaultx-app`), skip optional role assignment.
6. Open the new service account → **Keys → Add Key → Create new key → JSON**.
7. Download the JSON key file — you'll need its contents in step 5.

### 4.2 Create the spreadsheet

1. Create a new, blank Google Sheet (any name — e.g. "VaultX Data").
2. Share it with the service account's email address (found in the JSON
   key file as `client_email`), giving it **Editor** access.
3. Copy the sheet's URL — you'll need it in step 5.

> The app will create the following worksheets automatically the first
> time it runs: `Projects`, `Payments`, `SaaSMonthly`, `SaaSTransactions`,
> `Expenses`, `Settings`. It also seeds `Settings` with default service
> categories, currencies, expense categories, acquisition sources,
> product names, a base currency, and placeholder exchange rates.
>
> You don't need to create these tabs or type headers yourself — this is
> just so you know what to expect when you open the sheet after first run.
> The exact structure is below in case you want to inspect the data
> directly or write your own queries against it.

### 4.3 Worksheet structure (auto-created)

Each worksheet is a flat table with the columns below, in this exact
order (defined in `utils/sheets.py`, `SHEET_SCHEMAS`):

**`Projects`** — one row per client engagement
| Column | Notes |
|---|---|
| `project_id` | e.g. `PRJ-A1B2C3D4` |
| `client_name` | |
| `project_title` | |
| `service_category` | from Settings `service_category` values |
| `project_value` | total agreed value, in `currency` |
| `currency` | e.g. `USD`, `NGN`, `GBP`, `EUR` |
| `start_date`, `due_date` | `YYYY-MM-DD` |
| `project_status` | free text, e.g. In Progress / Completed |
| `payment_status` | derived: Unpaid / Partial / Paid |
| `acquisition_source` | from Settings `acquisition_source` values |
| `notes` | |
| `created_at` | ISO timestamp, set on creation |

**`Payments`** — one row per payment against a project
| Column | Notes |
|---|---|
| `payment_id` | e.g. `PAY-A1B2C3D4` |
| `project_id` | foreign key into `Projects` |
| `payment_date` | `YYYY-MM-DD` |
| `amount` | in the parent project's currency (not stored here) |
| `payment_method` | |
| `transaction_reference` | |
| `notes` | |
| `created_at` | |

**`SaaSMonthly`** — one quick manual revenue total per product per month
| Column | Notes |
|---|---|
| `entry_id` | e.g. `SM-A1B2C3D4` |
| `product` | from Settings `product` values |
| `month` | `YYYY-MM` |
| `amount` | |
| `currency` | |
| `notes` | |
| `created_at` | |

One row per product+month — re-saving the same product/month overwrites
the existing row instead of duplicating it.

**`SaaSTransactions`** — individual SaaS sales/subscription payments
| Column | Notes |
|---|---|
| `transaction_id` | e.g. `TXN-A1B2C3D4` |
| `product` | |
| `date` | `YYYY-MM-DD` |
| `amount` | |
| `currency` | |
| `customer` | |
| `payment_method` | |
| `notes` | |
| `created_at` | |

If a `SaaSMonthly` total exists for a product+month, it's treated as
authoritative for that period and the matching `SaaSTransactions` rows
are excluded from totals (to avoid double-counting) — see
`saas_reconciled_monthly()` in `utils/calculations.py`.

**`Expenses`**
| Column | Notes |
|---|---|
| `expense_id` | e.g. `EXP-A1B2C3D4` |
| `expense_date` | `YYYY-MM-DD` |
| `category` | from Settings `expense_category` values |
| `stream` | optional: a product name, `Research & Consulting`, or blank/`General/Overhead` |
| `amount` | |
| `currency` | |
| `description` | |
| `created_at` | |

**`Settings`** — key/value config, not a data table
| Column | Notes |
|---|---|
| `setting_type` | one of: `service_category`, `currency`, `expense_category`, `acquisition_source`, `product`, `base_currency`, `exchange_rate` |
| `value` | for most types, the plain value (e.g. `NGN`); for `exchange_rate`, stored as `CODE=rate` (e.g. `NGN=0.00062`), meaning 1 unit of that currency = `rate` units of `base_currency` |

`base_currency` and `exchange_rate` rows drive all cross-project /
cross-stream totals — every amount is converted into `base_currency`
before summing, never summed raw across currencies. There's no live FX
feed, so exchange rates must be kept up to date manually via the
**Settings** page in the app.

---

## 5. Configure secrets

Streamlit reads credentials from a `secrets.toml` file (local) or the
Secrets panel (Streamlit Cloud). Create the local file:

```bash
mkdir -p .streamlit
touch .streamlit/secrets.toml
```

Fill it in with this structure:

```toml
[app_config]
app_password = "choose-a-password-here"
sheet_url = "https://docs.google.com/spreadsheets/d/your-sheet-id/edit"

[gcp_service_account]
type = "service_account"
project_id = "your-project-id"
private_key_id = "..."
private_key = "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
client_email = "vaultx-app@your-project-id.iam.gserviceaccount.com"
client_id = "..."
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "..."
universe_domain = "googleapis.com"
```

- Copy every field except `type`/URLs directly from your downloaded JSON
  key file — the field names match 1:1.
- `app_password` is the single shared password gating the login screen
  (`app.py` checks it directly, no username/multi-user auth).
- `sheet_url` is the full URL of the Google Sheet from step 4.2.
- **Never commit `secrets.toml`** — add `.streamlit/secrets.toml` to
  `.gitignore` if it isn't already.

---

## 6. Run locally

```bash
streamlit run app.py
```

The app will open in your browser. On first load it connects to your
sheet and bootstraps the worksheets/schema/defaults described above —
this happens once per app process, so the first load may take a couple
seconds longer.

Log in with the `app_password` you set in `secrets.toml`.

---

## 7. Deploy to Streamlit Community Cloud (optional)

1. Push your repo to GitHub.
2. Go to [share.streamlit.io](https://share.streamlit.io/) → **New app**.
3. Point it at your repo, branch, and `app.py` as the main file.
4. In the app's **Settings → Secrets**, paste the same contents as your
   local `.streamlit/secrets.toml`.
5. Deploy. Subsequent pushes to the branch auto-redeploy.

---

## 8. Project structure

```
app.py                        # Entry point: login gate + main dashboard
pages/
  1_Consulting_Projects.py    # Client project CRUD
  2_Consulting_Payments.py    # Payment tracking against projects
  3_SaaS_Revenue.py           # Monthly totals + individual transactions per product
  4_Expenses.py               # Expense tracking by category/stream
  5_Analytics.py              # Cross-stream analytics and trends
  6_Settings.py                # Manage categories, currencies, products, FX rates
utils/
  sheets.py                   # All Google Sheets read/write logic + schema
  calculations.py             # Revenue/profit/FX aggregation logic
  charts.py                   # Chart building (streamlit-echarts)
  styling.py                  # Custom CSS/theming, including the login screen
```

---

## 9. Notes

- **Currency handling**: all cross-stream totals convert through the
  `base_currency` setting using the `exchange_rate` entries in Settings.
  Raw amounts in different currencies are never summed directly — keep
  the exchange rates current manually, as there's no live FX feed.
- **Caching**: sheet reads are cached for 20 seconds (`st.cache_data`)
  to avoid hammering the Sheets API on every widget interaction; writes
  invalidate the cache immediately so changes show up right away.
- **Single-user by design**: there's one shared `app_password`, not
  per-user accounts — this is meant as a personal/founder tool, not a
  multi-tenant product.
