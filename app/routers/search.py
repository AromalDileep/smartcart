from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from app.services.search_service import search_by_image, search_by_text, search_hybrid

router = APIRouter()

@router.get("/text")
def text_search(
    query: str = Query(..., description="Search text"),
    k: int = Query(10, description="Number of results")
):
    if not query:
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    return search_by_text(query, top_k=k)

@router.post("/image")
async def image_search(file: UploadFile = File(...), k: int = 10):
    if file.content_type not in ["image/jpeg", "image/png"]:
        raise HTTPException(status_code=400, detail="Image must be JPG or PNG")
    bytes_data = await file.read()
    return search_by_image(bytes_data, top_k=k)

@router.post("/hybrid")
async def hybrid_search_endpoint(
    file: UploadFile = File(...),
    text: str = None,
    w_image: float = 0.5,
    w_text: float = 0.5,
    k: int = 10
):
    if not text:
        raise HTTPException(status_code=400, detail="Text is required for hybrid search")

    bytes_data = await file.read()
    return search_hybrid(bytes_data, text, w_image, w_text, top_k=k)
