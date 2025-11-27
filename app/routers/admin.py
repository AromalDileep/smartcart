# app/routers/admin.py
from fastapi import APIRouter, HTTPException
from typing import List
from datetime import datetime
import os
import psycopg2
from app.db.database import get_connection
from app.services.embedding_service import CLIPEmbedder
from app.faiss_manager import FaissManager
import numpy as np

router = APIRouter()
embedder = None
faiss_mgr = None

def ensure_services():
    global embedder, faiss_mgr
    if embedder is None:
        embedder = CLIPEmbedder()
    if faiss_mgr is None:
        faiss_mgr = FaissManager()

@router.get("/pending-products", response_model=List[dict])
def list_pending():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM products WHERE status = 'pending' ORDER BY created_at ASC LIMIT 200;")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    items = []
    for r in rows:
        items.append({
            "id": r[0],
            "title": r[1],
            "description": r[2],
            "price": r[3],
            "image": r[4],
            "faiss_index": r[5],
            "status": r[7],
            "created_at": r[8],
            "main_category": r[9],
            "categories": r[10],
            "features": r[11],
            "details": r[12],
            "product_url": r[13]
        })
    return items

@router.post("/approve/{product_id}", response_model=dict)
def approve_product(product_id: int, admin_id: int = 1):
    """
    Approve a product: compute CLIP embedding (image), add to FAISS, update DB.
    admin_id optional (who approved).
    """
    ensure_services()

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

    image_path = os.path.join("/project_data/all_images", image_name)
    if not os.path.exists(image_path):
        cur.close()
        conn.close()
        raise HTTPException(status_code=400, detail=f"Image file not found: {image_name}")

    # compute embedding
    vec = embedder.embed_image(image_path)  # numpy float32 normalized

    # add to faiss using product_id as id
    faiss_mgr.add_vector(vec, int(product_id))

    # store embedding bytes in DB and update faiss_index, status, approved_by, approved_at
    embedding_bytes = psycopg2.Binary(vec.tobytes())

    cur.execute("""
        UPDATE products 
        SET embedding = %s, faiss_index = %s, status = %s, approved_by = %s, approved_at = %s
        WHERE id = %s
        RETURNING id;
    """, (embedding_bytes, int(product_id), "approved", int(admin_id), datetime.utcnow(), int(product_id)))

    updated_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()

    return {"id": updated_id, "faiss_index": int(product_id), "status": "approved"}
