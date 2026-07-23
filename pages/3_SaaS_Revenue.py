from datetime import date

import plotly.express as px
import streamlit as st

from utils import calculations as calc
from utils import sheets
from utils.styling import inject_css, fmt_money

st.set_page_config(page_title="SaaS Revenue — Founder Revenue OS", page_icon="🚀", layout="wide")
inject_css()

if not st.session_state.get("authenticated"):
    st.warning("Please log in from the main page first.")
    st.stop()

sheets.bootstrap_sheets()

st.title("🚀 SaaS Revenue")
st.caption(
    "Track revenue for each product two ways: a quick monthly total, or "
    "individual transactions. If both are logged for the same product+month, "
    "the monthly total is treated as authoritative — so nothing double-counts."
)

settings = sheets.read_sheet("Settings")
products = settings.loc[settings["setting_type"] == "product", "value"].tolist() or ["Other"]
currencies = settings.loc[settings["setting_type"] == "currency", "value"].tolist() or ["USD"]
payment_methods = ["Stripe", "PayPal", "Paddle", "LemonSqueezy", "Bank Transfer", "Crypto", "Other"]

rates = calc.get_fx_rates(settings)
base_currency = calc.get_base_currency(settings)

tab_overview, tab_monthly, tab_txn = st.tabs(
    ["Overview", "Log Monthly Total", "Log Transaction"]
)

saas_monthly = sheets.read_sheet("SaaSMonthly")
saas_transactions = sheets.read_sheet("SaaSTransactions")

with tab_overview:
    missing = calc.missing_fx_currencies(saas_monthly, saas_transactions, rates=rates)
    if missing:
        st.warning(
            f"No exchange rate saved for: **{', '.join(missing)}**. These are being "
            f"treated as 1:1 with {base_currency} below — fix in Settings → Exchange Rates."
        )

    reconciled = calc.saas_reconciled_monthly(saas_monthly, saas_transactions, rates, base_currency)
    if reconciled.empty:
        st.info("No SaaS revenue logged yet — use the tabs above to add a monthly total or a transaction.")
    else:
        st.caption(f"All totals below are converted to your reporting currency, **{base_currency}**.")
        by_product = calc.saas_total_by_product(saas_monthly, saas_transactions, rates, base_currency)
        cols = st.columns(min(len(by_product), 4) or 1)
        for i, (_, r) in enumerate(by_product.iterrows()):
            with cols[i % len(cols)]:
                st.metric(r["product"], fmt_money(r["revenue"], base_currency))

        st.divider()
        left, right = st.columns(2)
        with left:
            st.subheader("Revenue by Product")
            fig = px.pie(by_product, names="product", values="revenue", hole=0.45)
            fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), height=340)
            st.plotly_chart(fig, use_container_width=True)
        with right:
            st.subheader("Monthly Trend by Product")
            fig = px.bar(reconciled, x="month", y="revenue", color="product",
                         labels={"month": "Month", "revenue": f"Revenue ({base_currency})"}, barmode="stack")
            fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), height=340)
            st.plotly_chart(fig, use_container_width=True)

        st.subheader("Product + Month Detail")
        display = reconciled.copy()
        display["revenue"] = display["revenue"].map(lambda v: fmt_money(v, base_currency))
        st.dataframe(display, use_container_width=True, hide_index=True)

with tab_monthly:
    st.markdown("Use this when you just want a quick running total for a product this month — no need to log every sale.")
    with st.form("monthly_total_form"):
        c1, c2 = st.columns(2)
        with c1:
            product = st.selectbox("Product *", products)
            month = st.text_input("Month (YYYY-MM) *", value=date.today().strftime("%Y-%m"))
        with c2:
            amount = st.number_input("Total Amount *", min_value=0.0, step=10.0)
            currency = st.selectbox("Currency", currencies)
        notes = st.text_area("Notes")

        submitted = st.form_submit_button("Save Monthly Total", type="primary")
        if submitted:
            if amount < 0:
                st.error("Amount can't be negative.")
            else:
                existing = saas_monthly[(saas_monthly["product"] == product) & (saas_monthly["month"] == month)]
                sheets.upsert_saas_monthly(product, month, amount, currency, notes)
                if not existing.empty:
                    st.toast(f"Updated {product} total for {month}", icon="✅")
                else:
                    st.toast(f"Saved {product} total for {month}", icon="✅")
                st.rerun()

    if not saas_monthly.empty:
        st.markdown("**Existing monthly totals** (each in its own recorded currency)")
        view = saas_monthly.copy().sort_values(["product", "month"], ascending=[True, False])
        view["amount_display"] = view.apply(lambda r: fmt_money(float(r["amount"]), r["currency"]), axis=1)
        st.dataframe(
            view[["product", "month", "amount_display", "notes"]].rename(columns={"amount_display": "amount"}),
            use_container_width=True, hide_index=True,
        )
        del_options = {
            f"{r['product']} — {r['month']} — {fmt_money(float(r['amount']), r['currency'])}": r["entry_id"]
            for _, r in saas_monthly.iterrows()
        }
        chosen = st.selectbox("Select monthly total to delete", ["—"] + list(del_options.keys()), key="del_monthly")
        if chosen != "—" and st.button("🗑️ Delete Selected Monthly Total"):
            sheets.delete_row("SaaSMonthly", "entry_id", del_options[chosen])
            st.toast("Monthly total deleted", icon="🗑️")
            st.rerun()

with tab_txn:
    st.markdown("Use this to log an individual sale or subscription payment.")
    with st.form("txn_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            product = st.selectbox("Product *", products, key="txn_product")
            txn_date = st.date_input("Date", value=date.today())
            amount = st.number_input("Amount *", min_value=0.0, step=5.0, key="txn_amount")
        with c2:
            currency = st.selectbox("Currency", currencies, key="txn_currency")
            customer = st.text_input("Customer / Payer (optional)")
            payment_method = st.selectbox("Payment Method", payment_methods)
        notes = st.text_area("Notes", key="txn_notes")

        submitted = st.form_submit_button("Log Transaction", type="primary")
        if submitted:
            if amount <= 0:
                st.error("Amount must be greater than 0.")
            else:
                tid = sheets.create_saas_transaction({
                    "product": product,
                    "date": str(txn_date),
                    "amount": amount,
                    "currency": currency,
                    "customer": customer,
                    "payment_method": payment_method,
                    "notes": notes,
                })
                st.toast(f"Transaction {tid} logged!", icon="✅")
                st.rerun()

    if not saas_transactions.empty:
        st.markdown("**Existing transactions** (each in its own recorded currency)")
        fcol1, fcol2 = st.columns(2)
        with fcol1:
            product_filter = st.multiselect("Filter by product", sorted(saas_transactions["product"].unique()))
        with fcol2:
            search = st.text_input("🔎 Search customer")

        view = saas_transactions.copy()
        if product_filter:
            view = view[view["product"].isin(product_filter)]
        if search:
            view = view[view["customer"].str.contains(search, case=False, na=False)]

        view["amount_display"] = view.apply(lambda r: fmt_money(float(r["amount"]), r["currency"]), axis=1)
        st.dataframe(
            view[["date", "product", "amount_display", "customer", "payment_method", "notes"]]
            .rename(columns={"amount_display": "amount"})
            .sort_values("date", ascending=False),
            use_container_width=True, hide_index=True,
        )

        del_options = {
            f"{r['date']} — {r['product']} — {fmt_money(float(r['amount']), r['currency'])} ({r['transaction_id']})": r["transaction_id"]
            for _, r in saas_transactions.iterrows()
        }
        chosen = st.selectbox("Select transaction to delete", ["—"] + list(del_options.keys()), key="del_txn")
        if chosen != "—" and st.button("🗑️ Delete Selected Transaction"):
            sheets.delete_row("SaaSTransactions", "transaction_id", del_options[chosen])
            st.toast("Transaction deleted", icon="🗑️")
            st.rerun()
