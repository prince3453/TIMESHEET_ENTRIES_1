"""Database module for JSON-backed timesheet storage and optional MongoDB storage."""
import json
import os
import sqlite3
from datetime import datetime

import pandas as pd
import streamlit as st

try:
    from pymongo import MongoClient, DESCENDING, ASCENDING
except ImportError:  # pragma: no cover
    MongoClient = None
    DESCENDING = None
    ASCENDING = None

DB_FILE = "timesheet.db"
JSON_FILE = "timesheet_data.json"
DEFAULT_EMPLOYEES = [
    {
        "employee_id": 1,
        "name": "Priyanshi",
        "email": "priyanshi@example.com",
        "department": "Engineering",
        "created_at": "2026-01-01 00:00:00",
    },
    {
        "employee_id": 2,
        "name": "Tilak",
        "email": "tilak@example.com",
        "department": "Engineering",
        "created_at": "2026-01-01 00:00:00",
    },
    {
        "employee_id": 3,
        "name": "Riya",
        "email": "riya@example.com",
        "department": "Engineering",
        "created_at": "2026-01-01 00:00:00",
    },
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


def _ensure_json_file():
    if not os.path.exists(JSON_FILE):
        _write_json_file(_default_data())


def use_mongodb():
    return bool(os.environ.get("MONGO_URI") and os.environ.get("MONGO_DB"))


def get_mongo_client():
    if not use_mongodb():
        return None
    if MongoClient is None:
        raise RuntimeError(
            "pymongo is required for MongoDB support. Install it with `pip install pymongo`."
        )

    mongo_kwargs = {
        "serverSelectionTimeoutMS": 5000,
    }

    if os.environ.get("MONGO_TLS"):
        mongo_kwargs["tls"] = os.environ.get("MONGO_TLS").lower() in ("1", "true", "yes", "on")
    if os.environ.get("MONGO_TLS_CERTIFICATE_KEY_FILE"):
        mongo_kwargs["tlsCertificateKeyFile"] = os.environ["MONGO_TLS_CERTIFICATE_KEY_FILE"]
    if os.environ.get("MONGO_TLS_CA_FILE"):
        mongo_kwargs["tlsCAFile"] = os.environ["MONGO_TLS_CA_FILE"]
    if os.environ.get("MONGO_TLS_ALLOW_INVALID_CERTIFICATES"):
        mongo_kwargs["tlsAllowInvalidCertificates"] = os.environ.get(
            "MONGO_TLS_ALLOW_INVALID_CERTIFICATES"
        ).lower() in ("1", "true", "yes", "on")

    if os.environ.get("MONGO_USERNAME") and os.environ.get("MONGO_PASSWORD"):
        mongo_kwargs["username"] = os.environ["MONGO_USERNAME"]
        mongo_kwargs["password"] = os.environ["MONGO_PASSWORD"]
        if os.environ.get("MONGO_AUTH_SOURCE"):
            mongo_kwargs["authSource"] = os.environ["MONGO_AUTH_SOURCE"]

    return MongoClient(os.environ["MONGO_URI"], **mongo_kwargs)


@st.cache_resource
def get_cached_mongo_client():
    return get_mongo_client()


def get_mongo_db():
    client = get_cached_mongo_client()
    if client is None:
        return None
    return client[os.environ["MONGO_DB"]]


def get_mongo_collections():
    db = get_mongo_db()
    if db is None:
        return None, None
    employee_collection = os.environ.get("MONGO_EMPLOYEES_COLLECTION", "employees")
    entry_collection = os.environ.get("MONGO_ENTRIES_COLLECTION", "entries")
    return db[employee_collection], db[entry_collection]


def _migrate_json_to_mongo():
    if not use_mongodb() or not os.path.exists(JSON_FILE):
        return
    employee_coll, entry_coll = get_mongo_collections()
    if employee_coll.count_documents({}) or entry_coll.count_documents({}):
        return

    data = _read_json_file()
    if data["employees"]:
        employee_coll.insert_many(data["employees"])
    if data["entries"]:
        entry_coll.insert_many(data["entries"])


def load_data():
    if use_mongodb():
        employee_coll, entry_coll = get_mongo_collections()
        employees = list(employee_coll.find({}, {"_id": 0}).sort("name", ASCENDING))
        entries = list(entry_coll.find({}, {"_id": 0}).sort("created_at", DESCENDING))

        if not employees and not entries:
            default_data = _default_data()
            employee_coll.insert_many(default_data["employees"])
            return default_data

        return {"employees": employees, "entries": entries}

    _ensure_json_file()
    return _read_json_file()


@st.cache_resource
def init_db():
    if use_mongodb():
        _migrate_json_to_mongo()
    return load_data()


def get_connection():
    return sqlite3.connect(DB_FILE)


def _find_employee(data, name):
    return next((employee for employee in data["employees"] if employee["name"] == name), None)


def _find_entry(data, entry_id):
    return next((entry for entry in data["entries"] if entry["id"] == entry_id), None)


def _next_employee_id_mongo(employee_coll):
    highest = employee_coll.find_one(sort=[("employee_id", DESCENDING)])
    return int(highest["employee_id"] + 1) if highest else 1


def _next_entry_id_mongo(entry_coll):
    highest = entry_coll.find_one(sort=[("id", DESCENDING)])
    return int(highest["id"] + 1) if highest else 1


def insert_timesheet_entry(entry_date, hours_worked, employee_name, project_name):
    if use_mongodb():
        employee_coll, entry_coll = get_mongo_collections()
        employee = employee_coll.find_one({"name": employee_name})
        if not employee:
            employee = {
                "employee_id": _next_employee_id_mongo(employee_coll),
                "name": employee_name,
                "email": "",
                "department": "",
                "created_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
            }
            employee_coll.insert_one(employee)

        entry = {
            "id": _next_entry_id_mongo(entry_coll),
            "entry_date": entry_date.isoformat() if hasattr(entry_date, "isoformat") else str(entry_date),
            "hours_worked": float(hours_worked),
            "employee_id": employee["employee_id"],
            "employee_name": employee_name,
            "project_name": project_name,
            "paid_status": "Unpaid",
            "created_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        }
        entry_coll.insert_one(entry)
        fetch_recent_entries.clear()
        return entry["id"]

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
    if use_mongodb():
        _, entry_coll = get_mongo_collections()
        entries = list(
            entry_coll.find({}, {"_id": 0}).sort("created_at", DESCENDING).limit(limit)
        )
        return pd.DataFrame(entries)

    data = load_data()
    entries = sorted(data["entries"], key=lambda item: item["created_at"], reverse=True)
    return pd.DataFrame(entries[:limit])


def update_entry_status(entry_id, status):
    if use_mongodb():
        _, entry_coll = get_mongo_collections()
        result = entry_coll.update_one({"id": entry_id}, {"$set": {"paid_status": status}})
        if result.modified_count:
            fetch_recent_entries.clear()
        return

    data = load_data()
    entry = _find_entry(data, entry_id)
    if entry:
        entry["paid_status"] = status
        _write_json_file(data)
        fetch_recent_entries.clear()


def delete_entry(entry_id):
    if use_mongodb():
        _, entry_coll = get_mongo_collections()
        result = entry_coll.delete_one({"id": entry_id})
        if result.deleted_count:
            fetch_recent_entries.clear()
        return

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
    if use_mongodb():
        employee_coll, entry_coll = get_mongo_collections()
        result = entry_coll.update_many({"paid_status": "Unpaid"}, {"$set": {"paid_status": "Paid"}})
        if result.modified_count:
            fetch_recent_entries.clear()
        return

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
    if use_mongodb():
        employee_coll, _ = get_mongo_collections()
        employees = list(employee_coll.find({}, {"_id": 0}).sort("name", ASCENDING))
        return pd.DataFrame(employees)

    data = load_data()
    df = pd.DataFrame(data["employees"])
    if df.empty:
        return df
    return df.sort_values("name").reset_index(drop=True)


def get_employee_by_id(employee_id):
    if use_mongodb():
        employee_coll, _ = get_mongo_collections()
        return employee_coll.find_one({"employee_id": employee_id}, {"_id": 0})

    data = load_data()
    return next((employee for employee in data["employees"] if employee["employee_id"] == employee_id), None)


def get_employee_entries(employee_id):
    if use_mongodb():
        _, entry_coll = get_mongo_collections()
        entries = list(
            entry_coll.find({"employee_id": employee_id}, {"_id": 0}).sort("created_at", DESCENDING)
        )
        return pd.DataFrame(entries)

    data = load_data()
    entries = [entry for entry in data["entries"] if entry["employee_id"] == employee_id]
    df = pd.DataFrame(entries)
    if df.empty:
        return df
    return df.sort_values("created_at", ascending=False).reset_index(drop=True)


def approve_employee_payments(employee_id):
    if use_mongodb():
        _, entry_coll = get_mongo_collections()
        result = entry_coll.update_many(
            {"employee_id": employee_id, "paid_status": "Unpaid"},
            {"$set": {"paid_status": "Paid"}},
        )
        if result.modified_count:
            fetch_recent_entries.clear()
        return result.modified_count

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
    if use_mongodb():
        data = load_data()
        employees_df = pd.DataFrame(data["employees"])
        entries_df = pd.DataFrame(data["entries"])
    else:
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
        return employees_df[
            ["employee_id", "name", "total_entries", "total_hours", "paid_hours", "unpaid_hours"]
        ]

    summary = (
        entries_df.groupby("employee_id").agg(
            total_entries=("id", "count"),
            total_hours=("hours_worked", "sum"),
            paid_hours=("hours_worked", lambda x: x[entries_df.loc[x.index, "paid_status"] == "Paid"].sum()),
            unpaid_hours=("hours_worked", lambda x: x[entries_df.loc[x.index, "paid_status"] == "Unpaid"].sum()),
        )
    )
    summary = summary.reset_index()
    merged = employees_df.merge(summary, on="employee_id", how="left").fillna(
        {
            "total_entries": 0,
            "total_hours": 0.0,
            "paid_hours": 0.0,
            "unpaid_hours": 0.0,
        }
    )
    merged["total_entries"] = merged["total_entries"].astype(int)
    merged["total_hours"] = merged["total_hours"].astype(float).round(2)
    merged["paid_hours"] = merged["paid_hours"].astype(float).round(2)
    merged["unpaid_hours"] = merged["unpaid_hours"].astype(float).round(2)
    return merged[
        ["employee_id", "name", "total_entries", "total_hours", "paid_hours", "unpaid_hours"]
    ].sort_values("name").reset_index(drop=True)


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
        if use_mongodb():
            employee_coll, entry_coll = get_mongo_collections()
            employee_coll.delete_many({})
            entry_coll.delete_many({})
            employee_coll.insert_many(data["employees"])
            entry_coll.insert_many(data["entries"])
            fetch_recent_entries.clear()
        else:
            _write_json_file(data)
            fetch_recent_entries.clear()
    return sum(1 for entry in data["entries"] if entry["employee_id"])


def test_mongo_connection():
    if not use_mongodb():
        raise RuntimeError("MongoDB is not configured. Set MONGO_URI and MONGO_DB.")
    employee_coll, entry_coll = get_mongo_collections()
    stats = {
        "db": get_mongo_db().name,
        "employee_count": employee_coll.count_documents({}),
        "entry_count": entry_coll.count_documents({}),
    }
    stats["most_recent_entry"] = entry_coll.find_one(
        {}, {"_id": 0}, sort=[("created_at", DESCENDING)]
    )
    return stats
