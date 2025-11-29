# app/routers/seller.py
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Path, Query
from fastapi.responses import JSONResponse
import os
import uuid
from typing import List

from app.schemas.product_schema import ProductCreate, ProductUpdate, ProductResponse
from app.services import product_service

router = APIRouter()

# Directory inside your docker volume
UPLOAD_DIR = "/project_data/all_images"


# ------------------------------------------------------
# Upload Image  (This remains unchanged)
# ------------------------------------------------------
@router.post("/upload-image")
async def upload_image(file: UploadFile = File(...)):
    # Validate file type
    if file.content_type not in ["image/jpeg", "image/png", "image/jpg"]:
        raise HTTPException(status_code=400, detail="Only JPG/PNG images allowed.")

    ext = file.filename.split(".")[-1]
    unique_name = f"{uuid.uuid4().hex}.{ext}"

    os.makedirs(UPLOAD_DIR, exist_ok=True)

    file_path = os.path.join(UPLOAD_DIR, unique_name)
    with open(file_path, "wb") as f:
        f.write(await file.read())

    return {"filename": unique_name, "url": f"/images/{unique_name}"}


# ------------------------------------------------------
# Create Product   (BACKEND VALIDATION ADDED HERE)
# ------------------------------------------------------
@router.post("/create-product", response_model=dict)
async def create_product_endpoint(product: ProductCreate):
    """
    Create a new product (seller-facing).
    Returns: {"status": "success", "product_id": <id>}
    """

    # Validate seller ID
    if not product.seller_id:
        raise HTTPException(status_code=400, detail="seller_id is required")

    # Validate image (IMPORTANT)
    if not product.image:
        raise HTTPException(status_code=400, detail="Image is required for product creation")

    # Validate title
    if not product.title or product.title.strip() == "":
        raise HTTPException(status_code=400, detail="Title is required")

    # Validate price (optional but good)
    if product.price is not None and product.price < 0:
        raise HTTPException(status_code=400, detail="Price cannot be negative")

    # Everything OK → create product
    new_id = product_service.create_product(product, seller_id=product.seller_id)

    return {"status": "success", "product_id": new_id}


# ------------------------------------------------------
# List Products for Seller
# ------------------------------------------------------
@router.get("/products", response_model=List[dict])
async def get_products_for_seller(seller_id: int = Query(..., description="Seller ID")):
    rows = product_service.get_products_by_seller(seller_id)
    return rows


# ------------------------------------------------------
# Get single product
# ------------------------------------------------------
@router.get("/products/{product_id}", response_model=dict)
async def get_product(product_id: int = Path(...)):
    row = product_service.get_product(product_id)
    if not row:
        raise HTTPException(status_code=404, detail="Product not found")
    return row


# ------------------------------------------------------
# Update Product
# ------------------------------------------------------
@router.patch("/products/{product_id}", response_model=dict)
async def patch_product(product_id: int, payload: ProductUpdate):
    success = product_service.update_product(product_id, payload)
    if not success:
        raise HTTPException(status_code=400, detail="No valid fields provided or update failed")
    return {"status": "success", "product_id": product_id}


# ------------------------------------------------------
# Delete Product (Seller)
# ------------------------------------------------------
@router.delete("/products/{product_id}", response_model=dict)
async def delete_product(product_id: int):
    """
    - If product has faiss_index: seller cannot delete; must request admin.
    - Else delete DB row and delete image file.
    """
    product = product_service.get_product(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Determine faiss index
    faiss_idx = (
        product.get("faiss_index")
        if isinstance(product, dict)
        else None
    )

    if faiss_idx:
        raise HTTPException(
            status_code=400,
            detail="Product is indexed in FAISS. Contact admin for deletion."
        )

    # Safe delete from DB
    success = product_service.delete_product(product_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete product")

    # Delete image if exists
    image_name = product.get("image") if isinstance(product, dict) else None
    if image_name:
        image_path = os.path.join(UPLOAD_DIR, os.path.basename(image_name))
        try:
            if os.path.exists(image_path):
                os.remove(image_path)
        except:
            pass  # ignore file deletion failures

    return {"status": "deleted", "product_id": product_id}
