from aiogram import Bot
from aiogram.types import BotCommand, BotCommandScopeChat, BotCommandScopeDefault

from app.config import Config

users_commands = {
    "start": "Start bot / show setup guide",
    "help": "Show setup guide and command reference",
    "integrate": "Integrate a repository (in group)",
    "integrations": "List integrated repositories",
    "delete": "Remove an integration",
    "reinstall": "Re-sync GitHub webhook events for this chat",
    "install": "Install the GitHub App for your account (DM)",
    "token": "Set or replace your GitHub token (DM)",
    "set_topic": "Send notifications to current forum topic",
    "events": "Toggle event types per chat",
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
