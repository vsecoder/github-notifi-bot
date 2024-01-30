from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from app.db.functions import User

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message):
    user_id = message.from_user.id

    text = "<b>I'm a GitHub notifier bot.</b> I can notify you about events (commits) in your public/private GitHub repositories.\n\n"

    if not await User.is_registered(user_id):
        if message.chat.id != user_id:
            return await message.answer(
                "You are not registered. Please, send /start command in private chat with me to register."
            )
        await User.register(user_id)
        text += (
            "Now you need get your GitHub token and send it to me. You can get it here:\n"
            "<a href='https://telegra.ph/Poluchenie-tokena-GitHub-01-30'>link</a>"
        )

    user = await User.get(telegram_id=user_id)

    if user.token:
        text += (
            "You already have token. Now you can send repository name, for get information about it, "
            "and integration commands, for example: <code>/integrate hikariatama/Hikka</code>"
        )

    await message.answer(
        text,
        disable_web_page_preview=True,
        parse_mode="HTML",
    )
