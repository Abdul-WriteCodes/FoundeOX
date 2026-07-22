from datetime import date

import streamlit as st

from utils import calculations as calc
from utils import sheets
from utils.styling import inject_css, fmt_currency

st.set_page_config(page_title="Consulting Payments — Founder Revenue OS", page_icon="💳", layout="wide")
inject_css()

if not st.session_state.get("authenticated"):
    st.warning("Please log in from the main page first.")
    st.stop()

sheets.bootstrap_sheets()

st.title("💳 Consulting Payments")
st.caption("Payments received against Research & Consulting client projects.")

projects = sheets.read_sheet("Projects")
payments = sheets.read_sheet("Payments")
enriched = calc.enrich_projects(projects, payments)

payment_methods = ["Bank Transfer", "PayPal", "Wise", "Stripe", "Crypto", "Cash", "Other"]

tab_list, tab_new = st.tabs(["All Payments", "+ Record Payment"])

with tab_new:
    if enriched.empty:
        st.info("Create a project first (Consulting Projects page) before recording a payment.")
    else:
        with st.form("new_payment_form", clear_on_submit=True):
            label_map = {
                f"{r['project_title']} — {r['client_name']} "
                f"(owes {fmt_currency(r['outstanding_balance'])})": r["project_id"]
                for _, r in enriched.iterrows()
            }
            chosen_label = st.selectbox("Project *", list(label_map.keys()))
            payment_date = st.date_input("Payment Date", value=date.today())
            amount = st.number_input("Amount *", min_value=0.0, step=10.0)
            payment_method = st.selectbox("Payment Method", payment_methods)
            transaction_reference = st.text_input("Transaction Reference")
            notes = st.text_area("Notes")

            submitted = st.form_submit_button("Record Payment", type="primary")
            if submitted:
                if amount <= 0:
                    st.error("Amount must be greater than 0.")
                else:
                    project_id = label_map[chosen_label]
                    payid = sheets.create_payment({
                        "project_id": project_id,
                        "payment_date": str(payment_date),
                        "amount": amount,
                        "payment_method": payment_method,
                        "transaction_reference": transaction_reference,
                        "notes": notes,
                    })
                    st.toast(f"Payment {payid} recorded!", icon="✅")
                    st.rerun()

with tab_list:
    if payments.empty:
        st.info("No payments recorded yet.")
    else:
        merged = payments.merge(
            projects[["project_id", "project_title", "client_name"]],
            on="project_id", how="left",
        )
        search = st.text_input("🔎 Search by client or project")
        view = merged.copy()
        if search:
            mask = (
                view["client_name"].str.contains(search, case=False, na=False)
                | view["project_title"].str.contains(search, case=False, na=False)
            )
            view = view[mask]

        st.caption(f"Showing {len(view)} of {len(merged)} payments")
        st.dataframe(
            view[[
                "payment_date", "client_name", "project_title", "amount",
                "payment_method", "transaction_reference", "notes",
            ]].sort_values("payment_date", ascending=False),
            use_container_width=True, hide_index=True,
        )

        st.markdown("---")
        st.markdown("**Delete a payment**")
        del_options = {
            f"{r['payment_date']} — {r['client_name']} — {fmt_currency(r['amount'])} ({r['payment_id']})": r["payment_id"]
            for _, r in merged.iterrows()
        }
        chosen = st.selectbox("Select payment to delete", ["—"] + list(del_options.keys()))
        if chosen != "—" and st.button("🗑️ Delete Selected Payment"):
            sheets.delete_row("Payments", "payment_id", del_options[chosen])
            st.toast("Payment deleted", icon="🗑️")
            st.rerun()
