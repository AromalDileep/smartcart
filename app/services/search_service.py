import os
import numpy as np
import torch
from PIL import Image

from fastapi import HTTPException
from app.faiss_manager import FaissManager
from app.services.embedding_service import CLIPEmbedder
from app.db.database import get_connection

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
def search_by_image(image_file, top_k=10):
    ensure_services()

    temp_path = "/tmp/search_image.jpg"
    with open(temp_path, "wb") as f:
        f.write(image_file)

    vec = embedder.embed_image(temp_path)

    ids, scores = faiss_mgr.search(vec, top_k)
    return format_results(ids, scores)


# -------------------------------------------------------
# TEXT SEARCH (FIXED VERSION)
# -------------------------------------------------------
def search_by_text(query: str, top_k=10):
    ensure_services()

    # Encode text using CLIPProcessor + CLIPModel
    inputs = embedder.processor(
        text=[query],
        return_tensors="pt",
        padding=True,
        truncation=True
    ).to(embedder.device)

    # 🔥 Correct no_grad() usage
    with torch.no_grad():
        txt = embedder.model.get_text_features(**inputs)

    # Normalize
    txt = txt / txt.norm(dim=-1, keepdim=True)
    txt = txt.cpu().numpy().astype("float32")

    ids, scores = faiss_mgr.search(txt, top_k)
    return format_results(ids, scores)


# -------------------------------------------------------
# HYBRID SEARCH
# -------------------------------------------------------
def search_hybrid(image_bytes, text_query, w_image=0.5, w_text=0.5, top_k=10):
    ensure_services()

    # ---- IMAGE ----
    temp_path = "/tmp/hybrid_img.jpg"
    with open(temp_path, "wb") as f:
        f.write(image_bytes)

    img_vec = embedder.embed_image(temp_path)

    # ---- TEXT ----
    inputs = embedder.processor(
        text=[text_query],
        return_tensors="pt",
        padding=True,
        truncation=True
    ).to(embedder.device)

    with torch.no_grad():
        txt_vec = embedder.model.get_text_features(**inputs)

    txt_vec = txt_vec / txt_vec.norm(dim=-1, keepdim=True)
    txt_vec = txt_vec.cpu().numpy().astype("float32")

    # ---- HYBRID ----
    hybrid_vec = w_image * img_vec + w_text * txt_vec
    hybrid_vec = hybrid_vec / np.linalg.norm(hybrid_vec)

    ids, scores = faiss_mgr.search(hybrid_vec.astype("float32"), top_k)
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
