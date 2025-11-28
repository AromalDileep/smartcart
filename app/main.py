# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import logging

# DB auto-init
from app.db.models import create_products_table

logger = logging.getLogger("uvicorn.error")

app = FastAPI(
    title="SmartCart Semantic Search",
    description="FastAPI backend for SmartCart (FAISS + CLIP)",
    version="0.1.0",
)

# ---------------------------------------------------------
# CORS (safe for development; tighten in production)
# ---------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],       
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------
# STATIC FILE MOUNTS (CSS/JS/HTML/Images)
# ---------------------------------------------------------

# Serve images from the Docker volume
# Example: http://localhost:8000/images/myimage.jpg
app.mount(
    "/images",
    StaticFiles(directory="/project_data/all_images"),
    name="images"
)

# Serve static HTML/JS/CSS from app/static/
# Example: http://localhost:8000/static/seller/index.html
app.mount(
    "/static",
    StaticFiles(directory="app/static"),
    name="static"
)

# ---------------------------------------------------------
# Routers
# ---------------------------------------------------------
def include_routers():
    try:
        from app.routers.search import router as search_router
        app.include_router(search_router, prefix="/search", tags=["search"])
    except Exception as e:
        logger.debug(f"Search router not available yet: {e}")

    try:
        from app.routers.products import router as products_router
        app.include_router(products_router, prefix="/products", tags=["products"])
    except Exception as e:
        logger.debug(f"Products router not available yet: {e}")

    try:
        from app.routers.admin import router as admin_router
        app.include_router(admin_router, prefix="/admin", tags=["admin"])
    except Exception as e:
        logger.debug(f"Admin router not available yet: {e}")

    try:
        from app.routers.seller import router as seller_router
        app.include_router(seller_router, prefix="/seller", tags=["seller"])
    except Exception as e:
        logger.debug(f"Seller router not available yet: {e}")

include_routers()

# ---------------------------------------------------------
# Health Check
# ---------------------------------------------------------
@app.get("/", summary="Root")
async def root():
    return {"message": "SmartCart API is running"}

# ---------------------------------------------------------
# Startup & Shutdown Actions
# ---------------------------------------------------------
@app.on_event("startup")
async def on_startup():
    logger.info("SmartCart API starting up...")
    create_products_table()
    logger.info("Products table ensured.")

@app.on_event("shutdown")
async def on_shutdown():
    logger.info("SmartCart API shutting down...")

# ---------------------------------------------------------
# Shortcuts
# ---------------------------------------------------------

# Quick UI redirect (optional)
@app.get("/ui")
def serve_ui():
    """Serve customer UI from /static"""
    return FileResponse("app/static/customer/index.html")
