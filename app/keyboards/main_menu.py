"""Persistent reply keyboard shown to the user in DM after /start or /help.

Buttons here are the top-level navigation entry points; each one either opens
a dialog or shows a placeholder until the corresponding feature lands.
"""
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

# Button labels are also used as exact-text matchers in dm_menu handlers,
# so import these constants instead of duplicating the strings.
BTN_CONNECT = "🔌 Connect"
BTN_ADD_TO_CHAT = "➕ Add to chat"
BTN_REPOS = "🏢 Repos"
BTN_MY_CHATS = "💬 My chats"
BTN_HELP = "❓ Help"


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text=BTN_CONNECT),
                KeyboardButton(text=BTN_ADD_TO_CHAT),
            ],
            [
                KeyboardButton(text=BTN_REPOS),
                KeyboardButton(text=BTN_MY_CHATS),
            ],
            [KeyboardButton(text=BTN_HELP)],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )
