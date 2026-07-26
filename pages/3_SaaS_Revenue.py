from datetime import date

import pandas as pd
import streamlit as st
from streamlit_echarts import st_echarts

from utils import calculations as calc
from utils import charts
from utils import sheets
from utils.styling import inject_css, fmt_money, graffiti_divider, confirm_delete

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

    shadowed = calc.shadowed_saas_periods(saas_monthly, saas_transactions, rates, base_currency)
    if not shadowed.empty:
        with st.expander(
            f"⚠️ {len(shadowed)} product+month(s) have both a manual total AND individual "
            f"transactions — the manual total is what's shown below, transactions are ignored",
            expanded=False,
        ):
            st.caption(
                "This is why editing or deleting a transaction in one of these periods doesn't "
                "change the numbers on this page: the manual total overrides it completely. "
                "If you want transactions to be the source of truth again, delete the manual "
                "total for that product+month in the **Log Monthly Total** tab."
            )
            shadow_display = shadowed.copy()
            shadow_display["manual_total"] = shadow_display["manual_total"].map(lambda v: fmt_money(v, base_currency))
            shadow_display["transaction_sum"] = shadow_display["transaction_sum"].map(lambda v: fmt_money(v, base_currency))
            st.dataframe(
                shadow_display.rename(columns={
                    "manual_total": f"Manual total (shown)", "transaction_sum": "Transaction sum (ignored)",
                }),
                use_container_width=True, hide_index=True,
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

        graffiti_divider()
        left, right = st.columns(2)
        with left:
            st.subheader("Revenue by Product")
            opts = charts.donut_chart(by_product["product"].tolist(), by_product["revenue"].round(2).tolist(), unit_label=base_currency)
            st_echarts(options=opts, height="340px")
        with right:
            st.subheader("Monthly Trend by Product")
            pivot = reconciled.pivot_table(index="month", columns="product", values="revenue", aggfunc="sum").fillna(0).sort_index()
            series_data = {product: pivot[product].round(2).tolist() for product in pivot.columns}
            opts = charts.stacked_bar_chart(pivot.index.tolist(), series_data, axis_name=base_currency, height="340px")
            st_echarts(options=opts, height="340px")

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
            month_clean = month.strip()
            if amount < 0:
                st.error("Amount can't be negative.")
            elif not month_clean:
                st.error("Month is required.")
            else:
                existing = saas_monthly[(saas_monthly["product"] == product) & (saas_monthly["month"] == month_clean)]
                sheets.upsert_saas_monthly(product, month_clean, amount, currency, notes)
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
        st.markdown("**Edit a monthly total**")
        edit_options = {
            f"{r['product']} — {r['month']} — {fmt_money(float(r['amount']), r['currency'])}": r["entry_id"]
            for _, r in saas_monthly.iterrows()
        }
        chosen_edit = st.selectbox("Select monthly total to edit", ["—"] + list(edit_options.keys()), key="edit_monthly")
        if chosen_edit != "—":
            m_row = saas_monthly[saas_monthly["entry_id"] == edit_options[chosen_edit]].iloc[0]
            with st.form(f"edit_monthly_{m_row['entry_id']}"):
                ec1, ec2 = st.columns(2)
                with ec1:
                    e_product = st.selectbox("Product *", products, index=calc.safe_index(products, m_row["product"]))
                    e_month = st.text_input("Month (YYYY-MM) *", value=m_row["month"])
                with ec2:
                    e_amount = st.number_input("Total Amount *", min_value=0.0, step=10.0, value=float(m_row["amount"]))
                    e_currency = st.selectbox("Currency", currencies, index=calc.safe_index(currencies, m_row["currency"]))
                e_notes = st.text_area("Notes", value=m_row["notes"])

                if st.form_submit_button("Save Changes", type="primary"):
                    e_month_clean = e_month.strip()
                    if e_amount < 0:
                        st.error("Amount can't be negative.")
                    elif not e_month_clean:
                        st.error("Month is required.")
                    else:
                        sheets.update_row(
                            "SaaSMonthly", "entry_id", m_row["entry_id"],
                            {"product": e_product, "month": e_month_clean, "amount": e_amount,
                             "currency": e_currency, "notes": e_notes},
                        )
                        st.toast("Monthly total updated", icon="✅")
                        st.rerun()

        st.markdown("---")
        st.markdown("**Delete a monthly total**")
        del_options = {
            f"{r['product']} — {r['month']} — {fmt_money(float(r['amount']), r['currency'])}": r["entry_id"]
            for _, r in saas_monthly.iterrows()
        }
        chosen = st.selectbox("Select monthly total to delete", ["—"] + list(del_options.keys()), key="del_monthly")
        if chosen != "—":
            eid = del_options[chosen]
            if confirm_delete(f"confirm_del_monthly_{eid}", f"Delete this monthly total ({chosen})? This can't be undone.", button_label="🗑️ Delete Selected Monthly Total"):
                sheets.delete_row("SaaSMonthly", "entry_id", eid)
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

        st.markdown("**Edit a transaction**")
        edit_options = {
            f"{r['date']} — {r['product']} — {fmt_money(float(r['amount']), r['currency'])} ({r['transaction_id']})": r["transaction_id"]
            for _, r in saas_transactions.iterrows()
        }
        chosen_edit = st.selectbox("Select transaction to edit", ["—"] + list(edit_options.keys()), key="edit_txn")
        if chosen_edit != "—":
            t_row = saas_transactions[saas_transactions["transaction_id"] == edit_options[chosen_edit]].iloc[0]
            with st.form(f"edit_txn_{t_row['transaction_id']}"):
                ec1, ec2 = st.columns(2)
                with ec1:
                    e_product = st.selectbox("Product *", products, index=calc.safe_index(products, t_row["product"]))
                    e_date = st.date_input("Date", value=calc.parse_date(t_row["date"]))
                    e_amount = st.number_input("Amount *", min_value=0.0, step=5.0, value=float(t_row["amount"]))
                with ec2:
                    e_currency = st.selectbox("Currency", currencies, index=calc.safe_index(currencies, t_row["currency"]))
                    e_customer = st.text_input("Customer / Payer (optional)", value=t_row["customer"])
                    e_payment_method = st.selectbox(
                        "Payment Method", payment_methods, index=calc.safe_index(payment_methods, t_row["payment_method"])
                    )
                e_notes = st.text_area("Notes", value=t_row["notes"])

                if st.form_submit_button("Save Changes", type="primary"):
                    if e_amount <= 0:
                        st.error("Amount must be greater than 0.")
                    else:
                        sheets.update_row(
                            "SaaSTransactions", "transaction_id", t_row["transaction_id"],
                            {"product": e_product, "date": str(e_date), "amount": e_amount,
                             "currency": e_currency, "customer": e_customer,
                             "payment_method": e_payment_method, "notes": e_notes},
                        )
                        st.toast("Transaction updated", icon="✅")
                        st.rerun()

        st.markdown("---")
        st.markdown("**Delete a transaction**")
        del_options = {
            f"{r['date']} — {r['product']} — {fmt_money(float(r['amount']), r['currency'])} ({r['transaction_id']})": r["transaction_id"]
            for _, r in saas_transactions.iterrows()
        }
        chosen = st.selectbox("Select transaction to delete", ["—"] + list(del_options.keys()), key="del_txn")
        if chosen != "—":
            tid = del_options[chosen]
            sel_row = saas_transactions[saas_transactions["transaction_id"] == tid].iloc[0]
            sel_month = pd.to_datetime(sel_row["date"], errors="coerce")
            sel_month = sel_month.strftime("%Y-%m") if pd.notna(sel_month) else None
            has_manual_override = sel_month is not None and not saas_monthly[
                (saas_monthly["product"] == sel_row["product"]) & (saas_monthly["month"] == sel_month)
            ].empty
            if has_manual_override:
                st.info(
                    f"Heads up: **{sel_row['product']}** has a manual monthly total saved for "
                    f"**{sel_month}**, which overrides the transaction sum in Overview. Deleting "
                    f"this transaction won't change any totals unless you also update or delete "
                    f"that monthly total in the **Log Monthly Total** tab."
                )
            if confirm_delete(f"confirm_del_txn_{tid}", f"Delete this transaction ({chosen})? This can't be undone.", button_label="🗑️ Delete Selected Transaction"):
                sheets.delete_row("SaaSTransactions", "transaction_id", tid)
                st.toast("Transaction deleted", icon="🗑️")
                st.rerun()
