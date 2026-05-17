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
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
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
           (entry_date, hours_worked, employee_name, project_name) 
           VALUES (?, ?, ?, ?)""",
        (entry_date.isoformat(), hours_worked, employee_name, project_name),
    )
    conn.commit()
    conn.close()


@st.cache_data(ttl=30)
def fetch_recent_entries(limit=50):
    """Fetch recent timesheet entries from the database."""
    conn = get_connection()
    df = pd.read_sql_query(
        """SELECT entry_date, hours_worked, employee_name, project_name, created_at
           FROM TIMESHEET_ENTRIES
           ORDER BY created_at DESC
           LIMIT ?""",
        conn,
        params=(limit,),
    )
    conn.close()
    return df


# Initialize database on import
init_db()
