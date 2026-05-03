"""Small helpers shared between handlers — to keep callback bodies flat."""
from typing import Optional

from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message


def accessible_message(callback: CallbackQuery) -> Optional[Message]:
    """Return the Message attached to a callback, or None if it's an
    ``InaccessibleMessage`` (the original message is gone)."""
    msg = callback.message
    return msg if isinstance(msg, Message) else None


async def safe_edit_text(
    msg: Message,
    text: str,
    reply_markup: Optional[InlineKeyboardMarkup] = None,
) -> None:
    """``msg.edit_text`` that swallows the harmless 'message is not modified'
    error Telegram raises when the new content is byte-identical to the
    current one (e.g. user re-tapping the same button)."""
    try:
        await msg.edit_text(text, reply_markup=reply_markup)
    except TelegramBadRequest as e:
        if "message is not modified" not in str(e):
            raise


async def safe_edit_markup(
    msg: Message, reply_markup: Optional[InlineKeyboardMarkup] = None
) -> None:
    """``msg.edit_reply_markup`` variant that swallows 'message is not
    modified'. See :func:`safe_edit_text`."""
    try:
        await msg.edit_reply_markup(reply_markup=reply_markup)
    except TelegramBadRequest as e:
        if "message is not modified" not in str(e):
            raise
