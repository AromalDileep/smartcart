from fastapi import APIRouter
from pydantic import BaseModel

from app.core.config import settings

router = APIRouter()

class PublicConfig(BaseModel):
    image_base_url: str

@router.get("", response_model=PublicConfig)
def get_public_config():
    """
    Public configuration for frontend (safe values only).
    """
    return PublicConfig(image_base_url=settings.BASE_URL)
