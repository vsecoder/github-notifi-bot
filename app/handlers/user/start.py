from aiogram import Router
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.types import Message

from app.db.functions import Installation, User
from app.keyboards.main_menu import main_menu_keyboard

router = Router()


WELCOME = (
    "👋 <b>Hi! I'm a GitHub Notifier bot.</b>\n\n"
    "I deliver real-time notifications from your GitHub repositories — "
    "commits, pull requests, issues, releases, CI runs and more — into "
    "Telegram chats via GitHub webhooks.\n\n"
    "📌 <b>First step:</b> tap <b>🔌 Connect</b> below to authorize me with "
    "GitHub. Then use <b>➕ Add to chat</b> to invite me to a group, and "
    "<b>🏢 Repos</b> to pick what to integrate.\n\n"
    "📦 Source: https://github.com/vsecoder/github-notifi-bot"
)


HELP = (
    "<b>Buttons in DM:</b>\n"
    "• <b>🔌 Connect</b> — manage your GitHub authorization (App or PAT)\n"
    "• <b>➕ Add to chat</b> — invite me to a group via Telegram's chat picker\n"
    "• <b>🏢 Repos</b> — browse repositories and integrate them into chats\n"
    "• <b>💬 My chats</b> — overview of chats with your integrations\n"
    "• <b>❓ Help</b> — show this message\n\n"
    "<b>Commands in groups (admins only):</b>\n"
    "• <code>/integrate owner/repo</code> — add a repo to this chat\n"
    "• <code>/integrations</code> — list and manage repos integrated here\n"
    "• <code>/events</code> — toggle which event types are delivered\n"
    "• <code>/set_topic</code> — deliver to current forum topic\n"
    "• <code>/reinstall</code> — re-sync GitHub webhook subscriptions\n"
    "• <code>/delete owner/repo</code> — remove an integration\n\n"
    "📦 Source: https://github.com/vsecoder/github-notifi-bot"
)


async def _handle_install_deeplink(arg: str, message: Message) -> bool:
    """Handle ``/start installed_<installation_id>`` deep-link from the
    GitHub App Setup-URL callback. Returns True if the arg was a valid
    install deep-link and the message was sent."""
    if not arg.startswith("installed_"):
        return False
    try:
        installation_id = int(arg[len("installed_"):])
    except ValueError:
        return False
    inst = await Installation.get_by_installation_id(installation_id)
    if inst is None:
        return False
    await message.answer(
        f"✅ <b>GitHub App installed</b> for <code>{inst.account_login}</code>.\n\n"
        "Tap <b>🏢 Repos</b> on the keyboard to see the repositories "
        "I can now reach.",
        reply_markup=main_menu_keyboard(),
    )
    return True


@router.message(CommandStart())
async def cmd_start(message: Message, command: CommandObject):
    if message.from_user is None:
        return
    if message.chat.id != message.from_user.id:
        return await message.answer(
            "Please send /start to me in <b>private chat</b> to register."
        )

    user_id = message.from_user.id
    if not await User.is_registered(user_id):
        await User.register(user_id)

    arg = (command.args or "").strip()
    if await _handle_install_deeplink(arg, message):
        return

    await message.answer(WELCOME, reply_markup=main_menu_keyboard())


@router.message(Command(commands=["help"]))
async def cmd_help(message: Message):
    is_dm = (
        message.from_user is not None
        and message.chat.id == message.from_user.id
    )
    if is_dm:
        await message.answer(HELP, reply_markup=main_menu_keyboard())
    else:
        await message.answer(HELP)
