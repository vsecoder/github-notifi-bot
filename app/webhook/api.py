from fastapi import APIRouter, Request, Header
from app.db.functions import Integration

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


floodwait = 3
floodwait_cache = {}


def check_floodwait(chat_id):
    """
    Write a timestamp in the cache if the user has not sent a message in the last floodwait seconds.
    """
    if chat_id in floodwait_cache:
        if time.time() - floodwait_cache[chat_id] < floodwait:
            return True
    floodwait_cache[chat_id] = time.time()
    return False


@router.post("/{token}")
async def webhook(req: Request, token: str, X_GitHub_Event: str = Header()):
    res = await req.json()

    integrations = await Integration.get_by_token(token)
    if not integrations:
        return {"message": "No integrations found!"}

    message = None
    for integration in integrations:
        chat = integration.chat
        user = integration.user

        if X_GitHub_Event == "ping":
            message = ping_message(res)
        elif X_GitHub_Event == "push":
            message = commit_message(res, user.token)
        elif X_GitHub_Event == "issues":
            message = issue_message(res)
        elif X_GitHub_Event == "star":
            if check_floodwait(chat.chat_id):
                continue
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

        try:
            requests.post(
                f"https://api.telegram.org/bot{config.bot.token}/sendMessage",
                json=data,
                timeout=3,
            )
        except requests.RequestException as e:
            print(f"Error sending to chat {chat.chat_id}: {e}")

    return {"message": "Webhook processed for all integrations."}
