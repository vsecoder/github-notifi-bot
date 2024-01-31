from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from app.db.functions import User
from app.utils.hooks import validate

router = Router()


@router.message(Command(commands=["token"]))
async def cmd_start(message: Message):
    if len(message.text.split()) != 2:
        return await message.answer(
            "Invalid command. Use <code>/token token</code>",
            parse_mode="HTML",
        )

    token = message.text.split()[1]

    if not validate(token):
        return await message.answer("Invalid token.")

    await User.write_token(message.from_user.id, token)

    await message.answer("Token saved, /token <token> to change another.")
