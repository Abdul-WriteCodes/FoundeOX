from datetime import date

import streamlit as st

from utils import calculations as calc
from utils import sheets
from utils.styling import inject_css, fmt_money, confirm_delete

st.set_page_config(page_title="Consulting Payments — Founder Revenue OS", page_icon="💳", layout="wide")
inject_css()

if not st.session_state.get("authenticated"):
    st.warning("Please log in from the main page first.")
    st.stop()

sheets.bootstrap_sheets()

st.title("💳 Consulting Payments")
st.caption(
    "Payments received against Research & Consulting client projects. "
    "Every amount here is shown in that project's own currency — a payment "
    "against a project priced in NGN is recorded and shown in NGN, not converted."
)

projects = sheets.read_sheet("Projects")
payments = sheets.read_sheet("Payments")
settings = sheets.read_sheet("Settings")
rates = calc.get_fx_rates(settings)
base_currency = calc.get_base_currency(settings)
enriched = calc.enrich_projects(projects, payments, rates, base_currency)

payment_methods = ["Bank Transfer", "PayPal", "Wise", "Stripe", "Crypto", "Cash", "Other"]

tab_list, tab_new = st.tabs(["All Payments", "+ Record Payment"])

with tab_new:
    if enriched.empty:
        st.info("Create a project first (Consulting Projects page) before recording a payment.")
    else:
        with st.form("new_payment_form", clear_on_submit=True):
            label_map = {
                f"{r['project_title']} — {r['client_name']} "
                f"(owes {fmt_money(r['outstanding_balance'], r['currency'])})": r["project_id"]
                for _, r in enriched.iterrows()
            }
            chosen_label = st.selectbox("Project *", list(label_map.keys()))
            payment_date = st.date_input("Payment Date", value=date.today())
            amount = st.number_input("Amount * (in the project's own currency)", min_value=0.0, step=10.0)
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
            projects[["project_id", "project_title", "client_name", "currency"]],
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

        view["amount_display"] = view.apply(lambda r: fmt_money(r["amount"], r["currency"]), axis=1)

        st.caption(f"Showing {len(view)} of {len(merged)} payments")
        st.dataframe(
            view[[
                "payment_date", "client_name", "project_title", "amount_display",
                "payment_method", "transaction_reference", "notes",
            ]].rename(columns={"amount_display": "amount"}).sort_values("payment_date", ascending=False),
            use_container_width=True, hide_index=True,
        )

        st.markdown("---")
        st.markdown("**Edit a payment**")
        edit_options = {
            f"{r['payment_date']} — {r['client_name']} — {fmt_money(r['amount'], r['currency'])} ({r['payment_id']})": r["payment_id"]
            for _, r in merged.iterrows()
        }
        chosen_edit = st.selectbox("Select payment to edit", ["—"] + list(edit_options.keys()), key="edit_payment_select")
        if chosen_edit != "—":
            pay_row = merged[merged["payment_id"] == edit_options[chosen_edit]].iloc[0]
            with st.form(f"edit_payment_{pay_row['payment_id']}"):
                proj_label_map = {
                    f"{r['project_title']} — {r['client_name']}": r["project_id"]
                    for _, r in projects.iterrows()
                }
                proj_labels = list(proj_label_map.keys())
                current_proj_label = next(
                    (lbl for lbl, pid in proj_label_map.items() if pid == pay_row["project_id"]), None
                )
                ec1, ec2 = st.columns(2)
                with ec1:
                    new_proj_label = st.selectbox(
                        "Project *", proj_labels,
                        index=calc.safe_index(proj_labels, current_proj_label),
                    )
                    new_payment_date = st.date_input("Payment Date", value=calc.parse_date(pay_row["payment_date"]))
                    new_amount = st.number_input(
                        "Amount * (in the project's own currency)", min_value=0.0, step=10.0,
                        value=float(pay_row["amount"]),
                    )
                with ec2:
                    new_payment_method = st.selectbox(
                        "Payment Method", payment_methods,
                        index=calc.safe_index(payment_methods, pay_row["payment_method"]),
                    )
                    new_transaction_reference = st.text_input("Transaction Reference", value=pay_row["transaction_reference"])
                new_notes = st.text_area("Notes", value=pay_row["notes"])

                if st.form_submit_button("Save Changes", type="primary"):
                    if new_amount <= 0:
                        st.error("Amount must be greater than 0.")
                    else:
                        sheets.update_row(
                            "Payments", "payment_id", pay_row["payment_id"],
                            {
                                "project_id": proj_label_map[new_proj_label],
                                "payment_date": str(new_payment_date),
                                "amount": new_amount,
                                "payment_method": new_payment_method,
                                "transaction_reference": new_transaction_reference,
                                "notes": new_notes,
                            },
                        )
                        st.toast("Payment updated", icon="✅")
                        st.rerun()

        st.markdown("---")
        st.markdown("**Delete a payment**")
        del_options = {
            f"{r['payment_date']} — {r['client_name']} — {fmt_money(r['amount'], r['currency'])} ({r['payment_id']})": r["payment_id"]
            for _, r in merged.iterrows()
        }
        chosen = st.selectbox("Select payment to delete", ["—"] + list(del_options.keys()))
        if chosen != "—":
            pid = del_options[chosen]
            if confirm_delete(f"confirm_del_payment_{pid}", f"Delete this payment ({chosen})? This can't be undone.", button_label="🗑️ Delete Selected Payment"):
                sheets.delete_row("Payments", "payment_id", pid)
                st.toast("Payment deleted", icon="🗑️")
                st.rerun()
