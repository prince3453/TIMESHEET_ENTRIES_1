import os
import streamlit as st
from datetime import date
from database import (
    init_db,
    insert_timesheet_entry,
    fetch_recent_entries,
    update_paid_status,
    update_unpaid_status,
    update_all_paid_status,
    delete_entry,
    get_all_employees,
    get_employee_entries,
    approve_employee_payments,
    get_employee_summary,
    sync_existing_entries,
)

st.set_page_config(page_title="Timesheet Tracker", layout="wide")
st.title("Timesheet Tracker")

# Initialize database
init_db()

# Sync any existing entries that might have NULL employee_id values
sync_existing_entries()


ADMIN_USER = os.environ.get("ADMIN_USER", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "$Prince3453")

PROJECTS = [
    "Project Whetstone",
    "Project Telus",
]

# Sidebar - Admin and Employee Management
with st.sidebar:
    st.title("Admin Panel")
    
    # Get all employees
    employees_df = get_all_employees()
    
    admin_tab = st.tabs(["Approve by Employee", "Admin Controls"])
    
    with admin_tab[0]:
        st.subheader("Approve Payments by Employee")
        admin_password = st.text_input("Admin Password", type="password", key="admin_password_approve")
        
        if not employees_df.empty:
            employee_options = {f"{row['name']} (ID: {row['employee_id']})": row['employee_id'] 
                               for _, row in employees_df.iterrows()}
            selected_employee = st.selectbox("Select Employee", options=employee_options.keys())
            selected_employee_id = employee_options[selected_employee]
            
            if st.button("Approve All Unpaid Entries for Selected Employee"):
                if admin_password == ADMIN_PASSWORD:
                    affected = approve_employee_payments(selected_employee_id)
                    st.success(f"✓ Approved {affected} entries for {selected_employee}. Status changed to Paid.")
                    # Clear cache to refresh data
                    st.rerun()
                else:
                    st.error("Invalid admin password")
    
    with admin_tab[1]:
        st.subheader("Admin Controls")
        admin_password_ctrl = st.text_input("Admin Password", type="password", key="admin_password_ctrl")
        
        col1, col2 = st.columns(2)
        with col1:
            st.write("**Mark Entry as Paid/Unpaid:**")
            entry_id_input = st.text_input("Entry ID", key="entry_id_input")
            approve_pressed = st.button("Mark as Paid")
            unpaid_pressed = st.button("Mark as Unpaid")
            delete_pressed = st.button("Delete Entry")
        
        with col2:
            st.write("**Bulk Actions:**")
            all_paid_pressed = st.button("Mark All Unpaid as Paid")
        
        if approve_pressed or unpaid_pressed or delete_pressed or all_paid_pressed:
            if admin_password_ctrl == ADMIN_PASSWORD:
                try:
                    if approve_pressed:
                        entry_id = int(entry_id_input)
                        update_paid_status(entry_id)
                        st.success(f"Entry {entry_id} marked as Paid")
                    elif unpaid_pressed:
                        entry_id = int(entry_id_input)
                        update_unpaid_status(entry_id)
                        st.success(f"Entry {entry_id} marked as Unpaid")
                    elif delete_pressed:
                        entry_id = int(entry_id_input)
                        delete_entry(entry_id)
                        st.success(f"Entry {entry_id} deleted")
                    elif all_paid_pressed:
                        update_all_paid_status()
                        st.success("All unpaid entries marked as Paid")
                    st.rerun()
                except ValueError:
                    st.error("Please enter a valid numeric Entry ID")
            else:
                st.error("Invalid admin password")

# Main content
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("Log Your Hours")
    with st.form("timesheet_form", clear_on_submit=True):
        col1_form, col2_form = st.columns(2)
        with col1_form:
            entry_date = st.date_input("Date", value=date.today())
            hours_worked = st.number_input(
                "Hours Worked",
                min_value=0.0,
                max_value=24.0,
                value=8.0,
                step=0.01,
                format="%.2f",
            )
        with col2_form:
            if not employees_df.empty:
                employee_options_form = {f"{row['name']} (ID: {row['employee_id']})": row['name'] 
                                        for _, row in employees_df.iterrows()}
                employee_name = st.selectbox("Your Name", options=employee_options_form.keys())
                employee_name = employee_options_form[employee_name]
            else:
                employee_name = st.selectbox("Your Name", options=["Priyanshi", "Tilak", "Riya"])
            
            project_name = st.selectbox("Project", options=PROJECTS)

        submitted = st.form_submit_button("Submit Entry")

    if submitted:
        hours_worked = round(hours_worked, 2)
        insert_timesheet_entry(entry_date, hours_worked, employee_name, project_name)
        st.success(f"✓ Entry saved! {employee_name} recorded {hours_worked:.2f} hours")
        fetch_recent_entries.clear()
        st.experimental_rerun()

with col2:
    st.subheader("Employee Summary")
    summary_df = get_employee_summary()
    if not summary_df.empty:
        summary_df = summary_df.rename(columns={
            "employee_id": "ID",
            "name": "Employee",
            "total_entries": "Entries",
            "total_hours": "Total Hours",
            "paid_hours": "Paid Hours",
            "unpaid_hours": "Unpaid Hours",
        })
        st.dataframe(summary_df, use_container_width=True, hide_index=True)

st.divider()

# Tabs for different views
tab1, tab2, tab3 = st.tabs(["All Entries", "Unpaid Entries", "By Employee"])

with tab1:
    st.subheader("All Timesheet Entries")
    if st.button("Refresh All Entries", key="refresh_all"):
        fetch_recent_entries.clear()
    
    @st.cache_data(ttl=30)
    def load_entries():
        return fetch_recent_entries()
    
    df = load_entries()
    if df.empty:
        st.info("No entries yet. Submit your first timesheet above!")
    else:
        display_df = df.copy()
        display_df["hours_worked"] = display_df["hours_worked"].round(2)
        display_df = display_df.rename(columns={
            "id": "Entry ID",
            "employee_id": "Employee ID",
            "entry_date": "Date",
            "hours_worked": "Hours",
            "employee_name": "Employee",
            "project_name": "Project",
            "paid_status": "Status",
            "created_at": "Created At",
        })
        # Reorder columns for better visibility
        display_df = display_df[["Entry ID", "Employee ID", "Employee", "Date", "Hours", "Project", "Status", "Created At"]]
        st.dataframe(display_df, use_container_width=True, hide_index=True)

with tab2:
    st.subheader("Unpaid Entries")
    if st.button("Refresh Unpaid", key="refresh_unpaid"):
        load_entries.clear()
    
    df = load_entries()
    if df.empty:
        st.info("No entries yet!")
    else:
        unpaid_df = df[df["paid_status"] == "Unpaid"].copy()
        if unpaid_df.empty:
            st.success("✓ All entries are paid!")
        else:
            unpaid_df["hours_worked"] = unpaid_df["hours_worked"].round(2)
            unpaid_df = unpaid_df.rename(columns={
                "id": "Entry ID",
                "employee_id": "Employee ID",
                "entry_date": "Date",
                "hours_worked": "Hours",
                "employee_name": "Employee",
                "project_name": "Project",
                "paid_status": "Status",
                "created_at": "Created At",
            })
            # Reorder columns for better visibility
            unpaid_df = unpaid_df[["Entry ID", "Employee ID", "Employee", "Date", "Hours", "Project", "Status", "Created At"]]
            st.dataframe(unpaid_df, use_container_width=True, hide_index=True)

with tab3:
    st.subheader("View Entries by Employee")
    if not employees_df.empty:
        employee_options_view = {f"{row['name']} (ID: {row['employee_id']})": row['employee_id'] 
                                for _, row in employees_df.iterrows()}
        selected_emp = st.selectbox("Select Employee", options=employee_options_view.keys(), key="view_employee")
        selected_emp_id = employee_options_view[selected_emp]
        
        emp_entries = get_employee_entries(selected_emp_id)
        if emp_entries.empty:
            st.info(f"No entries for this employee yet.")
        else:
            emp_entries["hours_worked"] = emp_entries["hours_worked"].round(2)
            emp_entries = emp_entries.rename(columns={
                "id": "Entry ID",
                "employee_id": "Employee ID",
                "entry_date": "Date",
                "hours_worked": "Hours",
                "employee_name": "Employee",
                "project_name": "Project",
                "paid_status": "Status",
                "created_at": "Created At",
            })
            # Reorder columns for better visibility
            emp_entries = emp_entries[["Entry ID", "Employee ID", "Employee", "Date", "Hours", "Project", "Status", "Created At"]]
            st.dataframe(emp_entries, use_container_width=True, hide_index=True)
            
            # Summary for this employee
            total_hours = emp_entries["Hours"].sum()
            paid_hours = emp_entries[emp_entries["Status"] == "Paid"]["Hours"].sum()
            unpaid_hours = emp_entries[emp_entries["Status"] == "Unpaid"]["Hours"].sum()
            
            col1, col2, col3 = st.columns(3)
            col1.metric("Total Hours", f"{total_hours:.2f}")
            col2.metric("Paid Hours", f"{paid_hours:.2f}")
            col3.metric("Unpaid Hours", f"{unpaid_hours:.2f}")

