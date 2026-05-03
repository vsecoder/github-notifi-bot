"""``MyChatsSG`` state group + Pydantic ``MyChatsState`` mirror."""
from typing import Optional

from aiogram.fsm.state import State, StatesGroup

from app.utils.dialog_state import DialogState


class MyChatsSG(StatesGroup):
    chats = State()
    chat_detail = State()
    integration_detail = State()
    events = State()


class MyChatsState(DialogState):
    selected_chat_id: Optional[int] = None
    selected_integration_id: Optional[int] = None
