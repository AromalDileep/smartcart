import os
import numpy as np
import torch
from PIL import Image

from fastapi import HTTPException
from app.faiss_manager import FaissManager
from app.services.embedding_service import CLIPEmbedder
# change to import the DB function that actually exists in your repo
from app.db.models import get_db_connection

# constants (keep consistent with your mounting)
IMAGE_DIR = "/project_data/all_images"
BASE_URL = "http://localhost:8000/images/"

embedder = None
faiss_mgr = None


# -------------------------------------------------------
# INITIALIZE SERVICES SAFELY
# -------------------------------------------------------
def ensure_services():
    global embedder, faiss_mgr
    if embedder is None:
        embedder = CLIPEmbedder()
    if faiss_mgr is None:
        faiss_mgr = FaissManager()


# -------------------------------------------------------
# IMAGE SEARCH
# -------------------------------------------------------
def search_by_image(image_file_bytes, top_k=10):
    ensure_services()

    # write bytes to temp file
    temp_path = "/tmp/search_image.jpg"
    with open(temp_path, "wb") as f:
        f.write(image_file_bytes)

    # embed_image returns 1-d (512,) vector (float32)
    vec = embedder.embed_image(temp_path)  # shape (512,)
    # ensure shape is (1,512) for FAISS
    query_vec = np.asarray(vec, dtype="float32").reshape(1, -1)

    ids, scores = faiss_mgr.search(query_vec, top_k)
    return format_results(ids, scores)


# -------------------------------------------------------
# TEXT SEARCH
# -------------------------------------------------------
def search_by_text(query: str, top_k=10):
    ensure_services()

    inputs = embedder.processor(
        text=[query],
        return_tensors="pt",
        padding=True,
        truncation=True,
        max_length=77
    ).to(embedder.device)

    with torch.no_grad():
        txt = embedder.model.get_text_features(**inputs)

    txt = txt / txt.norm(dim=-1, keepdim=True)
    txt = txt.cpu().numpy().astype("float32")  # shape (1, 512)

    ids, scores = faiss_mgr.search(txt, top_k)
    return format_results(ids, scores)


# -------------------------------------------------------
# HYBRID SEARCH (robust: allow only-image, only-text, or both)
# -------------------------------------------------------
def search_hybrid(image_bytes, text_query, w_image=0.5, w_text=0.5, top_k=10):
    ensure_services()

    if (not image_bytes) and (not text_query):
        raise HTTPException(status_code=400, detail="Provide at least image or text for hybrid search")

    # normalize weights if they don't sum to 1
    w_image = float(w_image)
    w_text = float(w_text)
    s = w_image + w_text
    if s <= 0.0:
        raise HTTPException(status_code=400, detail="Invalid weights (sum must be > 0)")
    w_image /= s
    w_text /= s

    parts = []

    # image part
    if image_bytes:
        tmp = "/tmp/hybrid_img.jpg"
        with open(tmp, "wb") as f:
            f.write(image_bytes)
        img_vec = embedder.embed_image(tmp)  # shape (512,)
        img_vec = np.asarray(img_vec, dtype="float32").reshape(1, -1)  # (1,512)
        parts.append((w_image, img_vec))

    # text part
    if text_query:
        inputs = embedder.processor(
            text=[text_query],
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=77
        ).to(embedder.device)

        with torch.no_grad():
            txt_vec = embedder.model.get_text_features(**inputs)  # tensor (1,512)

        txt_vec = txt_vec / txt_vec.norm(dim=-1, keepdim=True)
        txt_vec = txt_vec.cpu().numpy().astype("float32").reshape(1, -1)  # (1,512)
        parts.append((w_text, txt_vec))

    # combine — both parts are (1,512); weight and sum
    # start with zeros
    combined = np.zeros_like(parts[0][1], dtype="float32")
    for w, v in parts:
        combined += w * v

    # final normalization
    norm = np.linalg.norm(combined, axis=1, keepdims=True)
    norm[norm == 0] = 1.0
    combined = combined / norm

    ids, scores = faiss_mgr.search(combined.astype("float32"), top_k)
    return format_results(ids, scores)


# -------------------------------------------------------
# FORMAT RESULTS
# -------------------------------------------------------
def format_results(ids, scores):
    conn = get_db_connection()
    cur = conn.cursor()

    results = []
    for fid, dist in zip(ids, scores):
        if fid == -1:
            continue

        cur.execute("""
            SELECT id, faiss_index, title, price, image, description
            FROM products
            WHERE faiss_index = %s
        """, (int(fid),))

        row = cur.fetchone()
        if not row:
            continue

        prod_id, faiss_index, title, price, image, description = row

        image_url = BASE_URL + image if image else None

        results.append({
            "id": prod_id,
            "faiss_index": faiss_index,
            "title": title,
            "price": float(price) if price else None,
            "description": description,
            "image_url": image_url,
            "distance": float(dist)
        })

    cur.close()
    conn.close()
    return results
