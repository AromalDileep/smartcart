# app/main.py
import logging
import numpy as np

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.db.models import create_products_table
from app.db.database import get_connection
from app.utils.db_sequence_fix import fix_product_id_sequence

from app.services.global_faiss import ensure_services  # global embedder + faiss
# --------------------------------------------------------------------

logger = logging.getLogger("uvicorn.error")

app = FastAPI(
    title="SmartCart Semantic Search",
    description="FastAPI backend for SmartCart (FAISS + CLIP)",
    version="0.1.0",
)

from app.core.config import settings

# ---------------------------------------------------------
# CORS
# ---------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------
# STATIC FILES
# ---------------------------------------------------------
app.mount(
    "/images",
    StaticFiles(directory=settings.IMAGE_DIR),
    name="images"
)

app.mount(
    "/static",
    StaticFiles(directory=settings.STATIC_DIR),
    name="static"
)

# ---------------------------------------------------------
# ROUTERS
# ---------------------------------------------------------
def include_routers():
    try:
        from app.routers.search import router as search_router
        app.include_router(search_router, prefix="/search", tags=["search"])
    except:
        pass

    try:
        from app.routers.products import router as products_router
        app.include_router(products_router, prefix="/products", tags=["products"])
    except:
        pass

    try:
        from app.routers.admin import router as admin_router
        app.include_router(admin_router, prefix="/admin", tags=["admin"])
    except:
        pass

    try:
        from app.routers.seller import router as seller_router
        app.include_router(seller_router, prefix="/seller", tags=["seller"])
    except:
        pass

include_routers()

# ---------------------------------------------------------
# ROOT
# ---------------------------------------------------------
@app.get("/")
async def root():
    return {"message": "SmartCart API is running"}


# ---------------------------------------------------------
# AUTO REBUILD FAISS
# ---------------------------------------------------------
def auto_rebuild_faiss():
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

    if not rows:
        print("[FAISS] No embeddings found — skipping rebuild.")
        return

    print(f"[FAISS] Rebuilding FAISS index with {len(rows)} vectors...")

    vectors = []
    ids = []
    for fid, emb_bytes in rows:
        vec = np.frombuffer(emb_bytes, dtype="float32")
        vectors.append(vec)
        ids.append(int(fid))

    faiss_mgr.rebuild(vectors, ids)
    print("[FAISS] Rebuild complete!")


# ---------------------------------------------------------
# STARTUP EVENT
# ---------------------------------------------------------
@app.on_event("startup")
async def on_startup():
    logger.info("SmartCart app starting up")

    # Ensure DB ready
    create_products_table()
    logger.info("Products table ensured")

    # Sequence fix
    fix_product_id_sequence()
    logger.info("Product ID sequence synchronized.")

    # Auto rebuild FAISS on every container start
    auto_rebuild_faiss()


# ---------------------------------------------------------
# SHUTDOWN
# ---------------------------------------------------------
@app.on_event("shutdown")
async def on_shutdown():
    logger.info("SmartCart API shutting down...")


# ---------------------------------------------------------
# UI SHORTCUT
# ---------------------------------------------------------
@app.get("/ui")
def serve_ui():
    return FileResponse("app/static/customer/index.html")
