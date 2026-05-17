import os
import streamlit as st
from datetime import date
from database import insert_timesheet_entry, fetch_recent_entries, update_paid_status, update_all_paid_status

st.set_page_config(page_title="Timesheet Tracker", layout="centered")
st.title("Timesheet Tracker")

ADMIN_USER = os.environ.get("ADMIN_USER", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "$Prince3453")

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

    st.subheader("Admin Approval")
    with st.form("approval_form"):
        entry_id_input = st.text_input("Entry ID to approve")
        username = st.text_input("User ID")
        password = st.text_input("Password", type="password")
        col1, col2 = st.columns(2)
        approve_pressed = col1.form_submit_button("Mark as Paid")
        all_paid_pressed = col2.form_submit_button("Mark as All Paid")

    if approve_pressed or all_paid_pressed:
        if not ADMIN_USER or not ADMIN_PASSWORD:
            st.error("Admin approval is not configured. Set ADMIN_USER and ADMIN_PASSWORD.")
        elif username == ADMIN_USER and password == ADMIN_PASSWORD:
            if approve_pressed:
                try:
                    entry_id = int(entry_id_input)
                    update_paid_status(entry_id)
                    load_entries.clear()
                    st.success(f"Entry {entry_id} marked as Paid.")
                    df = load_entries()
                except ValueError:
                    st.error("Please enter a valid numeric Entry ID.")
            elif all_paid_pressed:
                if unpaid_df.empty:
                    st.info("No unpaid entries to mark as Paid.")
                else:
                    update_all_paid_status()
                    load_entries.clear()
                    st.success("All unpaid entries marked as Paid.")
                    df = load_entries()
        else:
            st.error("Invalid credentials.")

    if not unpaid_df.empty:
        st.markdown("**Unpaid entries currently available:**")
        for _, row in unpaid_df.iterrows():
            st.write(
                f"ID {row['id']} — {row['created_at']} — {row['employee_name']} / {row['project_name']} / {row['hours_worked']}h"
            )

    st.subheader("Recent Entries")
    st.dataframe(df, use_container_width=True)
