from fastapi import APIRouter, Request
from app.db.functions import User

router = APIRouter()


@router.post("/")
async def webhook(req: Request, code: str):
    """
    Endpoint that receives the webhook payload.
    This endpoint is called by Github when the webhook is triggered.
    The payload is passed as a query parameters.
    """
    res = await req.json()
    return {"message": "Webhook triggered!"}
