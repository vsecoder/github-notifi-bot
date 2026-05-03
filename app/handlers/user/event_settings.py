from aiogram import Bot, Router, F
from aiogram.filters import Command
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)

from app.db.functions import EventSetting, Chat
from app.db.models import EventType

router = Router()


def build_keyboard(settings: list[EventSetting]) -> InlineKeyboardMarkup:
    buttons = [
        InlineKeyboardButton(
            text=f"{'✅' if s.enabled else '❌'} {s.event_type}",
            callback_data=f"toggle_event:{s.event_type}",
        )
        for s in settings
    ]
    return InlineKeyboardMarkup(
        inline_keyboard=[buttons[i : i + 2] for i in range(0, len(buttons), 2)]
    )


async def _is_admin(bot: Bot, chat_id: int, user_id: int) -> bool:
    admins = [admin.user.id for admin in await bot.get_chat_administrators(chat_id)]
    return user_id in admins


@router.message(Command("events"))
async def show_event_settings(message: Message, bot: Bot):
    if message.chat.id == message.from_user.id:
        return await message.answer(
            "You can manage event settings only in a group or channel."
        )

    if not await _is_admin(bot, message.chat.id, message.from_user.id):
        return await message.answer(
            "Only administrators can change event settings."
        )

    await Chat.ensure_registered(message.chat.id)

    settings = await EventSetting.for_chat(message.chat.id)
    await message.answer(
        "✨ Github events settings",
        reply_markup=build_keyboard(settings),
        message_thread_id=message.message_thread_id,
    )


@router.callback_query(F.data.startswith("toggle_event:"))
async def toggle_event_setting(callback: CallbackQuery, bot: Bot):
    if not await _is_admin(bot, callback.message.chat.id, callback.from_user.id):
        return await callback.answer(
            "Only administrators can change event settings.", show_alert=True
        )

    event_type_str = callback.data.split(":")[1]
    try:
        event_type = EventType(event_type_str)
    except ValueError:
        return await callback.answer("Unknown event type.", show_alert=True)

    setting = await EventSetting.get_or_none(
        chat_id=callback.message.chat.id, event_type=event_type.value
    )
    if setting is None:
        return await callback.answer("Setting not found.", show_alert=True)

    setting.enabled = not setting.enabled
    await setting.save()

    updated = await EventSetting.for_chat(callback.message.chat.id)
    await callback.message.edit_reply_markup(reply_markup=build_keyboard(updated))
    await callback.answer(
        f"{event_type.value} {'enabled' if setting.enabled else 'disabled'}"
    )
