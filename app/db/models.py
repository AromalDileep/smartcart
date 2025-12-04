# app/db/models.py

import os
import time
import psycopg2
from app.core.config import settings



def get_db_connection():
    """Connect to PostgreSQL with retry logic."""
    retries = 10
    for attempt in range(retries):
        try:
            conn = psycopg2.connect(
                host=settings.POSTGRES_HOST,
                database=settings.POSTGRES_DB,
                user=settings.POSTGRES_USER,
                password=settings.POSTGRES_PASSWORD
            )
            return conn
        except Exception as e:
            print(f"[DB] Connection failed ({attempt+1}/{retries}). Retrying in 3 seconds...")
            print("Error:", e)
            time.sleep(3)

    raise Exception("Failed to connect to PostgreSQL after multiple attempts.")


def create_products_table():
    """Create products table if it doesn't exist."""
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS products (
        id SERIAL PRIMARY KEY,
        title TEXT,
        description TEXT,
        price NUMERIC,
        image TEXT,
        faiss_index INTEGER UNIQUE,
        embedding BYTEA,
        status VARCHAR(20) DEFAULT 'pending',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        main_category TEXT,
        categories TEXT,
        average_rating NUMERIC,
        features TEXT,
        details TEXT,
        product_url TEXT,
        context TEXT,
        seller_id INTEGER,
        approved_by INTEGER,
        approved_at TIMESTAMP
    );
    """)

    conn.commit()
    cur.close()
    conn.close()


def create_sellers_table():
    """Create sellers table if it doesn't exist."""
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS sellers (
        id SERIAL PRIMARY KEY,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        name TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    conn.commit()
    cur.close()
    conn.close()
