# app/routers/admin.py
import os
from datetime import datetime
from typing import List

import numpy as np
import psycopg2
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.db.database import get_connection
from app.services.global_faiss import ensure_services, embedder, faiss_mgr

router = APIRouter()

ADMIN_EMAIL = settings.ADMIN_EMAIL
ADMIN_PASSWORD = settings.ADMIN_PASSWORD
ADMIN_ID = settings.ADMIN_ID

IMAGE_DIR = settings.IMAGE_DIR


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
# 2.5. Approve ALL Products (Train All)
# -------------------------
@router.post("/approve-all")
def approve_all_products(admin_id: int = ADMIN_ID):
    embedder, faiss_mgr = ensure_services()

    conn = get_connection()
    cur = conn.cursor()

    # Get all pending products
    cur.execute("SELECT id, image FROM products WHERE status = 'pending';")
    rows = cur.fetchall()

    if not rows:
        cur.close()
        conn.close()
        return {"count": 0, "status": "no_pending_products"}

    processed_count = 0
    
    for row in rows:
        product_id, image_name = row
        
        image_path = os.path.join(IMAGE_DIR, image_name)
        if not os.path.exists(image_path):
            # Skip if image missing, or maybe log it? For now just skip
            continue

        try:
            # embed
            vec = embedder.embed_image(image_path)
            emb_bytes = psycopg2.Binary(vec.tobytes())

            # add to FAISS
            faiss_mgr.add_vector(vec, product_id)

            # update DB
            cur.execute("""
                UPDATE products
                SET embedding = %s,
                    faiss_index = %s,
                    status = 'approved',
                    approved_by = %s,
                    approved_at = %s
                WHERE id = %s;
            """, (emb_bytes, product_id, admin_id, datetime.utcnow(), product_id))
            
            processed_count += 1
        except Exception as e:
            print(f"Error processing product {product_id}: {e}")
            # Continue with next product even if one fails
            continue

    conn.commit()
    cur.close()
    conn.close()

    return {"count": processed_count, "status": "approved_all"}


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
# 5.5. List Deleted Products
# -------------------------
@router.get("/deleted-products", response_model=List[dict])
def list_deleted_products(offset: int = 0, limit: int = 20):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, title, description, price, image, status, created_at, seller_id
        FROM products
        WHERE status = 'deleted'
        ORDER BY created_at DESC
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
# 5.6. Permanently Delete Product
# -------------------------
@router.delete("/permanent-delete/{product_id}")
def permanent_delete_product(product_id: int):
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

    return {"status": "permanently_deleted", "product_id": product_id}


@router.delete("/permanent-delete-all")
def permanent_delete_all_deleted_products():
    embedder, faiss_mgr = ensure_services()

    conn = get_connection()
    cur = conn.cursor()

    # 1. Get all deleted products
    cur.execute("SELECT id, image, faiss_index FROM products WHERE status = 'deleted';")
    rows = cur.fetchall()

    if not rows:
        cur.close()
        conn.close()
        return {"status": "no_deleted_products", "count": 0}

    count = 0
    for row in rows:
        pid, image_name, faiss_index = row

        # remove from FAISS
        if faiss_index is not None:
            faiss_mgr.remove_vector(faiss_index)

        # remove image
        if image_name:
            img_path = os.path.join(IMAGE_DIR, image_name)
            if os.path.exists(img_path):
                try:
                    os.remove(img_path)
                except:
                    pass

        # delete row
        cur.execute("DELETE FROM products WHERE id = %s;", (pid,))
        count += 1

    conn.commit()
    cur.close()
    conn.close()

    return {"status": "all_permanently_deleted", "count": count}


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
        if faiss_id is not None and emb_bytes:
            vec = np.frombuffer(emb_bytes, dtype="float32")
            vectors.append(vec)
            ids.append(faiss_id)
        else:
            print(f"SKIPPING: faiss_id={faiss_id}, emb_bytes_len={len(emb_bytes) if emb_bytes else 0}")

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


# -------------------------
# 9. Orphan Images
# -------------------------
@router.get("/orphan-images", response_model=List[str])
def list_orphan_images():
    # 1. Get all files in IMAGE_DIR
    try:
        all_files = set(os.listdir(IMAGE_DIR))
    except FileNotFoundError:
        return []

    # 2. Get all used images from DB
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT image FROM products WHERE image IS NOT NULL;")
    rows = cur.fetchall()
    cur.close()
    conn.close()

    used_images = set(r[0] for r in rows)

    # 3. Find orphans
    orphans = list(all_files - used_images)
    return sorted(orphans)


@router.delete("/orphan-images/{filename}")
def delete_orphan_image(filename: str):
    # Security check: prevent directory traversal
    if ".." in filename or "/" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    file_path = os.path.join(IMAGE_DIR, filename)
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    # Double check it's not in DB (race condition safety)
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM products WHERE image = %s;", (filename,))
    exists = cur.fetchone()
    cur.close()
    conn.close()

    if exists:
        raise HTTPException(status_code=400, detail="Image is currently in use")

    try:
        os.remove(file_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete: {e}")

    return {"status": "deleted", "filename": filename}


@router.delete("/orphan-images-all")
def delete_all_orphan_images():
    orphans = list_orphan_images()
    count = 0
    errors = []

    for filename in orphans:
        file_path = os.path.join(IMAGE_DIR, filename)
        try:
            os.remove(file_path)
            count += 1
        except Exception as e:
            errors.append(f"{filename}: {e}")

    return {"status": "cleaned", "deleted_count": count, "errors": errors}
