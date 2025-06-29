import time
import requests
from fastapi import APIRouter, Request, Header
from app.db.functions import Integration, EventSetting
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

router = APIRouter()
config = parse_config()

floodwait_cache: dict[int, float] = {}


def check_floodwait(chat_id: int, floodwait: int = 3) -> bool:
    now = time.time()
    if (last := floodwait_cache.get(chat_id)) and now - last < floodwait:
        return True
    floodwait_cache[chat_id] = now
    return False


def build_message(event: str, payload: dict, user_token: str | None) -> str | None:
    match event:
        case "ping":
            return ping_message(payload)
        case "push":
            return commit_message(payload, user_token)
        case "issues":
            return issue_message(payload)
        case "star":
            return star_message(payload)
        case "create":
            return create_message(payload)
        case "pull_request":
            return pull_request_message(payload)
        case "fork":
            return fork_message(payload)
        case _:
            return f"Unknown event: {event}"


def send_message(chat_id: int, topic_id: int | None, text: str) -> None:
    data = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    if topic_id:
        data["reply_to_message_id"] = topic_id

    try:
        requests.post(
            f"https://api.telegram.org/bot{config.bot.token}/sendMessage",
            json=data,
            timeout=3,
        )
    except requests.RequestException as e:
        print(f"Error sending to chat {chat_id}: {e}")


@router.post("/{token}")
async def webhook(req: Request, token: str, X_GitHub_Event: str = Header()):
    payload = await req.json()
    integrations = await Integration.get_by_token(token)

    if not integrations:
        return {"message": "No integrations found!"}

    for integration in integrations:
        chat = integration.chat
        user = integration.user

        #if not await EventSetting.is_enabled(chat, X_GitHub_Event):
        #    continue

        if X_GitHub_Event == "star" and check_floodwait(chat.chat_id, chat.floodwait):
            continue

        message = build_message(X_GitHub_Event, payload, user.token)
        if message:
            send_message(chat.chat_id, chat.topic_id, message)

    return {"message": "Webhook processed for all integrations."}
