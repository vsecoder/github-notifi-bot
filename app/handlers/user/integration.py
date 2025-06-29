from aiogram import Bot, Router
from aiogram.filters import Command
from aiogram.types import Message

from app.utils.hooks import check_repo, create_webhook
from app.db.functions import Chat, Integration, User
from app.config import Config

import html

router = Router()


@router.message(Command(commands=["integrate"]))
async def integrate_handler(message: Message, bot: Bot, config: Config):
    if message.chat.id == message.from_user.id:
        return await message.answer(
            "You can integrate repository only in group or channel."
        )

    await Chat.ensure_registered(message.chat.id)

    admins = [
        admin.user.id for admin in await bot.get_chat_administrators(message.chat.id)
    ]
    if message.from_user.id not in admins:
        return await message.answer(
            "You are not administrator. Only administrators can integrate repositories."
        )

    if not await User.is_registered(message.from_user.id):
        return await message.answer(
            "You are not registered. Please, use /start command in private chat with me to register."
        )

    parts = message.text.split()
    if len(parts) != 2:
        return await message.answer(
            "Invalid command. Use <code>/integrate username/repository_name</code>"
        )
    repo_name = parts[1]

    user = await User.get(telegram_id=message.from_user.id)
    repo = check_repo(user.token, repo_name)
    if isinstance(repo, dict):
        return await message.answer("Repository not found.")

    existing = await Integration.get_by_chat_and_repo(
        chat_id=message.chat.id, repo_name=repo_name
    )
    if existing:
        return await message.answer("Repository already integrated.")

    integration, exiting = await Chat.add_integration(
        chat_id=message.chat.id,
        user_id=user.id,
        repository_name=repo_name,
    )

    if not exiting:
        result = create_webhook(
            config.api.host, integration.integration_token, user.token, repo_name
        )

        if result:
            await message.answer(
                f"Error while creating webhook for repository <code>{repo_name}</code>.\n"
                f"{html.escape(result['message'])}\n\n"
            )
            await message.answer(
                f"<code>{result['error']}</code>"
            )
            return

    return await message.answer(
        f"Repository <code>{repo_name}</code> integrated. Now you will receive notifications about new commits.",
    )


@router.message(Command(commands=["integrations"]))
async def integrations_handler(message: Message):
    if message.chat.id == message.from_user.id:
        return await message.answer(
            "You can get integrations only in group or channel."
        )

    await Chat.ensure_registered(message.chat.id)

    integrations = await Chat.get_integrations(message.chat.id)
    if not integrations:
        return await message.answer("No integrations.")

    text = "<b>Integrations:</b>\n\n"
    for integration in integrations:
        text += f"<code>{integration.repository_name}</code>\n"

    await message.answer(text)


@router.message(Command(commands=["delete"]))
async def delete_handler(message: Message):
    if message.chat.id == message.from_user.id:
        return await message.answer(
            "You can delete integrations only in group or channel."
        )

    await Chat.ensure_registered(message.chat.id)

    parts = message.text.split()
    if len(parts) != 2:
        return await message.answer(
            "Invalid command. Use <code>/delete repository_name</code>"
        )
    repo_name = parts[1]

    integration = await Integration.get_by_chat_and_repo(
        chat_id=message.chat.id, repo_name=repo_name
    )
    if not integration:
        return await message.answer("Repository not integrated.")

    await Integration.delete(integration.id)

    await message.answer(
        f"Repository <code>{repo_name}</code> deleted.",
    )


@router.message(Command(commands=["set_topic"]))
async def set_topic_handler(message: Message, bot: Bot, config: Config):
    if message.chat.id == message.from_user.id:
        return await message.answer("You can set topic only in group or channel.")

    await Chat.ensure_registered(message.chat.id)

    admins = [
        admin.user.id for admin in await bot.get_chat_administrators(message.chat.id)
    ]
    if message.from_user.id not in admins:
        return await message.answer(
            "You are not administrator. Only administrators can set topic."
        )

    topic_id = message.message_thread_id
    if not topic_id:
        return await message.answer("This message is not in thread.")

    await Chat.set_topic(message.chat.id, topic_id)

    await message.answer("Topic set.")
