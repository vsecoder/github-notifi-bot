from aiogram import Bot, Router
from aiogram.filters import Command
from aiogram.types import Message

from app.utils.hooks import check_repo, create_webhook
from app.db.functions import Chat, Integration, User

from app.config import Config

router = Router()


@router.message(Command(commands=["integrate"]))
async def integrate_handler(message: Message, bot: Bot, config: Config):
    if message.chat.id == message.from_user.id:
        return await message.answer(
            "You can integrate repository only in group or channel."
        )

    if not await Chat.is_registered(message.chat.id):
        await Chat.register(message.chat.id)

    admins = await bot.get_chat_administrators(message.chat.id)
    admins = [admin.user.id for admin in admins]
    if message.from_user.id not in admins:
        return await message.answer(
            "You are not administrator. Only administrators can integrate repositories."
        )

    if not await User.is_registered(message.from_user.id):
        return await message.answer(
            "You are not registered. Please, use /start command in private chat with me to register."
        )

    if len(message.text.split()) != 2:
        return await message.answer(
            "Invalid command. Use <code>/integrate repository_name</code>",
            parse_mode="HTML",
        )

    repo = check_repo(
        (await User.get(telegram_id=message.from_user.id)).token,
        message.text.split()[1],
    )
    if type(repo) == dict:
        return await message.answer("Repository not found.")

    integrations = await Chat.get_integrations(message.chat.id)
    if repo.id in [i["integration_id"] for i in integrations]:
        return await message.answer("Repository already integrated.")

    await Integration.create_integration(repo=repo.full_name)
    integration = await Integration.get(repo=repo.full_name)
    user = await User.get(telegram_id=message.from_user.id)
    await Chat.add_integration(
        chat_id=message.chat.id,
        integration_id=integration.id,
        user_id=user.id,
    )

    create = create_webhook(
        config.api.host, integration.code, user.token, repo.full_name
    )

    if not create:
        await message.answer(
            f"Repository <code>{repo.full_name}</code> integrated. Now you will receive notifications about new commits.",
            parse_mode="HTML",
        )
    else:
        await message.answer(
            f"Error while creating webhook for repository <code>{repo.full_name}</code>.\n",
            f"{create['message']}\n\n",
            f"<code>{create['error']}</code>",
            parse_mode="HTML",
        )


@router.message(Command(commands=["integrations"]))
async def integrations_handler(message: Message):
    if message.chat.id == message.from_user.id:
        return await message.answer(
            "You can get integrations only in group or channel."
        )

    if not await Chat.is_registered(message.chat.id):
        await Chat.register(message.chat.id)

    Integrations = await Chat.get_integrations(message.chat.id)
    if not Integrations:
        return await message.answer("No integrations.")

    text = "<b>Integrations:</b>\n\n"
    for integration in Integrations:
        repo = await Integration.get(id=integration["integration_id"])
        text += f"<code>{repo.repo}</code>\n"

    await message.answer(text, parse_mode="HTML")


@router.message(Command(commands=["delete"]))
async def delete_handler(message: Message):
    if message.chat.id == message.from_user.id:
        return await message.answer(
            "You can delete integrations only in group or channel."
        )

    if not await Chat.is_registered(message.chat.id):
        await Chat.register(message.chat.id)

    if len(message.text.split()) != 2:
        return await message.answer(
            "Invalid command. Use <code>/delete repository_name</code>",
            parse_mode="HTML",
        )

    if len(message.text.split()) != 2:
        return await message.answer(
            "Invalid command. Use <code>/delete repository_name</code>",
            parse_mode="HTML",
        )
    repo = message.text.split()[1]

    integrations = await Chat.get_integrations(message.chat.id)
    integration = None

    for integration in integrations:
        integration = await Integration.get(id=integration["integration_id"])
        if integration.repo == repo:
            break

    if not integration:
        return await message.answer("Repository not integrated.")

    await Integration.delete(integration.id)

    await Chat.remove_integration(message.chat.id, integration.id)

    await message.answer(
        f"Repository <code>{repo}</code> deleted.",
        parse_mode="HTML",
    )
