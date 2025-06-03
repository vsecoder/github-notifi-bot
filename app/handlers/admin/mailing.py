from aiogram import Bot, Router
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.exceptions import TelegramAPIError

from app.db.functions import User, Chat
from app.config import Config

router = Router()


@router.message(Command(commands=["mail"]))
async def mail_handler(message: Message, bot: Bot, config: Config):
    if message.chat.id != config.settings.owner_id:
        return await message.answer("This command can only be used by the bot owner.")

    args = message.text.split(maxsplit=2)

    if len(args) < 2:
        return await message.answer("Usage:\n/mail [users|chats|all] <message>")

    target = args[1].lower()
    text = args[2] if len(args) > 2 else ""

    if not text:
        return await message.answer("You must provide a message to send.")

    if target not in ["users", "chats", "all"]:
        return await message.answer("Invalid target. Use 'users', 'chats' or 'all'.")

    users = await User.all() if target in ["users", "all"] else []
    chats = await Chat.all() if target in ["chats", "all"] else []

    recipients_users = [u.telegram_id for u in users]
    recipients_chats = [{"id": c.chat_id, "topic": c.topic_id} for c in chats]

    await message.answer(f"Broadcast started.\nTotal recipients: {len(recipients_users) + len(recipients_chats)}")

    sent_users = 0
    sent_chats = 0
    for tg_id in recipients_users:
        try:
            await bot.send_message(
                chat_id=tg_id, text=text, disable_web_page_preview=True
            )
            sent_users += 1
        except TelegramAPIError:
            continue

    for chat in recipients_chats:
        try:
            await bot.send_message(
                chat_id=chat["id"],
                text=text,
                disable_web_page_preview=True,
                message_thread_id=chat.get("topic", None) if chat.get("topic") else None,
            )
            sent_chats += 1
        except TelegramAPIError:
            continue

    await message.answer(f"Broadcast finished.\nSuccessfully delivered to {sent_users} users and {sent_chats} chats.")
