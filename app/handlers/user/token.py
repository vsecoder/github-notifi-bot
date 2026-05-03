"""/token command.

* ``/token`` (no arg) — opens the Token management dialog.
* ``/token <PAT>``   — legacy shortcut: validates and saves the token inline,
  then auto-deletes the message that contained the secret.
"""
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from aiogram_dialog import DialogManager, StartMode

from app.db.functions import User
from app.dialogs.token import TokenSG
from app.utils.hooks import HookError, validate

router = Router()


@router.message(Command(commands=["token"]))
async def cmd_token(message: Message, dialog_manager: DialogManager):
    if message.from_user is None:
        return
    if message.chat.id != message.from_user.id:
        return await message.answer(
            "Please use /token in private chat — your token is sensitive."
        )

    parts = (message.text or "").split(maxsplit=1)
    if len(parts) == 2:
        # Legacy shortcut: validate and save inline.
        token = parts[1].strip()
        try:
            await message.delete()
        except Exception:
            pass

        result = validate(token)
        if isinstance(result, HookError):
            return await message.answer(f"❌ {result.message}")

        if await User.get_or_none(telegram_id=message.from_user.id) is None:
            await User.register(message.from_user.id)
        await User.write_token(message.from_user.id, token)
        return await message.answer(
            "✅ Token saved. Tap <b>🔌 Connect</b> on the keyboard to manage it."
        )

    # No argument — open the dialog.
    await dialog_manager.start(TokenSG.main, mode=StartMode.RESET_STACK)
