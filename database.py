"""Database connection module for SQLite."""
import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

DB_FILE = "timesheet.db"


@st.cache_resource
def init_db():
    """Initialize SQLite database and create table if it doesn't exist."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS TIMESHEET_ENTRIES (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entry_date TEXT NOT NULL,
            hours_worked REAL NOT NULL,
            employee_name TEXT NOT NULL,
            project_name TEXT NOT NULL,
            paid_status TEXT NOT NULL DEFAULT 'Unpaid',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    cursor.execute("PRAGMA table_info(TIMESHEET_ENTRIES)")
    columns = [row[1] for row in cursor.fetchall()]
    if "paid_status" not in columns:
        cursor.execute(
            "ALTER TABLE TIMESHEET_ENTRIES ADD COLUMN paid_status TEXT NOT NULL DEFAULT 'Unpaid'"
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
    cursor.execute(
        """INSERT INTO TIMESHEET_ENTRIES 
           (entry_date, hours_worked, employee_name, project_name, paid_status) 
           VALUES (?, ?, ?, ?, ?)""",
        (entry_date.isoformat(), hours_worked, employee_name, project_name, "Unpaid"),
    )
    conn.commit()
    conn.close()


@st.cache_data(ttl=30)
def fetch_recent_entries(limit=50):
    """Fetch recent timesheet entries from the database."""
    conn = get_connection()
    df = pd.read_sql_query(
        """SELECT id, entry_date, hours_worked, employee_name, project_name, paid_status, created_at
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


def update_all_paid_status(status="Paid"):
    """Update the paid status of all unpaid timesheet entries."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE TIMESHEET_ENTRIES SET paid_status = ? WHERE paid_status = ?",
        (status, "Unpaid"),
    )
    conn.commit()
    conn.close()
    fetch_recent_entries.clear()


# Initialize database on import
init_db()
