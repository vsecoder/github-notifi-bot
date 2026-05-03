"""Shared bits for MyChatsSG window modules."""
from aiogram import Bot
from aiogram_dialog import DialogManager

from app.config import Config


async def get_bot(manager: DialogManager) -> Bot:
    return manager.middleware_data["bot"]


def get_config(manager: DialogManager) -> Config:
    return manager.middleware_data["config"]
