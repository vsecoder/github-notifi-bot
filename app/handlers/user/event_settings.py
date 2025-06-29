from aiogram import Router, F
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


@router.message(Command("events"))
async def show_event_settings(message: Message):
    chat = await Chat.get_chat(message.chat.id)
    await EventSetting.init_for_chat(chat.chat_id)

    existing = await EventSetting.exists(chat)
    if not existing:
        await EventSetting.init_for_chat(chat.chat_id)
    existing = await EventSetting.exists(chat)

    kb = build_keyboard(existing)
    await message.answer(
        "✨ Github events settings",
        reply_markup=kb,
    )


@router.callback_query(F.data.startswith("toggle_event:"))
async def toggle_event_setting(callback: CallbackQuery):
    event_type_str = callback.data.split(":")[1]
    event_type = EventType(event_type_str)

    chat = await Chat.get(chat_id=callback.message.chat.id)
    setting = await EventSetting.get_or_none(chat=chat, event_type=event_type)

    if setting:
        setting.enabled = not setting.enabled
        await setting.save()

    updated = await EventSetting.filter(chat=chat)
    kb = build_keyboard(updated)
    await callback.message.edit_reply_markup(reply_markup=kb)
    await callback.answer(
        f"{event_type.value} {'enabled' if setting.enabled else 'disabled'}"
    )
