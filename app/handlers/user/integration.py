from aiogram import Bot, Router
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.filters import Command
from aiogram.types import Message

from app.utils.hooks import HookError, check_repo, create_webhook
from app.db.functions import Chat, Integration, User
from app.config import Config
from app.services.integration import integrate_repo

router = Router()


async def _get_admin_ids(bot: Bot, chat_id: int) -> list[int] | None:
    """Returns admin telegram ids, or None if the bot can't read admins."""
    try:
        admins = await bot.get_chat_administrators(chat_id)
    except (TelegramBadRequest, TelegramForbiddenError):
        return None
    return [a.user.id for a in admins]


async def _require_group_admin(message: Message, bot: Bot) -> bool:
    if message.from_user is None:
        return False

    if message.chat.id == message.from_user.id:
        await message.answer(
            "This command works only in a <b>group or channel</b>."
        )
        return False

    admin_ids = await _get_admin_ids(bot, message.chat.id)
    if admin_ids is None:
        await message.answer(
            "I can't read the admin list in this chat. "
            "Please grant me <b>administrator</b> rights and try again."
        )
        return False

    if message.from_user.id not in admin_ids:
        await message.answer(
            "Only chat <b>administrators</b> can use this command."
        )
        return False

    return True


@router.message(Command(commands=["integrate"]))
async def integrate_handler(message: Message, bot: Bot, config: Config):
    if not await _require_group_admin(message, bot):
        return
    assert message.from_user is not None  # narrowed by _require_group_admin

    if not await User.is_registered(message.from_user.id):
        return await message.answer(
            "You're not registered. Send /start to me in private chat first."
        )

    parts = (message.text or "").split()
    if len(parts) != 2:
        return await message.answer(
            "Invalid command. Use <code>/integrate username/repository</code>"
        )
    repo_name = parts[1]

    result = await integrate_repo(
        bot=bot,
        chat_id=message.chat.id,
        telegram_user_id=message.from_user.id,
        repo_name=repo_name,
        host=config.api.host,
        skip_admin_check=True,  # already verified via _require_group_admin
    )
    if result.success:
        await message.answer(result.message)
    else:
        await message.answer(f"❌ {result.message}")


@router.message(Command(commands=["integrations"]))
async def integrations_handler(message: Message):
    if message.from_user is not None and message.chat.id == message.from_user.id:
        return await message.answer(
            "This command works only in a group or channel."
        )

    await Chat.ensure_registered(message.chat.id)

    integrations = await Chat.get_integrations(message.chat.id)
    if not integrations:
        return await message.answer("No integrations in this chat yet.")

    text = "<b>Integrations:</b>\n\n"
    for integration in integrations:
        text += f"• <code>{integration.repository_name}</code>\n"

    await message.answer(text)


@router.message(Command(commands=["delete"]))
async def delete_handler(message: Message, bot: Bot):
    if not await _require_group_admin(message, bot):
        return

    parts = (message.text or "").split()
    if len(parts) != 2:
        return await message.answer(
            "Invalid command. Use <code>/delete username/repository</code>"
        )
    repo_name = parts[1]

    integration = await Integration.get_by_chat_and_repo(
        chat_id=message.chat.id, repo_name=repo_name
    )
    if not integration:
        return await message.answer(
            f"Repository <code>{repo_name}</code> is not integrated in this chat."
        )

    await Integration.delete_by_id(integration.id)

    await message.answer(
        f"✅ Repository <code>{repo_name}</code> removed.\n"
        "<i>Note: this only removes the integration from the bot. "
        "The webhook on GitHub side stays — delete it manually in repo Settings → Webhooks "
        "if you want it gone there too.</i>"
    )


@router.message(Command(commands=["set_topic"]))
async def set_topic_handler(message: Message, bot: Bot, config: Config):
    if not await _require_group_admin(message, bot):
        return

    topic_id = message.message_thread_id
    if not topic_id:
        return await message.answer(
            "Send <code>/set_topic</code> from inside a <b>forum topic</b> — "
            "I'll deliver notifications to that topic."
        )

    await Chat.ensure_registered(message.chat.id)
    await Chat.set_topic(message.chat.id, topic_id)

    await message.answer("✅ Topic set. Notifications will go here.")
