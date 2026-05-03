"""Handlers for the persistent reply keyboard in DM.

Each tap on a reply button arrives as a regular text message whose body equals
the button label; we match by exact text and either start a dialog or show a
placeholder for the not-yet-implemented sections.
"""
from aiogram import F, Router
from aiogram.types import Message
from aiogram_dialog import DialogManager, StartMode

from app.dialogs.token import TokenSG
from app.keyboards.main_menu import (
    BTN_CONNECT,
    BTN_HELP,
    BTN_MY_CHATS,
    BTN_REPOS,
)

router = Router()
router.message.filter(F.chat.type == "private")


@router.message(F.text == BTN_CONNECT)
async def open_connect(message: Message, dialog_manager: DialogManager) -> None:
    await dialog_manager.start(TokenSG.main, mode=StartMode.RESET_STACK)


@router.message(F.text == BTN_HELP)
async def open_help(message: Message) -> None:
    # Reuse the existing /help text rendering.
    from app.handlers.user.start import cmd_help

    await cmd_help(message)


@router.message(F.text == BTN_REPOS)
async def open_repos(message: Message) -> None:
    await message.answer(
        "🚧 Repositories browser is coming soon.\n"
        "For now, send a repo name (<code>owner/repo</code>) here to view its "
        "summary, or run <code>/integrate owner/repo</code> in a group."
    )


@router.message(F.text == BTN_MY_CHATS)
async def open_my_chats(message: Message) -> None:
    await message.answer(
        "🚧 Cross-chat overview is coming soon. "
        "Until then, run <code>/integrations</code> in a specific group."
    )
