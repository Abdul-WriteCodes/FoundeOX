from datetime import date

import streamlit as st

from utils import calculations as calc
from utils import sheets
from utils.styling import inject_css, status_pill, fmt_money, confirm_delete

st.set_page_config(page_title="Consulting Projects — Founder Revenue OS", page_icon="📁", layout="wide")
inject_css()

if not st.session_state.get("authenticated"):
    st.warning("Please log in from the main page first.")
    st.stop()

sheets.bootstrap_sheets()

settings = sheets.read_sheet("Settings")


def options_for(setting_type, fallback):
    vals = settings.loc[settings["setting_type"] == setting_type, "value"].tolist()
    return vals if vals else fallback


service_categories = options_for("service_category", ["Consulting", "Other"])
currencies = options_for("currency", ["USD"])
acquisition_sources = options_for("acquisition_source", ["Referral", "Other"])
project_statuses = ["Not Started", "In Progress", "Completed", "On Hold", "Cancelled"]

st.title("📁 Consulting Projects")
st.caption("Research & Consulting engagements — from client acquisition to final payment.")

tab_list, tab_new = st.tabs(["All Projects", "+ New Project"])

with tab_new:
    with st.form("new_project_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            client_name = st.text_input("Client Name *")
            project_title = st.text_input("Project Title *")
            service_category = st.selectbox("Service Category", service_categories)
            project_value = st.number_input("Project Value *", min_value=0.0, step=50.0)
            currency = st.selectbox("Currency", currencies)
        with c2:
            start_date = st.date_input("Start Date", value=date.today())
            due_date = st.date_input("Due Date", value=date.today())
            project_status = st.selectbox("Project Status", project_statuses)
            acquisition_source = st.selectbox("Acquisition Source", acquisition_sources)
        notes = st.text_area("Notes")

        submitted = st.form_submit_button("Create Project", type="primary")
        if submitted:
            if not client_name or not project_title or project_value <= 0:
                st.error("Client Name, Project Title, and a Project Value greater than 0 are required.")
            else:
                pid = sheets.create_project({
                    "client_name": client_name,
                    "project_title": project_title,
                    "service_category": service_category,
                    "project_value": project_value,
                    "currency": currency,
                    "start_date": str(start_date),
                    "due_date": str(due_date),
                    "project_status": project_status,
                    "payment_status": "Unpaid",
                    "acquisition_source": acquisition_source,
                    "notes": notes,
                })
                st.toast(f"Project {pid} created!", icon="✅")
                st.rerun()

with tab_list:
    projects = sheets.read_sheet("Projects")
    payments = sheets.read_sheet("Payments")
    rates = calc.get_fx_rates(settings)
    base_currency = calc.get_base_currency(settings)
    enriched = calc.enrich_projects(projects, payments, rates, base_currency)

    if enriched.empty:
        st.info("No projects yet. Create your first one in the **+ New Project** tab.")
    else:
        fcol1, fcol2, fcol3 = st.columns(3)
        with fcol1:
            search = st.text_input("🔎 Search client or title")
        with fcol2:
            status_filter = st.multiselect("Filter by project status", sorted(enriched["project_status"].unique()))
        with fcol3:
            payment_filter = st.multiselect("Filter by payment status", ["Paid", "Partial", "Unpaid"])

        view = enriched.copy()
        if search:
            mask = (
                view["client_name"].str.contains(search, case=False, na=False)
                | view["project_title"].str.contains(search, case=False, na=False)
            )
            view = view[mask]
        if status_filter:
            view = view[view["project_status"].isin(status_filter)]
        if payment_filter:
            view = view[view["payment_status"].isin(payment_filter)]

        st.caption(f"Showing {len(view)} of {len(enriched)} projects")

        for _, row in view.iterrows():
            with st.expander(
                f"{row['project_title']} — {row['client_name']}  "
                f"({fmt_money(row['project_value'], row['currency'])})"
            ):
                top1, top2, top3 = st.columns([2, 1, 1])
                with top1:
                    st.markdown(f"**Service:** {row['service_category']}  \n**Source:** {row['acquisition_source']}")
                    st.markdown(f"**Notes:** {row['notes'] or '—'}")
                with top2:
                    st.markdown(f"**Status:** {row['project_status']}")
                    st.markdown(f"**Payment:** {status_pill(row['payment_status'])}", unsafe_allow_html=True)
                with top3:
                    st.markdown(f"**Received:** {fmt_money(row['amount_received'], row['currency'])}")
                    st.markdown(f"**Outstanding:** {fmt_money(row['outstanding_balance'], row['currency'])}")
                st.progress(min(row["payment_percentage"] / 100, 1.0), text=f"{row['payment_percentage']}% paid")

                proj_payments = payments[payments["project_id"] == row["project_id"]]
                if not proj_payments.empty:
                    st.markdown("**Payment History**")
                    st.dataframe(
                        proj_payments[["payment_date", "amount", "payment_method", "transaction_reference"]],
                        use_container_width=True, hide_index=True,
                    )

                st.markdown("---")
                st.markdown("**Edit Project**")
                st.caption(
                    "Changing the currency here does NOT convert already-recorded "
                    "payment amounts - it just changes how this project's numbers "
                    "are labeled and aggregated from now on."
                )
                with st.form(f"edit_form_{row['project_id']}"):
                    e1, e2 = st.columns(2)
                    with e1:
                        new_client_name = st.text_input(
                            "Client Name *", value=row["client_name"], key=f"client_{row['project_id']}"
                        )
                        new_project_title = st.text_input(
                            "Project Title *", value=row["project_title"], key=f"title_{row['project_id']}"
                        )
                        new_service_category = st.selectbox(
                            "Service Category", service_categories,
                            index=calc.safe_index(service_categories, row["service_category"]),
                            key=f"svc_{row['project_id']}",
                        )
                        new_project_value = st.number_input(
                            "Project Value *", min_value=0.0, step=50.0,
                            value=float(row["project_value"]), key=f"value_{row['project_id']}",
                        )
                        new_currency = st.selectbox(
                            "Currency", currencies,
                            index=calc.safe_index(currencies, row["currency"]),
                            key=f"cur_{row['project_id']}",
                        )
                    with e2:
                        new_start_date = st.date_input(
                            "Start Date", value=calc.parse_date(row["start_date"]), key=f"start_{row['project_id']}"
                        )
                        new_due_date = st.date_input(
                            "Due Date", value=calc.parse_date(row["due_date"]), key=f"due_{row['project_id']}"
                        )
                        new_status = st.selectbox(
                            "Project Status", project_statuses,
                            index=calc.safe_index(project_statuses, row["project_status"]),
                            key=f"status_{row['project_id']}",
                        )
                        new_acquisition_source = st.selectbox(
                            "Acquisition Source", acquisition_sources,
                            index=calc.safe_index(acquisition_sources, row["acquisition_source"]),
                            key=f"src_{row['project_id']}",
                        )
                    new_notes = st.text_area("Notes", value=row["notes"], key=f"notes_{row['project_id']}")

                    if st.form_submit_button("Save Changes", type="primary"):
                        if not new_client_name or not new_project_title or new_project_value <= 0:
                            st.error("Client Name, Project Title, and a Project Value greater than 0 are required.")
                        else:
                            sheets.update_row(
                                "Projects", "project_id", row["project_id"],
                                {
                                    "client_name": new_client_name,
                                    "project_title": new_project_title,
                                    "service_category": new_service_category,
                                    "project_value": new_project_value,
                                    "currency": new_currency,
                                    "start_date": str(new_start_date),
                                    "due_date": str(new_due_date),
                                    "project_status": new_status,
                                    "acquisition_source": new_acquisition_source,
                                    "notes": new_notes,
                                },
                            )
                            st.toast("Project updated", icon="✅")
                            st.rerun()

                st.markdown("**Danger Zone**")
                if confirm_delete(
                    f"confirm_del_project_{row['project_id']}",
                    f"Delete **{row['project_title']}** and its "
                    f"{len(payments[payments['project_id'] == row['project_id']])} payment(s)? This can't be undone.",
                    button_label="🗑️ Delete Project",
                ):
                    sheets.delete_row("Projects", "project_id", row["project_id"])
                    sheets.delete_rows_where("Payments", "project_id", row["project_id"])
                    st.toast("Project and its payments deleted", icon="🗑️")
                    st.rerun()
