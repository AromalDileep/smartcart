# app/routers/admin.py
import os
import tempfile
from datetime import datetime
from typing import List

import numpy as np
import psycopg2
from fastapi import APIRouter, HTTPException

import boto3
from botocore.exceptions import BotoCoreError, NoCredentialsError

from app.core.config import settings
from app.db.database import get_connection
from app.services.global_faiss import ensure_services

router = APIRouter()

ADMIN_EMAIL = settings.ADMIN_EMAIL
ADMIN_PASSWORD = settings.ADMIN_PASSWORD
ADMIN_ID = settings.ADMIN_ID

IMAGE_DIR = settings.IMAGE_DIR


# Utility: Download image from S3 → temporary file
def download_from_s3(image_name: str) -> str:
    """
    Downloads an image from S3 and returns a temp file path.
    """

    s3_key = f"all_images/{image_name}"       # <-- FIXED HERE

    s3 = boto3.client(
        "s3",
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_REGION,
    )

    try:
        suffix = os.path.splitext(image_name)[1]
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        s3.download_fileobj(settings.S3_BUCKET_NAME, s3_key, tmp)
        tmp.flush()
        tmp.close()
        return tmp.name
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to download {image_name} from S3: {e}"
        )


# Utility: Delete object from S3
def delete_from_s3(image_name: str):
    s3_key = f"all_images/{image_name}"       # <-- FIXED HERE

    s3 = boto3.client(
        "s3",
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_REGION,
    )

    try:
        s3.delete_object(Bucket=settings.S3_BUCKET_NAME, Key=s3_key)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete {image_name} from S3: {e}"
        )


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
            "seller_id": r[7],
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

    # Get image path (local or cloud)
    if settings.USE_CLOUD:
        image_path = download_from_s3(image_name)
    else:
        image_path = os.path.join(IMAGE_DIR, image_name)
        if not os.path.exists(image_path):
            raise HTTPException(status_code=400, detail=f"Image missing: {image_name}")

    try:
        vec = embedder.embed_image(image_path)
    finally:
        if settings.USE_CLOUD and os.path.exists(image_path):
            os.remove(image_path)  # cleanup temp file

    emb_bytes = psycopg2.Binary(vec.tobytes())

    # update DB + FAISS
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
# 2.5 Approve ALL Products
# -------------------------
@router.post("/approve-all")
def approve_all_products(admin_id: int = ADMIN_ID):
    embedder, faiss_mgr = ensure_services()

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT id, image FROM products WHERE status = 'pending';")
    rows = cur.fetchall()

    if not rows:
        cur.close()
        conn.close()
        return {"count": 0, "status": "no_pending_products"}

    processed = 0

    for product_id, image_name in rows:

        # Get correct image path
        if settings.USE_CLOUD:
            image_path = download_from_s3(image_name)
        else:
            image_path = os.path.join(IMAGE_DIR, image_name)
            if not os.path.exists(image_path):
                continue

        try:
            vec = embedder.embed_image(image_path)
        except Exception as e:
            print(f"Error embedding product {product_id}: {e}")
            continue
        finally:
            if settings.USE_CLOUD and os.path.exists(image_path):
                os.remove(image_path)

        emb_bytes = psycopg2.Binary(vec.tobytes())
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

        processed += 1

    conn.commit()
    cur.close()
    conn.close()

    return {"count": processed, "status": "approved_all"}


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
            "seller_id": r[6],
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

    # FAISS remove
    if faiss_index is not None:
        faiss_mgr.remove_vector(faiss_index)

    # Delete image from local or S3
    if image_name:
        if settings.USE_CLOUD:
            delete_from_s3(image_name)
        else:
            img_path = os.path.join(IMAGE_DIR, image_name)
            if os.path.exists(img_path):
                os.remove(img_path)

    cur.execute("DELETE FROM products WHERE id = %s;", (product_id,))
    conn.commit()

    cur.close()
    conn.close()

    return {"status": "deleted", "product_id": product_id}


# -------------------------
# 5.5 List Deleted Products
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
            "seller_id": r[7],
        }
        for r in rows
    ]


# -------------------------
# 5.6 Permanent Delete Product
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

    if faiss_index is not None:
        faiss_mgr.remove_vector(faiss_index)

    if image_name:
        if settings.USE_CLOUD:
            delete_from_s3(image_name)
        else:
            img_path = os.path.join(IMAGE_DIR, image_name)
            if os.path.exists(img_path):
                os.remove(img_path)

    cur.execute("DELETE FROM products WHERE id = %s;", (product_id,))
    conn.commit()

    cur.close()
    conn.close()

    return {"status": "permanently_deleted", "product_id": product_id}


# -------------------------
# Delete all deleted products
# -------------------------
@router.delete("/permanent-delete-all")
def permanent_delete_all_deleted_products():
    embedder, faiss_mgr = ensure_services()

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT id, image, faiss_index FROM products WHERE status = 'deleted';")
    rows = cur.fetchall()

    if not rows:
        cur.close()
        conn.close()
        return {"status": "no_deleted_products", "count": 0}

    count = 0

    for pid, image_name, faiss_index in rows:
        if faiss_index is not None:
            faiss_mgr.remove_vector(faiss_index)

        if image_name:
            if settings.USE_CLOUD:
                delete_from_s3(image_name)
            else:
                img_path = os.path.join(IMAGE_DIR, image_name)
                if os.path.exists(img_path):
                    os.remove(img_path)

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
        "faiss_vectors": faiss_vectors,
    }


# -------------------------
# 9. Orphan Images (Cloud-compatible)
# -------------------------
@router.get("/orphan-images", response_model=List[str])
def list_orphan_images():
    # 1. List images from S3 or local
    if settings.USE_CLOUD:
        s3 = boto3.client(
            "s3",
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION,
        )

        paginator = s3.get_paginator("list_objects_v2")
        files = []

        for page in paginator.paginate(Bucket=settings.S3_BUCKET_NAME):
            for obj in page.get("Contents", []):
                key = obj["Key"]
                if not key.endswith("/"):
                    files.append(key.replace("all_images/", ""))  # FIX: remove prefix

        all_files = set(files)

    else:
        try:
            all_files = set(os.listdir(IMAGE_DIR))
        except FileNotFoundError:
            return []

    # 2. DB used images
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT image FROM products WHERE image IS NOT NULL;")
    used = set([r[0] for r in cur.fetchall()])
    cur.close()
    conn.close()

    return sorted(list(all_files - used))


@router.delete("/orphan-images/{filename}")
def delete_orphan_image(filename: str):
    # Protect from directory traversal
    if ".." in filename or "/" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    # Check DB use
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM products WHERE image = %s;", (filename,))
    exists = cur.fetchone()
    cur.close()
    conn.close()

    if exists:
        raise HTTPException(status_code=400, detail="Image currently in use")

    # Delete from S3 or local
    if settings.USE_CLOUD:
        delete_from_s3(filename)
    else:
        file_path = os.path.join(IMAGE_DIR, filename)
        if os.path.exists(file_path):
            os.remove(file_path)
        else:
            raise HTTPException(status_code=404, detail="File not found")

    return {"status": "deleted", "filename": filename}


@router.delete("/orphan-images-all")
def delete_all_orphan_images():
    orphans = list_orphan_images()
    errors = []
    count = 0

    for filename in orphans:
        try:
            if settings.USE_CLOUD:
                delete_from_s3(filename)
            else:
                path = os.path.join(IMAGE_DIR, filename)
                if os.path.exists(path):
                    os.remove(path)
            count += 1
        except Exception as e:
            errors.append(f"{filename}: {e}")

    return {"status": "cleaned", "deleted_count": count, "errors": errors}
