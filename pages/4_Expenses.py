from datetime import date

import streamlit as st

from utils import calculations as calc
from utils import sheets
from utils.sheets import CONSULTING_STREAM, GENERAL_STREAM
from utils.styling import inject_css, fmt_money, confirm_delete

inject_css()

if not st.session_state.get("authenticated"):
    st.warning("Please log in from the main page first.")
    st.stop()

sheets.bootstrap_sheets()

st.title("🧾 Expenses")

settings = sheets.read_sheet("Settings")
expense_categories = settings.loc[settings["setting_type"] == "expense_category", "value"].tolist() or ["Miscellaneous"]
currencies = settings.loc[settings["setting_type"] == "currency", "value"].tolist() or ["USD"]
products = settings.loc[settings["setting_type"] == "product", "value"].tolist()
stream_options = [GENERAL_STREAM, CONSULTING_STREAM] + products

rates = calc.get_fx_rates(settings)
base_currency = calc.get_base_currency(settings)

tab_list, tab_new = st.tabs(["All Expenses", "+ New Expense"])

with tab_new:
    with st.form("new_expense_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            expense_date = st.date_input("Expense Date", value=date.today())
            category = st.selectbox("Category", expense_categories)
            stream = st.selectbox(
                "Attribute to stream (optional)", stream_options,
                help="Tag this expense to Research & Consulting or a specific product to see per-stream profit. Leave as General/Overhead if it's a shared business cost.",
            )
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
                    "stream": stream,
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
        missing = calc.missing_fx_currencies(expenses, rates=rates)
        if missing:
            st.warning(
                f"No exchange rate saved for: **{', '.join(missing)}**. The total below "
                f"treats these as 1:1 with {base_currency} — fix in Settings → Exchange Rates."
            )

        fcol1, fcol2, fcol3 = st.columns(3)
        with fcol1:
            cat_filter = st.multiselect("Filter by category", sorted(expenses["category"].unique()))
        with fcol2:
            stream_filter = st.multiselect("Filter by stream", sorted(expenses["stream"].replace("", GENERAL_STREAM).unique()))
        with fcol3:
            search = st.text_input("🔎 Search description")

        view = expenses.copy()
        view["stream"] = view["stream"].replace("", GENERAL_STREAM)
        if cat_filter:
            view = view[view["category"].isin(cat_filter)]
        if stream_filter:
            view = view[view["stream"].isin(stream_filter)]
        if search:
            view = view[view["description"].str.contains(search, case=False, na=False)]

        # this view can span multiple currencies, so the total is
        # converted to base currency rather than summed raw
        total_base = calc.convert_to_base(view["amount"].astype(float), view["currency"], rates, base_currency).sum() if not view.empty else 0.0
        st.caption(f"Showing {len(view)} of {len(expenses)} expenses — total {fmt_money(total_base, base_currency)}")

        view["amount_display"] = view.apply(lambda r: fmt_money(float(r["amount"]), r["currency"]), axis=1)
        st.dataframe(
            view[["expense_date", "category", "stream", "amount_display", "description"]]
            .rename(columns={"amount_display": "amount"})
            .sort_values("expense_date", ascending=False),
            use_container_width=True, hide_index=True,
        )

        st.markdown("---")
        st.markdown("**Edit an expense**")
        edit_options = {
            f"{r['expense_date']} — {r['category']} — {fmt_money(float(r['amount']), r['currency'])} ({r['expense_id']})": r["expense_id"]
            for _, r in expenses.iterrows()
        }
        chosen_edit = st.selectbox("Select expense to edit", ["—"] + list(edit_options.keys()), key="edit_expense")
        if chosen_edit != "—":
            x_row = expenses[expenses["expense_id"] == edit_options[chosen_edit]].iloc[0]
            with st.form(f"edit_expense_{x_row['expense_id']}"):
                ec1, ec2 = st.columns(2)
                with ec1:
                    e_date = st.date_input("Expense Date", value=calc.parse_date(x_row["expense_date"]))
                    e_category = st.selectbox(
                        "Category", expense_categories, index=calc.safe_index(expense_categories, x_row["category"])
                    )
                    e_stream = st.selectbox(
                        "Attribute to stream (optional)", stream_options,
                        index=calc.safe_index(stream_options, x_row["stream"] or GENERAL_STREAM),
                    )
                with ec2:
                    e_amount = st.number_input("Amount *", min_value=0.0, step=5.0, value=float(x_row["amount"]))
                    e_currency = st.selectbox("Currency", currencies, index=calc.safe_index(currencies, x_row["currency"]))
                e_description = st.text_area("Description", value=x_row["description"])

                if st.form_submit_button("Save Changes", type="primary"):
                    if e_amount <= 0:
                        st.error("Amount must be greater than 0.")
                    else:
                        sheets.update_row(
                            "Expenses", "expense_id", x_row["expense_id"],
                            {"expense_date": str(e_date), "category": e_category, "stream": e_stream,
                             "amount": e_amount, "currency": e_currency, "description": e_description},
                        )
                        st.toast("Expense updated", icon="✅")
                        st.rerun()

        st.markdown("---")
        st.markdown("**Delete an expense**")
        del_options = {
            f"{r['expense_date']} — {r['category']} — {fmt_money(float(r['amount']), r['currency'])} ({r['expense_id']})": r["expense_id"]
            for _, r in expenses.iterrows()
        }
        chosen = st.selectbox("Select expense to delete", ["—"] + list(del_options.keys()))
        if chosen != "—":
            eid = del_options[chosen]
            if confirm_delete(f"confirm_del_expense_{eid}", f"Delete this expense ({chosen})? This can't be undone.", button_label="🗑️ Delete Selected Expense"):
                sheets.delete_row("Expenses", "expense_id", eid)
                st.toast("Expense deleted", icon="🗑️")
                st.rerun()
