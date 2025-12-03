# app/db/database.py

import time
import psycopg2
from app.core.config import settings

def get_connection():
    """Connect to PostgreSQL with retry logic."""
    retries = settings.DB_RETRIES
    for attempt in range(retries):
        try:
            conn = psycopg2.connect(
                host=settings.POSTGRES_HOST,
                database=settings.POSTGRES_DB,
                user=settings.POSTGRES_USER,
                password=settings.POSTGRES_PASSWORD,
                port=settings.POSTGRES_PORT
            )
            return conn
        except Exception as e:
            print(f"[DB] Connection failed ({attempt+1}/{retries}). Retrying...")
            print("Error:", e)
            time.sleep(settings.DB_RETRY_DELAY)

    raise Exception("Failed to connect to PostgreSQL after multiple attempts.")

