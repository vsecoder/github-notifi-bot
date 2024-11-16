from fastapi import APIRouter, Request, Header
from app.db.functions import Chat, Integration

from app.config import parse_config
from app.utils.messages import (
    commit_message,
    issue_message,
    star_message,
    ping_message,
    create_message,
    pull_request_message,
    fork_message,
)

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

    if X_GitHub_Event == "ping":
        message = ping_message(res)
    if X_GitHub_Event == "push":
        message = commit_message(res)
    elif X_GitHub_Event == "issues":
        message = issue_message(res)
    elif X_GitHub_Event == "star":
        message = star_message(res)
    elif X_GitHub_Event == "create":
        message = create_message(res)
    elif X_GitHub_Event == "pull_request":
        message = pull_request_message(res)
    elif X_GitHub_Event == "fork":
        message = fork_message(res)
    else:
        message = f"Unknown event {X_GitHub_Event}!"

    requests.post(
        f"https://api.telegram.org/bot{config.bot.token}/sendMessage",
        json={
            "chat_id": chat.chat_id,
            "text": message,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        },
    )
    return {"message": "Webhook triggered!"}
