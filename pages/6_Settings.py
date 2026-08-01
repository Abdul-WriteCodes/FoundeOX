import streamlit as st

from utils import calculations as calc
from utils import sheets
from utils.styling import inject_css, graffiti_divider

inject_css()

if not st.session_state.get("authenticated"):
    st.warning("Please log in from the main page first.")
    st.stop()

sheets.bootstrap_sheets()

st.title("⚙️ Settings")
st.caption("These lists power the dropdowns across Consulting Projects, SaaS Revenue, and Expenses.")

settings = sheets.read_sheet("Settings")

setting_groups = [
    ("product", "SaaS Products"),
    ("service_category", "Consulting Service Categories"),
    ("currency", "Currencies"),
    ("expense_category", "Expense Categories"),
    ("acquisition_source", "Acquisition Sources"),
]

tab_labels = ["💱 Reporting Currency & FX Rates"] + [label for _, label in setting_groups]
tabs = st.tabs(tab_labels)

with tabs[0]:
    st.markdown(
        "**This is the fix for mixed-currency totals.** Every project, payment, "
        "expense, and SaaS entry is recorded in its own real currency — nothing "
        "changes there. But whenever the app needs to *combine* numbers across "
        "currencies (dashboard totals, monthly trends, per-client or per-stream "
        "totals), it converts everything to the single **reporting currency** "
        "below first, using the rates you set here. Without a correct rate, "
        "NGN 10,000 would get added as if it were $10,000 — which is the bug "
        "this page exists to prevent."
    )

    base_currency = calc.get_base_currency(settings)
    currency_options = settings.loc[settings["setting_type"] == "currency", "value"].tolist() or ["USD"]
    if base_currency not in currency_options:
        currency_options = [base_currency] + currency_options

    st.subheader("Reporting Currency")
    new_base = st.selectbox(
        "All combined totals across the app are shown in this currency",
        currency_options,
        index=currency_options.index(base_currency),
    )
    if new_base != base_currency and st.button("Save Reporting Currency", type="primary"):
        sheets.set_base_currency(new_base)
        st.toast(f"Reporting currency set to {new_base}", icon="✅")
        st.rerun()

    graffiti_divider()
    st.subheader("Exchange Rates")
    st.caption(
        f"For each currency you use, enter how many units of {base_currency} "
        f"one unit of that currency is worth right now (e.g. if 1 GBP = 1.27 USD "
        f"and your reporting currency is USD, enter 1.27 for GBP). "
        f"This app has no live FX feed — update these periodically yourself."
    )

    rates = calc.get_fx_rates(settings)
    for cur in currency_options:
        if cur == base_currency:
            st.text(f"{cur}: 1.00 (this is your reporting currency)")
            continue
        rcol1, rcol2 = st.columns([3, 1])
        with rcol1:
            current_rate = rates.get(cur, None)
            new_rate = st.number_input(
                f"1 {cur} = ? {base_currency}",
                min_value=0.0, step=0.0001, format="%.6f",
                value=float(current_rate) if current_rate is not None else 0.0,
                key=f"rate_{cur}",
            )
        with rcol2:
            st.write("")
            st.write("")
            if st.button("Save", key=f"save_rate_{cur}"):
                if new_rate <= 0:
                    st.error("Rate must be greater than 0.")
                else:
                    sheets.upsert_exchange_rate(cur, new_rate)
                    st.toast(f"Saved rate for {cur}", icon="✅")
                    st.rerun()
        if cur not in rates:
            st.warning(f"⚠️ No rate saved yet for {cur} — amounts in {cur} are currently NOT converted correctly.")

for tab, (setting_type, label) in zip(tabs[1:], setting_groups):
    with tab:
        if setting_type == "product":
            st.caption("Every product here becomes its own revenue stream, tracked on the SaaS Revenue page.")
        if setting_type == "currency":
            st.caption("Adding a currency here also makes it available to pick in Projects/Payments/Expenses/SaaS forms — remember to set its exchange rate in the tab above.")
        values = settings.loc[settings["setting_type"] == setting_type, "value"].tolist()

        col1, col2 = st.columns([2, 1])
        with col1:
            if values:
                for v in values:
                    vcol1, vcol2 = st.columns([4, 1])
                    vcol1.write(v)
                    if vcol2.button("Remove", key=f"rm_{setting_type}_{v}"):
                        sheets.delete_setting(setting_type, v)
                        st.rerun()
            else:
                st.caption(f"No {label.lower()} yet.")
        with col2:
            new_val = st.text_input(f"Add new {label[:-1].lower()}", key=f"new_{setting_type}")
            if st.button("Add", key=f"add_{setting_type}"):
                if new_val and new_val not in values:
                    sheets.add_setting(setting_type, new_val)
                    st.toast(f"Added '{new_val}' to {label}", icon="✅")
                    st.rerun()
                elif new_val in values:
                    st.warning("That value already exists.")

graffiti_divider()
st.subheader("About")
st.markdown(
    "**VaultX** — your personal business operating system, tracking "
    "Research & Consulting alongside every SaaS product you're shipping. "
    "Built with Streamlit + Google Sheets. Data lives entirely in your connected "
    "Google Sheet — nothing is stored elsewhere."
)
