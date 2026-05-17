import streamlit as st
from datetime import date
from database import insert_timesheet_entry, fetch_recent_entries, update_paid_status

st.set_page_config(page_title="Timesheet Tracker", layout="centered")
st.title("Timesheet Tracker")

PROJECTS = [
    "Project Whetstone",
    "Project Telus",
]

with st.form("timesheet_form", clear_on_submit=True):
    st.subheader("Log Your Hours")
    col1, col2 = st.columns(2)
    with col1:
        entry_date = st.date_input("Date", value=date.today())
        hours_worked = st.number_input(
            "Hours Worked", min_value=0.0, max_value=24.0, value=8.0, step=0.5
        )
    with col2:
        employee_name = st.selectbox("Your Name", options=["Priyanshi", "Tilak"])
        project_name = st.selectbox("Project", options=PROJECTS)

    submitted = st.form_submit_button("Submit Entry")

if submitted:
    insert_timesheet_entry(entry_date, hours_worked, employee_name, project_name)
    st.success("Entry saved!")

st.divider()
st.subheader("Recent Entries")

@st.cache_data(ttl=30)
def load_entries():
    return fetch_recent_entries()

if st.button("Refresh"):
    load_entries.clear()

df = load_entries()
if df.empty:
    st.info("No entries yet. Submit your first timesheet above!")
else:
    unpaid_df = df[df["paid_status"] == "Unpaid"]

    if not unpaid_df.empty:
        st.subheader("Approve Unpaid Entries")
        selection_labels = (
            unpaid_df["created_at"]
            + " — "
            + unpaid_df["employee_name"]
            + " / "
            + unpaid_df["project_name"]
            + " / "
            + unpaid_df["hours_worked"].astype(str)
            + "h"
        )
        options = list(zip(unpaid_df["id"].astype(str), selection_labels))
        selected = st.selectbox(
            "Select an unpaid entry to mark as Paid",
            options=options,
            format_func=lambda item: item[1],
        )
        if st.button("Mark as Paid"):
            entry_id = int(selected[0])
            update_paid_status(entry_id)
            load_entries.clear()
            st.success("Entry marked as Paid.")
            df = load_entries()

    st.subheader("Recent Entries")
    st.dataframe(df.drop(columns=["id"]), use_container_width=True)
