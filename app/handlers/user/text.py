from aiogram import Router
from aiogram.types import Message

from app.db.functions import User
from app.utils.hooks import check_repo

router = Router()


@router.message()
async def text_handler(message: Message):
    if getattr(message, "text", None) is None:
        return

    if not await User.is_registered(message.from_user.id):
        await message.answer(
            "You are not registered. Please, use /start command to register."
        )
        return

    if "/" not in message.text:
        await User.write_token(message.from_user.id, message.text)
        await message.answer("Token saved.")
        return await message.answer(
            "Now you can send repository name, for example: <b>hikariatama/Hikka</b>"
        )

    user = await User.get(telegram_id=message.from_user.id)

    repo = check_repo(user.token, message.text)
    if type(repo) == dict:
        return await message.answer("Repository not found.")

    if message.from_user.id == message.chat.id:
        text = (
            f"📐 <b><a href='https://github.com/{repo.full_name}'>{repo.full_name}</a></b> {repo.stargazers_count} ⭐️ \n"
            f"<i>{repo.description if repo.description else 'No description'}</i>\n\n"
            f"Run in chat <code>/integrate {repo.full_name}</code> to integrate this repository "
            "and get notifications about new commits."
        )

        return await message.answer(text)
