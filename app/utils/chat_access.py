"""Helpers for resolving Telegram chat titles and listing chats where a
particular user is an administrator. Used by DM dialogs (My chats, Repos
integrate flow). Results are cached in-process to avoid hammering Telegram
on every dialog interaction.
"""
import asyncio
import time
from typing import TypedDict

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError

from app.db.functions import Chat


class AdminChat(TypedDict):
    chat_id: int
    title: str


# Chat-title cache (kept long, titles rarely change).
_TITLE_TTL = 300.0
_title_cache: dict[int, tuple[str, float]] = {}

# Per-user "where am I admin" cache (kept short, admin status can flip).
_ADMIN_TTL = 60.0
_admin_cache: dict[int, tuple[list[AdminChat], float]] = {}


async def resolve_chat_title(bot: Bot, chat_id: int) -> str:
    cached = _title_cache.get(chat_id)
    now = time.monotonic()
    if cached and cached[1] > now:
        return cached[0]
    try:
        tg_chat = await bot.get_chat(chat_id)
        title = (
            tg_chat.title
            or getattr(tg_chat, "full_name", None)
            or f"chat {chat_id}"
        )
    except TelegramAPIError:
        title = f"(unavailable, id={chat_id})"
    _title_cache[chat_id] = (title, now + _TITLE_TTL)
    return title


def invalidate_titles() -> None:
    _title_cache.clear()


async def list_admin_chats(bot: Bot, telegram_user_id: int) -> list[AdminChat]:
    """Return chats from our DB where the user is currently an admin.

    One ``getChatAdministrators`` API call per known chat, fanned out in
    parallel. Failures (bot kicked / chat deleted / network) are silently
    skipped. Cached per user for ``_ADMIN_TTL`` seconds.
    """
    cached = _admin_cache.get(telegram_user_id)
    now = time.monotonic()
    if cached and cached[1] > now:
        return cached[0]

    chats = await Chat.all()

    async def _check(chat: Chat) -> AdminChat | None:
        try:
            admins = await bot.get_chat_administrators(chat.chat_id)
        except TelegramAPIError:
            return None
        if telegram_user_id not in [a.user.id for a in admins]:
            return None
        title = await resolve_chat_title(bot, chat.chat_id)
        return AdminChat(chat_id=chat.chat_id, title=title)

    raw = await asyncio.gather(*[_check(c) for c in chats])
    result = [x for x in raw if x is not None]
    result.sort(key=lambda c: c["title"].lower())
    _admin_cache[telegram_user_id] = (result, now + _ADMIN_TTL)
    return result


def invalidate_admin_chats(telegram_user_id: int | None = None) -> None:
    if telegram_user_id is None:
        _admin_cache.clear()
    else:
        _admin_cache.pop(telegram_user_id, None)
