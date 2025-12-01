from pydantic import BaseModel
from typing import Optional

# -------------------------------------------------
# BASE FIELDS (Common for Create/Update/Response)
# -------------------------------------------------
class ProductBase(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    image: Optional[str] = None

    main_category: Optional[str] = None
    categories: Optional[str] = None
    features: Optional[str] = None
    details: Optional[str] = None
    product_url: Optional[str] = None
    context: Optional[str] = None


# -------------------------------------------------
# PRODUCT CREATE (Seller uploads)
# -------------------------------------------------
class ProductCreate(ProductBase):
    seller_id: int  # REQUIRED


# -------------------------------------------------
# PRODUCT UPDATE (Admin or Seller)
# -------------------------------------------------
class ProductUpdate(ProductBase):
    status: Optional[str] = None


# -------------------------------------------------
# PRODUCT RESPONSE MODEL (API Output)
# -------------------------------------------------
class ProductResponse(ProductBase):
    id: int
    faiss_index: Optional[int] = None
    embedding: Optional[str] = None
    status: str
    created_at: Optional[str] = None

    class Config:
        from_attributes = True   # pydantic v2 replacement for orm_mode
