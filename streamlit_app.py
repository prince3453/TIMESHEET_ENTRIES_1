import os
import streamlit as st
from datetime import date
from database import (
    insert_timesheet_entry,
    fetch_recent_entries,
    update_paid_status,
    update_unpaid_status,
    update_all_paid_status,
    delete_entry,
)

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
            "Hours Worked",
            min_value=0.0,
            max_value=24.0,
            value=8.0,
            step=0.01,
            format="%.2f",
        )
    with col2:
        employee_name = st.selectbox("Your Name", options=["Priyanshi", "Tilak", "Riya"])
        project_name = st.selectbox("Project", options=PROJECTS)

    submitted = st.form_submit_button("Submit Entry")

if submitted:
    hours_worked = round(hours_worked, 2)
    insert_timesheet_entry(entry_date, hours_worked, employee_name, project_name)
    st.success(f"Entry saved! Hours recorded: {hours_worked:.2f}")

st.divider()

@st.cache_data(ttl=30)
def load_entries():
    return fetch_recent_entries()

if st.button("Refresh"):
    load_entries.clear()

df = load_entries()

with st.sidebar:
    st.title("Admin")
    admin_expander = st.expander("Run admin workflow")
    with admin_expander:
        st.write("Use your admin password to change the paid status of a timesheet entry or remove an entry.")
        admin_password = st.text_input("Admin Password", type="password", key="admin_password")
        entry_id_input = st.text_input("Entry ID to update or remove", key="entry_id_input")
        col1, col2, col3, col4 = st.columns(4)
        approve_pressed = col1.button("Mark as Paid")
        unpaid_pressed = col2.button("Mark as Unpaid")
        delete_pressed = col3.button("Remove Entry")
        all_paid_pressed = col4.button("Mark all Paid")

if df.empty:
    st.info("No entries yet. Submit your first timesheet above!")
else:
    unpaid_df = df[df["paid_status"] == "Unpaid"]

    if approve_pressed or unpaid_pressed or delete_pressed or all_paid_pressed:
        if not ADMIN_USER or not ADMIN_PASSWORD:
            st.sidebar.error("Admin approval is not configured. Set ADMIN_USER and ADMIN_PASSWORD.")
        elif admin_password == ADMIN_PASSWORD:
            if approve_pressed:
                try:
                    entry_id = int(entry_id_input)
                    update_paid_status(entry_id)
                    load_entries.clear()
                    st.sidebar.success(f"Entry {entry_id} marked as Paid.")
                    df = load_entries()
                except ValueError:
                    st.sidebar.error("Please enter a valid numeric Entry ID.")
            elif unpaid_pressed:
                try:
                    entry_id = int(entry_id_input)
                    update_unpaid_status(entry_id)
                    load_entries.clear()
                    st.sidebar.success(f"Entry {entry_id} marked as Unpaid.")
                    df = load_entries()
                except ValueError:
                    st.sidebar.error("Please enter a valid numeric Entry ID.")
            elif delete_pressed:
                try:
                    entry_id = int(entry_id_input)
                    delete_entry(entry_id)
                    load_entries.clear()
                    st.sidebar.success(f"Entry {entry_id} removed.")
                    df = load_entries()
                except ValueError:
                    st.sidebar.error("Please enter a valid numeric Entry ID.")
            elif all_paid_pressed:
                if unpaid_df.empty:
                    st.sidebar.info("No unpaid entries to mark as Paid.")
                else:
                    update_all_paid_status()
                    load_entries.clear()
                    st.sidebar.success("All unpaid entries marked as Paid.")
                    df = load_entries()
        else:
            st.sidebar.error("Invalid credentials.")

    summary_df = (
        df.assign(
            paid_hours=lambda x: x.loc[x["paid_status"] == "Paid", "hours_worked"],
            unpaid_hours=lambda x: x.loc[x["paid_status"] == "Unpaid", "hours_worked"],
        )
        .groupby("employee_name")
        .agg(
            total_hours=("hours_worked", "sum"),
            paid_hours=("paid_hours", "sum"),
            unpaid_hours=("unpaid_hours", "sum"),
        )
        .reset_index()
    )
    summary_df["total_hours"] = summary_df["total_hours"].round(2)
    summary_df["paid_hours"] = summary_df["paid_hours"].fillna(0).round(2)
    summary_df["unpaid_hours"] = summary_df["unpaid_hours"].fillna(0).round(2)
    summary_df = summary_df.rename(
        columns={
            "employee_name": "Employee",
            "total_hours": "Total Hours",
            "paid_hours": "Paid Hours",
            "unpaid_hours": "Unpaid Hours",
        }
    )

    display_df = df.copy()
    display_df["hours_worked"] = display_df["hours_worked"].round(2)
    display_df = display_df.rename(
        columns={
            "id": "Entry Id",
            "entry_date": "Date",
            "hours_worked": "Hours Worked",
            "employee_name": "Employee",
            "project_name": "Project",
            "paid_status": "Paid Status",
            "created_at": "Created At",
        }
    )

    st.subheader("Recent Entries")
    st.dataframe(
        display_df.style.hide(axis="index").format({"Hours Worked": "{:.2f}"}),
        use_container_width=True,
    )

    st.subheader("Dashboard")
    st.dataframe(
        summary_df.style.hide(axis="index").format(
            {"Total Hours": "{:.2f}", "Paid Hours": "{:.2f}", "Unpaid Hours": "{:.2f}"}
        ),
        use_container_width=True,
    )

    st.subheader("Paid vs Unpaid Hours")
    chart_df = summary_df.set_index("Employee")[["Paid Hours", "Unpaid Hours"]]
    st.bar_chart(chart_df)
