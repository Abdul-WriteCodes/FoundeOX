import streamlit as st

from utils import sheets
from utils.styling import inject_css

st.set_page_config(page_title="Settings — Founder Revenue OS", page_icon="⚙️", layout="wide")
inject_css()

if not st.session_state.get("authenticated"):
    st.warning("Please log in from the main page first.")
    st.stop()

sheets.bootstrap_sheets()

st.title("⚙️ Settings")
st.caption("These lists power the dropdowns across Projects, Payments, and Expenses.")

setting_groups = [
    ("service_category", "Service Categories"),
    ("currency", "Currencies"),
    ("expense_category", "Expense Categories"),
    ("acquisition_source", "Acquisition Sources"),
]

settings = sheets.read_sheet("Settings")

tabs = st.tabs([label for _, label in setting_groups])

for tab, (setting_type, label) in zip(tabs, setting_groups):
    with tab:
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
            if st.button(f"Add", key=f"add_{setting_type}"):
                if new_val and new_val not in values:
                    sheets.add_setting(setting_type, new_val)
                    st.toast(f"Added '{new_val}' to {label}", icon="✅")
                    st.rerun()
                elif new_val in values:
                    st.warning("That value already exists.")

st.divider()
st.subheader("About")
st.markdown(
    "**Founder Revenue OS** — your personal business operating system. "
    "Built with Streamlit + Google Sheets. "
    "Data lives entirely in your connected Google Sheet — nothing is stored elsewhere."
)
