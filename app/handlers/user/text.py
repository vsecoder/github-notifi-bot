from aiogram import Router
from aiogram.types import Message

from app.db.functions import User
from app.utils.hooks import HookError, check_repo, validate

router = Router()


@router.message()
async def text_handler(message: Message):
    text = message.text
    if text is None or message.from_user is None:
        return

    if message.chat.id != message.from_user.id:
        return

    if not await User.is_registered(message.from_user.id):
        return await message.answer(
            "You are not registered. Please use /start to register."
        )

    user = await User.get(telegram_id=message.from_user.id)

    if not user.token:
        if text.startswith("/"):
            return
        result = validate(text)
        if isinstance(result, HookError):
            return await message.answer(f"❌ {result.message}")

        await User.write_token(message.from_user.id, text)
        await message.answer(
            "✅ Token saved. Use <code>/token &lt;new_token&gt;</code> to replace it later."
        )
        return await message.answer(
            "Now add me as <b>administrator</b> to the group where you want notifications, "
            "and run <code>/integrate username/repository</code> there.\n"
            "You can also send me a repo name (e.g. <code>hikariatama/Hikka</code>) to view its summary."
        )

    if text.startswith("/"):
        return

    repo = check_repo(user.token, text)
    if isinstance(repo, HookError):
        return await message.answer(f"❌ {repo.message}")

    summary = (
        f"📐 <b>{'🔒' if repo.private else ''} <a href='https://github.com/{repo.full_name}'>"
        f"{repo.full_name}</a></b> {repo.stargazers_count} ⭐️\n"
        f"<i>{repo.description if repo.description else 'No description'}</i>\n\n"
        f"Run in a group: <code>/integrate {repo.full_name}</code> "
        "to start receiving notifications."
    )
    await message.answer(summary)
