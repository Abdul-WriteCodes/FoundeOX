from datetime import date

import streamlit as st

from utils import sheets
from utils.styling import inject_css, fmt_currency

st.set_page_config(page_title="Expenses — Founder Revenue OS", page_icon="🧾", layout="wide")
inject_css()

if not st.session_state.get("authenticated"):
    st.warning("Please log in from the main page first.")
    st.stop()

sheets.bootstrap_sheets()

st.title("🧾 Expenses")

settings = sheets.read_sheet("Settings")
expense_categories = settings.loc[settings["setting_type"] == "expense_category", "value"].tolist() or ["Miscellaneous"]
currencies = settings.loc[settings["setting_type"] == "currency", "value"].tolist() or ["USD"]

tab_list, tab_new = st.tabs(["All Expenses", "+ New Expense"])

with tab_new:
    with st.form("new_expense_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            expense_date = st.date_input("Expense Date", value=date.today())
            category = st.selectbox("Category", expense_categories)
        with c2:
            amount = st.number_input("Amount *", min_value=0.0, step=5.0)
            currency = st.selectbox("Currency", currencies)
        description = st.text_area("Description")

        submitted = st.form_submit_button("Add Expense", type="primary")
        if submitted:
            if amount <= 0:
                st.error("Amount must be greater than 0.")
            else:
                eid = sheets.create_expense({
                    "expense_date": str(expense_date),
                    "category": category,
                    "amount": amount,
                    "currency": currency,
                    "description": description,
                })
                st.toast(f"Expense {eid} added!", icon="✅")
                st.rerun()

with tab_list:
    expenses = sheets.read_sheet("Expenses")
    if expenses.empty:
        st.info("No expenses recorded yet.")
    else:
        fcol1, fcol2 = st.columns(2)
        with fcol1:
            cat_filter = st.multiselect("Filter by category", sorted(expenses["category"].unique()))
        with fcol2:
            search = st.text_input("🔎 Search description")

        view = expenses.copy()
        if cat_filter:
            view = view[view["category"].isin(cat_filter)]
        if search:
            view = view[view["description"].str.contains(search, case=False, na=False)]

        total = view["amount"].astype(float).sum() if not view.empty else 0.0
        st.caption(f"Showing {len(view)} of {len(expenses)} expenses — total {fmt_currency(total)}")

        st.dataframe(
            view[["expense_date", "category", "amount", "currency", "description"]]
            .sort_values("expense_date", ascending=False),
            use_container_width=True, hide_index=True,
        )

        st.markdown("---")
        st.markdown("**Delete an expense**")
        del_options = {
            f"{r['expense_date']} — {r['category']} — {fmt_currency(float(r['amount']))} ({r['expense_id']})": r["expense_id"]
            for _, r in expenses.iterrows()
        }
        chosen = st.selectbox("Select expense to delete", ["—"] + list(del_options.keys()))
        if chosen != "—" and st.button("🗑️ Delete Selected Expense"):
            sheets.delete_row("Expenses", "expense_id", del_options[chosen])
            st.toast("Expense deleted", icon="🗑️")
            st.rerun()
