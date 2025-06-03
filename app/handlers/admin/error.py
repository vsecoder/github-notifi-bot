from aiogram import Router
from aiogram.types import ErrorEvent
from aiogram.filters import Command

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

    try:
        user_id = update.callback_query.from_user.id
        user_username = update.callback_query.from_user.username
        request = f"callback_data: <code>{update.callback_query.data}</code>"
    except AttributeError:
        user_id = update.message.from_user.id
        user_username = update.message.from_user.username
        request = f"text: <code>{update.message.text}</code>"

    last_frame = traceback.extract_tb(exception.__traceback__)[-1]

    formatted_traceback = (
        f"<b>File:</b> <code>{html.escape(last_frame.filename)}</code>\n"
        f"<b>Line:</b> <code>{last_frame.lineno}</code>\n"
        f"<b>Name:</b> <code>{html.escape(exception.__class__.__name__)}</code>\n"
        f"<b>Function:</b> <code>{html.escape(last_frame.name)}</code>\n"
        f"<b>Message:</b> <code>{html.escape(str(exception))}</code>\n"
        f"<b>Code:</b> <code>{html.escape(last_frame.line)}</code>"
    )

    debug_info = f"user: @{user_username} {user_id}\n" f"{request}\n"

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
async def error_command_handler(message: ErrorEvent, config: Config):
    if message.from_user.id != config.settings.owner_id:
        return await message.answer("You are not allowed to use this command.")

    raise Exception("This is a test error for debugging purposes.")
