from fastapi import APIRouter, UploadFile, File, HTTPException, Query, Form
from typing import Optional
from app.services.search_service import search_by_image, search_by_text, search_hybrid

from app.core.config import settings

router = APIRouter()

@router.get("/text")
def text_search(
    query: str = Query(..., description="Search text"),
    k: int = Query(settings.DEFAULT_TOP_K, description="Number of results")
):
    if not query:
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    return search_by_text(query, top_k=k)


@router.post("/image")
async def image_search(
    image: UploadFile = File(...),
    k: int = settings.DEFAULT_TOP_K
):
    img_bytes = await image.read()
    return search_by_image(img_bytes, top_k=k)


@router.post("/hybrid")
async def hybrid_search_endpoint(
    image: Optional[UploadFile] = File(None),
    text: Optional[str] = Form(None),
    w_image: float = Form(settings.DEFAULT_WEIGHT_IMAGE),
    w_text: float = Form(settings.DEFAULT_WEIGHT_TEXT),
    k: int = Query(settings.DEFAULT_TOP_K)
):
    img_bytes = None
    if image:
        img_bytes = await image.read()

    return search_hybrid(img_bytes, text, w_image, w_text, top_k=k)
