"""Database connection module for Snowflake integration."""
import streamlit as st
import snowflake.connector
from cryptography.hazmat.primitives import serialization


@st.cache_resource
def get_connection():
    """
    Create and cache a Snowflake database connection.
    Uses credentials from st.secrets configuration.
    """
    # Get the private key - try from secrets first, fall back to file
    try:
        private_key_str = st.secrets["snowflake"]["private_key"]
    except:
        # For local development, read from file
        with open("rsa_key.p8", "r") as f:
            private_key_str = f.read()
    
    p_key = serialization.load_pem_private_key(
        private_key_str.encode(),
        password=None,
    )
    pkb = p_key.private_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    return snowflake.connector.connect(
        account=st.secrets["snowflake"]["account"],
        user=st.secrets["snowflake"]["user"],
        private_key=pkb,
        warehouse=st.secrets["snowflake"]["warehouse"],
        database="TIMESHEET_DB",
        schema="PUBLIC",
    )


def insert_timesheet_entry(entry_date, hours_worked, employee_name, project_name):
    """Insert a timesheet entry into the database."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO TIMESHEET_DB.PUBLIC.TIMESHEET_ENTRIES "
        "(ENTRY_DATE, HOURS_WORKED, EMPLOYEE_NAME, PROJECT_NAME) "
        "VALUES (%s, %s, %s, %s)",
        (entry_date.isoformat(), hours_worked, employee_name, project_name),
    )
    conn.commit()
    cur.close()


def fetch_recent_entries(limit=50):
    """Fetch recent timesheet entries from the database."""
    cur = get_connection().cursor()
    cur.execute(
        "SELECT ENTRY_DATE, HOURS_WORKED, EMPLOYEE_NAME, PROJECT_NAME, CREATED_AT "
        "FROM TIMESHEET_DB.PUBLIC.TIMESHEET_ENTRIES "
        "ORDER BY CREATED_AT DESC LIMIT %s",
        (limit,),
    )
    df = cur.fetch_pandas_all()
    cur.close()
    return df
