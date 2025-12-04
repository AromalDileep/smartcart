# app/routers/seller.py
from fastapi import APIRouter, UploadFile, File, HTTPException, Path, Query
import os
import uuid
from typing import List

from app.schemas.product_schema import ProductCreate, ProductUpdate
from app.services import product_service

from app.core.config import settings
from app.db.database import get_connection
from pydantic import BaseModel

router = APIRouter()

# Directory inside your docker volume
UPLOAD_DIR = settings.IMAGE_DIR


# ------------------------------------------------------
# Auth Schemas
# ------------------------------------------------------
class SellerRegister(BaseModel):
    email: str
    password: str
    name: str

class SellerLogin(BaseModel):
    email: str
    password: str


# ------------------------------------------------------
# Register
# ------------------------------------------------------
@router.post("/register")
def register_seller(payload: SellerRegister):
    conn = get_connection()
    cur = conn.cursor()

    # Check if email exists
    cur.execute("SELECT id FROM sellers WHERE email = %s;", (payload.email,))
    if cur.fetchone():
        cur.close()
        conn.close()
        raise HTTPException(status_code=400, detail="Email already registered")

    # Insert new seller
    cur.execute("""
        INSERT INTO sellers (email, password, name)
        VALUES (%s, %s, %s)
        RETURNING id;
    """, (payload.email, payload.password, payload.name))
    
    new_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()

    return {"status": "success", "seller_id": new_id, "name": payload.name}


# ------------------------------------------------------
# Login
# ------------------------------------------------------
@router.post("/login")
def login_seller(payload: SellerLogin):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT id, name, password FROM sellers WHERE email = %s;", (payload.email,))
    row = cur.fetchone()
    cur.close()
    conn.close()

    if not row:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    seller_id, name, stored_password = row

    # Simple password check (In production use hashing!)
    if payload.password != stored_password:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    return {"status": "success", "seller_id": seller_id, "name": name}



# ------------------------------------------------------
# Upload Image
# ------------------------------------------------------
@router.post("/upload-image")
async def upload_image(file: UploadFile = File(...)):
    if file.content_type not in ["image/jpeg", "image/png", "image/jpg"]:
        raise HTTPException(status_code=400, detail="Only JPG/PNG images allowed.")

    ext = file.filename.split(".")[-1]
    unique_name = f"{uuid.uuid4().hex}.{ext}"

    os.makedirs(UPLOAD_DIR, exist_ok=True)

    file_path = os.path.join(UPLOAD_DIR, unique_name)
    with open(file_path, "wb") as f:
        f.write(await file.read())

    # Return full URL or relative path depending on BASE_URL setting
    # If BASE_URL is absolute, this returns absolute.
    # We strip the trailing slash from BASE_URL if we want to be safe, but config has it.
    # Assuming BASE_URL ends with /
    return {"filename": unique_name, "url": f"{settings.BASE_URL}{unique_name}"}


# ------------------------------------------------------
# Create Product  (VALIDATED)
# ------------------------------------------------------
@router.post("/create-product", response_model=dict)
async def create_product_endpoint(product: ProductCreate):
    if not product.seller_id:
        raise HTTPException(status_code=400, detail="seller_id is required")

    if not product.image:
        raise HTTPException(status_code=400, detail="Image is required for product creation")

    if not product.title or product.title.strip() == "":
        raise HTTPException(status_code=400, detail="Title is required")

    if product.price is not None and product.price < 0:
        raise HTTPException(status_code=400, detail="Price cannot be negative")

    new_id = product_service.create_product(product, seller_id=product.seller_id)
    return {"status": "success", "product_id": new_id}


# ------------------------------------------------------
# List Products for Seller
# ------------------------------------------------------
@router.get("/products", response_model=List[dict])
async def get_products_for_seller(seller_id: int = Query(...)):
    return product_service.get_products_by_seller(seller_id)


# ------------------------------------------------------
# Get Single Product  (FIXED: remove BYTEA embedding)
# ------------------------------------------------------
@router.get("/products/{product_id}", response_model=dict)
async def get_product(product_id: int = Path(...)):
    row = product_service.get_product(product_id)

    if not row:
        raise HTTPException(status_code=404, detail="Product not found")

    # 🔥 CRITICAL FIX — remove non-JSON-serializable fields
    row.pop("embedding", None)

    return row


# ------------------------------------------------------
# Update Product (Seller edits)
# ------------------------------------------------------
@router.patch("/products/{product_id}", response_model=dict)
async def patch_product(product_id: int, payload: ProductUpdate):
    product = product_service.get_product(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    current_status = product.get("status")

    # If product is approved → move to pending on edit
    if current_status == "approved":
        payload.status = "pending"

    success = product_service.update_product(product_id, payload)

    if not success:
        raise HTTPException(status_code=400, detail="No valid fields provided or update failed")

    return {
        "status": payload.status or current_status,
        "product_id": product_id,
        "message": (
            "Product updated and sent for re-approval"
            if current_status == "approved"
            else "Product updated"
        )
    }


# ------------------------------------------------------
# Seller DELETE Product
# ------------------------------------------------------
@router.delete("/products/{product_id}", response_model=dict)
async def delete_product(product_id: int):
    product = product_service.get_product(product_id)

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    faiss_idx = product.get("faiss_index") if isinstance(product, dict) else None

    if faiss_idx:
        raise HTTPException(
            status_code=400,
            detail="Product is indexed in FAISS. Contact admin for deletion."
        )

    success = product_service.delete_product(product_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete product")

    # Remove image
    image_name = product.get("image") if isinstance(product, dict) else None
    if image_name:
        image_path = os.path.join(UPLOAD_DIR, os.path.basename(image_name))
        try:
            if os.path.exists(image_path):
                os.remove(image_path)
        except:
            pass

    return {"status": "deleted", "product_id": product_id}


# ------------------------------------------------------
# Seller RESUBMIT rejected product
# ------------------------------------------------------
@router.post("/resubmit/{product_id}", response_model=dict)
async def resubmit_product(product_id: int):
    product = product_service.get_product(product_id)

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    if product["status"] != "rejected":
        raise HTTPException(
            status_code=400,
            detail="Only rejected products can be resubmitted."
        )

    payload = ProductUpdate(status="pending")
    product_service.update_product(product_id, payload)

    return {"status": "pending", "product_id": product_id}
