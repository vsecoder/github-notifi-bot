from aiogram import Router
from aiogram.types import Message

from app.db.functions import User
from app.utils.hooks import check_repo, validate

router = Router()


@router.message()
async def text_handler(message: Message):
    if getattr(message, "text", None) is None:
        return

    if message.chat.id != message.from_user.id:
        return

    if not await User.is_registered(message.from_user.id):
        await message.answer(
            "You are not registered. Please, use /start command to register."
        )
        return

    user = await User.get(telegram_id=message.from_user.id)

    if "/" not in message.text:
        if not user.token:
            if not validate(message.text):
                return await message.answer("Invalid token.")

            await User.write_token(message.from_user.id, message.text)
            await message.answer("Token saved, /token <token> to change another.")

            return await message.answer(
                "Now you can send repository name, for example: <b>hikariatama/Hikka</b>"
            )

    repo = check_repo(user.token, message.text)
    if type(repo) == dict:
        return await message.answer("Repository not found.")

    if message.from_user.id == message.chat.id:
        text = (
            f"📐 <b>{'🔒' if repo.private else ''} <a href='https://github.com/{repo.full_name}'>"
            f"{repo.full_name}</a></b> {repo.stargazers_count} ⭐️ \n"
            f"<i>{repo.description if repo.description else 'No description'}</i>\n"
            f"Run in chat <code>/integrate {repo.full_name}</code> to integrate this repository "
            "and get notifications about new commits."
        )

        return await message.answer(text)
