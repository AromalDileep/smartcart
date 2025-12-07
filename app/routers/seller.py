# app/routers/seller.py
import os
import uuid
from typing import List
import boto3
from botocore.exceptions import BotoCoreError, NoCredentialsError

from fastapi import APIRouter, File, HTTPException, Path, Query, UploadFile
from pydantic import BaseModel

from app.core.config import settings
from app.db.database import get_connection
from app.schemas.product_schema import ProductCreate, ProductUpdate
from app.services import product_service

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
    """
    Registers a new seller with email, password, and name.
    """
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT id FROM sellers WHERE email = %s;", (payload.email,))
    if cur.fetchone():
        cur.close()
        conn.close()
        raise HTTPException(status_code=400, detail="Email already registered")

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
    """
    Authenticates a seller and returns their ID and name.
    """
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT id, name, password FROM sellers WHERE email = %s;", (payload.email,))
    row = cur.fetchone()
    cur.close()
    conn.close()

    if not row:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    seller_id, name, stored_password = row

    if payload.password != stored_password:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    return {"status": "success", "seller_id": seller_id, "name": name}



# ------------------------------------------------------
# Upload Image (FIXED FOR S3 /all_images/)
# ------------------------------------------------------
@router.post("/upload-image")
async def upload_image(file: UploadFile = File(...)):
    """
    Uploads a product image. Supports both local storage and AWS S3
    depending on the configuration. Returns the image filename/URL.
    """
    if file.content_type not in ["image/jpeg", "image/png", "image/jpg"]:
        raise HTTPException(status_code=400, detail="Only JPG/PNG images allowed.")

    ext = file.filename.split(".")[-1]
    unique_name = f"{uuid.uuid4().hex}.{ext}"

    # HYBRID UPLOAD LOGIC
    # -------------------
    # 1. Cloud Mode (S3)
    if settings.USE_CLOUD:
        try:
            if not settings.S3_BUCKET_NAME:
                raise HTTPException(status_code=500, detail="S3_BUCKET_NAME not configured.")

            s3_key = f"all_images/{unique_name}"  # <--- FIXED HERE

            s3_client = boto3.client(
                "s3",
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_REGION,
            )

            s3_client.upload_fileobj(
                file.file,
                settings.S3_BUCKET_NAME,
                s3_key,
                ExtraArgs={"ContentType": file.content_type}
            )

            # Return S3 URL
            return {
                "filename": unique_name,
                "url": f"https://{settings.S3_BUCKET_NAME}.s3.{settings.AWS_REGION}.amazonaws.com/{s3_key}"
            }

        except (NoCredentialsError, BotoCoreError, Exception) as e:
            raise HTTPException(status_code=500, detail=f"S3 Upload Failed: {str(e)}")

    # 2. Local Mode (Default)
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    file_path = os.path.join(UPLOAD_DIR, unique_name)
    with open(file_path, "wb") as f:
        f.write(await file.read())

    return {"filename": unique_name, "url": f"{settings.BASE_URL}{unique_name}"}


# ------------------------------------------------------
# Create Product
# ------------------------------------------------------
@router.post("/create-product", response_model=dict)
async def create_product_endpoint(product: ProductCreate):
    """
    Allows a seller to create a new product.
    """
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
    """
    Retrieves all products belonging to a specific seller.
    """
    return product_service.get_products_by_seller(seller_id)


# ------------------------------------------------------
# Get Single Product
# ------------------------------------------------------
@router.get("/products/{product_id}", response_model=dict)
async def get_product(product_id: int = Path(...)):
    """
    Retrieves a single product by ID, excluding embedding data.
    """
    row = product_service.get_product(product_id)

    if not row:
        raise HTTPException(status_code=404, detail="Product not found")

    row.pop("embedding", None)
    return row


# ------------------------------------------------------
# Update Product
# ------------------------------------------------------
@router.patch("/products/{product_id}", response_model=dict)
async def patch_product(product_id: int, payload: ProductUpdate):
    """
    Updates a seller's product. If the product was approved, it resets
    status to 'pending' for re-approval.
    """
    product = product_service.get_product(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    current_status = product.get("status")

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
    """
    Soft deletes a product by setting its status to 'deleted'.
    """
    product = product_service.get_product(product_id)

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    payload = ProductUpdate(status="deleted")
    success = product_service.update_product(product_id, payload)

    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete product")

    return {"status": "deleted", "product_id": product_id}


# ------------------------------------------------------
# Seller RESUBMIT rejected product
# ------------------------------------------------------
@router.post("/resubmit/{product_id}", response_model=dict)
async def resubmit_product(product_id: int):
    """
    Resubmits a rejected product for approval by setting its status back to 'pending'.
    """
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
