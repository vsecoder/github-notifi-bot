"""My-chats dialog package — overview of where the user has integrations.

Four windows on a single ``MyChatsSG``, one module per window:

* ``chats``              — list of chats grouped by chat_id.
* ``chat_detail``        — chosen chat: integrations as buttons + Manage events.
* ``integration_detail`` — single integration with Delete action.
* ``events``             — toggle event types for the selected chat.
"""
from aiogram_dialog import Dialog

from app.dialogs.my_chats._chat_detail_window import chat_detail_window
from app.dialogs.my_chats._chats_window import chats_window
from app.dialogs.my_chats._events_window import events_window
from app.dialogs.my_chats._integration_detail_window import (
    integration_detail_window,
)
from app.dialogs.my_chats.state import MyChatsSG, MyChatsState


my_chats_dialog = Dialog(
    chats_window,
    chat_detail_window,
    integration_detail_window,
    events_window,
)


__all__ = ["MyChatsSG", "MyChatsState", "my_chats_dialog"]
