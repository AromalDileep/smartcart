# app/utils/db_sequence_fix.py

import os

import psycopg2

def fix_product_id_sequence():
    try:
        conn = psycopg2.connect(
            host=os.getenv("POSTGRES_HOST", "db"),
            database=os.getenv("POSTGRES_DB", "smartcartdb_v2"),
            user=os.getenv("POSTGRES_USER", "postgres"),
            password=os.getenv("POSTGRES_PASSWORD", "lottery1234"),
        )
        cur = conn.cursor()

        # Get max product id
        cur.execute("SELECT COALESCE(MAX(id), 0) FROM products;")
        max_id = cur.fetchone()[0]

        # Reset sequence to max_id + 1
        cur.execute(
            "SELECT setval('products_id_seq', %s, false);",
            (max_id + 1,)
        )

        conn.commit()
        cur.close()
        conn.close()

        print(f"[DB SEQ FIX] products_id_seq reset to {max_id + 1}")

    except Exception as e:
        print("[DB SEQ FIX] Failed to fix sequence:", e)
