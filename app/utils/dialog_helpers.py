"""Small helpers for aiogram-dialog handlers."""
from typing import Optional

from aiogram_dialog import DialogManager

from app.db.functions import User


async def current_user_for_manager(manager: DialogManager) -> Optional[User]:
    """Resolve the Telegram user behind the current dialog event into our
    ``User`` row. Returns None if the event has no associated user (e.g.
    channel post)."""
    if manager.event.from_user is None:
        return None
    return await User.get_or_none(telegram_id=manager.event.from_user.id)
