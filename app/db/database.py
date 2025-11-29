# app/db/database.py

import os
import time
import psycopg2

def get_connection():
    """Connect to PostgreSQL with retry logic."""
    retries = 10
    for attempt in range(retries):
        try:
            conn = psycopg2.connect(
                host=os.getenv("POSTGRES_HOST", "db"),
                database=os.getenv("POSTGRES_DB", "smartcartdb_v2"),
                user=os.getenv("POSTGRES_USER", "postgres"),
                password=os.getenv("POSTGRES_PASSWORD", "lottery1234")
            )
            return conn
        except Exception as e:
            print(f"[DB] Connection failed ({attempt+1}/10). Retrying...")
            print("Error:", e)
            time.sleep(3)

    raise Exception("Failed to connect to PostgreSQL after multiple attempts.")
