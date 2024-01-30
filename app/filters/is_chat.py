from aiogram import types
from aiogram.filters import Filter


class IsChat(Filter):
    def __init__(self, is_chat: bool) -> None:
        self.is_chat = is_chat

    async def __call__(self, message: types.Message) -> bool:
        return self.is_chat is (message.from_user.id == message.chat.id)
