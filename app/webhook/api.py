from fastapi import APIRouter, Request, Header
from app.db.functions import Chat, Integration

from app.config import parse_config
from app.utils.messages import commit_message, issue_message, star_message

import requests

router = APIRouter()
config = parse_config()


@router.post("/{code}")
async def webhook(req: Request, code: str, X_GitHub_Event: str = Header()):
    """
    Endpoint that receives the webhook payload.
    This endpoint is called by Github when the webhook is triggered.
    The payload is passed as a query parameters.
    """
    res = await req.json()

    integration = await Integration.get_by_code(code)
    if not integration:
        return {"message": "Integration not found!"}

    chat = await Chat.get_by_integration(integration.id)
    if not chat:
        return {"message": "Chat not found!"}

    if X_GitHub_Event == "push":
        message = commit_message(res)
    elif X_GitHub_Event == "issues":
        message = issue_message(res)
    elif X_GitHub_Event == "star":
        message = star_message(res)
    else:
        message = "Unknown event!"

    requests.post(
        f"https://api.telegram.org/bot{config.bot.token}/sendMessage",
        json={
            "chat_id": chat.chat_id,
            "text": message,
            "parse_mode": "HTML",
        },
    )
    return {"message": "Webhook triggered!"}
