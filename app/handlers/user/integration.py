from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from app.config import Config
from app.db.functions import Chat, Integration, User
from app.handlers.user.event_settings import render_events_message
from app.keyboards.integration import (
    INTEGRATIONS_HEADER,
    build_integrations_keyboard,
    build_management_keyboard,
)
from app.services.integration import integrate_repo
from app.utils.aiogram_helpers import accessible_message, safe_edit_text
from app.utils.group_admin import get_admin_ids

router = Router()


async def _require_group_admin(message: Message, bot: Bot) -> bool:
    if message.from_user is None:
        return False

    if message.chat.id == message.from_user.id:
        await message.answer(
            "This command works only in a <b>group or channel</b>."
        )
        return False

    admin_ids = await get_admin_ids(bot, message.chat.id)
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


# ---------- /integrate ----------

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
        config=config,
        skip_admin_check=True,  # already verified via _require_group_admin
    )
    if result.success:
        await message.answer(result.message)
    else:
        await message.answer(f"❌ {result.message}")


# ---------- /integrations (buttoned) ----------

def _parse_integration_id(callback: CallbackQuery) -> int | None:
    if callback.data is None:
        return None
    parts = callback.data.split(":")
    if len(parts) < 3:
        return None
    try:
        return int(parts[2])
    except ValueError:
        return None


@router.message(Command(commands=["integrations"]))
async def integrations_handler(message: Message):
    if (
        message.from_user is not None
        and message.chat.id == message.from_user.id
    ):
        return await message.answer(
            "This command works only in a group or channel."
        )

    await Chat.ensure_registered(message.chat.id)

    integrations = await Chat.get_integrations(message.chat.id)
    if not integrations:
        return await message.answer("No integrations in this chat yet.")

    await message.answer(
        INTEGRATIONS_HEADER,
        reply_markup=build_integrations_keyboard(integrations),
    )


@router.callback_query(F.data == "integ:list")
async def cb_integ_list(callback: CallbackQuery):
    msg = accessible_message(callback)
    if msg is None:
        return await callback.answer(
            "Original message is gone.", show_alert=True
        )

    integrations = await Chat.get_integrations(msg.chat.id)
    if not integrations:
        await safe_edit_text(msg, "No integrations in this chat anymore.")
        return await callback.answer()

    await safe_edit_text(
        msg,
        INTEGRATIONS_HEADER,
        reply_markup=build_integrations_keyboard(integrations),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("integ:open:"))
async def cb_integ_open(callback: CallbackQuery):
    msg = accessible_message(callback)
    if msg is None:
        return await callback.answer(
            "Original message is gone.", show_alert=True
        )

    integ_id = _parse_integration_id(callback)
    if integ_id is None:
        return await callback.answer("Bad button data.", show_alert=True)

    integration = await Integration.get_by_id(integ_id)
    if integration is None:
        return await callback.answer(
            "Integration not found (already deleted?).", show_alert=True
        )

    text = (
        f"<b>{integration.repository_name}</b>\n"
        f"<i>Added {integration.created_at:%Y-%m-%d %H:%M} UTC</i>\n"
        f"Auth source: <code>{integration.auth_source}</code>"
    )
    await safe_edit_text(
        msg, text, reply_markup=build_management_keyboard(integration.id)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("integ:del:"))
async def cb_integ_delete(callback: CallbackQuery, bot: Bot):
    msg = accessible_message(callback)
    if msg is None:
        return await callback.answer(
            "Original message is gone.", show_alert=True
        )

    admin_ids = await get_admin_ids(bot, msg.chat.id)
    if admin_ids is None or callback.from_user.id not in admin_ids:
        return await callback.answer(
            "Only chat administrators can delete integrations.",
            show_alert=True,
        )

    integ_id = _parse_integration_id(callback)
    if integ_id is None:
        return await callback.answer("Bad button data.", show_alert=True)

    integration = await Integration.get_by_id(integ_id)
    repo_name = integration.repository_name if integration else "?"
    if integration is not None:
        await Integration.delete_by_id(integration.id)

    integrations = await Chat.get_integrations(msg.chat.id)
    if not integrations:
        await safe_edit_text(
            msg,
            f"✅ <code>{repo_name}</code> removed.\n"
            "No integrations left in this chat.\n\n"
            "<i>The webhook on GitHub side stays — delete it manually in "
            "the repo's Settings → Webhooks if you want it gone there too.</i>",
        )
    else:
        await safe_edit_text(
            msg,
            f"✅ <code>{repo_name}</code> removed.\n\n" + INTEGRATIONS_HEADER,
            reply_markup=build_integrations_keyboard(integrations),
        )
    await callback.answer("Deleted.")


@router.callback_query(F.data == "integ:events")
async def cb_integ_events(
    callback: CallbackQuery, bot: Bot, config: Config
):
    msg = accessible_message(callback)
    if msg is None:
        return await callback.answer(
            "Original message is gone.", show_alert=True
        )

    admin_ids = await get_admin_ids(bot, msg.chat.id)
    if admin_ids is None or callback.from_user.id not in admin_ids:
        return await callback.answer(
            "Only chat administrators can change event settings.",
            show_alert=True,
        )

    text, kb = await render_events_message(msg.chat.id, config)
    await msg.answer(text, reply_markup=kb)
    await callback.answer()


# ---------- /delete ----------

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


# ---------- /set_topic ----------

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
