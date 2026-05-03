"""DM-only ``/install`` command.

Generates a user-specific install URL with an HMAC-signed ``state`` so the
Setup-URL callback can attribute the new installation to this Telegram user.
"""
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from app.config import Config
from app.utils.github_app import install_url

router = Router()
router.message.filter(F.chat.type == "private")


@router.message(Command(commands=["install"]))
async def cmd_install(message: Message, config: Config):
    if message.from_user is None:
        return

    if not config.github_app.is_configured:
        return await message.answer(
            "GitHub App authentication isn't configured on this bot. "
            "Use <b>🔌 Connect</b> on the keyboard to set a personal access "
            "token instead."
        )

    url = install_url(config, message.from_user.id)
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔗 Install GitHub App", url=url)]
        ]
    )
    await message.answer(
        "Click the button below to install the GitHub App on your account "
        "or organisation. Pick the repositories you want me to access — "
        "you'll be redirected back here automatically.",
        reply_markup=kb,
    )
