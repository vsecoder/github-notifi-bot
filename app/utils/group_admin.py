"""Helpers for verifying chat-administrator status.

Centralised so handlers across the codebase share the same admin-check
semantics (silently treats "bot can't read admins" as "not admin").
"""
from typing import Optional

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError


async def get_admin_ids(bot: Bot, chat_id: int) -> Optional[list[int]]:
    """Return Telegram ids of chat administrators, or ``None`` if the bot
    can't read the admin list (kicked / chat gone / network)."""
    try:
        admins = await bot.get_chat_administrators(chat_id)
    except (TelegramBadRequest, TelegramForbiddenError):
        return None
    return [a.user.id for a in admins]


async def is_user_admin(bot: Bot, chat_id: int, user_id: int) -> bool:
    """True if the user is currently an admin in the chat. False on
    any failure to read the admin list."""
    admin_ids = await get_admin_ids(bot, chat_id)
    return admin_ids is not None and user_id in admin_ids
