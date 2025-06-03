from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from app.db.functions import User

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message):
    user_id = message.from_user.id

    text = (
        "Hello! <b>I’m a GitHub notifier bot</b> designed to keep you updated "
        "on events happening in your public and private GitHub repositories.\n"
        "<i><u>I rely on webhooks</u> to deliver real-time notifications, "
        "so please note that if you don’t have permission to create webhooks "
        "on your repositories, the bot won’t be able to work properly.</i>\n"
        "Learn more: https://habr.com/ru/articles/791006\n"
        "Source code: https://github.com/vsecoder/github-notifi-bot\n\n"
    )

    if not await User.is_registered(user_id):
        if message.chat.id != user_id:
            return await message.answer(
                "You are not registered. Please, send /start command in private chat with me to register."
            )
        await User.register(user_id)
        text += (
            "Now you need get your GitHub token and send it to me. You can get it by following this link:\n"
            "https://telegra.ph/Poluchenie-tokena-GitHub-01-30"
        )

    user = await User.get(telegram_id=user_id)

    if user.token:
        text += (
            "You already have token. Now you can send repository name, for get information about it, "
            "and integration commands, for example: <code>/integrate hikariatama/Hikka</code>"
        )

    await message.answer(text)
