from aiogram import Router
from aiogram.filters import Command
from aiogram.types import ErrorEvent, Message

import logging
import traceback
import html

from app.config import Config

router = Router()


@router.error()
async def error_handler(event: ErrorEvent, config: Config):
    bot = event.update.bot
    update = event.update
    exception = event.exception
    if bot is None:
        logging.error("Error event without bot reference: %s", exception)
        return

    user_id: int | None = None
    user_username: str | None = None
    request: str = ""

    if update.callback_query is not None and update.callback_query.from_user is not None:
        user_id = update.callback_query.from_user.id
        user_username = update.callback_query.from_user.username
        request = f"callback_data: <code>{update.callback_query.data or ''}</code>"
    elif update.message is not None and update.message.from_user is not None:
        user_id = update.message.from_user.id
        user_username = update.message.from_user.username
        request = f"text: <code>{update.message.text or ''}</code>"
    else:
        request = "<i>(unknown source)</i>"

    tb = traceback.extract_tb(exception.__traceback__)
    last_frame = tb[-1] if tb else None

    if last_frame is not None:
        formatted_traceback = (
            f"<b>File:</b> <code>{html.escape(last_frame.filename)}</code>\n"
            f"<b>Line:</b> <code>{last_frame.lineno}</code>\n"
            f"<b>Name:</b> <code>{html.escape(exception.__class__.__name__)}</code>\n"
            f"<b>Function:</b> <code>{html.escape(last_frame.name)}</code>\n"
            f"<b>Message:</b> <code>{html.escape(str(exception))}</code>\n"
            f"<b>Code:</b> <code>{html.escape(last_frame.line or '')}</code>"
        )
    else:
        formatted_traceback = (
            f"<b>Name:</b> <code>{html.escape(exception.__class__.__name__)}</code>\n"
            f"<b>Message:</b> <code>{html.escape(str(exception))}</code>"
        )

    debug_info = f"user: @{user_username} {user_id}\n{request}\n"

    await bot.send_message(
        chat_id=config.settings.owner_id,
        text=(
            f"<b>❌ Error info:</b>\n"
            f"<blockquote>{formatted_traceback}</blockquote>\n\n"
            f"<b>💻 Debug info:</b>\n"
            f"<blockquote>{html.escape(debug_info)}</blockquote>"
        ),
        disable_web_page_preview=True,
    )

    logging.error(
        f"Error in user @{user_username} ({user_id})\n"
        f"Request: {request}\n"
        f"Exception: {exception}\n"
        f"Traceback:\n{traceback.format_exc()}"
    )


@router.message(Command(commands=["error"]))
async def error_command_handler(message: Message, config: Config):
    if message.from_user is None or message.from_user.id != config.settings.owner_id:
        return await message.answer("You are not allowed to use this command.")

    raise Exception("This is a test error for debugging purposes.")
