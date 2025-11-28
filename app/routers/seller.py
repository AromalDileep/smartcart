# app/routers/seller.py
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Path, Query
from fastapi.responses import JSONResponse
import os
import uuid
from typing import List

from app.schemas.product_schema import ProductCreate, ProductUpdate, ProductResponse
from app.services import product_service

router = APIRouter()

# Directory inside your docker volume (already used in your project)
UPLOAD_DIR = "/project_data/all_images"

# -------------------------
# Upload Image (existing)
# -------------------------
@router.post("/upload-image")
async def upload_image(file: UploadFile = File(...)):
    # Validate file type
    if file.content_type not in ["image/jpeg", "image/png", "image/jpg"]:
        raise HTTPException(status_code=400, detail="Only JPG/PNG images allowed.")

    # Create a unique filename
    ext = file.filename.split(".")[-1]
    unique_name = f"{uuid.uuid4().hex}.{ext}"

    # Ensure directory exists in Docker volume
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    # Save file
    file_path = os.path.join(UPLOAD_DIR, unique_name)
    with open(file_path, "wb") as f:
        f.write(await file.read())

    return {"filename": unique_name, "url": f"/images/{unique_name}"}


# -------------------------
# Create Product
# -------------------------
@router.post("/create-product", response_model=dict)
async def create_product_endpoint(product: ProductCreate):
    """
    Create a new product (seller-facing). ProductCreate includes an optional seller_id.
    Returns: {"status":"success", "product_id": <id>}
    """
    # require seller_id inside payload (simple approach). You can replace with auth later.
    if not product.seller_id:
        raise HTTPException(status_code=400, detail="seller_id is required in the request body")

    new_id = product_service.create_product(product, seller_id=product.seller_id)
    return {"status": "success", "product_id": new_id}


# -------------------------
# List Products for Seller
# -------------------------
@router.get("/products", response_model=List[dict])
async def get_products_for_seller(seller_id: int = Query(..., description="Seller ID")):
    """
    Returns list of products for a seller.
    """
    rows = product_service.get_products_by_seller(seller_id)
    return rows


# -------------------------
# Get single product
# -------------------------
@router.get("/products/{product_id}", response_model=dict)
async def get_product(product_id: int = Path(...)):
    row = product_service.get_product(product_id)
    if not row:
        raise HTTPException(status_code=404, detail="Product not found")
    return row


# -------------------------
# Update product (seller can edit pending or rejected; admin should handle approved)
# -------------------------
@router.patch("/products/{product_id}", response_model=dict)
async def patch_product(product_id: int, payload: ProductUpdate):
    success = product_service.update_product(product_id, payload)
    if not success:
        raise HTTPException(status_code=400, detail="No valid fields provided or update failed")
    return {"status": "success", "product_id": product_id}


# -------------------------
# Delete product (seller)
# -------------------------
@router.delete("/products/{product_id}", response_model=dict)
async def delete_product(product_id: int):
    """
    Seller-initiated delete:
    - If product has faiss_index (approved/embedded), we prevent deletion and instruct to use admin.
    - Otherwise delete DB row and remove image file from disk (if exists).
    """
    product = product_service.get_product(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # product row shape: depends on product_service.get_product implementation; assume dict-like
    faiss_idx = product.get("faiss_index") if isinstance(product, dict) else product[ product_service.FAISS_INDEX_POS ] if hasattr(product_service, "FAISS_INDEX_POS") else None

    if faiss_idx:
        raise HTTPException(
            status_code=400,
            detail="This product has been indexed (faiss_index present). Please contact admin to delete (to ensure FAISS index consistency)."
        )

    # safe to delete: remove DB row and image file
    success = product_service.delete_product(product_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete product")

    # try remove image file (best-effort)
    image_name = product.get("image") if isinstance(product, dict) else None
    if image_name:
        image_basename = os.path.basename(image_name)
        image_path = os.path.join(UPLOAD_DIR, image_basename)
        try:
            if os.path.exists(image_path):
                os.remove(image_path)
        except Exception:
            # do not fail if file deletion fails; log and continue
            pass

    return {"status": "deleted", "product_id": product_id}

