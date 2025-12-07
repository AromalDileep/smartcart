from typing import List

from fastapi import APIRouter, HTTPException

from app.schemas.product_schema import ProductCreate, ProductUpdate
from app.services.product_service import (
    create_product,
    delete_product,
    get_all_products,
    get_product,
    update_product,
)

router = APIRouter()


# -------------------------------
# CREATE PRODUCT (Seller uploads)
# -------------------------------
@router.post("/", response_model=dict)
def create_new_product(product: ProductCreate):
    """
    Creates a new product entry in the database with 'pending' status.
    This is typically used by sellers to upload new items.
    """
    new_id = create_product(product)
    return {"id": new_id, "status": "pending"}


# -------------------------------
# GET ALL PRODUCTS
# -------------------------------
@router.get("/", response_model=List[dict])
def fetch_all_products():
    """
    Retrieves all products from the database, ordered by ID.
    """
    rows = get_all_products()
    products = []

    for row in rows:
        products.append({
            "id": row[0],
            "title": row[1],
            "description": row[2],
            "price": row[3],
            "image": row[4],
            "faiss_index": row[5],
            "embedding": str(row[6]) if row[6] else None,
            "status": row[7],
            "created_at": row[8],
            "main_category": row[9],
            "categories": row[10],
            "features": row[11],
            "details": row[12],
            "product_url": row[13]
        })

    return products


# -------------------------------
# GET PRODUCT BY ID
# -------------------------------
@router.get("/{product_id}", response_model=dict)
def fetch_product(product_id: int):
    """
    Retrieves details of a specific product by its ID.
    """
    row = get_product(product_id)
    if not row:
        raise HTTPException(status_code=404, detail="Product not found")

    return {
        "id": row[0],
        "title": row[1],
        "description": row[2],
        "price": row[3],
        "image": row[4],
        "faiss_index": row[5],
        "embedding": str(row[6]) if row[6] else None,
        "status": row[7],
        "created_at": row[8],
        "main_category": row[9],
        "categories": row[10],
        "features": row[11],
        "details": row[12],
        "product_url": row[13]
    }


# -------------------------------
# UPDATE PRODUCT
# -------------------------------
@router.patch("/{product_id}", response_model=dict)
def modify_product(product_id: int, product: ProductUpdate):
    """
    Updates attributes of an existing product.
    """
    updated = update_product(product_id, product)
    if not updated:
        raise HTTPException(status_code=400, detail="Nothing to update")
    return {"message": "Product updated"}


# -------------------------------
# DELETE PRODUCT
# -------------------------------
@router.delete("/{product_id}", response_model=dict)
def remove_product(product_id: int):
    """
    Hard deletes a product from the database.
    """
    deleted = delete_product(product_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Product not found")
    return {"message": "Product deleted"}
