"""Database connection module for SQLite."""
import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

DB_FILE = "timesheet.db"


@st.cache_resource
def init_db():
    """Initialize SQLite database and create tables if they don't exist."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Create EMPLOYEES table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS EMPLOYEES (
            employee_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            email TEXT,
            department TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create TIMESHEET_ENTRIES table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS TIMESHEET_ENTRIES (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entry_date TEXT NOT NULL,
            hours_worked REAL NOT NULL,
            employee_id INTEGER NOT NULL,
            employee_name TEXT NOT NULL,
            project_name TEXT NOT NULL,
            paid_status TEXT NOT NULL DEFAULT 'Unpaid',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (employee_id) REFERENCES EMPLOYEES(employee_id)
        )
    """)
    conn.commit()
    
    # Check if employee_id column exists, if not add it
    cursor.execute("PRAGMA table_info(TIMESHEET_ENTRIES)")
    columns = [row[1] for row in cursor.fetchall()]
    if "employee_id" not in columns:
        cursor.execute(
            "ALTER TABLE TIMESHEET_ENTRIES ADD COLUMN employee_id INTEGER"
        )
        conn.commit()
    if "paid_status" not in columns:
        cursor.execute(
            "ALTER TABLE TIMESHEET_ENTRIES ADD COLUMN paid_status TEXT NOT NULL DEFAULT 'Unpaid'"
        )
        conn.commit()
    
    # Initialize default employees if table is empty
    cursor.execute("SELECT COUNT(*) FROM EMPLOYEES")
    if cursor.fetchone()[0] == 0:
        default_employees = [
            ("Priyanshi", "priyanshi@example.com", "Engineering"),
            ("Tilak", "tilak@example.com", "Engineering"),
            ("Riya", "riya@example.com", "Engineering"),
        ]
        for name, email, dept in default_employees:
            cursor.execute(
                "INSERT OR IGNORE INTO EMPLOYEES (name, email, department) VALUES (?, ?, ?)",
                (name, email, dept)
            )
        conn.commit()
    
    conn.close()


def get_connection():
    """Get a connection to the SQLite database."""
    return sqlite3.connect(DB_FILE)


def insert_timesheet_entry(entry_date, hours_worked, employee_name, project_name):
    """Insert a timesheet entry into the database."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Get employee_id from employee_name
    cursor.execute("SELECT employee_id FROM EMPLOYEES WHERE name = ?", (employee_name,))
    result = cursor.fetchone()
    if result:
        employee_id = result[0]
    else:
        # If employee doesn't exist, create them
        cursor.execute(
            "INSERT INTO EMPLOYEES (name) VALUES (?)",
            (employee_name,)
        )
        conn.commit()
        employee_id = cursor.lastrowid
    
    cursor.execute(
        """INSERT INTO TIMESHEET_ENTRIES 
           (entry_date, hours_worked, employee_id, employee_name, project_name, paid_status) 
           VALUES (?, ?, ?, ?, ?, ?)""",
        (entry_date.isoformat(), hours_worked, employee_id, employee_name, project_name, "Unpaid"),
    )
    conn.commit()
    conn.close()



@st.cache_data(ttl=30)
def fetch_recent_entries(limit=50):
    """Fetch recent timesheet entries from the database."""
    conn = get_connection()
    df = pd.read_sql_query(
        """SELECT id, entry_date, hours_worked, employee_id, employee_name, project_name, paid_status, created_at
           FROM TIMESHEET_ENTRIES
           ORDER BY created_at DESC
           LIMIT ?""",
        conn,
        params=(limit,),
    )
    conn.close()
    return df


def update_entry_status(entry_id, status):
    """Update the paid status of a timesheet entry."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE TIMESHEET_ENTRIES SET paid_status = ? WHERE id = ?",
        (status, entry_id),
    )
    conn.commit()
    conn.close()
    fetch_recent_entries.clear()


def delete_entry(entry_id):
    """Delete a timesheet entry by ID."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM TIMESHEET_ENTRIES WHERE id = ?",
        (entry_id,),
    )
    conn.commit()
    conn.close()
    fetch_recent_entries.clear()


def update_paid_status(entry_id, status="Paid"):
    """Update the paid status of a timesheet entry to Paid."""
    update_entry_status(entry_id, status)


def update_unpaid_status(entry_id):
    """Update the paid status of a timesheet entry to Unpaid."""
    update_entry_status(entry_id, "Unpaid")


def update_all_paid_status():
    """Update all unpaid entries to Paid status."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE TIMESHEET_ENTRIES SET paid_status = ? WHERE paid_status = ?",
        ("Paid", "Unpaid"),
    )
    conn.commit()
    conn.close()
    fetch_recent_entries.clear()


def get_all_employees():
    """Fetch all employees from the database."""
    conn = get_connection()
    df = pd.read_sql_query(
        "SELECT employee_id, name, email, department, created_at FROM EMPLOYEES ORDER BY name",
        conn,
    )
    conn.close()
    return df


def get_employee_by_id(employee_id):
    """Get employee details by ID."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT employee_id, name, email, department FROM EMPLOYEES WHERE employee_id = ?",
        (employee_id,),
    )
    result = cursor.fetchone()
    conn.close()
    return result


def get_employee_entries(employee_id):
    """Fetch all timesheet entries for a specific employee."""
    conn = get_connection()
    df = pd.read_sql_query(
        """SELECT id, entry_date, hours_worked, employee_id, employee_name, project_name, paid_status, created_at
           FROM TIMESHEET_ENTRIES
           WHERE employee_id = ?
           ORDER BY created_at DESC""",
        conn,
        params=(employee_id,),
    )
    conn.close()
    return df


def approve_employee_payments(employee_id):
    """Approve all unpaid entries for a specific employee."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """UPDATE TIMESHEET_ENTRIES 
           SET paid_status = ? 
           WHERE employee_id = ? AND paid_status = ?""",
        ("Paid", employee_id, "Unpaid"),
    )
    affected_rows = cursor.rowcount
    conn.commit()
    conn.close()
    fetch_recent_entries.clear()
    return affected_rows


def get_employee_summary():
    """Get summary of hours (paid/unpaid) by employee."""
    conn = get_connection()
    df = pd.read_sql_query(
        """SELECT 
            e.employee_id,
            e.name,
            COUNT(t.id) as total_entries,
            ROUND(SUM(t.hours_worked), 2) as total_hours,
            ROUND(SUM(CASE WHEN t.paid_status = 'Paid' THEN t.hours_worked ELSE 0 END), 2) as paid_hours,
            ROUND(SUM(CASE WHEN t.paid_status = 'Unpaid' THEN t.hours_worked ELSE 0 END), 2) as unpaid_hours
        FROM EMPLOYEES e
        LEFT JOIN TIMESHEET_ENTRIES t ON e.employee_id = t.employee_id
        GROUP BY e.employee_id, e.name
        ORDER BY e.name""",
        conn,
    )
    conn.close()
    return df


def sync_existing_entries():
    """Sync employee_id for existing entries that might have NULL values."""
    conn = get_connection()
    cursor = conn.cursor()
    # Update entries where employee_id is NULL by matching employee_name
    cursor.execute("""
        UPDATE TIMESHEET_ENTRIES
        SET employee_id = (
            SELECT employee_id FROM EMPLOYEES 
            WHERE EMPLOYEES.name = TIMESHEET_ENTRIES.employee_name
        )
        WHERE employee_id IS NULL OR employee_id = 0
    """)
    affected = cursor.rowcount
    conn.commit()
    conn.close()
    if affected > 0:
        fetch_recent_entries.clear()
    return affected
