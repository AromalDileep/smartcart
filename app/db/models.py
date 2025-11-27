# app/db/models.py
import psycopg2
from psycopg2.extras import RealDictCursor
import os

def get_db_connection():
    conn = psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "db"),
        database=os.getenv("POSTGRES_DB", "smartcartdb_v2"),
        user=os.getenv("POSTGRES_USER", "postgres"),
        password=os.getenv("POSTGRES_PASSWORD", "lottery1234")
    )
    return conn

def create_products_table():
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
        status VARCHAR(20) DEFAULT 'pending',   -- pending, approved, rejected
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    
    conn.commit()
    cur.close()
    conn.close()
