import logging
import time

import aiohttp
from fastapi import APIRouter, Header, Request

from app.config import parse_config
from app.db.functions import EventSetting, Integration
from app.events import EventCtx, build_message

router = APIRouter()
config = parse_config()

floodwait_cache: dict[int, float] = {}


def check_floodwait(chat_id: int, floodwait: int = 3) -> bool:
    now = time.time()
    if (last := floodwait_cache.get(chat_id)) and now - last < floodwait:
        return True
    floodwait_cache[chat_id] = now
    return False


async def _post_send(
    session: aiohttp.ClientSession, data: dict
) -> tuple[int, str]:
    async with session.post(
        f"https://api.telegram.org/bot{config.bot.token}/sendMessage",
        json=data,
        timeout=aiohttp.ClientTimeout(total=5),
    ) as response:
        return response.status, await response.text()


async def send_message(
    session: aiohttp.ClientSession,
    chat_id: int,
    topic_id: int | None,
    text: str,
) -> None:
    data = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    if topic_id:
        data["message_thread_id"] = topic_id

    try:
        status, body = await _post_send(session, data)
        if status < 400:
            return

        if topic_id and status == 400 and (
            "thread not found" in body.lower() or "topic_closed" in body.lower()
        ):
            logging.warning(
                "Topic %s in chat %s is unavailable, retrying without thread.",
                topic_id,
                chat_id,
            )
            data.pop("message_thread_id", None)
            status, body = await _post_send(session, data)
            if status < 400:
                return

        if status == 403:
            logging.warning(
                "Bot can't write to chat %s (kicked / no permission): %s",
                chat_id,
                body,
            )
        else:
            logging.warning(
                "Telegram sendMessage to %s returned %s: %s",
                chat_id,
                status,
                body,
            )
    except aiohttp.ClientError as e:
        logging.error("Error sending to chat %s: %s", chat_id, e)


@router.post("/{token}")
async def webhook(req: Request, token: str, X_GitHub_Event: str = Header()):
    payload = await req.json()
    integrations = await Integration.get_by_token(token)

    if not integrations:
        return {"message": "No integrations found!"}

    async with aiohttp.ClientSession() as session:
        for integration in integrations:
            chat = integration.chat
            user = integration.user

            if not await EventSetting.is_enabled(chat.chat_id, X_GitHub_Event):
                continue

            if X_GitHub_Event == "star" and check_floodwait(
                chat.chat_id, chat.floodwait
            ):
                continue

            ctx = EventCtx(user_token=user.token)
            message = build_message(X_GitHub_Event, payload, ctx)
            if message:
                await send_message(session, chat.chat_id, chat.topic_id, message)

    return {"message": "Webhook processed for all integrations."}
