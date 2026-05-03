from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware, Dispatcher
from aiogram.types import Message, TelegramObject
from cachetools import TTLCache

from app.config import Config


class ThrottlingMiddleware(BaseMiddleware):

    def __init__(self, config: Config):
        self.cache: TTLCache[int, None] = TTLCache(
            maxsize=10_000, ttl=config.settings.throttling_rate
        )

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        # Registered on dp.message — runtime always sees a Message.
        if not isinstance(event, Message):
            return await handler(event, data)
        if event.chat.id in self.cache:
            return None
        self.cache[event.chat.id] = None
        return await handler(event, data)


def register_middleware(dp: Dispatcher, config: Config):
    throttling_middleware = ThrottlingMiddleware(config=config)
    dp.message.middleware(throttling_middleware)
