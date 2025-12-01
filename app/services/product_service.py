# app/services/product_service.py
from typing import Optional, List, Dict
from app.schemas.product_schema import ProductCreate, ProductUpdate
from app.db.database import get_connection
import psycopg2
from psycopg2.extras import RealDictCursor

FAISS_INDEX_POS = None


# -----------------------------------
# CREATE PRODUCT
# -----------------------------------
def create_product(product: ProductCreate, seller_id: int) -> int:
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO products 
        (seller_id, title, description, price, image, status, main_category, categories, features, details, product_url, context)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id;
    """, (
        seller_id,
        product.title,
        product.description,
        product.price,
        product.image,
        "pending",
        product.main_category,
        product.categories,
        product.features,
        product.details,
        product.product_url,
        getattr(product, "context", None)
    ))

    new_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    return new_id


# -----------------------------------
# GET PRODUCT BY ID
# REMOVE NON-JSON FIELDS (embedding)
# -----------------------------------
def get_product(product_id: int) -> Optional[Dict]:
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("SELECT * FROM products WHERE id = %s;", (product_id,))
    row = cur.fetchone()

    cur.close()
    conn.close()

    if not row:
        return None

    row = dict(row)

    # IMPORTANT FIX
    row.pop("embedding", None)

    return row


# -----------------------------------
# GET PRODUCTS BY SELLER
# (no embedding here, so OK)
# -----------------------------------
def get_products_by_seller(seller_id: int) -> List[Dict]:
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("""
        SELECT id, seller_id, title, description, price, image, status,
               faiss_index, created_at, main_category, categories, average_rating
        FROM products
        WHERE seller_id = %s
        ORDER BY id DESC;
    """, (seller_id,))

    rows = cur.fetchall()
    cur.close()
    conn.close()

    clean_rows = []
    for r in rows:
        r = dict(r)
        r.pop("embedding", None)  # extra safety
        clean_rows.append(r)

    return clean_rows


# -----------------------------------
# GET ALL PRODUCTS
# -----------------------------------
def get_all_products() -> List:
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT * FROM products ORDER BY id ASC;")
    rows = cur.fetchall()

    cur.close()
    conn.close()
    return rows


# -----------------------------------
# UPDATE PRODUCT
# -----------------------------------
def update_product(product_id: int, product: ProductUpdate) -> bool:
    conn = get_connection()
    cur = conn.cursor()

    updates = []
    values = []

    fields = {
        "title": product.title,
        "description": product.description,
        "price": product.price,
        "image": product.image,
        "main_category": product.main_category,
        "categories": product.categories,
        "features": product.features,
        "details": product.details,
        "product_url": product.product_url,
        "context": getattr(product, "context", None),
        "status": product.status
    }

    for key, value in fields.items():
        if value is not None:
            updates.append(f"{key} = %s")
            values.append(value)

    if not updates:
        cur.close()
        conn.close()
        return False

    values.append(product_id)
    query = f"UPDATE products SET {', '.join(updates)} WHERE id = %s;"
    cur.execute(query, tuple(values))

    conn.commit()
    cur.close()
    conn.close()
    return True


# -----------------------------------
# DELETE PRODUCT
# -----------------------------------
def delete_product(product_id: int) -> bool:
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT image FROM products WHERE id = %s;", (product_id,))
    _ = cur.fetchone()

    cur.execute("DELETE FROM products WHERE id = %s;", (product_id,))
    conn.commit()

    cur.close()
    conn.close()
    return True
