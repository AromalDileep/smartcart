# app/routers/admin.py
from fastapi import APIRouter, HTTPException
from typing import List
from datetime import datetime
import os
import psycopg2
import numpy as np

from fastapi.responses import JSONResponse
from app.db.database import get_connection
from app.services.global_faiss import ensure_services, embedder, faiss_mgr

router = APIRouter()

ADMIN_EMAIL = "admin@smartcart.com"
ADMIN_PASSWORD = "admin1234"
ADMIN_ID = 1

IMAGE_DIR = "/project_data/all_images"


# -------------------------
# LOGIN
# -------------------------
@router.post("/login")
def admin_login(payload: dict):
    if payload.get("email") == ADMIN_EMAIL and payload.get("password") == ADMIN_PASSWORD:
        return {"admin_id": ADMIN_ID, "email": ADMIN_EMAIL, "status": "success"}
    raise HTTPException(status_code=401, detail="Invalid admin credentials")


# -------------------------
# 1. Pending products
# -------------------------
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

    return [
        {
            "id": r[0],
            "title": r[1],
            "description": r[2],
            "price": float(r[3]) if r[3] else None,
            "image": r[4],
            "status": r[5],
            "created_at": str(r[6]),
            "seller_id": r[7]
        }
        for r in rows
    ]


# -------------------------
# 2. Approve Product
# -------------------------
@router.post("/approve/{product_id}")
def approve_product(product_id: int, admin_id: int = ADMIN_ID):
    embedder, faiss_mgr = ensure_services()

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT id, image FROM products WHERE id = %s;", (product_id,))
    row = cur.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Product not found")

    _, image_name = row

    image_path = os.path.join(IMAGE_DIR, image_name)
    if not os.path.exists(image_path):
        raise HTTPException(status_code=400, detail=f"Image file missing: {image_name}")

    # embed
    vec = embedder.embed_image(image_path)
    emb_bytes = psycopg2.Binary(vec.tobytes())

    # add to FAISS
    faiss_mgr.add_vector(vec, product_id)

    cur.execute("""
        UPDATE products
        SET embedding = %s,
            faiss_index = %s,
            status = 'approved',
            approved_by = %s,
            approved_at = %s
        WHERE id = %s;
    """, (emb_bytes, product_id, admin_id, datetime.utcnow(), product_id))

    conn.commit()
    cur.close()
    conn.close()

    return {"product_id": product_id, "status": "approved"}


# -------------------------
# 3. Reject Product
# -------------------------
@router.post("/reject/{product_id}")
def reject_product(product_id: int, admin_id: int = ADMIN_ID):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        UPDATE products
        SET status = 'rejected',
            approved_by = %s,
            approved_at = %s
        WHERE id = %s;
    """, (admin_id, datetime.utcnow(), product_id))

    if cur.rowcount == 0:
        raise HTTPException(status_code=404, detail="Product not found")

    conn.commit()
    cur.close()
    conn.close()

    return {"product_id": product_id, "status": "rejected"}


# -------------------------
# 4. Approved Products
# -------------------------
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

    return [
        {
            "id": r[0],
            "title": r[1],
            "price": float(r[2]) if r[2] else None,
            "image": r[3],
            "faiss_index": r[4],
            "approved_at": str(r[5]),
            "seller_id": r[6]
        }
        for r in rows
    ]


# -------------------------
# 5. Delete Product
# -------------------------
@router.delete("/delete/{product_id}")
def delete_product_admin(product_id: int):
    embedder, faiss_mgr = ensure_services()

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT image, faiss_index FROM products WHERE id = %s;", (product_id,))
    row = cur.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Product not found")

    image_name, faiss_index = row

    # remove from FAISS
    if faiss_index is not None:
        faiss_mgr.remove_vector(faiss_index)

    # remove image
    if image_name:
        img_path = os.path.join(IMAGE_DIR, image_name)
        if os.path.exists(img_path):
            os.remove(img_path)

    # delete row
    cur.execute("DELETE FROM products WHERE id = %s;", (product_id,))
    conn.commit()

    cur.close()
    conn.close()

    return {"status": "deleted", "product_id": product_id}


# -------------------------
# 6. Rebuild FAISS
# -------------------------
@router.post("/rebuild-faiss")
def rebuild_faiss_index():
    embedder, faiss_mgr = ensure_services()

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT faiss_index, embedding
        FROM products
        WHERE status='approved' AND embedding IS NOT NULL;
    """)

    rows = cur.fetchall()
    cur.close()
    conn.close()

    vectors = []
    ids = []

    for faiss_id, emb_bytes in rows:
        if faiss_id and emb_bytes:
            vec = np.frombuffer(emb_bytes, dtype="float32")
            vectors.append(vec)
            ids.append(faiss_id)

    faiss_mgr.rebuild(vectors, ids)

    return {"status": "faiss_rebuilt", "count": len(ids)}


# -------------------------
# 7. Backup FAISS
# -------------------------
@router.post("/backup-faiss")
def backup_faiss():
    embedder, faiss_mgr = ensure_services()

    path = faiss_mgr.backup_index()
    return {"status": "backup_done", "path": path}


# -------------------------
# 8. FAISS Stats
# -------------------------
@router.get("/faiss-stats")
def faiss_stats():
    embedder, faiss_mgr = ensure_services()

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM products;")
    total = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM products WHERE status='approved';")
    approved = cur.fetchone()[0]

    faiss_vectors = faiss_mgr.index.ntotal

    cur.close()
    conn.close()

    return { 
        "total_products": total,
        "approved_products": approved,
        "faiss_vectors": faiss_vectors
    }
