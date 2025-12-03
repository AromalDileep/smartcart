
import numpy as np
import torch
from fastapi import HTTPException

from app.core.config import settings

# Use global FAISS + CLIP (shared across app)
from app.services.global_faiss import ensure_services

# Correct database import
from app.db.database import get_connection

IMAGE_DIR = settings.IMAGE_DIR
BASE_URL = settings.BASE_URL


# -------------------------------------------------------
# IMAGE SEARCH
# -------------------------------------------------------
def search_by_image(image_file_bytes, top_k=10):
    embedder, faiss_mgr = ensure_services()

    temp_path = settings.TEMP_IMAGE_PATH
    with open(temp_path, "wb") as f:
        f.write(image_file_bytes)

    vec = embedder.embed_image(temp_path)
    query_vec = np.asarray(vec, dtype="float32").reshape(1, -1)

    ids, scores = faiss_mgr.search(query_vec, top_k)
    return format_results(ids, scores)


# -------------------------------------------------------
# TEXT SEARCH
# -------------------------------------------------------
def search_by_text(query: str, top_k=10):
    embedder, faiss_mgr = ensure_services()

    inputs = embedder.processor(
        text=[query],
        return_tensors="pt",
        padding=True,
        truncation=True,
        max_length=settings.MAX_TEXT_LENGTH
    ).to(embedder.device)

    with torch.no_grad():
        txt = embedder.model.get_text_features(**inputs)

    txt = txt / txt.norm(dim=-1, keepdim=True)
    txt_vec = txt.cpu().numpy().astype("float32").reshape(1, -1)

    ids, scores = faiss_mgr.search(txt_vec, top_k)
    return format_results(ids, scores)


# -------------------------------------------------------
# HYBRID SEARCH
# -------------------------------------------------------
def search_hybrid(image_bytes, text_query, w_image=0.5, w_text=0.5, top_k=10):
    embedder, faiss_mgr = ensure_services()

    if not image_bytes and not text_query:
        raise HTTPException(status_code=400, detail="Provide at least image or text")

    w_image = float(w_image)
    w_text = float(w_text)
    s = w_image + w_text
    if s <= 0:
        raise HTTPException(status_code=400, detail="Invalid weights")

    w_image /= s
    w_text /= s

    parts = []

    # Image embedding
    if image_bytes:
        tmp = settings.TEMP_HYBRID_IMAGE_PATH
        with open(tmp, "wb") as f:
            f.write(image_bytes)
        img_vec = embedder.embed_image(tmp)
        img_vec = np.asarray(img_vec, dtype="float32").reshape(1, -1)
        parts.append((w_image, img_vec))

    # Text embedding
    if text_query:
        inputs = embedder.processor(
            text=[text_query],
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=settings.MAX_TEXT_LENGTH
        ).to(embedder.device)

        with torch.no_grad():
            txt = embedder.model.get_text_features(**inputs)

        txt = txt / txt.norm(dim=-1, keepdim=True)
        txt_vec = txt.cpu().numpy().astype("float32").reshape(1, -1)
        parts.append((w_text, txt_vec))

    combined = np.zeros_like(parts[0][1], dtype="float32")
    for w, v in parts:
        combined += w * v

    norm = np.linalg.norm(combined, axis=1, keepdims=True)
    if norm[0] == 0:
        norm[0] = 1
    combined = combined / norm

    ids, scores = faiss_mgr.search(combined.astype("float32"), top_k)
    return format_results(ids, scores)


# -------------------------------------------------------
# FORMAT RESULTS
# -------------------------------------------------------
def format_results(ids, scores):
    conn = get_connection()
    cur = conn.cursor()

    results = []

    for fid, dist in zip(ids, scores):
        if fid == -1:
            continue

        cur.execute("""
            SELECT id, faiss_index, title, price, image, description, product_url
            FROM products
            WHERE faiss_index = %s;
        """, (int(fid),))

        row = cur.fetchone()
        if not row:
            continue

        prod_id, faiss_index, title, price, image, description, product_url = row

        results.append({
            "id": prod_id,
            "faiss_index": faiss_index,
            "title": title,
            "price": float(price) if price else None,
            "description": description,
            "image_url": BASE_URL + image if image else None,
            "product_url": product_url,
            "distance": float(dist)
        })

    cur.close()
    conn.close()

    return results
