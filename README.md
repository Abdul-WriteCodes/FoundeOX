# Founder Metrics Dashboard

A single-file Streamlit app that turns a Google Sheet into a personal
business-intelligence dashboard across all your ventures.

---

## 1. What you get

```
founder-metrics-dashboard/
├── app.py                          # the whole app (single file, as spec'd)
├── setup_sheets.py                 # one-time script to build the Sheet structure
├── requirements.txt
├── .streamlit/
│   ├── config.toml                 # theme
│   └── secrets.toml.example        # copy -> secrets.toml, fill in your keys
└── README.md
```

---

## 2. Google Cloud setup (you said you already have a console account — good, start here)

### Step 1 — Create / select a project
In the [Google Cloud Console](https://console.cloud.google.com/), create a new
project (or reuse an existing one) — e.g. `founder-metrics-dashboard`.

### Step 2 — Enable two APIs
In **APIs & Services → Library**, enable:
- **Google Sheets API**
- **Google Drive API**

### Step 3 — Create a Service Account
1. **APIs & Services → Credentials → Create Credentials → Service Account**
2. Give it any name, e.g. `founder-metrics-bot`. No special roles needed.
3. Open the service account you just created → **Keys → Add Key → Create new key → JSON**.
4. This downloads a `.json` file — this is your only credential file. Keep it private.

### Step 4 — Share your Google Sheet with the service account
1. Create a new Google Sheet (any name — e.g. "Founder Metrics").
2. Open the downloaded JSON file, copy the `client_email` value
   (looks like `founder-metrics-bot@your-project.iam.gserviceaccount.com`).
3. In the Google Sheet, click **Share** and paste that email in as an **Editor**.

Without this share step, the app will authenticate fine but get a
"permission denied" error reading the sheet.

---

## 3. Build the sheet structure automatically

Instead of manually creating tabs and headers, run the included script once:

```bash
pip install gspread google-auth
python setup_sheets.py --key path/to/your-service-account.json --sheet-url "https://docs.google.com/spreadsheets/d/YOUR_ID/edit"
```

This creates all 7 tabs with the correct headers:

| Tab | Columns |
|---|---|
| Overview | Business, Metric 1, Metric 2 |
| BizTrack-OS | Month, Users, Revenue |
| StaX360 | Month, Users, Revenue |
| Research & Consulting | Month, Projects, Revenue |
| Crea8it Studio | Month, Members, Onboarded |
| Goals | Business, Metric, Current, Target |
| Milestones | Date, Business, Milestone |

It's safe to re-run — it won't overwrite existing data, only adds
missing tabs/headers.

**Data entry tips:**
- `Month` values should be consistent, e.g. `2026-01`, `2026-02` (sorts correctly).
- `Date` in Milestones can be any parseable date, e.g. `2026-03-14`.
- Numbers should be plain (no currency symbols, no commas) — the app formats
  currency for you based on the Settings page.

---

## 4. Configure secrets (local development)

```bash
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
```

Open `.streamlit/secrets.toml` and fill in:
- `general.sheet_url` — the full URL of your Google Sheet
- `gcp_service_account.*` — copy every field straight out of your downloaded JSON key
  (the `private_key` field keeps its `\n` characters as literal `\n` — don't
  reformat it)

**Never commit `secrets.toml` to git.** Add this to `.gitignore`:
```
.streamlit/secrets.toml
```

---

## 5. Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

Open the local URL Streamlit prints (usually `http://localhost:8501`).

---

## 6. Deploy to Streamlit Cloud

1. Push this folder to a GitHub repo (make sure `secrets.toml` is **not** included — only `secrets.toml.example`).
2. Go to [share.streamlit.io](https://share.streamlit.io/) → **New app** → pick your repo/branch → main file path `app.py`.
3. Before/after first deploy, go to **App → Settings → Secrets** and paste in the
   full contents of your local `secrets.toml` (same TOML format).
4. Deploy. Every time you edit rows in the Google Sheet, the app picks up
   changes within 5 minutes automatically (cache TTL), or instantly via the
   **Refresh Data** button in the sidebar / Settings page.

---

## 7. How the app is organized

- **Main Dashboard** — ecosystem-wide KPIs, revenue trend, business comparison, recent milestones, goal progress.
- **Per-business pages** (BizTrack-OS, StaX360, Research & Consulting, Crea8it Studio) — KPI cards, monthly trend charts, historical data table.
- **Revenue Dashboard** — lifetime/monthly revenue, revenue by business, growth, best month, line/bar/pie charts.
- **Analytics Dashboard** — highest revenue business, fastest growing business, revenue contribution, user growth, comparison table.
- **Goals Dashboard** — progress bars per goal (Current vs Target).
- **Milestones** — filterable timeline.
- **Monthly Report** — pick a month, get an auto-generated summary + downloadable Markdown report.
- **Settings** — currency, logo upload (session-only), connected sheet URL (read-only), refresh/cache clear.

All data comes from the Google Sheet — no code changes are needed to update
any chart; just edit rows in the Sheet.

---

## 8. Extending toward the multi-user vision

When you're ready to evolve this into a multi-user product (per the spec's
long-term vision), the natural next steps are:
- Replace the single `secrets.toml` sheet URL with a per-user sheet URL stored
  in a lightweight user database (e.g. Supabase, which you're already using
  on other projects).
- Add simple auth (Streamlit's `st.login` / an external auth provider) so each
  user only sees their own connected sheet.
- Turn `setup_sheets.py`'s logic into an in-app "Connect your Google Sheet"
  onboarding flow that provisions the tabs for a newly connected sheet.

None of the current `app.py` logic needs to change for this — it already
reads the sheet URL from a single config source, which just needs to become
per-user instead of global.
