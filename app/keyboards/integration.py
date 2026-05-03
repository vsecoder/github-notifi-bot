"""Inline-keyboards and shared text for the in-group ``/integrations`` flow.

Callback-data scheme (consumed by handlers in ``app.handlers.user.integration``):

* ``integ:list``       — back to the list view
* ``integ:open:<id>``  — show management menu for a single integration
* ``integ:del:<id>``   — delete (admin-gated)
* ``integ:events``     — open the ``/events`` keyboard for this chat
"""
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.db.functions import Integration


INTEGRATIONS_HEADER = (
    "<b>Integrations in this chat</b>\n"
    "Tap a repository to manage it, or <b>Manage events</b> to toggle "
    "event types."
)


def build_integrations_keyboard(
    integrations: list[Integration],
) -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(
                text=f"🔌 {i.repository_name}",
                callback_data=f"integ:open:{i.id}",
            )
        ]
        for i in integrations
    ]
    buttons.append(
        [
            InlineKeyboardButton(
                text="✏ Manage events", callback_data="integ:events"
            )
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def build_management_keyboard(integration_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🗑 Delete from chat",
                    callback_data=f"integ:del:{integration_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="« Back", callback_data="integ:list"
                )
            ],
        ]
    )
