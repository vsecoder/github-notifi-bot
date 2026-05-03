from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from app.db.functions import User
from app.utils.hooks import HookError, validate

router = Router()


@router.message(Command(commands=["token"]))
async def cmd_token(message: Message):
    if message.from_user is None:
        return
    if message.chat.id != message.from_user.id:
        return await message.answer(
            "Please use /token in private chat — your token is sensitive."
        )

    parts = (message.text or "").split()
    if len(parts) != 2:
        return await message.answer(
            "Invalid command. Use <code>/token &lt;your_personal_access_token&gt;</code>"
        )

    token = parts[1]
    result = validate(token)
    if isinstance(result, HookError):
        return await message.answer(f"❌ {result.message}")

    await User.write_token(message.from_user.id, token)
    await message.answer(
        "✅ Token saved. Use <code>/token &lt;new_token&gt;</code> later to replace it."
    )
