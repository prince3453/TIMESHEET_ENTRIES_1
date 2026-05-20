"""Database module for JSON-backed timesheet storage."""
import json
import os
import sqlite3
from datetime import datetime

import pandas as pd
import streamlit as st

DB_FILE = "timesheet.db"
JSON_FILE = "timesheet_data.json"

DEFAULT_EMPLOYEES = [
    {"employee_id": 1, "name": "Priyanshi", "email": "priyanshi@example.com", "department": "Engineering", "created_at": "2026-01-01 00:00:00"},
    {"employee_id": 2, "name": "Tilak", "email": "tilak@example.com", "department": "Engineering", "created_at": "2026-01-01 00:00:00"},
    {"employee_id": 3, "name": "Riya", "email": "riya@example.com", "department": "Engineering", "created_at": "2026-01-01 00:00:00"},
]


def _read_json_file():
    with open(JSON_FILE, "r", encoding="utf-8") as json_file:
        return json.load(json_file)


def _write_json_file(data):
    temp_file = JSON_FILE + ".tmp"
    with open(temp_file, "w", encoding="utf-8") as json_file:
        json.dump(data, json_file, indent=2, ensure_ascii=False)
    os.replace(temp_file, JSON_FILE)


def _next_employee_id(data):
    return max((employee["employee_id"] for employee in data["employees"]), default=0) + 1


def _next_entry_id(data):
    return max((entry["id"] for entry in data["entries"]), default=0) + 1


def _default_data():
    return {"employees": DEFAULT_EMPLOYEES.copy(), "entries": []}


def _migrate_sqlite_to_json():
    data = {"employees": [], "entries": []}
    if not os.path.exists(DB_FILE):
        return data

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    try:
        cursor.execute(
            "SELECT employee_id, name, email, department, created_at FROM EMPLOYEES"
        )
        for row in cursor.fetchall():
            data["employees"].append({
                "employee_id": row[0],
                "name": row[1],
                "email": row[2],
                "department": row[3],
                "created_at": row[4] if row[4] else datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
            })
    except sqlite3.OperationalError:
        # Table does not exist or schema differs
        pass

    try:
        cursor.execute(
            "SELECT id, entry_date, hours_worked, employee_id, employee_name, project_name, paid_status, created_at FROM TIMESHEET_ENTRIES"
        )
        for row in cursor.fetchall():
            data["entries"].append({
                "id": row[0],
                "entry_date": row[1],
                "hours_worked": float(row[2]),
                "employee_id": row[3],
                "employee_name": row[4],
                "project_name": row[5],
                "paid_status": row[6] or "Unpaid",
                "created_at": row[7] or datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
            })
    except sqlite3.OperationalError:
        pass

    conn.close()
    if data["employees"]:
        _write_json_file(data)
    return data


def load_data():
    if os.path.exists(JSON_FILE):
        return _read_json_file()
    if os.path.exists(DB_FILE):
        data = _migrate_sqlite_to_json()
        if data["employees"] or data["entries"]:
            return data
    default_data = _default_data()
    _write_json_file(default_data)
    return default_data


@st.cache_resource
def init_db():
    """Initialize JSON storage and migrate existing DB data if needed."""
    return load_data()


def get_connection():
    """Get a connection to the SQLite database for compatibility if needed."""
    return sqlite3.connect(DB_FILE)


def _find_employee(data, name):
    return next((employee for employee in data["employees"] if employee["name"] == name), None)


def _find_entry(data, entry_id):
    return next((entry for entry in data["entries"] if entry["id"] == entry_id), None)


def insert_timesheet_entry(entry_date, hours_worked, employee_name, project_name):
    """Insert a timesheet entry into the JSON storage."""
    data = load_data()
    employee = _find_employee(data, employee_name)
    if not employee:
        employee = {
            "employee_id": _next_employee_id(data),
            "name": employee_name,
            "email": "",
            "department": "",
            "created_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        }
        data["employees"].append(employee)

    entry = {
        "id": _next_entry_id(data),
        "entry_date": entry_date.isoformat() if hasattr(entry_date, "isoformat") else str(entry_date),
        "hours_worked": float(hours_worked),
        "employee_id": employee["employee_id"],
        "employee_name": employee_name,
        "project_name": project_name,
        "paid_status": "Unpaid",
        "created_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
    }
    data["entries"].append(entry)
    _write_json_file(data)
    fetch_recent_entries.clear()
    return entry["id"]


@st.cache_data(ttl=30)
def fetch_recent_entries(limit=50):
    """Fetch recent timesheet entries from JSON storage."""
    data = load_data()
    entries = sorted(data["entries"], key=lambda item: item["created_at"], reverse=True)
    df = pd.DataFrame(entries[:limit])
    return df


def update_entry_status(entry_id, status):
    data = load_data()
    entry = _find_entry(data, entry_id)
    if entry:
        entry["paid_status"] = status
        _write_json_file(data)
        fetch_recent_entries.clear()


def delete_entry(entry_id):
    data = load_data()
    before = len(data["entries"])
    data["entries"] = [entry for entry in data["entries"] if entry["id"] != entry_id]
    if len(data["entries"]) != before:
        _write_json_file(data)
        fetch_recent_entries.clear()


def update_paid_status(entry_id, status="Paid"):
    update_entry_status(entry_id, status)


def update_unpaid_status(entry_id):
    update_entry_status(entry_id, "Unpaid")


def update_all_paid_status():
    data = load_data()
    changed = False
    for entry in data["entries"]:
        if entry["paid_status"] == "Unpaid":
            entry["paid_status"] = "Paid"
            changed = True
    if changed:
        _write_json_file(data)
        fetch_recent_entries.clear()


def get_all_employees():
    data = load_data()
    df = pd.DataFrame(data["employees"])
    if df.empty:
        return df
    return df.sort_values("name").reset_index(drop=True)


def get_employee_by_id(employee_id):
    data = load_data()
    return next((employee for employee in data["employees"] if employee["employee_id"] == employee_id), None)


def get_employee_entries(employee_id):
    data = load_data()
    entries = [entry for entry in data["entries"] if entry["employee_id"] == employee_id]
    df = pd.DataFrame(entries)
    if df.empty:
        return df
    return df.sort_values("created_at", ascending=False).reset_index(drop=True)


def approve_employee_payments(employee_id):
    data = load_data()
    affected_rows = 0
    for entry in data["entries"]:
        if entry["employee_id"] == employee_id and entry["paid_status"] == "Unpaid":
            entry["paid_status"] = "Paid"
            affected_rows += 1
    if affected_rows > 0:
        _write_json_file(data)
        fetch_recent_entries.clear()
    return affected_rows


def get_employee_summary():
    data = load_data()
    employees_df = pd.DataFrame(data["employees"])
    entries_df = pd.DataFrame(data["entries"])

    if entries_df.empty:
        employees_df = employees_df.assign(
            total_entries=0,
            total_hours=0.0,
            paid_hours=0.0,
            unpaid_hours=0.0,
        )
        return employees_df[["employee_id", "name", "total_entries", "total_hours", "paid_hours", "unpaid_hours"]]

    summary = (
        entries_df.groupby("employee_id").agg(
            total_entries=("id", "count"),
            total_hours=("hours_worked", "sum"),
            paid_hours=("hours_worked", lambda x: x[entries_df.loc[x.index, "paid_status"] == "Paid"].sum()),
            unpaid_hours=("hours_worked", lambda x: x[entries_df.loc[x.index, "paid_status"] == "Unpaid"].sum()),
        )
    )
    summary = summary.reset_index()
    merged = employees_df.merge(summary, on="employee_id", how="left").fillna({
        "total_entries": 0,
        "total_hours": 0.0,
        "paid_hours": 0.0,
        "unpaid_hours": 0.0,
    })
    merged["total_entries"] = merged["total_entries"].astype(int)
    merged["total_hours"] = merged["total_hours"].astype(float).round(2)
    merged["paid_hours"] = merged["paid_hours"].astype(float).round(2)
    merged["unpaid_hours"] = merged["unpaid_hours"].astype(float).round(2)
    return merged[["employee_id", "name", "total_entries", "total_hours", "paid_hours", "unpaid_hours"]].sort_values("name").reset_index(drop=True)


def sync_existing_entries():
    data = load_data()
    employees_by_name = {employee["name"]: employee["employee_id"] for employee in data["employees"]}
    changed = False
    for entry in data["entries"]:
        if not entry.get("employee_id") or entry["employee_id"] == 0:
            employee_id = employees_by_name.get(entry["employee_name"])
            if employee_id is None:
                employee_id = _next_employee_id(data)
                new_employee = {
                    "employee_id": employee_id,
                    "name": entry["employee_name"],
                    "email": "",
                    "department": "",
                    "created_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
                }
                data["employees"].append(new_employee)
                employees_by_name[entry["employee_name"]] = employee_id
            entry["employee_id"] = employee_id
            changed = True
    if changed:
        _write_json_file(data)
        fetch_recent_entries.clear()
    return sum(1 for entry in data["entries"] if entry["employee_id"])
