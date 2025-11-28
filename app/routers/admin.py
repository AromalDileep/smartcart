# app/routers/admin.py
from fastapi import APIRouter, HTTPException
from typing import List
from datetime import datetime
import os
import psycopg2
import numpy as np

from app.db.database import get_connection
from app.services.embedding_service import CLIPEmbedder
from app.faiss_manager import FaissManager
from fastapi.responses import JSONResponse

router = APIRouter()

# ---------------------------------------
# ADMIN LOGIN (simple, no DB for now)
# ---------------------------------------
ADMIN_EMAIL = "admin@smartcart.com"
ADMIN_PASSWORD = "admin1234"
ADMIN_ID = 1  # fixed for now


@router.post("/login")
def admin_login(payload: dict):
    email = payload.get("email")
    password = payload.get("password")

    if email == ADMIN_EMAIL and password == ADMIN_PASSWORD:
        return {"admin_id": ADMIN_ID, "email": email, "status": "success"}

    raise HTTPException(status_code=401, detail="Invalid admin credentials")


# ---------------------------------------
# Global services cached
# ---------------------------------------
embedder = None
faiss_mgr = None


def ensure_services():
    global embedder, faiss_mgr
    if embedder is None:
        embedder = CLIPEmbedder()
    if faiss_mgr is None:
        faiss_mgr = FaissManager()


IMAGE_DIR = "/project_data/all_images"


# ---------------------------------------
# 1. List pending products
# ---------------------------------------
@router.get("/pending-products", response_model=List[dict])
def list_pending_products(offset: int = 0, limit: int = 20):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, title, description, price, image, status, created_at, seller_id
        FROM products
        WHERE status = 'pending'
        ORDER BY created_at ASC
        LIMIT %s OFFSET %s;
    """, (limit, offset))

    rows = cur.fetchall()
    cur.close()
    conn.close()

    items = []
    for r in rows:
        items.append({
            "id": r[0],
            "title": r[1],
            "description": r[2],
            "price": float(r[3]) if r[3] else None,
            "image": r[4],
            "status": r[5],
            "created_at": str(r[6]),
            "seller_id": r[7]
        })

    return items


# ---------------------------------------
# 2. Approve product (embed + FAISS)
# ---------------------------------------
@router.post("/approve/{product_id}")
def approve_product(product_id: int, admin_id: int = ADMIN_ID):
    ensure_services()

    # fetch product
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, image FROM products WHERE id = %s;", (product_id,))
    row = cur.fetchone()

    if not row:
        cur.close()
        conn.close()
        raise HTTPException(status_code=404, detail="Product not found")

    _, image_name = row

    if not image_name:
        cur.close()
        conn.close()
        raise HTTPException(status_code=400, detail="Product has no image")

    image_path = os.path.join(IMAGE_DIR, image_name)

    if not os.path.exists(image_path):
        cur.close()
        conn.close()
        raise HTTPException(status_code=400, detail=f"Image file missing: {image_name}")

    # ----- CLIP embedding -----
    vec = embedder.embed_image(image_path)  # numpy float32 normalized
    embedding_bytes = psycopg2.Binary(vec.tobytes())

    # ----- FAISS insert -----
    faiss_mgr.add_vector(vec, int(product_id))

    # update DB
    cur.execute("""
        UPDATE products
        SET embedding = %s, faiss_index = %s, status = %s,
            approved_by = %s, approved_at = %s
        WHERE id = %s
        RETURNING id;
    """, (
        embedding_bytes,
        product_id,
        "approved",
        admin_id,
        datetime.utcnow(),
        product_id
    ))

    _ = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()

    return {"product_id": product_id, "status": "approved"}


# ---------------------------------------
# 3. Reject product
# ---------------------------------------
@router.post("/reject/{product_id}")
def reject_product(product_id: int, admin_id: int = ADMIN_ID):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        UPDATE products
        SET status = 'rejected',
            approved_by = %s,
            approved_at = %s
        WHERE id = %s
        RETURNING id;
    """, (admin_id, datetime.utcnow(), product_id))

    updated = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()

    if not updated:
        raise HTTPException(status_code=404, detail="Product not found")

    return {"product_id": product_id, "status": "rejected"}


# ---------------------------------------
# 4. List approved products
# ---------------------------------------
@router.get("/approved-products", response_model=List[dict])
def list_approved_products(offset: int = 0, limit: int = 50):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, title, price, image, faiss_index, approved_at, seller_id
        FROM products
        WHERE status = 'approved'
        ORDER BY approved_at DESC
        LIMIT %s OFFSET %s;
    """, (limit, offset))

    rows = cur.fetchall()
    cur.close()
    conn.close()

    results = []
    for r in rows:
        results.append({
            "id": r[0],
            "title": r[1],
            "price": float(r[2]) if r[2] else None,
            "image": r[3],
            "faiss_index": r[4],
            "approved_at": str(r[5]),
            "seller_id": r[6]
        })

    return results



# ---------------------------------------
# 5. Delete product (FAISS + DB + image)
# ---------------------------------------
@router.delete("/delete/{product_id}")
def delete_product_admin(product_id: int):
    ensure_services()

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT image, faiss_index FROM products WHERE id = %s", (product_id,))
    row = cur.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Product not found")

    image_name, faiss_index = row

    # remove vector
    if faiss_index is not None:
        faiss_mgr.remove_vector(int(faiss_index))

    # delete image file
    if image_name:
        img_path = os.path.join(IMAGE_DIR, image_name)
        if os.path.exists(img_path):
            os.remove(img_path)

    # delete DB row
    cur.execute("DELETE FROM products WHERE id = %s", (product_id,))
    conn.commit()

    cur.close()
    conn.close()

    return {"status": "deleted", "product_id": product_id}


# ---------------------------------------
# 6. Rebuild FAISS index
# ---------------------------------------
@router.post("/rebuild-faiss")
def rebuild_faiss_index():
    ensure_services()

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT faiss_index, embedding
        FROM products
        WHERE status = 'approved' AND embedding IS NOT NULL;
    """)

    rows = cur.fetchall()
    cur.close()
    conn.close()

    vectors = []
    ids = []

    for row in rows:
        faiss_id, emb_bytes = row
        if faiss_id and emb_bytes:
            vec = np.frombuffer(emb_bytes, dtype="float32")
            vectors.append(vec)
            ids.append(int(faiss_id))

    faiss_mgr.rebuild(vectors, ids)

    return {"status": "faiss_rebuilt", "count": len(ids)}


# ---------------------------------------
# 7. Backup FAISS index
# ---------------------------------------
@router.post("/backup-faiss")
def backup_faiss():
    ensure_services()

    backup_path = faiss_mgr.backup_index()

    return {"status": "backup_done", "path": backup_path}
