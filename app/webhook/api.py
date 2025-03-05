from fastapi import APIRouter, Request, Header
from app.db.functions import Chat, Integration, User

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

import time
import requests

router = APIRouter()
config = parse_config()


floodwait = 3 # Seconds to wait between messages
floodwait_cache = {} # Cache to avoid sending too many messages


def check_floodwait(chat_id):
    """
    Write a timestamp in the cache if the user has not sent a message in the last floodwait seconds.
    """
    if chat_id in floodwait_cache:
        if time.time() - floodwait_cache[chat_id] < floodwait:
            return True
    floodwait_cache[chat_id] = time.time()
    return False


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

    user_id = [
        integration
        for integration in chat.integrations
        if integration['integration_id'] == integration.id
    ][0]['user_id']

    user = await User.get_by_id(user_id)
    if not user:
        return {"message": "User not found!"}

    if X_GitHub_Event == "ping":
        message = ping_message(res)
    elif X_GitHub_Event == "push":
        message = commit_message(res, user.token)
    elif X_GitHub_Event == "issues":
        message = issue_message(res)
    elif X_GitHub_Event == "star":
        if check_floodwait(chat.chat_id):
            return {"message": "Too many messages!"}
        message = star_message(res)
    elif X_GitHub_Event == "create":
        message = create_message(res)
    elif X_GitHub_Event == "pull_request":
        message = pull_request_message(res)
    elif X_GitHub_Event == "fork":
        message = fork_message(res)
    else:
        message = f"Unknown event {X_GitHub_Event}!"

    data = {
        "chat_id": chat.chat_id,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }

    if chat.topic_id:
        data["reply_to_message_id"] = chat.topic_id

    requests.post(
        f"https://api.telegram.org/bot{config.bot.token}/sendMessage",
        json=data,
    )
    return {"message": "Webhook triggered!"}
