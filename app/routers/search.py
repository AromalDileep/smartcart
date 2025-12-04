from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile
from pydantic import BaseModel

from app.core.config import settings
from app.services.groq_service import ask_groq_question
from app.services.product_service import get_product
from app.services.search_service import search_by_image, search_by_text, search_hybrid

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


# -----------------------------------
# ASK QUESTION (GROQ)
# -----------------------------------

class AskQuestionRequest(BaseModel):
    product_id: int
    question: str

@router.post("/ask-question")
def ask_question_endpoint(req: AskQuestionRequest):
    # 1. Fetch product
    product = get_product(req.product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # 2. Build context
    # Use 'context' field if available, else fallback to title + description
    context = product.get("context")
    if not context:
        title = product.get("title", "")
        desc = product.get("description", "")
        context = f"Title: {title}\nDescription: {desc}"

    # 3. Call Groq
    result = ask_groq_question(context, req.question)
    return result
