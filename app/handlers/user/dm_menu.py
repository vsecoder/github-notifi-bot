"""Handlers for the persistent reply keyboard in DM.

Each tap on a reply button arrives as a regular text message whose body equals
the button label; we match by exact text and either start a dialog or open
help.

Reply-keyboard taps are top-level navigation: starting a dialog with
``mode=StartMode.RESET_STACK`` collapses any in-progress dialog so the new
action runs in a clean context.
"""
from aiogram import F, Router
from aiogram.types import Message
from aiogram_dialog import DialogManager, StartMode

from app.dialogs.my_chats import MyChatsSG
from app.dialogs.repos import ReposSG
from app.dialogs.token import TokenSG
from app.keyboards.main_menu import (
    BTN_CONNECT,
    BTN_HELP,
    BTN_MY_CHATS,
    BTN_REPOS,
)

router = Router()
router.message.filter(F.chat.type == "private")


async def _close_active_dialog(manager: DialogManager) -> None:
    if manager.current_context() is not None:
        await manager.reset_stack()


@router.message(F.text == BTN_CONNECT)
async def open_connect(message: Message, dialog_manager: DialogManager) -> None:
    await dialog_manager.start(TokenSG.main, mode=StartMode.RESET_STACK)


@router.message(F.text == BTN_REPOS)
async def open_repos(message: Message, dialog_manager: DialogManager) -> None:
    await dialog_manager.start(ReposSG.orgs, mode=StartMode.RESET_STACK)


@router.message(F.text == BTN_MY_CHATS)
async def open_my_chats(
    message: Message, dialog_manager: DialogManager
) -> None:
    await dialog_manager.start(MyChatsSG.chats, mode=StartMode.RESET_STACK)


@router.message(F.text == BTN_HELP)
async def open_help(message: Message, dialog_manager: DialogManager) -> None:
    await _close_active_dialog(dialog_manager)
    from app.handlers.user.start import cmd_help

    await cmd_help(message)
