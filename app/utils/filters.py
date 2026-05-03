"""Reusable aiogram Magic filter constants.

Use these instead of inline ``F.chat.type == "private"`` checks so the
intent is searchable and consistent across the codebase.
"""
from aiogram import F


# Private chat (DM with the bot).
IS_DM = F.chat.type == "private"

# Group / supergroup / channel — anywhere that isn't a DM.
IS_GROUP_LIKE = F.chat.type.in_({"group", "supergroup", "channel"})
