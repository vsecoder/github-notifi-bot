from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

from app.db.functions import User

router = Router()


WELCOME_HEADER = (
    "👋 <b>Hi! I'm a GitHub Notifier bot.</b>\n\n"
    "I deliver real-time notifications about your repositories "
    "(commits, issues, pull requests, stars, forks) to Telegram chats — "
    "<b>via GitHub webhooks</b>.\n"
)

REQUIREMENTS = (
    "\n⚠️ <b>Before you start — important:</b>\n"
    "• You must be the <b>owner</b> of the repository, or have <b>admin / maintain</b> "
    "access to it. Only such users can install webhooks. This is a GitHub limitation, "
    "not a bot one.\n"
    "• You need a <b>Personal Access Token</b> with these scopes:\n"
    "    – <code>admin:repo_hook</code> — required (to manage webhooks)\n"
    "    – <code>repo</code> — required for <b>private</b> repositories\n"
    "• I have to be added to the target group as an <b>administrator</b>.\n"
    "\n📚 How to create a token: https://telegra.ph/Poluchenie-tokena-GitHub-01-30\n"
    "📦 Source code: https://github.com/vsecoder/github-notifi-bot\n"
)

QUICK_START_NEW = (
    "\n🚀 <b>Quick start:</b>\n"
    "1. Send your <b>Personal Access Token</b> to me here in DM.\n"
    "2. Add me to a group as an <b>administrator</b>.\n"
    "3. In the group, run: <code>/integrate username/repository</code>\n"
    "4. Use <code>/events</code> in the group to toggle event types.\n"
    "5. Use <code>/set_topic</code> in a forum topic if you want notifications "
    "delivered to a specific topic.\n"
)

QUICK_START_HAS_TOKEN = (
    "\n✅ Your token is already saved.\n"
    "• Add me to a group as <b>administrator</b>.\n"
    "• Run <code>/integrate username/repository</code> in that group.\n"
    "• Use <code>/token &lt;new_token&gt;</code> here to replace your token.\n"
    "• In DM you can also send a repo name like <code>hikariatama/Hikka</code> "
    "to view its summary.\n"
)


@router.message(CommandStart())
async def cmd_start(message: Message):
    user_id = message.from_user.id

    if message.chat.id != user_id:
        return await message.answer(
            "Please send /start to me in <b>private chat</b> to register."
        )

    if not await User.is_registered(user_id):
        await User.register(user_id)

    user = await User.get(telegram_id=user_id)

    text = WELCOME_HEADER + REQUIREMENTS
    text += QUICK_START_HAS_TOKEN if user.token else QUICK_START_NEW

    await message.answer(text)


@router.message(Command(commands=["help"]))
async def cmd_help(message: Message):
    user = (
        await User.get_or_none(telegram_id=message.from_user.id)
        if message.chat.id == message.from_user.id
        else None
    )
    text = WELCOME_HEADER + REQUIREMENTS
    text += QUICK_START_HAS_TOKEN if (user and user.token) else QUICK_START_NEW
    await message.answer(text)
