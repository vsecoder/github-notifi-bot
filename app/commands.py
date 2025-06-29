from aiogram import Bot
from aiogram.types import BotCommand, BotCommandScopeChat, BotCommandScopeDefault

from app.config import Config

users_commands = {
    "start": "Start bot",
    "integrate": "Integrate repository",
    "integrations": "Show integrated repositories",
    "delete": "Delete integration",
    "token": "Set GitHub token",
    "set_topic": "Set notification topic",
    "events": "Setup chat events",
}


async def setup_bot_commands(bot: Bot, config: Config):
    await bot.set_my_commands(
        [
            BotCommand(command=command, description=description)
            for command, description in users_commands.items()
        ],
        scope=BotCommandScopeDefault(),
    )


async def remove_bot_commands(bot: Bot, config: Config):
    await bot.delete_my_commands(scope=BotCommandScopeDefault())
    await bot.delete_my_commands(
        scope=BotCommandScopeChat(chat_id=config.settings.owner_id)
    )
