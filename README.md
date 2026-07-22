# Founder Revenue OS

A personal business operating system for consultants, freelancers, and
solo founders — track every project from proposal to payment, log
expenses, and see real-time revenue/profit analytics. Built with
**Streamlit** + **Google Sheets** (no database to manage).

---

## 1. Project structure

```
founder-revenue-os/
├── app.py                      # Main dashboard (entry point)
├── requirements.txt
├── .streamlit/
│   └── secrets.toml.example    # Rename to secrets.toml and fill in
├── utils/
│   ├── sheets.py                # Google Sheets connection + CRUD
│   ├── calculations.py          # All derived metrics
│   └── styling.py               # CSS + metric cards
└── pages/
    ├── 1_Projects.py
    ├── 2_Payments.py
    ├── 3_Expenses.py
    ├── 4_Analytics.py
    └── 5_Settings.py
```

Streamlit auto-detects everything in `pages/` and builds the sidebar
navigation for you — you don't need to register pages anywhere.

---

## 2. Google Cloud setup (one-time, ~10 minutes)

You need a **Google Cloud service account** — this is a "robot" account
that the app uses to read/write your Sheet without you having to log in
every time.

1. Go to https://console.cloud.google.com/ and create a new project
   (or reuse an existing one).
2. In the search bar, enable these two APIs:
   - **Google Sheets API**
   - **Google Drive API**
3. Go to **APIs & Services → Credentials → Create Credentials → Service Account**.
   - Give it any name, e.g. `revenue-os-bot`.
   - Skip granting it project-level roles — not needed.
4. Click into the service account you just created → **Keys** tab →
   **Add Key → Create new key → JSON**. This downloads a `.json` file.
   **Keep this file secret — it's the credential for your data.**
5. Open the JSON file. You'll copy fields from it into `secrets.toml`
   in step 4 below.

---

## 3. Create the Google Sheet

1. Create a new blank Google Sheet (sheets.new). Name it anything,
   e.g. "Founder Revenue OS Data".
2. Click **Share** → paste the service account's email address (looks
   like `revenue-os-bot@your-project.iam.gserviceaccount.com` — find it
   in the JSON file under `client_email`) → give it **Editor** access →
   Send.
3. Copy the Sheet's URL from your browser address bar — you'll need it
   in the next step.

**You do not need to create the worksheets/tabs yourself.** The app
creates all four automatically (`Projects`, `Payments`, `Expenses`,
`Settings`) the first time it runs, and seeds `Settings` with sensible
default categories.

### Sheet schema reference

If you're curious what the app builds, or want to inspect/edit data
directly in Sheets:

**Projects**
| Column | Notes |
|---|---|
| project_id | auto-generated, e.g. `PRJ-A1B2C3D4` |
| client_name | |
| project_title | |
| service_category | from Settings |
| project_value | number |
| currency | from Settings |
| start_date | YYYY-MM-DD |
| due_date | YYYY-MM-DD |
| project_status | Not Started / In Progress / Completed / On Hold / Cancelled |
| payment_status | computed by the app — Unpaid / Partial / Paid |
| acquisition_source | from Settings |
| notes | |
| created_at | timestamp |

**Payments**
| Column | Notes |
|---|---|
| payment_id | auto-generated, e.g. `PAY-A1B2C3D4` |
| project_id | links to Projects |
| payment_date | YYYY-MM-DD |
| amount | number |
| payment_method | Bank Transfer / PayPal / Wise / Stripe / Crypto / Cash / Other |
| transaction_reference | free text |
| notes | |
| created_at | timestamp |

**Expenses**
| Column | Notes |
|---|---|
| expense_id | auto-generated, e.g. `EXP-A1B2C3D4` |
| expense_date | YYYY-MM-DD |
| category | from Settings |
| amount | number |
| currency | from Settings |
| description | |
| created_at | timestamp |

**Settings** (key-value list, editable from the app's Settings page)
| Column | Notes |
|---|---|
| setting_type | service_category / currency / expense_category / acquisition_source |
| value | the option text |

---

## 4. Configure secrets

1. Rename `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml`.
2. From the downloaded service account JSON, copy these fields into the
   matching keys in `secrets.toml`:
   - `project_id`, `private_key_id`, `private_key`, `client_email`,
     `client_id`, `client_x509_cert_url`
   - **Important:** the `private_key` must keep its `\n` characters
     exactly as they appear in the JSON — don't reformat it.
3. Set `app_config.sheet_url` to the full URL of the Sheet you created
   in step 3.
4. Set `app_config.app_password` to any password you'll use to log into
   the app (this is a simple shared-password gate, not full auth — see
   "Security note" below).

---

## 5. Run locally

```bash
cd founder-revenue-os
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

Open the URL Streamlit prints (usually `http://localhost:8501`), enter
your `app_password`, and you're in.

---

## 6. Deploy to Streamlit Community Cloud

1. Push this folder to a **GitHub repo** (public or private — Streamlit
   Cloud can access private repos too).

   ```bash
   git init
   git add .
   git commit -m "Initial commit — Founder Revenue OS"
   git branch -M main
   git remote add origin https://github.com/<you>/founder-revenue-os.git
   git push -u origin main
   ```

   **Do NOT commit `secrets.toml`** — it contains your private key.
   Add this to a `.gitignore`:
   ```
   .streamlit/secrets.toml
   venv/
   __pycache__/
   ```

2. Go to https://share.streamlit.io/ → **New app** → connect your GitHub
   repo → set the main file path to `app.py`.
3. Before deploying (or right after, via **Settings → Secrets**), paste
   the entire contents of your local `secrets.toml` into the app's
   **Secrets** box in the Streamlit Cloud dashboard.
4. Deploy. First load will take ~30-60 seconds while it installs
   dependencies and bootstraps your Sheet's worksheets.

---

## 7. Security note

The password gate in `app.py` is intentionally simple — it's meant to
keep this off Google's index and away from casual visitors, not to be
bank-grade auth. Since this is a single-user tool by design (per the
spec), that's an acceptable tradeoff. If you later add multi-user
support, replace `check_password()` with proper per-user auth (e.g.
Streamlit's built-in OIDC support, or Supabase Auth) — that's also the
natural point to move off Google Sheets and onto a real database, since
concurrent multi-user writes are where Sheets starts to strain.

---

## 8. Extending it later

The code is structured so each future enhancement has an obvious home:

- **Invoice/PDF generation** → new page, reuse `enrich_projects()` for
  the numbers, use a PDF library to render.
- **Tax estimation / forecasting** → new functions in `calculations.py`.
- **Client CRM** → new `Clients` worksheet + schema entry in `sheets.py`.
- **Multi-business support** → add a `business` column to each sheet
  and filter by it everywhere `read_sheet()` is called.
