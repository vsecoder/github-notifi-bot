"""Handlers for the persistent reply keyboard in DM.

Each tap on a reply button arrives as a regular text message whose body equals
the button label; we match by exact text and either start a dialog or open
help / a deep-link prompt.

Reply-keyboard taps are top-level navigation: starting a dialog with
``mode=StartMode.RESET_STACK`` collapses any in-progress dialog so the new
action runs in a clean context.
"""
from aiogram import F, Router
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from aiogram_dialog import DialogManager, StartMode
from aiogram_dialog.api.exceptions import NoContextError

from app.config import Config
from app.dialogs.my_chats import MyChatsSG
from app.dialogs.repos import ReposSG
from app.dialogs.token import TokenSG
from app.keyboards.main_menu import (
    BTN_ADD_TO_CHAT,
    BTN_CONNECT,
    BTN_HELP,
    BTN_MY_CHATS,
    BTN_REPOS,
)
from app.utils.filters import IS_DM

router = Router()
router.message.filter(IS_DM)


async def _close_active_dialog(manager: DialogManager) -> None:
    # ``current_context()`` raises ``NoContextError`` (not returns None) when
    # there's no active dialog — e.g. user tapped the same reply button twice
    # in a row.
    try:
        manager.current_context()
    except NoContextError:
        return
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


@router.message(F.text == BTN_ADD_TO_CHAT)
async def open_add_to_chat(
    message: Message, dialog_manager: DialogManager, config: Config
) -> None:
    await _close_active_dialog(dialog_manager)
    if not config.bot.username:
        await message.answer(
            "Bot username isn't configured — ping the admin to set "
            "<code>bot.username</code> in config.toml."
        )
        return
    # Request admin rights upfront so we can:
    #   • pin_messages — pin important releases (TODO feature)
    #   • manage_topics — create / route messages to forum topics
    # Telegram will show the user a confirmation dialog with these rights.
    url = (
        f"https://t.me/{config.bot.username}"
        "?startgroup=true&admin=pin_messages+manage_topics"
    )
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ Pick a group", url=url)]
        ]
    )
    await message.answer(
        "Tap below — Telegram will let you pick a group and confirm me as "
        "an administrator with these permissions:\n"
        "• <b>Pin messages</b> — for pinning important releases\n"
        "• <b>Manage topics</b> — for delivering into forum topics\n\n"
        "After adding, come back here and tap <b>🏢 Repos</b> to integrate "
        "a repository, or run <code>/integrate owner/repo</code> directly "
        "in the group.",
        reply_markup=kb,
    )


@router.message(F.text == BTN_HELP)
async def open_help(message: Message, dialog_manager: DialogManager) -> None:
    await _close_active_dialog(dialog_manager)
    from app.handlers.user.start import cmd_help

    await cmd_help(message)
