from fastapi import APIRouter

router = APIRouter()

@router.get("/test")
async def test_search():
    return {"message": "Search router working"}
