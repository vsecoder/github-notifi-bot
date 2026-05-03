import html
import logging
import time

import aiohttp
from fastapi import APIRouter, Header, Request

from app.config import parse_config
from app.db.functions import Chat, EventSetting, Integration
from app.events import EventCtx, build_message

router = APIRouter()
config = parse_config()

floodwait_cache: dict[int, float] = {}

# Rate-limit DM notifications about delivery failures.
# Keyed by (telegram_user_id, chat_id) so different chats / different users
# don't suppress each other.
_delivery_failure_notified: dict[tuple[int, int], float] = {}
_NOTIFY_INTERVAL = 1800.0  # 30 minutes


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


async def _notify_owner_of_delivery_failure(
    session: aiohttp.ClientSession,
    integration: Integration,
    failure_summary: str,
) -> None:
    """DM the user who set up this integration about a persistent delivery
    failure. Rate-limited per (user, chat) to avoid spamming on every event
    while the chat is unreachable."""
    user = integration.user  # prefetched in get_by_token
    chat = integration.chat
    if user is None or chat is None or not user.telegram_id:
        return

    key = (user.telegram_id, chat.chat_id)
    now = time.time()
    last = _delivery_failure_notified.get(key)
    if last is not None and now - last < _NOTIFY_INTERVAL:
        logging.info(
            "Suppressed delivery-failure DM to %s about chat %s "
            "(last notified %.0fs ago, interval %.0fs)",
            user.telegram_id,
            chat.chat_id,
            now - last,
            _NOTIFY_INTERVAL,
        )
        return
    _delivery_failure_notified[key] = now

    text = (
        "⚠️ <b>I couldn't deliver a notification</b>\n\n"
        f"Repository: <code>{html.escape(integration.repository_name or '?')}</code>\n"
        f"Target chat id: <code>{chat.chat_id}</code>\n"
        f"Error: <code>{html.escape(failure_summary[:300])}</code>\n\n"
        "Possible causes:\n"
        "• I was removed from the chat\n"
        "• The chat was deleted or migrated to a different id\n"
        "• I lost permissions to write there\n"
        "• The forum topic the integration uses was closed\n\n"
        "Run <code>/integrations</code> in that chat to manage, or "
        "<code>/delete owner/repo</code> there to remove the integration "
        "if the chat is gone."
    )
    data = {
        "chat_id": user.telegram_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    try:
        status, body = await _post_send(session, data)
        if status < 400:
            logging.info(
                "Sent delivery-failure DM to %s about chat %s",
                user.telegram_id,
                chat.chat_id,
            )
        else:
            logging.warning(
                "Couldn't DM owner %s about delivery failure: %s — %s",
                user.telegram_id,
                status,
                body,
            )
    except aiohttp.ClientError as e:
        logging.warning(
            "Network error DM-ing owner %s about delivery failure: %s",
            user.telegram_id,
            e,
        )


async def send_message(
    session: aiohttp.ClientSession,
    integration: Integration,
    text: str,
) -> None:
    chat = integration.chat
    if chat is None:
        return
    chat_id = chat.chat_id
    topic_id = chat.topic_id

    data: dict = {
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

        # Topic deleted / closed — retry without thread so the message at
        # least lands in General. We don't notify the owner if the retry
        # succeeds; if it also fails, fall through to the persistent-failure
        # branch below which DOES notify.
        if topic_id and status == 400 and (
            "thread not found" in body.lower() or "topic_closed" in body.lower()
        ):
            thread_gone = "thread not found" in body.lower()
            logging.warning(
                "Topic %s in chat %s is unavailable, retrying without thread.",
                topic_id,
                chat_id,
            )
            data.pop("message_thread_id", None)
            status, body = await _post_send(session, data)
            if status < 400:
                # Retry to General succeeded. If the thread was *deleted*
                # (not just closed), drop the dead topic_id from the chat
                # row so future events don't waste an extra round-trip.
                if thread_gone:
                    try:
                        await Chat.remove_topic(chat_id)
                        logging.info(
                            "Cleared dead topic %s from chat %s",
                            topic_id,
                            chat_id,
                        )
                    except Exception:
                        logging.exception(
                            "Couldn't clear topic_id for chat %s", chat_id
                        )
                return

        # Persistent failure: log + DM the owner (5xx is treated as transient
        # and only logged, since GitHub will keep delivering future events
        # and the next one might succeed).
        if status == 403:
            logging.warning(
                "Bot can't write to chat %s (kicked / no permission): %s",
                chat_id,
                body,
            )
            await _notify_owner_of_delivery_failure(session, integration, body)
        elif 400 <= status < 500:
            logging.warning(
                "Telegram sendMessage to %s returned %s: %s",
                chat_id,
                status,
                body,
            )
            await _notify_owner_of_delivery_failure(session, integration, body)
        else:
            # 5xx
            logging.warning(
                "Telegram sendMessage to %s returned %s (transient): %s",
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
                await send_message(session, integration, message)

    return {"message": "Webhook processed for all integrations."}
